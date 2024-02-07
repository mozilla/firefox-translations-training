class Dataset:
    """
    Convert a dataset key into a structured format.

    e.g.

    self.key             "bucket_releng-translations-dev/data/en-ru/pytest-dataset"
    self.importer:       "bucket"
    self.name:           "releng-translations-dev/data/en-ru/pytest-dataset"
    self.file_safe_name: "releng-translations-dev_data_en-ru_pytest-dataset"
    """

    def __init__(self, dataset_key: str) -> None:
        key_parts = dataset_key.split("_")

        self.key = dataset_key
        self.importer = key_parts[0]
        self.name = "_".join(key_parts[1:])
        self.file_safe_name = self.name.replace("/", "_").replace(".", "_")

        if not self.importer:
            raise Exception(f"Could not find the importer in the dataset key {dataset_key}")

        if not self.name:
            raise Exception(f"Could not find the name in the dataset key {dataset_key}")
