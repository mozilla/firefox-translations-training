# Metrics publication

This package reads and extracts metrics data from the training system of Firefox Translations.
It actually supports logs from Marian version **1.10**.
Above versions (even minor) will raise a warning as not supported.

## Behavior

Logs are extracted from [Marian](https://marian-nmt.github.io/) training tasks, usually running in a Task Cluster environment.

The parser has 2 entry points:
* Parsing logs from a file or process in real time
* Reading a folder with multiple training data

Publication is handled via extensible `translations_parser.publishers`.
It actually supports writting to local CSV files or puiblish metrics to [Weight & Biases](https://docs.wandb.ai/ref/python) (W&B).

### Reading a folder

The parser supports reading a folder containing multiple trainings with a structure like above example:
```
.
├── logs
│   └── en-sv
│       └── opusmt-multimodel-test
│           └── opusmt-multimodel-test
│               ├── alignments.log
│               ├── ce_filter.log
│               └── …
└── models
    └── en-sv
        └── opusmt-multimodel-test
            ├── evaluation
            │   └── speed
            │       ├── tc_Tatoeba-Challenge-v2021-08-07.metrics
            │       └── …
            ├── student-finetuned
            │   ├── train.log
            │   └── valid.log
            └─ …
```


The following rules are applied:
* `./models` sub-folders are projects (e.g. `en-sv`), corresponding to projects in W&B.
* Projects contains multiple groups (e.g. `opusmt-multimodel-test`), each containing multiple runs (e.g. `student-finetuned`) and usually an `evaluation` folder.
* For each run, `train.log` is parsed (`valid.log` results are usually contained in `train.log`) and published to W&B.
* `.metrics` files in the `evaluation` are parsed (looking for one float value per line) and also published on the same run (e.g. `[metric] tc_Tatoeba-Challenge-v2021-08-07`).
* Once all runs of a group have been published, a last group is pushed to W&B, named `group_logs`. That run contains no metrics but all experiment files published as artifacts.

## Install

The parser can be built as a distinct package to make deployment and developments easier.

You can install the package using pip:
```sh
$ pip install -r requirements/common.txt
$ pip install .
```

### Requirements

The full list of dependencies (hash pinned) is specified in `requirements/comon.txt`.

This file is generated using `pip-tools`, and must be updated once dependecies change:
```sh
pip-compile --generate-hashes --output-file=requirements/common.txt requirements/common.in
```

### Development

On a virtual environment, you can install the package using pip:
A developer may want to install the package in editable mode (i.e install from the local path directly):
```sh
$ pip install -r requirements/common.txt
$ pip install -e .
```

Pre-commit rules are automatically run once pre-commits hooks have been installed:
```sh
$ pip install pre-commit
$ pre-commit install
$ pre-commit run -a # Run pre-commit once
```

## Usage

Run the parser with the local sample:
```sh
$ parse_tc_logs -i ../tests/data/KZPjvTEiSmO--BXYpQCNPQ.txt
```

Simulate reading logs from a process:
```sh
../tests/data/simulate_process.py | parse_tc_logs -s --verbose
```

Publish data to Weight & Biases:
```sh
$ parse_tc_logs -i ../tests/data/KZPjvTEiSmO--BXYpQCNPQ.txt --wandb-project <project> --wandb-group <group> --wandb-run-name <run>
```

Run the parser on a directory containing experiments and publis to Weight & Biases:
```sh
$ parse_experiment_dir -d models
```
