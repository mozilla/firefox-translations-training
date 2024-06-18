# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This transform sequence is used to workaround the fact that Taskcluster only
# allows a task to have ~100 upstream dependencies. This transform will clone
# each job given to and split the dependencies across these clones. Eg:
# - A job with 50 dependencies will result in 1 job yielded
# - A job with 150 dependencies will result in 2 jobs yielded
# - A job with 1550 depedencies will result in 16 jobs yielded
#
# The jobs yielded are identical to their original, aside from
# a `-N` being appended to their name, where N is a distinct number.

import copy

from taskgraph import MAX_DEPENDENCIES
from taskgraph.transforms.base import TransformSequence

# One less than taskgraph, because some dummy tasks may depend on:
# - decision task (taskgraph MAX_DEPENDENCIES already accounts for this)
# - a docker image task (taskgraph MAX_DEPENDENCIES does _not_ account for this)
# - N other upstream tasks
OUR_MAX_DEPENDENCIES = MAX_DEPENDENCIES - 1

transforms = TransformSequence()


def yield_job(orig_job, deps, fetches, count):
    job = copy.deepcopy(orig_job)
    job["dependencies"] = deps
    if fetches:
        job["fetches"] = fetches
        job["attributes"]["fetched_artifacts"] = []
        for artifacts in fetches.values():
            for a in artifacts:
                job["attributes"]["fetched_artifacts"].append(a["artifact"])
    job["name"] = "{}-{}".format(orig_job["name"], count)

    return job


@transforms.add
def add_dependencies(config, jobs):
    for job in jobs:
        count = 1
        deps = {}
        fetches = {}

        for dep_label in sorted(job["dependencies"].keys()):
            deps[dep_label] = dep_label
            if job.get("fetches", {}).get(dep_label):
                fetches[dep_label] = job["fetches"][dep_label]
            if len(deps) == OUR_MAX_DEPENDENCIES:
                yield yield_job(job, deps, fetches, count)
                deps = {}
                fetches = {}
                count += 1

        if deps:
            yield yield_job(job, deps, fetches, count)
            count += 1
