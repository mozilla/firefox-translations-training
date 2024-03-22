# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import json

from taskgraph.transforms.base import TransformSequence

transforms = TransformSequence()


@transforms.add
def enable_or_disable_bicleaner(config, jobs):
    """Set the appropriate dependencies and fetches based on whether bicleaner
    is enabled or disabled."""

    merge_corpus_task = None
    for name, task in config.kind_dependencies_tasks.items():
        if name.startswith("merge-corpus"):
            merge_corpus_task = task

    if not merge_corpus_task:
        raise Exception("Couldn't find merge corpus task!")

    pull_from = "bicleaner"
    if config.params["training_config"]["experiment"]["bicleaner"]["disable"]:
        pull_from = "clean-corpus"

    # If bicleaner is disabled, we pull upstream artifacts from `clean-corpus`
    new_deps = {}
    for name, task in config.kind_dependencies_tasks.items():
        if name.startswith(pull_from):
            new_deps[task.kind] = task.label

    merge_corpus_task.dependencies.update(new_deps)
    # Also need to set up fetches, which will involve setting the `MOZ_FETCHES` env var
    # like the `run` transform does: https://github.com/taskcluster/taskgraph/blob/1a7dba0db709c84940fcf85a421c1dfc931f9747/src/taskgraph/transforms/run/__init__.py#L207
    # this will have to get somehow combined with the existing `MOZ_FETCHES` present in merge_corpus_task.task["payload"]["env"]
    fetches = json.loads(merge_corpus_task.task["payload"]["env"]["MOZ_FETCHES"]["task-reference"])
    # Consult an existing task definition for the MOZ_FETCHES format
    fetches.append([
        {"artifact": "something", "extract": True, "task": f"<{pull_from}>"}
    ])
    merge_corpus_task.task["payload"]["env"]["MOZ_FETCHES"]["task-reference"] = json.dumps(fetches)

    # We don't actually make any adjustements to the new jobs; this transform only exists
    # to cause the side effects done above.
    yield from jobs
