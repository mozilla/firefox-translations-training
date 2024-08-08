# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.parameters import extend_parameters_schema
from voluptuous import Extra, Optional, Required


# These defaults line up with the `config.ci.yml` pipeline as much as possible.
# Their purpose is to provide a minimal config with a few datasets that can run
# the entire pipeline reasonably quickly to validate changes to the pipeline
# itself. Any real training should be overriding most, if not all, of these
# via the input to the `train` action.
def get_defaults(_) -> dict:
    return {
        "training_config": {
            "target-stage": "all",
            "experiment": {
                "name": "ci",
                "src": "ru",
                "trg": "en",
                "teacher-ensemble": 1,
                "teacher-mode": "two-stage",
                "mono-max-sentences-trg": {"total": 10000, "per-dataset": 10000},
                "mono-max-sentences-src": {"total": 10000, "per-dataset": 10000},
                "spm-sample-size": 10000,
                "spm-vocab-size": 1000,
                "best-model": "chrf",
                "use-opuscleaner": "true",
                "opuscleaner-mode": "custom",
                "bicleaner": {
                    "default-threshold": 0.5,
                    "dataset-thresholds": {
                        "opus_ada83/v1": 0.0,
                        "opus_ELRC-3075-wikipedia_health/v1": 0.6,
                    },
                },
            },
            "marian-args": {
                "training-backward": {
                    "disp-freq": "2",
                    "save-freq": "25",
                    "valid-freq": "50",
                    "after": "50u",
                    "dim-vocabs": "1000 1000",
                },
                "training-teacher": {
                    "disp-freq": "1",
                    "save-freq": "25",
                    "valid-freq": "50",
                    "after": "50u",
                    "dim-vocabs": "1000 1000",
                    "task": "transformer-base",
                },
                "training-student": {
                    "disp-freq": "1",
                    "save-freq": "25",
                    "valid-freq": "50",
                    "after": "50u",
                    "dim-vocabs": "1000 1000",
                },
                "training-student-finetuned": {
                    "disp-freq": "1",
                    "save-freq": "25",
                    "valid-freq": "50",
                    "after": "50u",
                    "dim-vocabs": "1000 1000",
                },
                "decoding-backward": {
                    "mini-batch-words": "2000",
                },
                "decoding-teacher": {
                    "mini-batch-words": "1000",
                    "precision": "float16",
                },
            },
            # These will never be used in practice, but specifying them ensures
            # that we always generate at least one task for each kind, which helps
            # to avoid bustage that doesn't show up until we run the training action.
            "datasets": {
                "train": [
                    "opus_ada83/v1",
                    "opus_ELRC-3075-wikipedia_health/v1",
                    "url_https://storage.googleapis.com/releng-translations-dev/data/en-ru/pytest-dataset.[LANG].zst",
                    "mtdata_ELRC-web_acquired_data_related_to_scientific_research-1-eng-rus",
                ],
                "devtest": [
                    "flores_dev",
                    "sacrebleu_aug-upper_wmt19",
                ],
                "test": [
                    "flores_devtest",
                ],
                "mono-src": [
                    "news-crawl_news.2008",
                ],
                "mono-trg": [
                    "news-crawl_news.2007",
                ],
            },
            # Taskcluster-specific configuration
            "taskcluster": {
                "split-chunks": 2,
                "worker-classes": {
                    "default": "gcp-spot",
                },
            },
            # Disable Weight & Biases publication on CI
            "wandb-publication": False,
        },
    }


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
    defaults_fn=get_defaults,
)


def deep_setdefault(dict_, defaults):
    for k, v in defaults.items():
        if isinstance(dict_.get(k), dict):
            deep_setdefault(dict_[k], defaults[k])
        else:
            dict_[k] = v


def get_decision_parameters(graph_config, parameters):
    parameters.setdefault("training_config", {})
    deep_setdefault(parameters, get_defaults(""))
