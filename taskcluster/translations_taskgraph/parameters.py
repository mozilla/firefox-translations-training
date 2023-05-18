# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.parameters import extend_parameters_schema
from voluptuous import Optional

def get_defaults(repo_root):
    return {
        "bicleaner_threshold": "0.0",
        "train_vocab_sample_size": "1000",
        # These will never be used in practice, but specifying them ensures
        # that we always generate at least one task for each kind, which helps
        # to avoid bustage that doesn't show up until we run the training action.
        "datasets": {
            "train": [
                "flores_dev",
                "sacrebleu_wmt19",
            ],
            "devtest": [
                "flores_dev",
                "sacrebleu_wmt19",
            ],
            "test": [
                "flores_dev",
                "sacrebleu_wmt19",
            ],
            "mono-src": [
                "flores_dev",
                "sacrebleu_wmt19",
            ],
            "mono-trg": [
                "flores_dev",
                "sacrebleu_wmt19",
            ],
        },
    }

extend_parameters_schema(
    {
        Optional("bicleaner_threshold"): str,
        Optional("train_vocab_sample_size"): str,
        Optional("datasets"): {
            str: [str],
        },
    },
    defaults_fn=get_defaults,
)

def get_decision_parameters(graph_config, parameters):
    for k, v in get_defaults("").items():
        parameters.setdefault(k, v)
