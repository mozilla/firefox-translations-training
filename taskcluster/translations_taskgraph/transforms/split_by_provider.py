import copy

from taskgraph.transforms.base import TransformSequence

transforms = TransformSequence()


@transforms.add
def split_by_provider(config, jobs):
    for job in jobs:
        for provider in config.graph_config["datasets"]:
            subjob = copy.deepcopy(job)
            subjob["provider"] = provider
            if "{provider}" not in subjob["name"]:
                raise Exception(f"Cannot find {{provider}} substitution in {subjob['name']}; aborting")

            subjob["name"] = subjob["name"].replace("{provider}", provider)
            yield subjob
