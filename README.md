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
1. Adjust settings in the `Makefile` (paths, which config to use, resources etc.)
2. Configure experiment and datasets in the chosen application config (for example `configs/config.prod.yml`)
3. (Cluster mode) Adjust Snakemake and cluster settings in the cluster profile.
   For Slurm: `profiles/slurm/config.yml` and `profiles/slurm/config.cluster.yml`
4. Change source code if needed for the experiment

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

Without containerization:
```
make run-local
```
With containerization:
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

### Tensorboard

Using interactive mode, run:
```
cd ./pipeline/train/tensorboard
MODELS=<absolute_path_to_models_directory> bash tensorboard.sh
```

Tensorboard will be available on port 6006

## Pipeline steps

The steps are based on [train-student](https://github.com/browsermt/students/tree/master/train-student) recipe.

Step | Description | Bottleneck | Comments
--- | --- | --- | ---
Installation | Installing dependencies and compiling | CPU | Takes ~1 hour
Data downloading | Downloads datasets, samples sentences | Network, Disk | Time depends on dataset size, sampling of huge mono datasets (100M+ sentences) is the most intensive operation.
Data cleaning | Basic preprocessing, language specific, rule based, deduplication,  and other attempts to clean noisy data in parallel and mono datasets | CPU | Good parallelization across CPU cores. To make cleaning of a new language more efficient add it to [clean_parallel.py](/pipeline/clean/clean_parallel.py).
Bicleaner | Filters noisy sentence pairs in a parallel corpus using [bicleaner](https://github.com/bitextor/bicleaner) or [bicleaner-ai](https://github.com/bitextor/bicleaner-ai) depending on available language packs. | CPU, GPU | If there are no pretrained language packs for bicleaner-ai, it uses bicleaner. If there are no ones for bicleaner either, this step is skipped. Cleaning threshold is controlled by `BICLEANER_THRESHOLD` config setting.
Training s2s | Trains a backward shallow s2s model, which is useful for back-translations and ce-filtering | GPU | Inspired by a [marian example](https://github.com/marian-nmt/marian-examples/tree/master/training-basics-sentencepiece).
Augmentation with back-translations | Translates mono corpus combined from `MONO_DATASETS_TRG` using shallow s2s model. | GPU | It is more useful for low-resource languages and can be skipped for others.
Training teacher | Trains one or multiple big transformer models | GPU | You might want to adjust [early stopping](pipeline/train/configs/training/teacher.transformer.train.yml) parameters depending on datasets size. Inspired by [transformer](https://github.com/marian-nmt/marian-examples/tree/master/transformer) and [wmt2017-uedin](https://github.com/marian-nmt/marian-examples/tree/master/wmt2017-uedin) marian examples and extended with [SentencePiece](https://github.com/google/sentencepiece).
Translation by teacher | Translates a corpus and monolingual data combined from `MONO_DATASETS_SRC` using the teacher model (ensemble is not supported yet) | GPU | The slowest part of the pipeline. Can take days. It is possible to speed it up launching the same scripts ([corpus](pipeline/translate/translate-corpus.sh), [mono](pipeline/translate/translate-mono.sh)) in parallel from another machine with access to the same network directory.
Cross-entropy filtering | Scores translated corpus with backward s2s model and removes a part of the corpus with the lowest scores to reduce noise | GPU, CPU, Disk | At this point we work with huge datasets, so it utilizes copying to a local disk to make things faster.
Training alignments and shortlist | Trains alignments using [fast_align](https://github.com/clab/fast_align) and extracts lexical shortlist using [extract_lex](https://github.com/marian-nmt/extract-lex) tool | CPU, Disk | Some tools requires uncompressed datasets on disk and they are huge at this point. Data is copied to a local disk to make things faster. Might take 100+GB of local disk depending on a dataset size. Good CPU parallelization.
Training student | Trains a small transformer student model on filtered data and using alignments | GPU | Run [Tensorboard](utils/tensorboard/tensorboard.sh) manually to see training visualization.
Fine-tuning student | Finetunes the student model by emulating 8bit GEMM during training | GPU | Converges very quickly and then degrades. It's quick but you might want to reduce early stopping threshold.
Quantizaiton |  Applies 8 bit quantization to the fined-tuned student model and evaluates on CPU | CPU | CPU threads must be set to 1 for this step.
Export | Exports trained model and shortlist to (bergamot-translator)(https://github.com/mozilla/bergamot-translator) format | |

## Datasets importers

Dataset importers can be used in `TRAIN_DATASETS, DEVTEST_DATASETS, MONO_DATASETS_SRC, MONO_DATASETS_TRG` config settings.

Example:
```
TRAIN_DATASETS="opus_OPUS-ParaCrawl/v7.1 mtdata_newstest2019_ruen"
TEST_DATASETS="sacrebleu_wmt20 sacrebleu_wmt18"
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

Example:

`python ./pipeline/utils/find-corpus.py en ru opus`

### Adding a new importer

Just add a shell script to [corpus](pipeline/data/importers/corpus) or [mono]() which is named as `<prefix>.sh` 
and accepts the same parameters as the other scripts from the same folder.

## Development

### Architecture

The pipeline is designed with workflow manager integration in mind (like [Airflow](https://airflow.apache.org/), 
[Kubeflow pipelines](https://www.kubeflow.org/docs/components/pipelines/overview/pipelines-overview/), 
[Snakemake](https://snakemake.readthedocs.io/en/stable/) and others).

All steps are independent and contain scripts that accept input arguments, read input files from disk and output the results on disk.
It allows to write the steps in any language (currently it's historically mostly bash and Python) and 
represent the pipeline as a DAG to be compatible with workflow managers.

The main script `run.sh` can be easily replaced with a DAG definition in workflow manager terms. 
A workflow manager will provide easy resource management, parallelization, monitoring and scheduling which will allow horizontal scalability required to train massive number of langauges.

At the same time it is possible to run it all locally end to end or to do interactive experimentation running specific scripts manually.

### Conventions

- All scripts work with respect to repo root directory. 
  It allows to not think about relative paths and execution folders.
  
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