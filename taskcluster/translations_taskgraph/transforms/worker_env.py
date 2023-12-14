from taskgraph.transforms.base import TransformSequence

transforms = TransformSequence()


@transforms.add
def inject_worker_env(config, jobs):
    for job in jobs:
        # It's called worker-type in jobs, but in reality it's an alias resolved in the graph config...
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
