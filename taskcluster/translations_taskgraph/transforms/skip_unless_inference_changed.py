# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This transform sequence will remove all jobs unless at least one inference
# impacting thing (an inference script or relevant Taskcluster code) has changed
# (This is done with the `files_changed` helper, which uses data in the
# parameters to determine files changed between the `base` and `head` revisions.)

# When upstream taskgraph supports better selection (https://github.com/taskcluster/taskgraph/issues/369)
# this can be replaced with it.

import os
from pathlib import Path

from taskgraph.transforms.base import TransformSequence

KIND_DIR = Path(__file__).parent.parent.parent / "kinds"

# Kinds are slightly special - there are some kinds that don't affect inference,
# and changing them shouldn't force inference to run.
INCLUDE_KINDS = ["inference"]
# Touching any file in any of these directories is considered an inference change
INFERENCE_DIRS = [
    "inference/**",
    "taskcluster/docker/inference/**",
]
INFERENCE_DIRS.extend(
    f"taskcluster/kinds/{kind}" for kind in os.listdir(KIND_DIR) if kind in INCLUDE_KINDS
)

transforms = TransformSequence()


@transforms.add
def skip_unless_inference_changed(config, jobs):
    for job in jobs:
        job.setdefault("optimization", {})
        job["optimization"]["skip-unless-changed"] = INFERENCE_DIRS

        yield job
