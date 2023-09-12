import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Optional

from translations_taskgraph.util.substitution import substitute
from translations_taskgraph.util.dataset_helpers import (
    shorten_dataset_name,
    sanitize_dataset_name,
    shorten_provider_name,
)

SCHEMA = Schema(
    {
        Optional("dataset-config"): {
            # Fields in each `job` that need to be substituted with data
            # provided by this transform.
            Optional("substitution-fields"): [str],
            Optional("category"): str,
            Optional("provider"): str,
            Optional("exclude-locales"): [
                {
                    "src": str,
                    "trg": str,
                },
            ],
        },
    },
    extra=ALLOW_EXTRA,
)

per_dataset = TransformSequence()
per_dataset.add_validate(SCHEMA)

mono = TransformSequence()
mono.add_validate(SCHEMA)


@per_dataset.add
def jobs_from_datasets(config, jobs):
    for job in jobs:
        dataset_config = job.pop("dataset-config", {})
        category = dataset_config.get("category", "")
        provider = dataset_config.get("provider", "")
        substitution_fields = dataset_config.get("substitution-fields", [])
        exclude_locales = dataset_config.get("exclude-locales", [])
        datasets = config.params["training_config"]["datasets"]
        src = config.params["training_config"]["experiment"]["src"]
        trg = config.params["training_config"]["experiment"]["trg"]

        included_datasets = set()
        if category:
            included_datasets.update(datasets[category])
        else:
            for sets in datasets.values():
                included_datasets.update(sets)

        if {"src": src, "trg": trg} in exclude_locales:
            continue

        for full_dataset in included_datasets:
            dataset_provider, dataset = full_dataset.split("_", 1)
            if provider and provider != dataset_provider:
                continue

            subjob = copy.deepcopy(job)

            subs = {
                "provider": dataset_provider,
                "provider_short": shorten_provider_name(dataset_provider),
                "dataset": full_dataset,
                "dataset_short": shorten_dataset_name(dataset),
                "dataset_sanitized": sanitize_dataset_name(dataset),
                "src_locale": src,
                "trg_locale": trg,
            }
            for field in substitution_fields:
                container, subfield = subjob, field
                while "." in subfield:
                    f, subfield = subfield.split(".", 1)
                    container = container[f]

                container[subfield] = substitute(container[subfield], **subs)

            subjob.setdefault("attributes", {})
            subjob["attributes"]["provider"] = dataset_provider
            subjob["attributes"]["dataset"] = dataset
            subjob["attributes"]["src_locale"] = src
            subjob["attributes"]["trg_locale"] = trg

            yield subjob


@mono.add
def jobs_for_mono_datasets(config, jobs):
    for job in jobs:
        dataset_config = job.pop("dataset-config", {})
        category = dataset_config.get("category")
        provider = dataset_config.get("provider", "")
        substitution_fields = dataset_config.get("substitution-fields", [])
        exclude_locales = dataset_config.get("exclude-locales", [])
        datasets = config.params["training_config"]["datasets"]
        src = config.params["training_config"]["experiment"]["src"]
        trg = config.params["training_config"]["experiment"]["trg"]

        if {"src": src, "trg": trg} in exclude_locales:
            continue

        if category not in ("mono-src", "mono-trg"):
            raise Exception(
                "from_datasets:mono can only be used with mono-src and mono-trg categories"
            )

        included_datasets = set()
        if category:
            included_datasets.update(datasets[category])
        else:
            for sets in datasets.values():
                included_datasets.update(sets)

        for full_dataset in included_datasets:
            dataset_provider, dataset = full_dataset.split("_", 1)
            if provider and provider != dataset_provider:
                continue

            subjob = copy.deepcopy(job)

            if category == "mono-src":
                locale = src
            elif category == "mono-trg":
                locale = trg
            else:
                raise Exception(
                    "from_datasets:mono can only be used with mono-src and mono-trg categories"
                )

            subs = {
                "provider": dataset_provider,
                "provider_short": shorten_provider_name(dataset_provider),
                "dataset": full_dataset,
                "dataset_short": shorten_dataset_name(dataset),
                "dataset_sanitized": sanitize_dataset_name(dataset),
                "locale": locale,
                "src_locale": src,
                "trg_locale": trg,
            }
            for field in substitution_fields:
                container, subfield = subjob, field
                while "." in subfield:
                    f, subfield = subfield.split(".", 1)
                    container = container[f]

                container[subfield] = substitute(container[subfield], **subs)

            subjob.setdefault("attributes", {})
            subjob["attributes"]["provider"] = dataset_provider
            subjob["attributes"]["dataset"] = dataset
            subjob["attributes"]["locale"] = locale
            subjob["attributes"]["src_locale"] = src
            subjob["attributes"]["trg_locale"] = trg

            yield subjob
