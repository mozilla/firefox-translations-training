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

transforms = TransformSequence()


def yield_job(orig_job, deps, count):
    job = copy.deepcopy(orig_job)
    job["dependencies"] = deps
    job["name"] = "{}-{}".format(orig_job["name"], count)

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
