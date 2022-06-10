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
- CUDNN installed
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
- Many terabytes of NFS mounted storage

### Cluster mode

- Slurm cluster with CPU and Nvidia GPU nodes
- CUDA 11.2 ( it was also tested on 11.5)
- CUDNN library installed
- Singularity module if running with containerization (recommended)
- If running without containerization, there is no procedure to configure the environment automatically.
  All the required modules (for example `parallel`) should be preinstalled and loaded in ~/.bashrc

It was tested on Mozilla Slurm cluster using Singularity containers.
The pipeline can also be launched on [CSD3 HPC](https://docs.hpc.cam.ac.uk/hpc/index.html) but it was not fully tested.

### Cloud mode

Snakemake workflows can work on Kubernetes, Google Cloud Life Sciences and other cloud platforms. 
The pipeline was not tested in this mode and might require modification.

Please refer to [Cloud execution](https://snakemake.readthedocs.io/en/stable/executing/cloud.html) section of Snakemake documentation.

It is also possible to deploy Slurm cluster in the cloud. For example, using [Slurm on Google Cloud Platform](https://github.com/SchedMD/slurm-gcp).

## Configuration

0. Clone the repo:
``` 
git clone https://github.com/mozilla/firefox-translations-training.git
cd firefox-translations-training
```
1. Choose a [Snakemake profile](https://github.com/Snakemake-Profiles) from `profiles/` or create a new one 
2. Adjust paths in the `Makefile` if needed and set `PROFILE` variable to the name of your profile
3. Adjust Snakemake and workflow settings in the `profiles/<profile>/config.yaml`, see [Snakemake CLI reference](https://snakemake.readthedocs.io/en/stable/executing/cli.html) for details
4. Configure experiment and datasets in `configs/config.prod.yml` (or `configs/config.test.yml` for test run)
5. Change source code if needed for the experiment
6. **(Cluster mode)** Adjust cluster settings in the cluster profile.
   For `slurm-moz`: `profiles/slurm-moz/config.cluster.yml`
   You can also modify `profiles/slurm-moz/submit.sh` or create a new Snakemake [profile](https://github.com/Snakemake-Profiles).
7. **(Cluster mode)** It might require further tuning of requested resources in `Snakemake` file:
    - Use `threads` for a rule to adjust parallelism
    - Use `resources: mem_mb=<memory>` to adjust total memory requirements per task 
      (default is set in `profile/slurm-moz/config.yaml`)

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

For example,
```
module load singularity
```
but the way to load Singularity depends on cluster installation

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

To run the pipeline:
```
make run
```

To test the whole pipeline end to end (it is supposed to run relatively quickly and does not train anything useful):

```
make test
```
You can also run a speicific profile or config by overriding variables from Makefile
```
make run PROFILE=slurm-moz CONFIG=configs/config.test.yml
```

### Specific target

By default, all Snakemake rules are executed. To run the pipeline up to a specific rule use:
```
make run TARGET=<non-wildcard-rule-or-path>
```
For example, collect corpus first:
```
make run TARGET=merge_corpus
```

You can also use the full file path, for example:
```
make run TARGET=/models/ru-en/bicleaner/teacher-base0/model.npz.best-ce-mean-words.npz
```
### Rerunning

If you want to rerun a specific step or steps, you can delete the result files that are expected in the Snakemake rule output.
Snakemake might complain about a missing file and suggest to run it with `--clean-metadata` flag. In this case run:
```
make clean-meta TARGET=<missing-file-name>
```
and then as usual:
```
make run
```

### Reporting

To create a Snakemake [html report](https://snakemake.readthedocs.io/en/stable/snakefiles/reporting.html), run:
```
make report
```

### Results

See [Directory Structure](#directory-structure) section.

The main directories inside `SHARED_ROOT` are:
- `data/<lang_pair>/<experiment>` - data produced by the pipeline jobs
- `logs/<lang_pair>/<experiment>` - logs of the jobs for troubleshooting
- `experiments/<lang_pair>/<experiment>` - saved experiment settings for future reference
- `models/<lang_pair>/<experiment>` - all models produced by the pipeline. The final compressed models are in `exported` folder.

#### Exported models example

```
/models/ru-en/test/exported/model.ruen.intgemm.alphas.bin.gz
/models/ru-en/test/exported/lex.50.50.ruen.s2t.bin.gz
/models/ru-en/test/exported/vocab.ruen.spm.gz
```

## Pipeline steps

The steps are based on [train-student](https://github.com/browsermt/students/tree/master/train-student) recipe.

Step | Description | Bottleneck | Comments
--- | --- | --- | ---
Installation | Installing dependencies and compiling | CPU | Takes ~1 hour
Data downloading | Downloads datasets, samples sentences | Network, Disk | Time depends on dataset size, sampling of huge mono datasets (100M+ sentences) is the most intensive operation.
Data cleaning | Basic preprocessing, dataset specific, language specific, rule based and other attempts to clean noisy data in parallel and mono datasets | CPU | Good parallelization across CPU cores. To make cleaning of a new language more efficient add it to [clean_parallel.py](/pipeline/clean/tools/clean_parallel.py).
Bicleaner | Filters noisy sentence pairs in a parallel corpus using [bicleaner](https://github.com/bitextor/bicleaner) or [bicleaner-ai](https://github.com/bitextor/bicleaner-ai) depending on available language packs. | CPU, GPU | If there are no pretrained language packs for bicleaner-ai, it uses bicleaner. If there are no ones for bicleaner either, this step is skipped. Cleaning thresholds are configurable per dataset, see [Dataset cleaning](##Dataset cleaning).
Merge and dedupe | Merges clean dataset and applies deduplicaiton | CPU, Disk | 
Training vocabulary | Trains [SentencePiece](https://github.com/google/sentencepiece) vocabulary/tokenizer model on parallel corpus. | CPU |
Training s2s | Trains a backward shallow s2s model, which is useful for back-translations and ce-filtering | GPU | Inspired by a [marian example](https://github.com/marian-nmt/marian-examples/tree/master/training-basics-sentencepiece).
Augmentation with back-translations | Translates mono corpus combined from monolingual datasets in target language using shallow s2s model. | GPU | It is more useful for low-resource languages and can be skipped for others.
Training teacher | Trains an ensemble of big transformer models on augmented dataset | GPU | You might want to adjust [early stopping](pipeline/train/configs/training/teacher.transformer.train.yml) or `after-epochs` parameters depending on datasets size.
Fine-tuning teacher | Continue training an ensemble of teachers on parallel data only | GPU | You might want to adjust [early stopping](pipeline/train/configs/training/teacher.transformer.train.yml) parameters depending on datasets size.
Translation by teacher | Translates a corpus and monolingual data combined from configurable `dataset.mono-src` using the ensemble of teacher models | GPU | The slowest part of the pipeline. Can take days. It is possible to speed it up by using multiple nodes in cluster mode.
Cross-entropy filtering | Scores translated corpus with backward s2s model and removes a part of the corpus with the lowest scores to reduce noise | GPU, CPU, Disk | At this point we work with huge datasets. Very disk intensive.
Training alignments and shortlist | Trains alignments using [fast_align](https://github.com/clab/fast_align) and extracts lexical shortlist using [extract_lex](https://github.com/marian-nmt/extract-lex) tool | CPU, Disk | Some tools require uncompressed datasets on disk and they are huge at this point. Good CPU parallelization.
Training student | Trains a small transformer student model on filtered data and using alignments. Shuffling in RAM might fail if dataset is huge and there's not enough RAM on the machine, so it's recommended to remove it and use `shuffle: batches` marian settings (see [issue](https://github.com/mozilla/firefox-translations-training/issues/21)).  | GPU |
Fine-tuning student | Finetunes the student model by emulating 8bit GEMM during training | GPU | Converges very quickly and then degrades. It's quick but you might want to reduce early stopping threshold.
Quantizaiton |  Applies 8 bit quantization to the fined-tuned student model and runs evaluation on CPU | CPU | CPU threads must be set to 1 for this step.
Evaluation |  Calculates metrics for all models (BLEU, chrf) using [SacreBLEU](https://github.com/mjpost/sacrebleu) | GPU | Uses `datasets.test` configuration section.
Export | Exports trained model and shortlist to (bergamot-translator)(https://github.com/mozilla/bergamot-translator) format | |

## Dataset importers

Dataset importers can be used in `datasets` sections of the config.

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
[SacreBLEU](https://github.com/mjpost/sacrebleu) | sacrebleu | wmt20 | corpus | Official evaluation datasets available in SacreBLEU tool. Recommended to use in `datasets:test` config section. Look up supported datasets and language pairs in `sacrebleu.dataset` python module.
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
python utils/find-corpus.py en ru mtdata
python utils/find-corpus.py en ru sacrebleu
```
Make sure to check licenses of the datasets before using them.

### Adding a new importer

Just add a shell script to [corpus](pipeline/data/importers/corpus) or [mono](pipeline/data/importers/mono) which is named as `<prefix>.sh` 
and accepts the same parameters as the other scripts from the same folder.

## Dataset fixing

Some datasets require fixes like detokenization. Dataset and language specific fixes are implemented in [pipeline/clean/fixes](pipeline/clean/fixes).
Naming convention: 
- `<dataset_name>.sh` for parallel dataset cleaning
- `<dataset_name>.<lang>.sh` for language specific cleaning of parallel or monolingual dataset
- `/` in dataset name should be replaced with `_`

## Dataset cleaning
Some parallel datasets require more aggressive filtering.
Dataset specific Bicleaner thresholds can be set in config. 
`0` means skipping filtering entirely (useful for Paracrawl).

Example:

```
experiment:
...
  bicleaner:
    default-threshold: 0.5
    dataset-thresholds:
      opus_ParaCrawl/v8: 0
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
    │   └ ru-en
    │       └ test
    │          ├ backward
    │          ├ teacher-base0
    │          ├ teacher-base1
    │          ├ teacher-finetuned0
    │          ├ teacher-finetuned1
    │          ├ student
    │          ├ student-finetuned
    │          ├ speed
    │          ├ evaluation
    │          │  ├ backward
    │          │  ├ teacher-base0
    │          │  ├ teacher-base1
    │          │  ├ teacher-finetuned0
    │          │  ├ teacher-finetuned1
    │          │  ├ teacher-ensemble
    │          │  ├ student
    │          │  ├ student-finetuned
    │          │  └ speed
    │          └ exported
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
represent the pipeline as a directed acyclic graph (DAG).

Snakemake workflow manager infers the DAG implicitly from the specified inputs and outputs of the steps. The workflow manager checks which files are missing and runs the corresponding jobs either locally or on a cluster depending on the configuration. 

Snakemake parallelizes steps that can be executed simultaneously. It is especially useful for teacher ensemble training and translation.

The main Snakemake process (scheduler) should be launched interactively. It runs job processes on the worker nodes in cluster mode or on a local machine in local mode.

### Conventions
  
- Scripts inside the `pipeline` directory are independent and operate only using input arguments, input files 
  and global envs.
  
- All scripts test expected environment variables early.

- If a script step fails, it can be safely retried.

- Ideally, every script should start from the last unfinished step, 
  checking presence of intermediate results of previous steps.

- A script fails as early as possible.

- Maximum bash verbosity is set for easy debugging.

- Input data is always read only.

- Output data is placed in a new folder for script results.
  
- It is expected that the specified output folder might not exist and should be created by the script.

- A script creates a folder for intermediate files and cleans it in the end 
  unless intermediate files are useful for retries.
    
- Global variables are upper case, local variables are lower case.

- Scripts should utilize resources provided by Snakemake (number of threads, memory).
  

## References

Here is a list of selected publications on which the training pipeline is based. You can find more relevant publications on [Bergamot project web-site](https://browser.mt/publications).

1. V. M. Sánchez-Cartagena, M. Bañón, S. Ortiz-Rojas and G. Ramírez-Sánchez, 
"[Prompsit's submission to WMT 2018 Parallel Corpus Filtering shared task](http://www.statmt.org/wmt18/pdf/WMT116.pdf)",
in *Proceedings of the Third Conference on Machine Translation, Volume 2: Shared Task Papers*.
Brussels, Belgium: Association for Computational Linguistics, October 2018

2. Gema Ramírez-Sánchez, Jaume Zaragoza-Bernabeu, Marta Bañón and Sergio Ortiz Rojas 
"[Bifixer and Bicleaner: two open-source tools to clean your parallel data.](https://eamt2020.inesc-id.pt/proceedings-eamt2020.pdf#page=311)",
in *Proceedings of the 22nd Annual Conference of the European Association for Machine Translation*.
Lisboa, Portugal: European Association for Machine Translation, November 2020
   
3. Mölder F, Jablonski KP, Letcher B, et al. [Sustainable data analysis with Snakemake](https://pubmed.ncbi.nlm.nih.gov/34035898/). F1000Res. 2021;10:33. Published 2021 Jan 18. doi:10.12688/f1000research.29032.2


4. [Edinburgh’s Submissions to the 2020 Machine Translation Efficiency Task](https://aclanthology.org/2020.ngt-1.26) (Bogoychev et al., NGT 2020)

5. [From Research to Production and Back: Ludicrously Fast Neural Machine Translation](https://aclanthology.org/D19-5632) (Kim et al., EMNLP 2019)

6. [The University of Edinburgh’s Submissions to the WMT19 News Translation Task](https://aclanthology.org/W19-5304) (Bawden et al., 2019)

7. Jörg Tiedemann, 2012, [Parallel Data, Tools and Interfaces in OPUS](http://www.lrec-conf.org/proceedings/lrec2012/pdf/463_Paper.pdf). In Proceedings of the 8th International Conference on Language Resources and Evaluation (LREC'2012)
8. [The University of Edinburgh’s Neural MT Systems for WMT17](https://arxiv.org/abs/1708.00726), Rico Sennrich, Alexandra Birch, Anna Currey, Ulrich Germann, Barry Haddow, Kenneth Heafield, Antonio Valerio Miceli Barone, and Philip Williams. In Proceedings of the EMNLP 2017 Second Conference on Machine Translation (WMT17), 2017.
9. [Marian: Fast Neural Machine Translation in C++](https://arxiv.org/abs/1804.00344), Marcin Junczys-Dowmunt, Roman Grundkiewicz, Tomasz Dwojak, Hieu Hoang, Kenneth Heafield, Tom Neckermann, Frank Seide, Ulrich Germann, Alham Fikri Aji, Nikolay Bogoychev, Andre ́ F. T. Martins, and Alexandra Birch.
10. [Improving Neural Machine Translation Models with Monolingual Data](https://arxiv.org/abs/1511.06709), Rico Sennrich,Barry Haddow,Alexandra Birch, Proceedings of the 54th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), 2016.
11. [A Call for Clarity in Reporting BLEU Scores](https://aclanthology.org/W18-6319) (Post, 2018)
12. [The FLORES-101 Evaluation Benchmark for Low-Resource and Multilingual Machine Translation](https://ai.facebook.com/research/publications/the-flores-101-evaluation-benchmark-for-low-resource-and-multilingual-machine-translation), Facebook
13. [Many-to-English Machine Translation Tools, Data, and Pretrained Models](https://aclanthology.org/2021.acl-demo.37) (Gowda et al., ACL 2021)
14. Chris Dyer, Victor Chahuneau, and Noah A. Smith. (2013). [A Simple, Fast, and Effective Reparameterization of IBM Model 2](http://www.ark.cs.cmu.edu/cdyer/fast_valign.pdf). In Proc. of NAACL.
15. [Neural Machine Translation of Rare Words with Subword Units](https://aclanthology.org/P16-1162) (Sennrich et al., ACL 2016)
16. [Subword Regularization: Improving Neural Network Translation Models with Multiple Subword Candidates](https://arxiv.org/abs/1804.10959) (Taku Kudo, 2018)
