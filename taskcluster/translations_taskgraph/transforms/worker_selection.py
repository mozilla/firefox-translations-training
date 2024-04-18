# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This transform sequence injects worker-specific environment variables
# (such as those that dependent on the number and type of GPUs a worker has)
# into task definitions. This avoids the need to discover this information at
# runtime, or adjust in kinds when changing worker types.

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import evaluate_keyed_by

transforms = TransformSequence()


@transforms.add
def set_worker_type(config, jobs):
    """Determines the general type of worker each task wants, which sometimes
    depends on `tasks-for`. Tasks typically will end up specifying one of the
    worker `aliases` from config.yml after this is evaluated, eg: b-cpu,
    b-largegpu-largedisk."""

    training_config = config.params.get("training_config")
    worker_classes = training_config["taskcluster"]["worker-classes"]
    worker_class = worker_classes.get(config.kind, worker_classes["default"])
    for job in jobs:
        # First, evaluate the `keyed-by` in the initial task specification from
        # the kind, if present. This should give us one of the keys from
        # `worker-configuration` in config.yml.
        task_worker_type = evaluate_keyed_by(
            job["worker-type"],
            job["description"],
            {"tasks-for": config.params["tasks_for"]},
        )

        # Now that we have one of the aliases, we need to resolve it to a
        # specific worker type, as some of those aliases have their own
        # `keyed-by` blocks, which may give different worker types depending
        # on what's in the training config.
        worker_alias_block = config.graph_config["local-worker-aliases"][task_worker_type].copy()
        job["worker-type"] = evaluate_keyed_by(
            worker_alias_block,
            task_worker_type,
            {"worker-class": worker_class},
        )

        yield job


@transforms.add
def inject_worker_env(config, jobs):
    for job in jobs:
        # This is called worker-type in jobs, but in reality it's an alias resolved in the graph config...
        worker_type = job["worker-type"]
        worker_config = config.graph_config["worker-configuration"].get(worker_type, {})

        worker_env = worker_config.get("env", {})
        if "GPUS" not in worker_env or "WORKSPACE" not in worker_env:
            # GPU tasks will not function correctly without these set; make this an error
            # before they even run.
            if "gpu" in worker_type:
                raise Exception(
                    "GPUS and/or WORKSPACE values missing from worker env, this is probably misconfiguration."
                )
            else:
                yield job
                continue

        job["worker"]["env"].update(worker_env)

        yield job
