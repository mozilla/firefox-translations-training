import os
from unittest import mock

import pytest
import train_taskcluster

TRAIN_TASKCLUSTER_SH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "taskcluster",
        "scripts",
        "pipeline",
        "train-taskcluster.sh",
    )
)


@pytest.mark.parametrize(
    "args",
    (
        pytest.param(
            [
                "model_type",
                "type",
                "src",
                "trg",
                "train_set_prefix",
                "valid_set_prefix",
                "model_dir",
                "best_model_metric",
                "alignments",
                "seed",
            ],
            id="required_only",
        ),
        pytest.param(
            [
                "model_type",
                "type",
                "src",
                "trg",
                "train_set_prefix",
                "valid_set_prefix",
                "model_dir",
                "best_model_metric",
                "alignments",
                "seed",
                "pretrained_model_mode",
                "pretrained_model_type",
            ],
            id="with_pretrained_model",
        ),
        pytest.param(
            [
                "model_type",
                "type",
                "src",
                "trg",
                "train_set_prefix",
                "valid_set_prefix",
                "model_dir",
                "best_model_metric",
                "alignments",
                "seed",
                "pretrained_model_mode",
                "pretrained_model_type",
                "--foo",
                "--bar",
            ],
            id="with_extra_params",
        ),
    ),
)
def test_all_args_forwarded(args):
    with mock.patch("train_taskcluster.subprocess") as mocked_subprocess:
        train_taskcluster.main(args)
        assert mocked_subprocess.run.call_args_list == [
            mock.call([TRAIN_TASKCLUSTER_SH] + args, check=True),
        ]
