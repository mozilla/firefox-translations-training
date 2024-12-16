# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pathlib import Path
from taskgraph.parameters import extend_parameters_schema
from voluptuous import Extra, Optional, Required
import yaml


# By default, provide a very minimal config for CI that runs very quickly. This allows
# the pipeline to be validated in CI. The production training configs should override
# all of these values.
def get_ci_training_config(_=None) -> dict:
    vcs_path = (Path(__file__).parent / "../..").resolve()
    config_path = vcs_path / "taskcluster/configs/config.ci.yml"

    with config_path.open() as file:
        return {"training_config": yaml.safe_load(file)}


extend_parameters_schema(
    {
        Required("training_config"): {
            Required("target-stage"): str,
            Required("marian-args"): {
                Optional("training-backward"): {str: str},
                Optional("training-teacher"): {str: str},
                Optional("training-student"): {str: str},
                Optional("training-student-finetuned"): {str: str},
                Optional("decoding-backward"): {str: str},
                Optional("decoding-teacher"): {str: str},
            },
            Required("experiment"): {
                Required("name"): str,
                Required("src"): str,
                Required("trg"): str,
                Required("teacher-ensemble"): int,
                Required("teacher-mode"): str,
                Required("teacher-decoder"): str,
                Required("student-model"): str,
                Optional("corpus-max-sentences"): int,
                Required("mono-max-sentences-trg"): {
                    Required("total"): int,
                    Required("per-dataset"): int,
                },
                Required("mono-max-sentences-src"): {
                    Required("total"): int,
                    Required("per-dataset"): int,
                },
                Required("spm-sample-size"): int,
                Optional("spm-vocab-size"): int,
                Required("best-model"): str,
                Required("use-opuscleaner"): str,
                Optional("opuscleaner-mode"): str,
                Required("bicleaner"): {
                    Required("default-threshold"): float,
                    Optional("dataset-thresholds"): {
                        str: float,
                    },
                },
                Required("min-fluency-threshold"): {
                    Required("mono-src"): float,
                    Required("mono-trg"): float,
                },
                Optional("pretrained-models"): {
                    Optional("train-teacher"): {
                        Required("urls"): [str],
                        Required("mode"): str,
                        Required("type"): str,
                    },
                    Optional("train-backwards"): {
                        Required("urls"): [str],
                        Required("mode"): str,
                        Required("type"): str,
                    },
                },
            },
            Optional("datasets"): {
                str: [str],
            },
            Optional("taskcluster"): {
                Optional("split-chunks"): int,
                Required("worker-classes"): {
                    Required("default"): str,
                    Extra: str,
                },
            },
            Optional("wandb-publication"): bool,
        },
    },
    defaults_fn=get_ci_training_config,
)


def deep_setdefault(dict_, defaults):
    for k, v in defaults.items():
        if isinstance(dict_.get(k), dict):
            deep_setdefault(dict_[k], defaults[k])
        else:
            dict_[k] = v


def get_decision_parameters(graph_config, parameters):
    parameters.setdefault("training_config", {})
    deep_setdefault(parameters, get_ci_training_config())
