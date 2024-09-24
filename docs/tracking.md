# Experiment tracking

The [tracking module](/tracking) handles parsing training logs to extract [Marian](https://marian-nmt.github.io/) training metrics in real time.

The parser supports different sources:
* Online publication from Taskcluster training or evaluation tasks.
* Deferred publication from a Taskcluster task or group of tasks.
* Deferred publication from a local directory containing archived training data.

It actually supports logs from **Marian 1.10** and **Marian 1.12**. Above versions (even minor) will raise a warning and may result in missing data.

## Publication

The parser supports writting metrics to [Weight & Biases](https://wandb.ai/) external storage, or produce local artifacts (CSV files).
The publication is handled via the extensible module `translations_parser.publishers`.

### Real time publication

Publication is implemented within the training (`pipeline.train.train.get_log_parser_command`) and evaluation (`pipeline.eval.eval.main`). This is the prefered way to track metrics, as machine resource usage will also be published to Weight & Biases.

Any new experiment will automatically be published to the [public Weight & Biases dashboard](https://wandb.ai/moz-translations/projects).

Any new pull request will trigger publication to the `ci` project in Weight & Biases. You may want to edit a value in `taskcluster/configs/config.ci.yml` (e.g. the first `disp-freq` entry) to force a new publication, because of Taskcluster cache.

### Deffered publication from Taskcluster

It is possible to use the parser on Taskcluster's tasks that have finished.
The parser supports reading training tasks directly from the Taskcluster API (no authentication).

This method is useful to reupload data of past training and evaluation tasks.

You can run the parser on a Taskcluster group by running:
```sh
$ parse_tc_group <task_group_id>
```
By default, this command will fetch other traversal tasks (related experiments). You can avoid this behavior by using the `--no-recursive-lookup` option.

You can also run the parser based on the logs of a single task:
```sh
parse_tc_logs ----input-file=live_backing.log
```

### Deffered publication from GCP archive

The parser supports browsing a folder structure from a GCP archive of multiple training runs.
This method is useful to reupload data of past training and evaluation tasks that are not available anymore from Taskcluster (expired) or when handling a large amount of data.

The structure from experiments that ran on Taskcluster should look like this:
```
.
├── logs
│   └── en-hu
│       └── baseline_enhu_aY25-4fXTcuJNuMcWXUYtQ
│           └── student
│               ├── train.log
│               └── …
└── models
    └── en-hu
        └── baseline_enhu_aY25-4fXTcuJNuMcWXUYtQ
            └── evaluation
                ├── speed
                │   ├── sacrebleu_wmt09.metrics
                │   └── …
                └── student
                    ├── flores_devtest.metrics
                    └── …
```

The structure from older experiments that ran with Snakemake should look like this:
```
.
├── logs
│   └── …
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

## Development

The parser can be built as a distinct package to make developments easier using pip.

### Installation

On a virtual environment, you can install the package in editable mode (i.e from the local folder):
```sh
$ pip install -e ./tracking
```

### Extend supported Marian metrics

The parser does not supports arbitrary metrics (i.e. via the `--valid-metrics` argument).

In order to support new values, you may want to update the regular expression matching Marian output lines in `tracking.translations_parser.parser` and the dataclass in `tracking.translations_parser.data`.
