# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This transform sequence injects worker-specific environment variables
# (such as those that dependent on the number and type of GPUs a worker has)
# into task definitions. This avoids the need to discover this information at
# runtime, or adjust in kinds when changing worker types.

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import resolve_keyed_by

transforms = TransformSequence()


@transforms.add
def evaluate_keyed_by(config, jobs):
    for job in jobs:
        resolve_keyed_by(
            job,
            "worker-type",
            item_name=job["description"],
            **{"tasks-for": config.params["tasks_for"]},
        )

        yield job


@transforms.add
def inject_worker_env(config, jobs):
    for job in jobs:
        # This is called worker-type in jobs, but in reality it's an alias resolved in the graph config...
        worker_alias = job["worker-type"]

        worker_definition = config.graph_config["workers"]["aliases"].get(worker_alias)
        if not worker_definition:
            raise Exception(f"Couldn't find worker definition for {worker_alias} in graph config!")

        worker_type = worker_definition["worker-type"]
        worker_config = config.graph_config["worker-configuration"].get(worker_type)
        if not worker_config:
            raise Exception(
                f"Couldn't find worker configuration for {worker_type} in graph config!"
            )

        worker_env = worker_config["env"]
        if "GPUS" not in worker_env or "WORKSPACE" not in worker_env:
            raise Exception(
                "GPUS and/or WORKSPACE values missing from worker env, this is probably misconfiguration."
            )

        job["worker"]["env"].update(worker_env)

        yield job
