# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.transforms.base import TransformSequence

transforms = TransformSequence()


@transforms.add
def set_dataset_category(config, jobs):
    datasets = config.params["training_config"]["datasets"]

    for job in jobs:
        if "dataset-category" not in job["attributes"]:
            provider = job["attributes"]["provider"]
            dataset = job["attributes"]["dataset"]
            config_dataset = f"{provider}_{dataset}"

            categories = set()
            for category, dataset_list in datasets.items():
                if config_dataset in dataset_list:
                    categories.add(category)

            if len(categories) == 0:
                raise Exception(f"Could not determine dataset category for: {config_dataset}!")
            elif len(categories) > 1:
                raise Exception(
                    f"Found multiple dataset categorys for {config_dataset}: {categories}!"
                )
            else:
                job["attributes"]["dataset-category"] = categories.pop()

        yield job
