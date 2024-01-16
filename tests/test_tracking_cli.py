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


@pytest.fixture(autouse=True)
def disable_wandb():
    """Prevent publication on W&B"""
    os.environ["WANDB_API_KEY"] = "fake"
    os.environ["WANDB_MODE"] = "offline"


@pytest.fixture(scope="function")
def tmp_dir():
    return Path(DataDir("test_tracking").path)


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
        wandb_run_name="run",
    ),
)
@patch("translations_parser.publishers.wandb")
def test_taskcluster(wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir):
    caplog.set_level(logging.DEBUG)
    wandb_dir = tmp_dir / "wandb"
    wandb_dir.mkdir(parents=True)
    wandb_mock.init.return_value.dir = wandb_dir
    tc_publish.main()
    assert [(level, message) for _module, level, message in caplog.record_tuples] == [
        (logging.INFO, "Reading logs stream.")
    ] + [
        (
            logging.DEBUG,
            f"Skipping line {i} : Headers does not match the filter",
        )
        for i in [*range(1, 128), 154, 558, 561, 1056, 1059, 1061, 1064, 1066]
    ] + [
        (logging.DEBUG, "Reading Marian version."),
        (logging.DEBUG, "Reading Marian run description."),
        (logging.DEBUG, "Reading Marian configuration."),
    ] + [
        (
            logging.DEBUG,
            f"Skipping line {i} : Headers does not match the filter",
        )
        for i in range(1664, 1691)
    ] + [
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
    return_value=argparse.Namespace(directory=Path(__file__).parent / "data" / "experiments"),
)
@patch("translations_parser.publishers.wandb")
def test_experiments(wandb_mock, getargs_mock, caplog, samples_dir, tmp_dir):
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
                f"Parsing folder {samples_dir}/experiments/models/en-nl/prod/student",
            ),
            (logging.INFO, "Reading metrics file mtdata_Neulab-tedtalks_test-1-eng-nld.metrics"),
            (logging.INFO, "Reading metrics file flores_devtest.metrics"),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Successfully parsed 1002 lines"),
            (logging.INFO, "Found 550 training entries"),
            (logging.INFO, "Found 108 validation entries"),
            # teacher-finetuned0
            (
                logging.INFO,
                f"Parsing folder {samples_dir}/experiments/models/en-nl/prod/teacher-finetuned0",
            ),
            (logging.INFO, "Reading metrics file mtdata_Neulab-tedtalks_test-1-eng-nld.metrics"),
            (logging.INFO, "Reading metrics file flores_devtest.metrics"),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Successfully parsed 993 lines"),
            (logging.INFO, "Found 567 training entries"),
            (logging.INFO, "Found 189 validation entries"),
            # teacher-finetuned1
            (
                logging.INFO,
                f"Parsing folder {samples_dir}/experiments/models/en-nl/prod/teacher-finetuned1",
            ),
            (logging.INFO, "Reading metrics file mtdata_Neulab-tedtalks_test-1-eng-nld.metrics"),
            (logging.INFO, "Reading metrics file flores_devtest.metrics"),
            (logging.INFO, "Reading logs stream."),
            (logging.INFO, "Successfully parsed 1000 lines"),
            (logging.INFO, "Found 573 training entries"),
            (logging.INFO, "Found 191 validation entries"),
            # Group extra logs
            (
                logging.INFO,
                "Publishing 'en-nl' group 'prod' metrics and files to a last fake run 'group_logs'",
            ),
            # Metrics for `speed` directory
            (logging.INFO, "Reading metrics file mtdata_Neulab-tedtalks_test-1-eng-nld.metrics"),
            (logging.INFO, "Reading metrics file flores_devtest.metrics"),
        ]
    )
    log_calls, metrics_calls = [], []
    for log in wandb_mock.init.return_value.log.call_args_list:
        if log.args:
            metrics_calls.append(log)
        elif log.kwargs:
            log_calls.append(log)
    with (samples_dir / "experiments_wandb_calls.json").open("r") as f:
        assert log_calls == [call(**entry) for entry in json.load(f)]
    # Custom calls for .metrics files publication
    assert set([list(v.keys())[0] for c in metrics_calls for v in c.args]) == set(
        [
            "Mtdata_neulab-tedtalks_test-1-eng-nld summary",
            "Flores_devtest summary",
            "Mtdata_neulab-tedtalks_test-1-eng-nld summary",
            "Flores_devtest summary",
            "Mtdata_neulab-tedtalks_test-1-eng-nld summary",
            "Flores_devtest summary",
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
        wandb_run_name="run",
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
        wandb_run_name="run",
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
