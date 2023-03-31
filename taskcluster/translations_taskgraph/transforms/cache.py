from taskgraph.transforms.base import TransformSequence
from taskgraph.util.hash import hash_path

transforms = TransformSequence()

@transforms.add
def add_cache(config, jobs):
    for job in jobs:
        cache_type = job["attributes"]["cache-type"]
        cache_resources = job["attributes"]["cache-resources"]
        digest_data = []

        if cache_resources:
            for r in cache_resources:
                digest_data.append(hash_path(r))

        job["cache"] = {
            "type": cache_type,
            "name": job["label"],
            "digest-data": digest_data,
        }

        yield job
