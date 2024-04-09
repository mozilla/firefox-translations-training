#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# https://github.com/marian-nmt/marian-tensorboard/blob/main/src/marian_tensorboard/marian_tensorboard.py
# fix the fixed regex to parse logs without learning rate reporting

import argparse
import calendar
import logging
import os
import pickle
import re
import signal
import sys
import threading
import time

from functools import reduce
from pathlib import Path


def get_marian_tensorboard_version():
    """Returns package version"""
    variables = {}
    file_path = Path(__file__).parent / "version.py"
    with open(file_path, "r", encoding="utf8") as file_io:
        exec(file_io.read(), variables)
    return variables["__version__"]


try:
    from .version import __version__ as VERSION
except ImportError:
    # Extract the version number from the file as a backup - the relative
    # import will not work when calling the script directly during development.
    # Note that adding the script directory to PYTHONPATH and importing version
    # as a module breaks launching TensorBoard server. TODO: debug and fix
    VERSION = "0.2.1"

# Monitoring for updates in log files every this number of seconds. Note that
# it also determines length of gentle script exit
UPDATE_FREQ = 10

# Use the number of batch "updates" as the step statistic (x-Axis) in tensorboard.
# Other options are "sentences" and "labels".
UPDATE_STEP = "updates"

# Setup logger suppressing logging from external modules
logger = logging.getLogger("marian-tensorboard")
logging.basicConfig(level=logging.ERROR)


class LogFileReader(object):
    """Reader for log files in a text format."""

    def __init__(self, path, workdir):
        self.log_file = Path(path)
        if workdir:
            self.state_file = Path(workdir) / "state.pkl"
            if not Path(workdir).exists():
                Path(workdir).mkdir(parents=True, exist_ok=True)
        else:
            self.state_file = None
        self.last_update = 0
        self.last_line = 0

        self._load_state()

        logger.info(
            f"Log file {self.log_file} "
            + f"last updated at {self.last_update}, "
            + f"previously processed lines: {self.last_line}"
        )

    def read(self):
        """Reads new lines added since the last read."""
        if not self._need_update():
            logger.debug(f"No need to update {self.log_file}")
            return
        with open(self.log_file, "r", encoding="utf-8") as logs:
            for line_no, line in enumerate(logs):
                if self.last_line and self.last_line < line_no:
                    yield line
                if line_no > self.last_line:
                    self.last_line = line_no
                if self.log_file.stat().st_mtime > self.last_update:
                    self.last_update = self.log_file.stat().st_mtime
            self._save_state()

    def _load_state(self):
        if Path(self.state_file).exists():
            with open(self.state_file, "rb") as fstate:
                self.last_update, self.last_line = pickle.load(fstate)

    def _save_state(self):
        with open(self.state_file, "wb") as fstate:
            pickle.dump((self.last_update, self.last_line), fstate)

    def _need_update(self):
        # logger.debug(f"Last update: {self.last_update}, last touch: {self.log_file.stat().st_mtime}")
        if self.last_update > 0 and self.last_update >= self.log_file.stat().st_mtime:
            return False
        return True


class MarianLogParser(object):
    """Parser for Marian logs."""

    def __init__(self, step="updates"):
        self.train_re = re.compile(
            r"Ep\.[\s]+(?P<epoch>[\d.]+)[\s]+:[\s]"  # Ep. 1.234 :
            r"Up\.[\s](?P<updates>[\d]+)[\s]+:[\s]"  # Up. 1234 :
            r"Sen\.[\s](?P<sentences>[0-9|,]+).*?"  # Sen. 1,234,567 :
            r"(?P<metric>[A-z|-]+)[\s]+(?P<value>[\d\.]+)(?: \* (?P<disp_labels>[\d,]+) \@ (?P<batch_labels>[\d,]+) after (?P<total_labels>[\d,]+))?.*?"
            # Cost 0.14988677 * 24,252,140 @ 4,877,125 after 211,752,292,869
            r"(?P<wordspersecond>[\d\.]+) words/s.*?"  #
            r"(?P<gradientnorm>[\d\.]+)"  #
            r"( :.*?L\.r\.[\s](?P<learnrate>[\d\.]+e-[\d]+))?"  # L.r. 1.234-05
        )
        self.valid_re = re.compile(
            r"\[valid\][\s]+"
            r"Ep\.[\s]+(?P<epoch>[\d.]+)[\s]+:[\s]"
            r"Up\.[\s](?P<updates>[\d]+).*?"
            r"(?P<metric>[a-z|-]+)[\s]+:[\s]+(?P<value>[\d\.]+)([\s]+:[\s]stalled[\s](?P<stalled>[\d]+))?"
        )
        self.config_re = re.compile(
            r"\[config\].*?(?P<config_name>[A-z|-]+):[\s]+(?P<config_value>[\d\.|A-z]+)"
        )

        self.step = step
        self.last_step = 0

    def parse_line(self, line):
        """
        Parses a log line and returns tuple(s) of (time, update, metric, value).
        """
        m = self.config_re.search(line)
        if m:
            config_name = m.group("config_name")
            config_value = m.group("config_value")
            yield ("text", None, None, config_name, config_value)

        m = self.valid_re.search(line)
        if m:
            _date, _time, *rest = line.split()
            epoch = float(m.group("epoch"))
            update = int(m.group("updates"))
            metric = m.group("metric")
            value = float(m.group("value"))
            stalled = int(m.group("stalled") or 0)

            if self.step == "updates":
                self.last_step = update

            yield (
                "scalar",
                self.wall_time(_date + " " + _time),
                self.last_step,
                f"valid/{metric}",
                value,
            )
            yield (
                "scalar",
                self.wall_time(_date + " " + _time),
                self.last_step,
                f"valid/{metric}_stalled",
                stalled,
            )

        m = self.train_re.search(line)
        if m:
            _date, _time, *rest = line.split()
            epoch = float(m.group("epoch"))
            total_updates = int(m.group("updates"))
            total_sentences = self._get_group_num(m, "sentences")

            metric = m.group("metric")
            value = float(m.group("value"))
            batch_labels = self._get_group_num(m, "batch_labels")
            total_labels = self._get_group_num(m, "total_labels")

            wps = float(m.group("wordspersecond"))
            gradient_norm = float(m.group("gradientnorm"))
            if "learnrate" in m.groupdict() and m.group("learnrate"):
                learnrate = float(m.group("learnrate"))
            else:
                learnrate = 0.0

            if self.step == "updates":
                self.last_step = total_updates or 0
            elif self.step == "sentences":
                self.last_step = total_sentences or 0
            elif self.step == "labels":
                self.last_step = total_labels or 0
            else:
                self.step = total_updates

            yield (
                "scalar",
                self.wall_time(_date + " " + _time),
                self.last_step,
                "train/epoch",
                epoch,
            )
            yield (
                "scalar",
                self.wall_time(_date + " " + _time),
                self.last_step,
                f"train/{metric}",
                value,
            )
            if batch_labels is not None:
                yield (
                    "scalar",
                    self.wall_time(_date + " " + _time),
                    self.last_step,
                    f"train/effective_batch_size",
                    batch_labels,
                )

            if self.step != "updates":
                yield (
                    "scalar",
                    self.wall_time(_date + " " + _time),
                    self.last_step,
                    f"train/total_updates",
                    total_updates,
                )
            if self.step != "sentences" and total_sentences is not None:
                yield (
                    "scalar",
                    self.wall_time(_date + " " + _time),
                    self.last_step,
                    f"train/total_sentences",
                    total_sentences,
                )
            if self.step != "labels" and total_labels is not None:
                yield (
                    "scalar",
                    self.wall_time(_date + " " + _time),
                    self.last_step,
                    f"train/total_labels",
                    total_labels,
                )

            yield (
                "scalar",
                self.wall_time(_date + " " + _time),
                self.last_step,
                f"train/learning_rate",
                learnrate,
            )
            yield (
                "scalar",
                self.wall_time(_date + " " + _time),
                self.last_step,
                f"train/gradient_norm",
                gradient_norm,
            )
            yield (
                "scalar",
                self.wall_time(_date + " " + _time),
                self.last_step,
                f"train/words_per_second",
                wps,
            )

    def wall_time(self, string):
        """Converts timestamp string into strptime. Strips brackets if necessary."""
        if string.startswith("["):
            string = string[1:]
        if string.endswith("]"):
            string = string[:-1]
        return calendar.timegm(time.strptime(string, "%Y-%m-%d %H:%M:%S"))

    def reset(self):
        """Resets the internal state of the parser. Used for unit testing."""
        self.last_step = 0

    def _get_group_num(self, m, group_name, cast_to=int):
        """Returns numerical value from a named group or None"""
        if not m or group_name not in m.groupdict() or m.group(group_name) is None:
            return None
        return cast_to(str(m.group(group_name)).replace(",", ""))


class LogWriter(object):
    """Template class for logging writers."""

    def write(self, type, time, update, metric, value):
        raise NotImplemented


class TensorboardWriter(LogWriter):
    """Writing logs for TensorBoard using TensorboardX."""

    def __init__(self, path):
        import tensorboardX as tbx

        self.writer = tbx.SummaryWriter(path)
        logger.info(f"Exporting to Tensorboard directory: {path}")

    def write(self, type, time, update, metric, value):
        if type == "scalar":
            self.writer.add_scalar(metric, value, update, time)
        elif type == "text":
            self.writer.add_text(metric, value)
        else:
            raise NotImplemented


class AzureMLMetricsWriter(LogWriter):
    """Writing logs for Azure ML metrics."""

    def __init__(self):
        from azureml.core import Run

        logger.info("Logging to Azure ML Metrics...")
        self.writer = Run.get_context()

    def write(self, type, time, update, metric, value):
        if type == "scalar":
            self.writer.log_row(metric, x=update, y=value)
        else:
            pass


class MLFlowTrackingWriter(LogWriter):
    """Writing logs for MLflow Tracking."""

    def __init__(self):
        import mlflow

        self.run_id = None
        logger.info("Autologging to MLflow...")
        try:
            mlflow.autolog()
            self.run_id = mlflow.active_run().info.run_id
            logger.info(f"MLflow RunID: {run_id}")
        except:
            logger.warning("Could not autolog or extract MLflow run ID")

    def write(self, type, time, update, metric, value):
        if not self.run_id:
            return
        if type == "scalar":
            mlflow.log_metric(metric, value, step=update)
        elif type == "text":
            mlflow.log_param(metric, value)
        else:
            pass


class ConversionJob(threading.Thread):
    """Job connecting logging readers and writers in a subthread."""

    def __init__(
        self,
        log_file,
        work_dir,
        update_freq=5,
        step="updates",
        tb=True,
        azureml=False,
        mlflow=False,
    ):
        threading.Thread.__init__(self)

        # The shutdown_flag is a threading.Event object that
        # indicates whether the thread should be terminated.
        self.shutdown_flag = threading.Event()

        self.log_file = Path(log_file)
        self.work_dir = Path(work_dir)
        self.update_freq = update_freq
        self.step = step

        self.tb = tb
        self.azureml = azureml
        self.mlflow = mlflow

    def run(self):
        """Runs the convertion job."""
        logger = logging.getLogger("marian-tensorboard")
        logger.debug(f"Thread #{self.ident} handling {self.log_file} started")

        log_dir = self.work_dir / self._abs_path_to_dir_name(self.log_file)
        reader = LogFileReader(path=self.log_file, workdir=log_dir)
        parser = MarianLogParser(step=self.step)

        writers = []
        if self.tb:
            writers.append(TensorboardWriter(log_dir))
        if self.azureml:
            writers.append(AzureMLMetricsWriter())
        if self.mlflow:
            writers.append(MLFlowTrackingWriter())

        first = True
        while not self.shutdown_flag.is_set():
            if first:
                logger.info(f"Processing logs for {self.log_file}")

            for line_no, line in enumerate(reader.read()):
                for log_tuple in parser.parse_line(line):
                    logger.debug(f"{self.log_file}:{line_no} produced {log_tuple}")
                    for writer in writers:
                        writer.write(*log_tuple)

            if first:
                logger.info(f"Finished processing logs for {self.log_file}")

            if self.update_freq == 0:  # just a single iteration if requested
                break

            if first:
                logger.info(
                    f"Monitoring {self.log_file} for updates every {self.update_freq}s"
                )

            time.sleep(self.update_freq)
            first = False

        logger.debug(f"Thread #{self.ident} stopped")

    def _abs_path_to_dir_name(self, path):
        normalizations = {"/": "__", "\\": "__", " ": ""}
        tmp_path = str(Path(path).resolve().with_suffix(""))
        nrm_path = reduce(
            lambda x, y: x.replace(y[0], y[1]), normalizations.items(), tmp_path
        )
        logger.debug(f"Normalized '{path}' to '{nrm_path}'")
        return nrm_path


class ServiceExit(Exception):
    """Custom exception for signal handling."""

    pass


def main():
    args = parse_user_args()

    logger.info(f"Enabled tools: {', '.join(args.tool)}")

    # Setup signal handling
    def service_shutdown(signum, frame):
        raise ServiceExit

    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)

    # Create working directory if it does not exist
    if not Path(args.work_dir).exists():
        logger.warning(f"The directory '{args.work_dir}' does not exists, creating...")
        try:
            Path(args.work_dir).mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.error(f"Insufficient permission to create {args.work_dir}")
            sys.exit(os.EX_OSFILE)

    try:
        # Create a convertion job for each log file
        jobs = []
        for log_file in args.log_file:
            if not Path(log_file).exists():
                logger.error(f"Log file not found: {log_file}")
                raise FileNotFoundError

            # --offline simply means that the log file is not monitored for updates,
            # so it is equivalent to --update-freq 0
            update_freq = 0 if args.offline else args.update_freq

            job = ConversionJob(
                log_file,
                args.work_dir,
                update_freq,
                args.step,
                tb="tb" in args.tool,
                azureml="azureml" in args.tool,
                mlflow="mlflow" in args.tool,
            )
            job.start()
            jobs.append(job)

        if args.offline:
            for job in jobs:
                job.join()
            logger.info("Done")

        # --offline simply means that the log file is not monitored for updates,
        # but the TensorBoard server still can be started for the user
        if "tb" in args.tool:
            if args.port > 0:
                logger.info("Starting TensorBoard server...")
                launch_tensorboard(args.work_dir, args.port)  # Start teansorboard
                logger.info(f"Serving TensorBoard at https://localhost:{args.port}/")
            else:
                logger.info(
                    "Not starting a local TensorBoard server. Logs are still generated"
                )

        while True:  # Keep the main thread running so that signals are not ignored
            time.sleep(0.5)

    except ServiceExit:
        logger.info("Exiting... it may take a few seconds")
        for job in jobs:
            job.shutdown_flag.set()
        for job in jobs:
            job.join()

    except FileNotFoundError:
        sys.exit(os.EX_NOINPUT)

    logger.info("Done")


def launch_tensorboard(logdir, port):
    """Launches TensorBoard server."""
    import tensorboard as tb

    tb_server = tb.program.TensorBoard()
    tb_server.configure(argv=[None, "--logdir", str(logdir), "--port", str(port)])
    tb_server.launch()


def parse_user_args():
    """Defines and parses user command line options."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--log-file",
        nargs="+",
        help="path to train.log files/directory",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--tool",
        nargs="+",
        help="set visualization tools: tb, azureml, default: tb",
        # Note that "mlflow" is not yet fully supported
        choices=["tb", "azureml"],
    )
    parser.add_argument(
        "-w", "--work-dir", help="TensorBoard logging directory, default: logdir"
    )
    parser.add_argument(
        "-p",
        "--port",
        help="port number for TensorBoard, default: %(default)s",
        type=int,
        default=6006,
    )
    parser.add_argument(
        "-s",
        "--step",
        help="chose which stat to use for tensorboard step (updates, sentences, labels), default: %(default)s",
        choices=["updates", "sentences", "labels"],
        default=UPDATE_STEP,
    )
    parser.add_argument(
        "-u",
        "--update-freq",
        help="update frequency in seconds, default: %(default)s",
        type=int,
        default=UPDATE_FREQ,
    )
    parser.add_argument(
        "--offline",
        help="do not monitor for log updates, overwrites --update-freq",
        action="store_true",
    )
    parser.add_argument("--debug", help="print debug messages", action="store_true")
    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(VERSION)
    )
    args = parser.parse_args()

    # Set logging level
    logging.getLogger("marian-tensorboard").setLevel(
        logging.DEBUG if args.debug else logging.INFO
    )

    # Case breakdown:
    # 1. '-t' not provided, AzureML not detected
    #   => changing to '-t tb'
    # 2. '-t' not provided, AzureML detected
    #   => changing to '-t tb azureml'
    # 3. provided '-t tb', AzureML not detected
    #   => no changes
    # 4. provided '-t tb', AzureML detected
    #   => changing to '-t tb azureml -p 0'
    # 5. provided '-t tb azureml', AzureML not detected
    #   => changing to `-t tb`, warning for AzureML
    # 6. provided '-t tb azureml', AzureML detected
    #   => no changes
    # 7. provided '-t azureml', AzureML not detected
    #   => warning for AzureML, exception
    # 8. provided '-t azureml', AzureML detected
    #   => no changes

    tools_set = args.tool != None

    # Add azureml automatically if running on Azure ML and no tools were
    # specified in command-line arguments
    azureml_run_id = os.getenv("AZUREML_RUN_ID", None)
    if azureml_run_id and not tools_set:
        args.tool = ["azureml"]
        # Do not start the server on Azure ML if automatically detected
        args.port = 0

    if args.tool is None:
        args.tool = []

    if "azureml" in args.tool or "mlflow" in args.tool:
        # Try to set TensorBoard logdir to the one set on Azure ML
        if not args.work_dir:
            args.work_dir = os.getenv("AZUREML_TB_PATH", None)
        if not args.work_dir:
            args.work_dir = "/tb_logs"

        if azureml_run_id:
            logger.info(f"AzureML RunID: {azureml_run_id}")
            logger.info(f"AzureML Setting TensorBoard logdir: {args.work_dir}")
        else:
            logger.warning(
                "AzureML run ID not found in the 'AZUREML_RUN_ID' envvar, "
                "logging to AzureML is disabled"
            )
            args.tool = [t for t in args.tool if t != 'azureml']

            # `-t azureml` was set, but AzureML cannot be detected
            if tools_set and len(args.tool) == 0:
                logger.error(
                    "Could not log into AzureML, but it was the only tool selected, exit"
                )
                sys.exit(os.EX_UNAVAILABLE)

    # If none tool was specified in arguments, add TensorBoard regardless if
    # Azure ML was detected or not
    if not tools_set:
        args.tool.append("tb")

    # Set default value for --work-dir
    if not args.work_dir:
        args.work_dir = "logdir"

    # Make it a set for convenience
    args.tool = set([name.lower() for name in args.tool])
    return args


if __name__ == "__main__":
    main()
