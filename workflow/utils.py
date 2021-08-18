

def get_log_dir(config):
    src = config['src']
    trg = config['trg']
    experiment = config['experiment']
    data_root_dir = config['dirs']['data-root']

    return f"{data_root_dir}/logs/{src}-{trg}/{experiment}"
