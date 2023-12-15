import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Callable

import yaml

from translations_parser.data import TrainingEpoch, TrainingLog, ValidationEpoch
from translations_parser.publishers import Publisher

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

HEADER_RE = re.compile(r"(?<=\[)(?P<value>.+?)\] ")
VALIDATION_RE = re.compile(r"Ep\.[ :]+(?P<ep>\d+)[ :]+Up\.[ :]+(?P<up>\d+)[ :]+(?P<key>[\w-]+)[ :]+(?P<value>[\d\.]+)")
TRAINING_RE = re.compile(
    r"Ep\.[ :]+(?P<epoch>\d+)[ :]+"
    r"Up\.[ :]+(?P<up>\d+)[ :]+"
    r"Sen\.[ :]+(?P<sen>[\d,]+)[ :]+"
    r"Cost[ :]+(?P<cost>[\d.]+)[ :]+"
    r"Time[ :]+(?P<time>[\d\.]+)s[ :]+"
    r"(?P<rate>[\d\.]+) words\/s[ :]+"
    r"gNorm[ :]+(?P<gnorm>[\d\.]+)"
)
# Expected version of Marian for a clean parsing
MARIAN_MAJOR, MARIAN_MINOR = 1, 10


class TrainingParser:
    def __init__(
        self,
        logs_iter: Iterable[str],
        publishers: Sequence[Publisher],
        log_filter: Callable = None,
        skip_marian_context: bool = False,
    ):
        # Iterable reading logs lines
        self.logs_iter = logs_iter
        # Function to exclude log lines depending on the headers
        self.log_filter = log_filter
        self._current_index = 0
        self.parsed = False
        self.config = {}
        self.indexed_logs = defaultdict(list)
        # List of TrainingEpoch
        self.training = []
        # List of ValidationEpoch
        self.validation = []
        # Dict mapping (epoch, up) to values parsed on multiple lines
        self._validation_entries = defaultdict(dict)
        # Option to read logs directly (skip check for Marian context)
        self.skip_marian_context = skip_marian_context
        # Marian exection data
        self.version = None
        self.version_hash = None
        self.release_date = None
        self.run_date = None
        self.description = None
        # Data publication after parsing logs
        self.publishers = publishers

    def get_headers(self, line):
        """
        Returns a list of tuples representing the headers of a log line
        and the position of the last index
        """
        matches = list(HEADER_RE.finditer(line))
        if not matches:
            return ((), None)
        return ([tuple(m.group("value").split()) for m in matches], matches[-1].span()[-1])

    def get_timestamp(self, headers):
        """
        Look for a timestamp in header tags.
        Returns the timestamp if found, None otherwise.
        """
        for values in headers:
            if len(values) != 2:
                continue
            base, timestamp = values
            # TC adds a timestamp after the task header
            if base == "task":
                try:
                    return datetime.fromisoformat(timestamp.rstrip("Z"))
                except ValueError:
                    pass
            # Marian timestamp is composed of two values, one for date and one for hour precision
            try:
                return datetime.fromisoformat("T".join(values))
            except ValueError:
                pass

    def parse_training_log(self, headers, text):
        match = TRAINING_RE.match(text)
        if not match:
            return
        values = match.groupdict()
        # Update sen value from 1,234,567 to 1_234_567 that Python interprets
        values["sen"] = values["sen"].replace(",", "_")
        # Transform values to match output types
        values = {k: TrainingEpoch.__annotations__[k](v) for k, v in values.items()}
        training_epoch = TrainingEpoch(**values)
        self.training.append(training_epoch)
        for publisher in self.publishers:
            try:
                publisher.handle_training(training_epoch)
            except Exception as e:
                logger.error(f"Error publishing training epoch using {publisher.__class__.__name__}: {e}")
        return training_epoch

    def parse_validation_log(self, headers, text):
        if ("valid",) not in headers or not (match := VALIDATION_RE.match(text)):
            return
        epoch, up, key, val = match.groups()
        # Replace items keys to match ValidationEpoch dataclass
        key = key.replace("-", "_")
        # Transform values to match output types
        epoch, up = int(epoch), int(up)
        val = ValidationEpoch.__annotations__[key](val)
        entry = self._validation_entries[(epoch, up)]
        entry[key] = val
        # Build a validation epochs from multiple lines
        if not (set(("chrf", "ce_mean_words", "bleu_detok")) - set(entry.keys())):
            validation_epoch = ValidationEpoch(epoch=epoch, up=up, **entry)
            self.validation.append(validation_epoch)
            for publisher in self.publishers:
                try:
                    publisher.handle_validation(validation_epoch)
                except Exception as e:
                    logger.error(f"Error publishing validation epoch using {publisher.__class__.__name__}: {e}")
            del self._validation_entries[(epoch, up)]
            return validation_epoch

    def _iter_log_entries(self):
        for line in self.logs_iter:
            self._current_index += 1
            headers, position = self.get_headers(line)
            if self.log_filter and not self.log_filter(headers):
                logger.debug(f"Skipping line {self._current_index} : Headers does not match the filter")
                continue
            elif self.run_date is None:
                # Try to fill run date from log headers
                self.run_date = self.get_timestamp(headers)
            text = line[position:]

            # Record logs depending on Marian headers
            if len(headers) >= 2:
                # First is task timestamp, second is marian timestamp
                _, _, *marian_tags = headers
                tag = "_".join(*marian_tags) if marian_tags else "_"
                self.indexed_logs[tag].append(text)

            yield headers, text

    def _parse(self):
        if self.parsed:
            raise Exception("The parser already ran.")
        logs_iter = self._iter_log_entries()

        logger.info("Reading logs stream.")
        if self.skip_marian_context:
            headers, text = next(logs_iter)
        else:
            # Consume first lines until we get the Marian header
            headers = []
            while ("marian",) not in headers:
                headers, text = next(logs_iter)

            logger.debug("Reading Marian version.")
            _, version, self.version_hash, self.release_date, *_ = text.split()
            self.version = version.rstrip(";")
            major, minor = map(int, version.lstrip("v").split(".")[:2])
            if (major, minor) > (MARIAN_MAJOR, MARIAN_MINOR):
                logger.warning(
                    f"Parsing logs from a newer version of Marian ({major}.{minor} > {MARIAN_MAJOR}.{MARIAN_MINOR})"
                )

            logger.debug("Reading Marian run description.")
            desc = []
            for headers, text in logs_iter:
                if ("marian",) not in headers:
                    break
                desc.append(text)
            self.description = " ".join(desc)

            # Try to parse all following config lines as YAML
            logger.debug("Reading Marian configuration.")
            config_yaml = ""
            while ("config",) in headers:
                if "Model is being created" in text:
                    headers, text = next(logs_iter)
                    break
                config_yaml += f"{text}\n"
                headers, text = next(logs_iter)
            try:
                self.config = yaml.safe_load(config_yaml)
            except Exception as e:
                raise Exception(f"Invalid config section: {e}")

        # Iterate until the end of file to find training or validation logs
        for publisher in self.publishers:
            publisher.open(self)
        while True:
            try:
                try:
                    training = self.parse_training_log(headers, text)
                    if not training:
                        self.parse_validation_log(headers, text)
                except ValueError as e:
                    logger.warning(f"Line {self._current_index} could not be stored: {e}.")
                finally:
                    headers, text = next(logs_iter)
            except StopIteration:
                break

        # Report incomplete validation logs
        if self._validation_entries.keys():
            logger.warning("Some validation data is incomplete with the following epoch/up couples:")
            for epoch, up in self._validation_entries.keys():
                logger.warning(f"* Ep. {epoch}, Up. {up}")

        self.parsed = True

    @property
    def logs_str(self):
        return "\n".join("".join(f"[{key}] {val}\n" for val in values) for key, values in self.indexed_logs.items())

    @property
    def output(self):
        if not self.parsed:
            raise Exception("Please run the parser before reading the output")
        return TrainingLog(
            run_date=self.run_date,
            configuration=self.config,
            training=self.training,
            validation=list(self.validation),
            logs=self.indexed_logs,
        )

    def run(self):
        """
        Parse the log lines.
        """
        try:
            self._parse()
        except StopIteration:
            # A StopIteration can be raised if some required lines are never found.
            raise ValueError("Logs file ended up unexpectedly")

        count = sum(len(vals) for vals in self.indexed_logs.values())
        logger.info(f"Successfully parsed {count} lines")
        logger.info(f"Found {len(self.training)} training entries")
        logger.info(f"Found {len(self.validation)} validation entries")

        for publisher in self.publishers:
            try:
                publisher.publish(self.output)
            except Exception as e:
                logger.error(f"Error publishing data using {publisher.__class__.__name__}: {e}")
            finally:
                publisher.close()
