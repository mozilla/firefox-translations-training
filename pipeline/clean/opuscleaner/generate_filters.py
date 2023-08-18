"""
Generates filter config for a dataset based on defaults to use in OpusCleaner
"""

import argparse
import json
import os


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input_prefix', metavar='INPUT_PREFIX', type=str, help='Dataset file prefix')
    parser.add_argument('src', metavar='SRC', type=str, help='Source language code')
    parser.add_argument('trg', metavar='TRG', type=str, help='Target language code')
    parser.add_argument('dataset', metavar='DATASET', type=str, help='Dataset name')
    parser.add_argument('output', metavar='OUTPUT_PATH', type=str, help='Write filter config here')

    args = parser.parse_args()
    input_prefix = args.input_prefix
    src = args.src
    trg = args.trg
    dataset = args.dataset
    output = args.output

    # look whether there are filters produced by OpusCleaner UI first
    custom_filter = f'configs/{src}-{trg}/{dataset}.{src}-{trg}.filters.json'
    # workaround: we use "_" to separate the dataset version for OPUS datasets and OpusCleaner uses "-"
    custom_filter_opus = None
    idx = dataset.rfind('_')
    if idx:
        dataset_opus = f'{dataset[:idx]}-{dataset[idx+1:]}'
        custom_filter_opus = f'configs/{src}-{trg}/{dataset_opus}.{src}-{trg}.filters.json'

    if os.path.exists(custom_filter_opus):
        with open(custom_filter_opus) as f:
            config = json.load(f)
            print(f'Using filter {custom_filter_opus}')
    elif os.path.exists(custom_filter):
        with open(custom_filter) as f:
            config = json.load(f)
            print(f'Using filter {custom_filter}')
    else:
        # if custom filter is not found, use defaults
        # note: do not call the folder with default filters "filters" because it's a magic work for opuscleaner-clean
        # and it starts processing such folder
        with open('configs/default.filters.json') as f:
            config_str = f.read()
            config_str = config_str.replace('<src>', src).replace('<trg>', trg)
            config = json.loads(config_str)
            print(f'Using filter default.filters.json')

    # remove if we can use stdin
    config['files'] = [
        f'{input_prefix}.{src}.gz',
        f'{input_prefix}.{trg}.gz'
    ]

    with open(output, 'w') as f:
        json.dump(config, f, indent=2)


if __name__ == '__main__':
    main()
