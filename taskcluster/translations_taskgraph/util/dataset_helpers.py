def sanitize_dataset_name(dataset):
    return dataset.replace("/", "_").replace(".", "_")
