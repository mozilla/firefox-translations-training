import copy

from taskgraph import MAX_DEPENDENCIES
from taskgraph.transforms.base import TransformSequence
from taskgraph.util.treeherder import add_suffix

transforms = TransformSequence()


def yield_job(orig_job, deps, count):
    job = copy.deepcopy(orig_job)
    job["dependencies"] = deps
    job["name"] = "{}-{}".format(orig_job["name"], count)
    if "treeherder" in job:
        job["treeherder"]["symbol"] = add_suffix(job["treeherder"]["symbol"], f"-{count}")

    return job


@transforms.add
def add_dependencies(config, jobs):
    for job in jobs:
        count = 1
        deps = {}

        for dep_label in sorted(job["dependencies"].keys()):
            deps[dep_label] = dep_label
            if len(deps) == MAX_DEPENDENCIES:
                yield yield_job(job, deps, count)
                deps = {}
                count += 1

        if deps:
            yield yield_job(job, deps, count)
            count += 1
