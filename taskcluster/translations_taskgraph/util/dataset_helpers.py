def shorten_dataset_name(dataset):
    """Shortens various dataset names. Mainly used to make sure we can have
    useful Treeherder symbols."""
    # TODO: should the replacements live in ci/config.yml?
    return (dataset
        .replace("new-crawl", "nc")
        .replace("news.2020", "n2020")
        .replace("Neulab-tedtalks_train-1", "Ntt1")
    )
