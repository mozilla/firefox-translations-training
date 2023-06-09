# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.parameters import extend_parameters_schema
from voluptuous import Optional, Required

# These defaults line up with the `config.test.yml` pipeline as much as possible.
# Their purpose is to provide a minimal config with a few datasets that can run
# the entire pipeline reasonably quickly to validate changes to the pipeline
# itself. Any real training should be overriding most, if not all, of these
# via the input to the `train` action.
def get_defaults(_):
    return {
        "training_config": {
            "target-stage": "evaluate-backwards",
            "experiment": {
                "src": "ru",
                "trg": "en",
                "bicleaner": {
                    "default-threshold": 0.5,
                    "dataset-thresholds": {
                        "opus_ada83/v1": 0.0,
                        "mtdata_Neulab-tedtalks_train-1-eng-rus": 0.6,
                    },
                },
                "best-model": "chrf",
                "spm-sample-size": 100000,
                "mono-max-sentences-trg": 200000,
                "mono-max-sentences-src": 100000,
            },
            "marian-args": {
                "training-backward": {
                    "disp-freq": "10",
                    "save-freq": "100",
                    "valid-freq": "100",
                    "after": "500u",
                },
            },
            # These will never be used in practice, but specifying them ensures
            # that we always generate at least one task for each kind, which helps
            # to avoid bustage that doesn't show up until we run the training action.
            "datasets": {
                "train": [
                    "opus_ada83/v1",
                    "opus_GNOME/v1",
                    "mtdata_Neulab-tedtalks_train-1-eng-rus",
                ],
                "devtest": [
                    "flores_dev",
                    "sacrebleu_wmt19",
                ],
                "test": [
                    "flores_devtest",
                    "sacrebleu_wmt20",
                ],
                "mono-src": [
                    "news-crawl_news.2020",
                ],
                "mono-trg": [
                    "news-crawl_news.2020",
                ],
            },
        },
    }

extend_parameters_schema(
    {
        Required("training_config"): {
            Required("target-stage"): str,
            Required("marian-args"): {
                Optional("training-backward"): {str: str},
            },
            Required("experiment"): {
                Required("src"): str,
                Required("trg"): str,
                Required("bicleaner"): {
                    Required("default-threshold"): float,
                    Optional("dataset-thresholds"): {
                        str: float,
                    },
                },
                Required("best-model"): str,
                Required("spm-sample-size"): int,
                Required("mono-max-sentences-trg"): int,
                Required("mono-max-sentences-src"): int,
            },
            Optional("bicleaner_threshold"): str,
            Optional("train_vocab_sample_size"): str,
            Optional("datasets"): {
                str: [str],
            },
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
