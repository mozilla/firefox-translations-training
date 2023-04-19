# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.parameters import extend_parameters_schema
from voluptuous import Optional

def get_defaults(repo_root):
    return {
        "bicleaner_threshold": "0.0",
    }

extend_parameters_schema(
    {
        Optional("bicleaner_threshold"): str,
    },
    defaults_fn=get_defaults,
)

def get_decision_parameters(graph_config, parameters):
    for k, v in get_defaults("").items():
        if k not in parameters:
            parameters[k] = v
