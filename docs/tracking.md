# Metrics publication

The tracking [module](/tracking) within handles parsing training logs to extract Marian metrics in real time.

The parser supports reading logs from a Task Cluster environment, or a local directory containing multiple training data. It can publish metrics to an external dashboard, for example [Weight & Biases](https://wandb.ai/).

It actually supports logs from **Marian 1.10**. Above versions (even minor) will raise a warning as not supported.

## Install

The parser can be built as a distinct package to make developments easier using pip.
On a virtual environment, you can install the package in editable mode (i.e from the local folder):
```sh
$ pip install -e ./tracking
```

## Behavior

Logs are extracted from [Marian](https://marian-nmt.github.io/) training tasks, usually running in a Task Cluster environment.

The parser has 3 entry points:
* Parsing logs from a file or process in real time
* Reading a folder with multiple training data
* Reading a Taskcluster group (and related experiments, mentioned as "traversal")

Publication is handled via the extensible module `translations_parser.publishers`.
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

### Publish from Taskcluster

The parser supports reading training tasks directly from the Taskcluster API (no authentication).
The results are published the same way as for experiments folder.

You can parse a group (with other traversal tasks) by running:
```sh
$ parse_tc_group <task_group_id>
```

### Extend supported Marian metrics

The parser does not supports arbitrary metrics (i.e. via the `--valid-metrics` argument).

In order to support new values, you may want to update the regular expression matching Marian output lines in `tracking.translations_parser.parser` and the dataclass in `tracking.translations_parser.data`.
