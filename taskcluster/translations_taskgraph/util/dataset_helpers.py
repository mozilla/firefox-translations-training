def sanitize_dataset_name(dataset):
    # Keep in sync with `Dataset` in pipeline/common/datasets.py.
    return dataset.replace("://", "_").replace("/", "_").replace(".", "_").replace(":", "_")
