# Firefox Translations training
Training pipelines for Firefox Translations machine translation models.
The trained models are hosted in [firefox-translations-models](https://github.com/mozilla/firefox-translations-models/),
compatible with [bergamot-translator](https://github.com/mozilla/bergamot-translator) and can be used by
[firefox-translations](https://github.com/mozilla/firefox-translations) web extension. This work is a part of [Bergamot](https://browser.mt/) project  that focuses on improving client-side machine translation in a web browser.

The pipeline is capable of training a translation model for a language pair end to end. 
Translation quality depends on chosen datasets, data cleaning procedures and hyperparameters. 
Some settings, especially low resource languages might require extra tuning.

It uses fast translation engine [Marian](https://marian-nmt.github.io) 
and [Snakemake](https://snakemake.github.io/) framework for workflow management and parallelization.

## System requirements

### Local mode

- Ubuntu 18.04 (it can work on other Linux distributions, but might require `setup` scripts fixes; see more details in [marian installation instructions](https://marian-nmt.github.io/quickstart/)).
- One or several Nvidia GPUs with CUDA drivers installed and at least 8 GB of memory.
- At least 16 CPU cores ( some steps of the pipeline utilize multiple cores pretty well, so the more the better).
- 64 GB RAM (128 GB+ might be required for bigger datasets)
- 200+ GB of disk space ( mostly for datasets and transformations ). 
  It depends on chosen datasets and can be significantly higher.
  
It was tested on: 
- Ubuntu 18.04
- 56 core Xeon server
- 128 GB of RAM
- x8 NVIDIA RTX 2080 GPUs with 12 GB of memory
- CUDA 11.2
- 100 GB of local disk space
- Many terabytes of sshfs mounted storage

### Cluster mode

- Slurm cluster with CPU and Nvidia GPU nodes with CUDA
- Singularity module if running with containerization (recommended)
- If running without containerization, there is no procedure to configure environment automatically.
  All the required modules (for example `parallel`) should be preinstalled and loaded in ~/.bashrc

It was tested on [CSD3 HPC](https://docs.hpc.cam.ac.uk/hpc/index.html) using Singularity containers.

### Cloud mode

Snakemake workflows can work on Kubernetes, Google Cloud Life Sciences and other cloud platforms. 
The pipeline was not tested in this mode and might require modificaiton.

Please refer to [Cloud execution](https://snakemake.readthedocs.io/en/stable/executing/cloud.html) section of Snakemake documentation.

It is also possible to deploy Slurm cluster in the cloud. Fore example, using [Slurm on Google Cloud Platform](https://github.com/SchedMD/slurm-gcp).

## Configuration

0. Clone the repo:
``` 
git clone https://github.com/mozilla/firefox-translations-training.git
cd firefox-translations-training
```
1. Adjust settings in the `Makefile` 
    - Configure paths to a data storage `SHARED_ROOT` and CUDA libraries `CUDA_DIR`
    - Adjust `GPUS` - number of GPUs per task that requires GPU and `WORKSPACE` - GPU memory pre-allocation for Marian
    - Choose a config file to use (`configs/config.test.yml` is useful for testing)
    - (Cluster mode) Adjust `CLUSTER_CORES` - total number of CPU cores to use on a cluster simultaneously
2. Configure experiment and datasets in the chosen application config (for example `configs/config.prod.yml`)
3. Change source code if needed for the experiment
4. (Cluster mode) Adjust Snakemake and cluster settings in the cluster profile.
   For Slurm: `profiles/slurm/config.yml` and `profiles/slurm/config.cluster.yml`
   You can also modify `profiles/slurm/submit.sh` or create a new Snakemake [profile](https://github.com/Snakemake-Profiles).
5. (Cluster mode) It might require further tuning of requested resources in `Snakemake` file:
    - Use `threads` for a rule to adjust parallelism
    - Use `resources: mem_mb=<memory>` to adjust total memory requirements per task 
      (default is set in `profile/slurm/config.yaml`)

## Installation

See also [Snakemake installation](https://snakemake.readthedocs.io/en/stable/getting_started/installation.html)

1. Install Mamba - fast Conda package manager

```
make conda
```

2. Install Snakemake

```
make snakemake
```

3. Update git submodules

```
make git-modules
```

4. (Optional) Install Singularity if running with containerization 

Local mode: See [Singularity installation](https://sylabs.io/guides/3.8/user-guide/quick_start.html), requries root

Cluster mode: 

```
module load singularity
```

5. (Optional) Prepare a container image if using Singularity

    
Either pull the prebuilt image:

```
make pull
```

Or build it (requires root):

```
make build
```

## Running

Dry run first to check that everything was installed correctly:

```
make dry-run
```

### Local mode

#### Without containerization

```
make run-local
```
To test the whole pipeline end to end (it supposed to run quickly and does not train anything useful):

```
make test
```
Or run
#### With containerization
```
make run-local-container
```



### Cluster mode

To run on Slurm

without containerization:
```
make run-slurm
```
with containerization (recommended):
```
make run-slurm-container
```
### Specific target

By default, all Snakemake rules are executed. To run the pipeline up to a specific rule use:
```
make <run-command> TARGET=<non-wildcard-rule>
```

For example, collect corpus first:
```
make run-local TARGET=merge_corpus
```


### Using Snakepit

Snakepit is a Mozilla machine learning job scheduler.
See [Snakepit installation](https://github.com/mozilla/snakepit-client).

#### To run the pipeline interactively:

1. Create an empty directory 
2. Create a file `.compute` in the directory:
```
# install any development dependencies
apt-get update
apt-get install -y tmux htop nano
curl -fsSL https://code-server.dev/install.sh | sh

while true; do : ; sleep 1000; done
```
3. Run `pit run "<user-name>-interactive" "[8:g2080]"`
4. Run `pit status` to check the job id
4. Run `pit exec <job-id> -- bash`
5. After attaching run `tmux`
6. Follow configuration and installation procedures for the local mode without containerization
7. Run `make run-local`

 
#### To download exported models:

```
pit pull home firefox-translations-training/models/ru-en/test/exported/model.ruen.intgemm.alphas.bin.gz .
pit pull home firefox-translations-training/models/ru-en/test/exported/lex.50.50.ruen.s2t.bin.gz .
pit pull home firefox-translations-training/models/ru-en/test/exported/vocab.ruen.spm.gz .
```

### Reporting

To create a Snakemake [html report](https://snakemake.readthedocs.io/en/stable/snakefiles/reporting.html), run:
```
make report
```

### Results

See `Snakefile` file for directory structure documentation.

The main directories inside `SHARED_ROOT` are:
- `data/<lang_pair>/<experiment>` - data produced by the pipeline jobs
- `logs/<lang_pair>/<experiment>` - logs of the jobs for troubleshooting
- `experiments/<lang_pair>/<experiment>` - saved experiment settings for future reference
- `models/<lang_pair>/<experiment>` - all models produced by the pipeline. The final compressed models are in `exported` folder.


## Pipeline steps

The steps are based on [train-student](https://github.com/browsermt/students/tree/master/train-student) recipe.

Step | Description | Bottleneck | Comments
--- | --- | --- | ---
Installation | Installing dependencies and compiling | CPU | Takes ~1 hour
Data downloading | Downloads datasets, samples sentences | Network, Disk | Time depends on dataset size, sampling of huge mono datasets (100M+ sentences) is the most intensive operation.
Data cleaning | Basic preprocessing, dataset specific, language specific, rule based and other attempts to clean noisy data in parallel and mono datasets | CPU | Good parallelization across CPU cores. To make cleaning of a new language more efficient add it to [clean_parallel.py](/pipeline/clean/tools/clean_parallel.py).
Bicleaner | Filters noisy sentence pairs in a parallel corpus using [bicleaner](https://github.com/bitextor/bicleaner) or [bicleaner-ai](https://github.com/bitextor/bicleaner-ai) depending on available language packs. | CPU, GPU | If there are no pretrained language packs for bicleaner-ai, it uses bicleaner. If there are no ones for bicleaner either, this step is skipped. Cleaning thresholds are configurable per dataset, see [Dataset cleaning](##Dataset cleaning).
Merge and dedupe | Merges clean dataset and applies deduplicaiton | CPU, Disk | 
Training s2s | Trains a backward shallow s2s model, which is useful for back-translations and ce-filtering | GPU | Inspired by a [marian example](https://github.com/marian-nmt/marian-examples/tree/master/training-basics-sentencepiece).
Augmentation with back-translations | Translates mono corpus combined from monolingual datasets in target language using shallow s2s model. | GPU | It is more useful for low-resource languages and can be skipped for others.
Training teacher | Trains an ensemble of big transformer models on augmented dataset | GPU | You might want to adjust [early stopping](pipeline/train/configs/training/teacher.transformer.train.yml) or `after-epochs` parameters depending on datasets size.
Continue training teacher | Continue training an ensemble of teachers on parallel data only | GPU | You might want to adjust [early stopping](pipeline/train/configs/training/teacher.transformer.train.yml) parameters depending on datasets size.
Translation by teacher | Translates a corpus and monolingual data combined from `MONO_DATASETS_SRC` using the teacher model (ensemble is not supported yet) | GPU | The slowest part of the pipeline. Can take days. It is possible to speed it up launching the same scripts ([corpus](pipeline/translate/translate-corpus.sh), [mono](pipeline/translate/translate-mono.sh)) in parallel from another machine with access to the same network directory.
Cross-entropy filtering | Scores translated corpus with backward s2s model and removes a part of the corpus with the lowest scores to reduce noise | GPU, CPU, Disk | At this point we work with huge datasets, so it utilizes copying to a local disk to make things faster.
Training alignments and shortlist | Trains alignments using [fast_align](https://github.com/clab/fast_align) and extracts lexical shortlist using [extract_lex](https://github.com/marian-nmt/extract-lex) tool | CPU, Disk | Some tools requires uncompressed datasets on disk and they are huge at this point. Data is copied to a local disk to make things faster. Might take 100+GB of local disk depending on a dataset size. Good CPU parallelization.
Training student | Trains a small transformer student model on filtered data and using alignments | GPU |
Fine-tuning student | Finetunes the student model by emulating 8bit GEMM during training | GPU | Converges very quickly and then degrades. It's quick but you might want to reduce early stopping threshold.
Quantizaiton |  Applies 8 bit quantization to the fined-tuned student model and evaluates on CPU | CPU | CPU threads must be set to 1 for this step.
Evaluation |  Calculates metrics for all models (BLEU, chrf) using [SacreBLEU](https://github.com/mjpost/sacrebleu) | GPU | Uses `datasets.test` configuration section.
Export | Exports trained model and shortlist to (bergamot-translator)(https://github.com/mozilla/bergamot-translator) format | |

## Dataset importers

Dataset importers can be used in `datasets` sections of experiment config.

Example:
```
  train:
    - opus_ada83/v1
    - mtdata_newstest2014_ruen
```

Data source | Prefix | Name examples | Type | Comments
--- | --- | --- | ---| ---
[MTData](https://github.com/thammegowda/mtdata) | mtdata | newstest2017_ruen | corpus | Supports many datasets. Run `mtdata list -l ru-en` to see datasets for a specific language pair.
[OPUS](opus.nlpl.eu/) | opus | ParaCrawl/v7.1 | corpus | Many open source datasets. Go to the website, choose a language pair, check links under Moses column to see what names and version is used in a link.
[SacreBLEU](https://github.com/mjpost/sacrebleu) | sacrebleu | wmt20 | corpus | Official evaluation datasets available in SacreBLEU tool. Recommended to use in `TEST_DATASETS`. Look up supported datasets and language pairs in `sacrebleu.dataset` python module.
[Flores](https://github.com/facebookresearch/flores) | flores | dev, devtest | corpus | Evaluation dataset from Facebook that supports 100 languages.
Custom parallel | custom-corpus | /tmp/test-corpus | corpus | Custom parallel dataset that is already downloaded to a local disk. The dataset name is an absolute path prefix without ".lang.gz"
[Paracrawl](https://paracrawl.eu/) | paracrawl-mono | paracrawl8 | mono | Datasets that are crawled from the web. Only [mono datasets](https://paracrawl.eu/index.php/moredata) are used in this importer. Parallel corpus is available using opus importer.
[News crawl](http://data.statmt.org/news-crawl) | news-crawl | news.2019 | mono | Some news monolingual datasets from [WMT21](https://www.statmt.org/wmt21/translation-task.html)
[Common crawl](https://commoncrawl.org/) | commoncrawl | wmt16 | mono | Huge web crawl datasets. The links are posted on [WMT21](https://www.statmt.org/wmt21/translation-task.html)
Custom mono | custom-mono | /tmp/test-mono | mono | Custom monolingual dataset that is already downloaded to a local disk. The dataset name is an absolute path prefix without ".lang.gz"

You can also use [find-corpus](pipeline/utils/find-corpus.py) tool to find all datasets for an importer and get them formatted to use in config.

```
conda env create -f envs/corpus.yml 
conda activate corpus
python utils/find-corpus.py en ru opus
```

### Adding a new importer

Just add a shell script to [corpus](pipeline/data/importers/corpus) or [mono]() which is named as `<prefix>.sh` 
and accepts the same parameters as the other scripts from the same folder.

## Dataset fixing

Some datasets require fixes like detokenization. Dataset and language specific fixes are implemented in [pipeline/clean/fixes]([pipeline/clean/fixes]).
Naming convention: 
- `<dataset_name>.sh` for parallel dataset cleaning
- `<dataset_name>.<lang>.sh` for language specific cleaning of parallel or monolingual dataset
- `/` in dataset name should be replaced with `_`

## Dataset cleaning
Some parallel datasets require more aggressive filtering.
Dataset specific Bicleaner thretholds can be set in config. Example:

```angular2html
experiment:
...
  bicleaner:
    default-threshold: 0.5
    dataset-thresholds:
      mtdata_neulab_tedtalksv1_train: 0.6
```

## Utilities

### Tensorboard

To see training graphs run tensorboard:

```
make install-tensorboard
make tensorboard
```

Then port forward 6006.

## Directory structure
    
    ├ data
    │   └ ru-en
    │      └ test
    │        ├ original
    │        │   ├ corpus
    │        │   │   ├ mtdata_JW300.en.gz
    │        │   │   └ mtdata_JW300.ru.gz
    │        │   ├ devset
    │        │   │   ├ flores_dev.en.gz
    │        │   │   └ flores_dev.ru.gz
    │        │   ├ eval
    │        │   │   ├ sacrebleu_wmt20.en.gz
    │        │   │   └ sacrebleu_wmt20.ru.gz
    │        │   ├ mono
    │        │   │   ├ news-crawl_news.2020.ru.gz
    │        │   │   └ news-crawl_news.2020.en.gz
    │        │   ├ devset.ru.gz
    │        │   └ devset.en.gz
    │        ├ clean
    │        │   ├ corpus
    │        │   │   ├ mtdata_JW300.en.gz
    │        │   │   └ mtdata_JW300.ru.gz
    │        │   ├ mono
    │        │   │   ├ news-crawl_news.2020.ru.gz
    │        │   │   └ news-crawl_news.2020.en.gz
    │        │   ├ mono.ru.gz
    │        │   └ mono.en.gz
    │        ├ biclean
    │        │   ├ corpus
    │        │   │   ├ mtdata_JW300.en.gz
    │        │   │   └ mtdata_JW300.ru.gz
    │        │   ├ corpus.ru.gz
    │        │   ├ corpus.en.gz
    │        ├ translated
    │        │   ├ mono.ru.gz
    │        │   └ mono.en.gz
    │        ├ augmented
    │        │   ├ corpus.ru.gz
    │        │   └ corpus.en.gz
    │        ├ alignment
    │        │   ├ corpus.aln.gz
    │        │   └ lex.s2t.pruned.gz
    │        ├ merged
    │        │   ├ corpus.ru.gz
    │        │   └ corpus.en.gz
    │        └ filtered
    │            ├ corpus.ru.gz
    │            └ corpus.en.gz
    ├ models
    │   ├ ru-en
    │   │   └ test
    │   │      ├ teacher
    │   │      ├ student
    │   │      ├ student-finetuned
    │   │      ├ speed
    │   │      ├ evaluation
    │   │      │  ├ backward
    │   │      │  ├ teacher0
    │   │      │  ├ teacher1
    │   │      │  ├ teacher-ensemble
    │   │      │  ├ student
    │   │      │  ├ student-finetuned
    │   │      │  └ speed
    │   │      └ exported
    │   ├ en-ru
    │      └ test
    │         └ backward
    │
    ├ experiments
    │   └ ru-en
    │      └ test
    │         └ config.sh
    ├ logs
    │   └ ru-en
    │      └ test
    │         └ clean_corpus.log

## Development

### Architecture

All steps are independent and contain scripts that accept arguments, read input files from disk and output the results to disk.
It allows writing the steps in any language (currently it's historically mostly bash and Python) and 
represent the pipeline as directed acyclic graph (DAG).

Snakemake workflow manager infers the DAG implicitly from the specified inputs and outputs of the steps. The workflow manager checks which files are missing and runs the corresponding jobs either locally or on a cluster depending on configuration. 

Snakemake parallelizes steps that can be executed simultniously. It is especially usefull for teacher ensemble training and translation.

The main snakemkae process (scheduler) should be launched interactively. It runs job processes on the worker nodes in cluster mode or on a local machine in local mode.

### Conventions
  
- Scripts inside the `pipeline` directory are independent and operate only using input arguments, input files 
  and global envs.
  
- All scripts test expected environment variables early.

- If a script step fails, it can be safely retried.

- Ideally every script should start from the last unfinished step, 
  checking presence of intermediate results of previous steps.

- A script fails as early as possible.

- Maximum bash verbosity is set for easy debugging.

- Input data is always read only.

- Output data is placed to a new folder for script results.
  
- It is expected that the specified output folder might not exist and should be created by the script.

- A script creates a folder for intermediate files and cleans it in the end 
  unless intermediate files are useful for retries.
    
- Global variables are upper case, local variable are lower case.

- Scripts should utilize resources provided by Snakemake (number of threads, memory).
  

## References

1. V. M. Sánchez-Cartagena, M. Bañón, S. Ortiz-Rojas and G. Ramírez-Sánchez, 
"[Prompsit's submission to WMT 2018 Parallel Corpus Filtering shared task](http://www.statmt.org/wmt18/pdf/WMT116.pdf)",
in *Proceedings of the Third Conference on Machine Translation, Volume 2: Shared Task Papers*.
Brussels, Belgium: Association for Computational Linguistics, October 2018

2. Gema Ramírez-Sánchez, Jaume Zaragoza-Bernabeu, Marta Bañón and Sergio Ortiz Rojas 
"[Bifixer and Bicleaner: two open-source tools to clean your parallel data.](https://eamt2020.inesc-id.pt/proceedings-eamt2020.pdf#page=311)",
in *Proceedings of the 22nd Annual Conference of the European Association for Machine Translation*.
Lisboa, Portugal: European Association for Machine Translation, November 2020
   
3. Mölder, F., Jablonski, K.P., Letcher, B., Hall, M.B., Tomkins-Tinch, C.H., Sochat, V., Forster, J., Lee, S., Twardziok, S.O., Kanitz, A., Wilm, A., Holtgrewe, M., Rahmann, S., Nahnsen, S., Köster, J., 2021. Sustainable data analysis with Snakemake. F1000Res 10, 33.
