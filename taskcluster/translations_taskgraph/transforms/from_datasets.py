import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Optional

from translations_taskgraph.util.substitution import substitute

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

locales_only = TransformSequence()
locales_only.add_validate(SCHEMA)


def shorten_dataset_name(dataset):
    """Shortens various dataset names. Mainly used to make sure we can have
    useful Treeherder symbols."""
    # TODO: should the replacements live in ci/config.yml?
    return (dataset
        .replace("new-crawl", "nc")
        .replace("news.2020", "n2020")
        .replace("Neulab-tedtalks_train-1", "Ntt1")
    )


def get_dataset_category(provider, dataset, dataset_categories):
    for category, datasets in dataset_categories.items():
        if f"{provider}_{dataset}" in datasets:
            return category

    return ""


@per_dataset.add
def jobs_from_datasets(config, jobs):
    for job in jobs:
        dataset_config = job.pop("dataset-config", {})
        include_categories = dataset_config.get("include-categories", [])
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

                category = get_dataset_category(provider, dataset, training_datasets)
                if include_categories and category not in include_categories:
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
                        "dataset_sanitized": dataset.replace("/", "_").replace(".", "_"),
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


@locales_only.add
def jobs_from_locales(config, jobs):
    for job in jobs:
        dataset_config = job.pop("dataset-config", {})
        include_categories = dataset_config.get("include-categories", [])
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

                category = get_dataset_category(provider, dataset, training_datasets)
                if include_categories and category not in include_categories:
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
