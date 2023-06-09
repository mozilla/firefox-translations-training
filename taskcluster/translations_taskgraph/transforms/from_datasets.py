import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Optional

from translations_taskgraph.util.substitution import substitute
from translations_taskgraph.util.dataset_helpers import shorten_dataset_name, sanitize_dataset_name

SCHEMA = Schema(
    {
        Optional("dataset-config"): {
            # Fields in each `job` that need to be substituted with data
            # provided by this transform.
            Optional("substitution-fields"): [str],
            Optional("include-categories"): [str],
            # Dataset/locale pairs to include (and split each `job` by), by
            # provider and dataset name. This is essentially an override for
            # what's listed in `ci/config.yml`, which means that:
            # - If no providers are listed, the entire value of `datasets` from
            #   that file will be used.
            # - If no datasets are listed for a provider, all datasets and locale
            #   pairs for that provider will be used (so long as they are not excluded
            #   by `exclude-datasets')
            # - If no locale pairs are listed for a dataset, all locale pairs for that
            #   dataset will be used (so long as they are not excluded
            #   by `exclude-datasets` or `exclude-locales`)
            Optional("include-datasets"): {
                # provider name
                str: {
                    # dataset name
                    str: [
                        # src/trg locale pairs
                        {
                            "src": str,
                            "trg": str,
                        },
                    ],
                },
            },
            # Very similar to the above block, but excludes datasets that were
            # pulled in from `ci/config.yml` by the following rules:
            # - If no providers are listed, nothing is excluded (otherwise we'd
            #   have nothing to split `jobs` by, which would be an error.
            # - If no datasets are listed for a provider, that entire provider
            #   is excluded. If specific ones are listed, only those datasets are
            #   excluded.
            # - If no locale pairs are listed for a dataset, that entire dataset is
            #   excluded. If specific pairs are listed, only those pairs are excluded.
            Optional("exclude-datasets"): {
                # provider name
                str: {
                    # dataset name
                    str: [
                        # src/trg locale pairs
                        {
                            "src": str,
                            "trg": str,
                        },
                    ],
                },
            },
            # Locales that will be excluded from all providers & datasets
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

locales_only = TransformSequence()
locales_only.add_validate(SCHEMA)


def get_dataset_categories(provider, dataset, dataset_categories):
    categories = set()
    for category, datasets in dataset_categories.items():
        if f"{provider}_{dataset}" in datasets:
            categories.add(category)

    return categories


@per_dataset.add
def jobs_from_datasets(config, jobs):
    for job in jobs:
        dataset_config = job.pop("dataset-config", {})
        include_categories = set(dataset_config.get("include-categories", []))
        include_datasets = dataset_config.get("include-datasets", {})
        exclude_datasets = dataset_config.get("exclude-datasets", {})
        exclude_locales = dataset_config.get("exclude-locales", [])
        substitution_fields = dataset_config.get("substitution-fields", [])
        training_datasets = config.params.get("training_config", {}).get("datasets", {})

        providers = include_datasets.keys()
        if not providers:
            providers = config.graph_config["datasets"].keys()

        for provider in providers:
            datasets = include_datasets.get(provider, {})
            if not datasets:
                datasets = config.graph_config["datasets"][provider]

            for dataset, locale_pairs in datasets.items():
                if dataset in exclude_datasets.get(provider, {}):
                    continue

                categories = get_dataset_categories(provider, dataset, training_datasets)
                if include_categories and not include_categories.intersection(categories):
                    continue

                for pair in locale_pairs:
                    if pair in exclude_datasets.get(provider, {}).get(dataset, []):
                        continue

                    if pair in exclude_locales:
                        continue

                    subjob = copy.deepcopy(job)
                    subs = {
                        "provider": provider,
                        "dataset": dataset,
                        "dataset_short": shorten_dataset_name(dataset),
                        "dataset_sanitized": sanitize_dataset_name(dataset),
                        "src_locale": pair["src"],
                        "trg_locale": pair["trg"],
                    }
                    for field in substitution_fields:
                        container, subfield = subjob, field
                        while "." in subfield:
                            f, subfield = subfield.split(".", 1)
                            container = container[f]

                        container[subfield] = substitute(container[subfield], **subs)

                    # If the job has command-context, add these values there
                    # as well. These helps to avoid needing two levels of
                    # substitution in a command.
                    if subjob.get("run", {}).get("command-context") is not None:
                        subjob["run"]["command-context"].update(subs)

                    subjob.setdefault("attributes", {})
                    subjob["attributes"]["provider"] = provider
                    subjob["attributes"]["dataset"] = dataset
                    subjob["attributes"]["src_locale"] = pair["src"]
                    subjob["attributes"]["trg_locale"] = pair["trg"]

                    yield subjob


@mono.add
def jobs_for_mono_datasets(config, jobs):
    for job in jobs:
        dataset_config = job.pop("dataset-config", {})
        include_categories = set(dataset_config.get("include-categories", []))
        include_datasets = dataset_config.get("include-datasets", {})
        exclude_datasets = dataset_config.get("exclude-datasets", {})
        exclude_locales = dataset_config.get("exclude-locales", [])
        substitution_fields = dataset_config.get("substitution-fields", [])
        training_datasets = config.params.get("training_config", {}).get("datasets", {})

        if "mono-src" in include_categories and "mono-trg" in include_categories:
            raise Exception("from_datasets:mono can only use one of: `mono-src`, `mono-trg` in include_categories")

        providers = include_datasets.keys()
        if not providers:
            providers = config.graph_config["datasets"].keys()

        for provider in providers:
            datasets = include_datasets.get(provider, {})
            if not datasets:
                datasets = config.graph_config["datasets"][provider]

            for dataset, locale_pairs in datasets.items():
                if dataset in exclude_datasets.get(provider, {}):
                    continue

                categories = get_dataset_categories(provider, dataset, training_datasets)
                if include_categories and not include_categories.intersection(categories):
                    continue

                for pair in locale_pairs:
                    if pair in exclude_datasets.get(provider, {}).get(dataset, []):
                        continue

                    if pair in exclude_locales:
                        continue

                    if "mono-src" in include_categories:
                        locale = pair["src"]
                    elif "mono-trg" in include_categories:
                        locale = pair["trg"]
                    else:
                        raise Exception("Don't use `from_datasets:mono` without the `mono-src` or `mono-trg` category!")
                    subjob = copy.deepcopy(job)
                    subs = {
                        "provider": provider,
                        "dataset": dataset,
                        "dataset_short": shorten_dataset_name(dataset),
                        "dataset_sanitized": sanitize_dataset_name(dataset),
                        "locale": locale,
                        "src_locale": pair["src"],
                        "trg_locale": pair["trg"],
                    }
                    for field in substitution_fields:
                        container, subfield = subjob, field
                        while "." in subfield:
                            f, subfield = subfield.split(".", 1)
                            container = container[f]

                        container[subfield] = substitute(container[subfield], **subs)

                    # If the job has command-context, add these values there
                    # as well. These helps to avoid needing two levels of
                    # substitution in a command.
                    if subjob.get("run", {}).get("command-context") is not None:
                        subjob["run"]["command-context"].update(subs)

                    subjob.setdefault("attributes", {})
                    subjob["attributes"]["provider"] = provider
                    subjob["attributes"]["dataset"] = dataset
                    subjob["attributes"]["locale"] = locale
                    subjob["attributes"]["src_locale"] = pair["src"]
                    subjob["attributes"]["trg_locale"] = pair["trg"]

                    yield subjob


@locales_only.add
def jobs_from_locales(config, jobs):
    for job in jobs:
        dataset_config = job.pop("dataset-config", {})
        include_categories = set(dataset_config.get("include-categories", []))
        include_datasets = dataset_config.get("include-datasets", {})
        exclude_datasets = dataset_config.get("exclude-datasets", {})
        exclude_locales = dataset_config.get("exclude-locales", [])
        substitution_fields = dataset_config.get("substitution-fields", [])
        training_datasets = config.params.get("training_config", {}).get("datasets", {})

        all_pairs = set()

        providers = include_datasets.keys()
        if not providers:
            providers = config.graph_config["datasets"].keys()

        for provider in providers:
            datasets = include_datasets.get(provider, {})
            if not datasets:
                datasets = config.graph_config["datasets"][provider]

            for dataset, locale_pairs in datasets.items():
                if dataset in exclude_datasets.get(provider, {}):
                    continue

                categories = get_dataset_categories(provider, dataset, training_datasets)
                if include_categories and not include_categories.intersection(categories):
                    continue

                for pair in locale_pairs:
                    if pair in exclude_datasets.get(provider, {}).get(dataset, []):
                        continue

                    if pair in exclude_locales:
                        continue
                    
                    all_pairs.add((pair["src"], pair["trg"]))

        # Now that we've got all of our distinct locale pairs, create jobs for them
        for (src, trg) in all_pairs:
            subjob = copy.deepcopy(job)
            subs = {
                "src_locale": src,
                "trg_locale": trg,
            }
            for field in substitution_fields:
                container, subfield = subjob, field
                while "." in subfield:
                    f, subfield = field.split(".", 1)
                    container = container[f]

                container[subfield] = substitute(container[subfield], **subs)

            # If the job has command-context, add these values there
            # as well. These helps to avoid needing two levels of
            # substitution in a command.
            if subjob.get("run", {}).get("command-context") is not None:
                subjob["run"]["command-context"].update(subs)

            subjob["attributes"]["src_locale"] = src
            subjob["attributes"]["trg_locale"] = trg

            yield subjob
