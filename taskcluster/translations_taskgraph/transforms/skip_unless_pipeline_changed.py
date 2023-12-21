# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This transform sequence will remove all jobs unless at least one pipeline
# impacting thing (a pipeline script or relevant Taskcluster code) has changed
# (This is done with the `files_changed` helper, which uses data in the
# parameters to determine files changed between the `base` and `head` revisions.)

# When upstream taskgraph supports better selection (https://github.com/taskcluster/taskgraph/issues/369)
# this can be replaced with it.

import os
from pathlib import Path

from taskgraph import files_changed
from taskgraph.transforms.base import TransformSequence

KIND_DIR = Path(__file__).parent.parent.parent / "kinds"

# Kinds are slightly special - there are some kinds that don't affect the pipeline,
# and changing them shouldn't force the pipeline to run.
EXCLUDE_KINDS = ["test"]
# Touching any file in any of these directories is considered a pipeline change
PIPELINE_DIRS = [
    "pipeline/**",
    "taskcluster/docker/**",
    "taskcluster/requirements.txt",
    "taskcluster/scripts/**",
    "taskcluster/translations_taskgraph/**",
]
PIPELINE_DIRS.extend(
    f"taskcluster/kinds/{kind}" for kind in os.listdir(KIND_DIR) if kind not in EXCLUDE_KINDS
)

transforms = TransformSequence()


@transforms.add
def skip_unless_pipeline_changed(config, jobs):
    if not files_changed.check(config.params, PIPELINE_DIRS):
        return

    yield from jobs
