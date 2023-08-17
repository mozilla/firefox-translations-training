"""
Generates filter config for a dataset based on defaults to use in OpusCleaner
"""

import argparse
import json


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

    with open('filters/default.filters.json') as f:
        config_str = f.read()

    config_str = config_str.replace('<src>', src).replace('<trg>', trg)
    config = json.loads(config_str)

    config['files'] += [
        f'{input_prefix}.{src}.gz',
        f'{input_prefix}.{trg}.gz'
    ]

    with open(output, 'w') as f:
        json.dump(config, f, indent=2)


if __name__ == '__main__':
    main()
