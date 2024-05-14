import argparse
import json
import logging
import os
from pathlib import Path
from unittest.mock import call, patch

import pytest
from fixtures import DataDir
from translations_parser.cli import experiments as experiments_publish
from translations_parser.cli import taskcluster as tc_publish

"""
Tests tracking parser and publication via CLI entrypoints
"""


@pytest.fixture(scope="function")
def tmp_dir():
    return Path(DataDir("test_tracking").path)


@pytest.fixture(autouse=True)
def disable_wandb(tmp_dir):
    """Prevent publication on W&B"""
    os.environ["WANDB_API_KEY"] = "fake"
    os.environ["WANDB_MODE"] = "offline"
    os.environ["WANDB_DIR"] = str(tmp_dir / "wandb")


@pytest.fixture
def samples_dir():
    return Path(__file__).parent / "data"


@patch(
    "translations_parser.cli.taskcluster.get_args",
    return_value=argparse.Namespace(
        input_file=Path(__file__).parent / "data" / "taskcluster.log",
        loglevel=logging.DEBUG,
        output_dir=Path(DataDir("test_tracking").path),
        from_stream=False,
        wandb_project="test",
        wandb_artifacts=None,
        wandb_group="group",
        wandb_publication=True,
        wandb_run_name="run",
        tags=[
            "unittest",
        ],
        taskcluster_secret=None,
    ),
)
@patch("translations_parser.publishers.wandb")
def test_taskcluster(wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir):
    caplog.set_level(logging.INFO)
    wandb_dir = tmp_dir / "wandb"
    wandb_dir.mkdir(parents=True)
    wandb_mock.init.return_value.dir = wandb_dir
    tc_publish.main()
    assert [(level, message) for _module, level, message in caplog.record_tuples] == [
        (logging.INFO, "Reading logs stream."),
        (logging.INFO, "Detected Marian version 1.10"),
        (logging.INFO, "Successfully parsed 588 lines"),
        (logging.INFO, "Found 102 training entries"),
        (logging.INFO, "Found 34 validation entries"),
    ]
    with (samples_dir / "taskcluster_wandb_calls.json").open("r") as f:
        assert list(wandb_mock.init.return_value.log.call_args_list) == [
            call(**entry) for entry in json.load(f)
        ]


@patch(
    "translations_parser.cli.experiments.get_args",
    return_value=argparse.Namespace(directory=Path(__file__).parent / "data" / "experiments_1_10"),
)
@patch("translations_parser.publishers.wandb")
def test_experiments_marian_1_10(wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir):
    caplog.set_level(logging.INFO)
    wandb_dir = tmp_dir / "wandb"
    wandb_dir.mkdir(parents=True)
    wandb_mock.init.return_value.dir = wandb_dir
    wandb_mock.plot.bar = lambda *args, **kwargs: (args, kwargs)
    wandb_mock.Table = lambda *args, **kwargs: (args, kwargs)
    experiments_publish.main()
    # Assert on a `set` since the logging order may vary between runs.
    assert set([(level, message) for _module, level, message in caplog.record_tuples]) == set(
        [
            (logging.INFO, "Reading 3 train.log data"),
            # student
            (
                logging.INFO,
                f"Parsing folder {samples_dir}/experiments_1_10/models/en-nl/prod/student",
            ),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Detected Marian version 1.10"),
            (logging.INFO, "Successfully parsed 1002 lines"),
            (logging.INFO, "Found 550 training entries"),
            (logging.INFO, "Found 108 validation entries"),
            # teacher-finetuned0
            (
                logging.INFO,
                f"Parsing folder {samples_dir}/experiments_1_10/models/en-nl/prod/teacher-finetuned0",
            ),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Successfully parsed 993 lines"),
            (logging.INFO, "Found 567 training entries"),
            (logging.INFO, "Found 189 validation entries"),
            # teacher-finetuned1
            (
                logging.INFO,
                f"Parsing folder {samples_dir}/experiments_1_10/models/en-nl/prod/teacher-finetuned1",
            ),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Successfully parsed 1000 lines"),
            (logging.INFO, "Found 573 training entries"),
            (logging.INFO, "Found 191 validation entries"),
            # Publish group files and quantized/evaluated metrics
            (
                logging.INFO,
                "Publishing 'en-nl/prod' evaluation metrics and files (fake run 'group_logs')",
            ),
            (logging.INFO, "Found 2 quantized metrics from speed folder"),
            (logging.INFO, "Found 16 metrics from task logs"),
            (logging.INFO, "Creating missing run backward with associated metrics"),
            (logging.INFO, "Creating missing run quantized with associated metrics"),
            (logging.INFO, "Creating missing run student-finetuned with associated metrics"),
            (logging.INFO, "Creating missing run teacher-base0 with associated metrics"),
            (logging.INFO, "Creating missing run teacher-base1 with associated metrics"),
            (logging.INFO, "Creating missing run teacher-ensemble with associated metrics"),
        ]
    )
    log_calls, metrics_calls = [], []
    for log in wandb_mock.init.return_value.log.call_args_list:
        if log.args:
            metrics_calls.append(log)
        elif log.kwargs:
            log_calls.append(log)
    with (samples_dir / "experiments_wandb_calls_1_10.json").open("r") as f:
        assert log_calls == [call(**entry) for entry in json.load(f)]
    # Custom calls for .metrics files publication (3 runs + 6 evaluation metrics)
    assert sorted([list(v.keys())[0] for c in metrics_calls for v in c.args]) == sorted(
        [
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            # This call builds the table with all metrics on the group fake run
            "metrics",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
            "mtdata_Neulab-tedtalks_test-1-eng-nld",
        ]
    )


@patch(
    "translations_parser.cli.experiments.get_args",
    return_value=argparse.Namespace(directory=Path(__file__).parent / "data" / "experiments_1_12"),
)
@patch("translations_parser.publishers.wandb")
def test_experiments_marian_1_12(wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir):
    caplog.set_level(logging.INFO)
    wandb_dir = tmp_dir / "wandb"
    wandb_dir.mkdir(parents=True)
    wandb_mock.init.return_value.dir = wandb_dir
    wandb_mock.plot.bar = lambda *args, **kwargs: (args, kwargs)
    wandb_mock.Table = lambda *args, **kwargs: (args, kwargs)
    experiments_publish.main()
    # Assert on a `set` since the logging order may vary between runs.
    assert set([(level, message) for _module, level, message in caplog.record_tuples]) == set(
        [
            (logging.INFO, "Reading 2 train.log data"),
            (
                logging.INFO,
                f"Parsing folder {samples_dir}/experiments_1_12/models/fi-en/opusprod/student",
            ),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Successfully parsed 786 lines"),
            (logging.INFO, "Found 405 training entries"),
            (logging.INFO, "Found 79 validation entries"),
            (
                logging.INFO,
                f"Parsing folder {samples_dir}/experiments_1_12/models/fi-en/opusprod/student-finetuned",
            ),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Successfully parsed 660 lines"),
            (logging.INFO, "Found 330 training entries"),
            (logging.INFO, "Found 64 validation entries"),
            (
                logging.INFO,
                "Publishing 'fi-en/opusprod' evaluation metrics and files (fake run 'group_logs')",
            ),
            (logging.INFO, "Found 4 quantized metrics from speed folder"),
            (logging.INFO, "Found 8 metrics from task logs"),
            (logging.INFO, "Creating missing run quantized with associated metrics"),
            (logging.INFO, "Detected Marian version 1.12"),
        ]
    )
    log_calls, metrics_calls = [], []
    for log in wandb_mock.init.return_value.log.call_args_list:
        if log.args:
            metrics_calls.append(log)
        elif log.kwargs:
            log_calls.append(log)
    with (samples_dir / "experiments_wandb_calls_1_12.json").open("r") as f:
        assert log_calls == [call(**entry) for entry in json.load(f)]
    # Custom calls for .metrics files publication (3 runs + 6 evaluation metrics)
    assert sorted([list(v.keys())[0] for c in metrics_calls for v in c.args]) == sorted(
        [
            "flores_devtest",
            "flores_devtest",
            "flores_devtest",
            # This call builds the table with all metrics on the group fake run
            "metrics",
            "sacrebleu_wmt15",
            "sacrebleu_wmt15",
            "sacrebleu_wmt15",
            "sacrebleu_wmt17",
            "sacrebleu_wmt17",
            "sacrebleu_wmt17",
            "sacrebleu_wmt19",
            "sacrebleu_wmt19",
            "sacrebleu_wmt19",
        ]
    )


@patch(
    "translations_parser.cli.taskcluster.get_args",
    return_value=argparse.Namespace(
        input_file=Path(__file__).parent / "data" / "taskcluster.log",
        loglevel=logging.DEBUG,
        output_dir=Path(DataDir("test_tracking").path),
        from_stream=False,
        wandb_project="test",
        wandb_artifacts=None,
        wandb_group="group",
        wandb_publication=True,
        wandb_run_name="run",
        tags=[
            "unittest",
        ],
        taskcluster_secret=None,
    ),
)
@patch("translations_parser.publishers.wandb")
def test_taskcluster_wandb_initialization_failure(
    wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir
):
    """
    Ensures tracking continues despite W&B initialization failure
    """
    caplog.set_level(logging.INFO)
    wandb_mock.init.side_effect = Exception("Invalid credentials")
    tc_publish.main()
    assert [(level, message) for _module, level, message in caplog.record_tuples] == [
        (logging.INFO, "Reading logs stream."),
        (logging.INFO, "Detected Marian version 1.10"),
        (
            logging.ERROR,
            "WandB client could not be initialized: Invalid credentials. No data will be published.",
        ),
        (logging.INFO, "Successfully parsed 588 lines"),
        (logging.INFO, "Found 102 training entries"),
        (logging.INFO, "Found 34 validation entries"),
    ]


@patch(
    "translations_parser.cli.taskcluster.get_args",
    return_value=argparse.Namespace(
        input_file=Path(__file__).parent / "data" / "taskcluster.log",
        loglevel=logging.DEBUG,
        output_dir=Path(DataDir("test_tracking").path),
        from_stream=False,
        wandb_project="test",
        wandb_artifacts=None,
        wandb_group="group",
        wandb_publication=True,
        wandb_run_name="run",
        tags=[
            "unittest",
        ],
        taskcluster_secret=None,
    ),
)
@patch("translations_parser.publishers.wandb")
def test_taskcluster_wandb_log_failures(wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir):
    """
    Ensures tracking continues despite potential W&B data log failures
    """
    caplog.set_level(logging.INFO)
    wandb_dir = tmp_dir / "wandb"
    wandb_dir.mkdir(parents=True)
    wandb_mock.init.return_value.dir = wandb_dir
    wandb_mock.init.return_value.log.side_effect = Exception("Unexpected failure")
    tc_publish.main()
    assert [(level, message) for _module, level, message in caplog.record_tuples] == [
        (logging.INFO, "Reading logs stream."),
        (logging.INFO, "Detected Marian version 1.10"),
    ] + [
        (logging.ERROR, "Error publishing training epoch using WandB: Unexpected failure"),
        (logging.ERROR, "Error publishing training epoch using WandB: Unexpected failure"),
        (logging.ERROR, "Error publishing training epoch using WandB: Unexpected failure"),
        (logging.ERROR, "Error publishing validation epoch using WandB: Unexpected failure"),
    ] * 34 + [
        (logging.INFO, "Successfully parsed 588 lines"),
        (logging.INFO, "Found 102 training entries"),
        (logging.INFO, "Found 34 validation entries"),
    ]


@patch(
    "translations_parser.cli.taskcluster.get_args",
    return_value=argparse.Namespace(
        input_file=Path(__file__).parent / "data" / "taskcluster.log",
        loglevel=logging.DEBUG,
        output_dir=Path(DataDir("test_tracking").path),
        from_stream=False,
        wandb_project=None,
        wandb_artifacts=None,
        wandb_group=None,
        wandb_publication=False,
        wandb_run_name="run",
        tags=[
            "unittest",
        ],
        taskcluster_secret=None,
    ),
)
@patch("translations_parser.publishers.wandb")
def test_taskcluster_wandb_disabled(wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir):
    """
    Ensures tracking continues without Weight & Biases publication
    """
    caplog.set_level(logging.INFO)
    tc_publish.main()
    assert [(level, message) for _module, level, message in caplog.record_tuples] == [
        (
            logging.INFO,
            "Skip weight & biases publication as requested by operator through WANDB_PUBLICATION",
        ),
        (logging.INFO, "Reading logs stream."),
        (logging.INFO, "Detected Marian version 1.10"),
        (logging.INFO, "Successfully parsed 588 lines"),
        (logging.INFO, "Found 102 training entries"),
        (logging.INFO, "Found 34 validation entries"),
    ]
