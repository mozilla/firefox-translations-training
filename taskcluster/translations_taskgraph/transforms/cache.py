from taskgraph.transforms.base import TransformSequence
from taskgraph.util.hash import hash_path
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Any, Optional, Required

from translations_taskgraph.util.dict_helpers import deep_get

SCHEMA = Schema(
    {
        Required("attributes"): {
            Required("cache"): {
                Required("type"): str,
                Optional("resources"): [str],
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
def add_cache(config, jobs):
    for job in jobs:
        cache = job["attributes"]["cache"]
        cache_type = cache["type"]
        cache_resources = cache["resources"]
        cache_parameters = cache.get("from-parameters", {})
        digest_data = []

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
