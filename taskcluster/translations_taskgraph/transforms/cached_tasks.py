# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This transform is largely of the upstream `cached_task` transform in Taskgraph.
# It exists because there are two features that we need that are missing upstream:
# - The ability to influence the cache digest from parameters.
#   (https://github.com/taskcluster/taskgraph/issues/391)
# - The ability to avoid adding some upstream tasks to the cache digest (which
#   allows us to avoid rebuilding the world when, eg: we upgrade a Docker base
#   image version). No upstream issue is filed for this, because for the vast
#   majority of use cases it is better to take the rebuilds. Our use case is
#   an exception, because of the truly massive amount of time it takes to
#   train a model.


import itertools

import taskgraph
from taskgraph.transforms.base import TransformSequence
from taskgraph.transforms.cached_tasks import order_tasks, format_task_digest
from taskgraph.util.cached_tasks import add_optimization
from taskgraph.util.hash import hash_path
from taskgraph.util.schema import Schema, optionally_keyed_by, resolve_keyed_by
from voluptuous import ALLOW_EXTRA, Any, Required, Optional

from translations_taskgraph.util.dict_helpers import deep_get

transforms = TransformSequence()


DONT_INVALIDATE_KINDS = ["docker-image", "fetch", "toolchain"]

SCHEMA = Schema(
    {
        Required("attributes"): {
            Required("cache"): {
                Required("type"): str,
                Optional("resources"): optionally_keyed_by("provider", [str]),
                Optional("from-parameters"): {
                    str: Any([str], str),
                },
            },
        },
    },
    extra=ALLOW_EXTRA,
)

transforms = TransformSequence()
transforms.add_validate(SCHEMA)


@transforms.add
def resolved_keyed_by_fields(config, jobs):
    for job in jobs:
        provider = job["attributes"].get("provider", None)
        resolve_keyed_by(
            job["attributes"]["cache"],
            "resources",
            item_name=job["description"],
            **{"provider": provider},
        )

        yield job


@transforms.add
def add_cache(config, jobs):
    for job in jobs:
        cache = job["attributes"]["cache"]
        cache_type = cache["type"]
        cache_resources = cache["resources"]
        cache_parameters = cache.get("from-parameters", {})
        digest_data = []
        digest_data.extend(list(itertools.chain.from_iterable(job["worker"]["command"])))

        if cache_resources:
            for r in cache_resources:
                digest_data.append(hash_path(r))

        if cache_parameters:
            for param, path in cache_parameters.items():
                if isinstance(path, str):
                    value = deep_get(config.params, path)
                    digest_data.append(f"{param}:{value}")
                else:
                    for choice in path:
                        value = deep_get(config.params, choice)
                        if value is not None:
                            digest_data.append(f"{param}:{value}")
                            break

        job["cache"] = {
            "type": cache_type,
            # Upstream cached tasks use "/" as a separator for different parts
            # of the digest. If we don't remove them, caches are busted for
            # anything with a "/" in its label.
            "name": job["label"].replace("/", "_"),
            "digest-data": digest_data,
        }

        yield job


@transforms.add
def cache_task(config, tasks):
    if taskgraph.fast:
        for task in tasks:
            yield task
        return

    digests = {}
    for task in config.kind_dependencies_tasks.values():
        if "cached_task" in task.attributes:
            digests[task.label] = format_task_digest(task.attributes["cached_task"])

    for task in order_tasks(config, tasks):
        cache = task.pop("cache", None)
        if cache is None:
            yield task
            continue

        dependency_digests = []
        for p in task.get("dependencies", {}).values():
            # Here in Translations, we explicit do _not_ invalidate cached
            # training jobs when non-training jobs are invalidated.
            if any([kind in p for kind in DONT_INVALIDATE_KINDS]):
                continue
            if p in digests:
                dependency_digests.append(digests[p])
            else:
                raise Exception(
                    "Cached task {} has uncached parent task: {}".format(task["label"], p)
                )

        digest_data = cache["digest-data"] + sorted(dependency_digests)

        # Chain of trust affects task artifacts therefore it should influence
        # cache digest.
        if task.get("worker", {}).get("chain-of-trust"):
            digest_data.append(str(task["worker"]["chain-of-trust"]))

        add_optimization(
            config,
            task,
            cache_type=cache["type"],
            cache_name=cache["name"],
            digest_data=digest_data,
        )
        digests[task["label"]] = format_task_digest(task["attributes"]["cached_task"])

        yield task
