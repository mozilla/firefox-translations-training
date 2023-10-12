# Model training guide

First of all, choose a language pair to train.

## Configuration
Clone the repo and follow the instructions that correspond to the workflow manager you will be using 
([TaskCluster](task-cluster.md), [Snakemake](snakemake.md)).

The Marian workspace is usually safe to set to about 3/4 of available GPU memory 
(in a [profile for Snakemake](/pipeline/train/train.sh) and throughout the ci steps in Task cluster).

### Optimizaiton

`mini-batch-words` can be set depending on GPUs and the number of teachers
```
marian-args:
...
  decoding-backward:
    # 12 Gb GPU, s2s model
    mini-batch-words: 2000
  decoding-teacher:
    # 12 Gb GPU, ensemble of 2 teachers
    mini-batch-words: 1000
```

### Half precision decoding

Make sure to use it only for teacher models and on GPUs that support it .
```
marian-args:
...
  decoding-teacher:
    # 2080ti or newer
    precision: float16
```

## Mozilla Slurm cluster

I usually set just one GPU partition per run in the [cluster config](https://github.com/mozilla/firefox-translations-training/blob/main/pipeline/train/train.sh). It simplifies configuration and monitoring.

Make sure to not set `precision: float16` on `txp` partition.



## Finding datasets

### Parallel corpus for training
1. Go to [opus](https://opus.nlpl.eu/) and see how much data is available for the language pair
2. Go to [paracrawl](https://paracrawl.eu/) and see if it's available there
3. Go to [statmt22](https://www.statmt.org/wmt22/translation-task.html), [statmt21](https://www.statmt.org/wmt21/translation-task.html) etc. and check if the language pair participated in the competition. If yes, there's a good chance some data is available for training.
4. It's hard to say how much data is required to train something useful. My guess would be at least 10 million sentences. Ideally 100M+.
5. Use [find-corpus](https://github.com/mozilla/firefox-translations-training/blob/main/pipeline/utils/find-corpus.py) tool to get opus datasets and copy to `datasets.train` section in the [prod config](https://github.com/mozilla/firefox-translations-training/blob/main/configs/config.prod.yml).
Example:
```
conda env create -f envs/corpus.yml 
conda activate corpus
python utils/find-corpus.py en ru opus
```
4. In the same way obtain and copy mtdata datasets `python utils/find-corpus.py en ru mtdata`
5. Look what's there and remove old versions of datasets (for example there should be only mtdata paracrawl v9 left like `mtdata_ParaCrawl-paracrawl-9-eng-swe`)
6. Deduplicate datasets between opus and mtdata (for example, remove `opus_ParaCrawl/v8`). If the versions are the same I prefer opus ones as a more stable resource.

### Evaluation datasets
Use `python utils/find-corpus.py en ru sacrebleu` first. There might be some statmt datasets available. For example `sacrebleu_wmt20`. 

Add some datasets for validation while training to `datasets.devtest` and other datasets for evaluation to `datasets.test`.

Flores dataset is available for 100 languages, so it's always a good idea to add `flores_dev` to `datasets.devtest` and `flores_devtest` to `datasets.test`

Make sure that training, validation and evaluation datasets are different.

### Monolingual corpus
It's almost always a good idea to use back translations to augment training data and to use monolingual corpus to augment data for decoding by the teachers, especially for low-resource languages. The only limitation is probably available computational resources.

Find monolingual data and add it to `datasets.mono-src` and `datasets.mono-trg`. I usually use [News Crawl](https://data.statmt.org/news-crawl/) datasets from statmt. Example: `news-crawl_news.2020` 

### Custom datasets

It is also possible to use manually downloaded datasets with prefix `custom_<path>`.

## Cleaning

Make sure the language is present in [clean_parallel](https://github.com/mozilla/firefox-translations-training/blob/main/pipeline/clean/tools/clean_parallel.py#L19) script.

It is recommended to use bicleaner for noisy data like OpenSubtitles. Check that the bicleaner model is available and add `opus_OpenSubtitles/v2018: 0.8` to `experiment.bicleaner.dataset-thresholds` section of the prod config. Set to 0 to skip cleaning explicitly, for example for ParaCrawl that comes already cleaned.

You can also add some dataset specific fixes like detokenizaiton [here](https://github.com/mozilla/firefox-translations-training/tree/main/pipeline/clean/fixes).

## Running (Snakemake)

After everything is configured do `make run`. It will compile Marian and other tools first which is important to do on the target machine in cluster mode.

Then it will start downloading the data. It often fails on some datasets either because of hitting the rate limits of the servers or because some resources are just unavailable. It's a good idea to restart several times and then after inspecting the logs remove broken datasets from the config.

When datasets are downloaded, cleaning procedures start.

If you want to inspect data  first, run `make run TARGET=merge_corpus`

## Training

### Hyperparameters
I usually increase early stopping for teachers to make sure the models converge.

```
marian-args:
# these configs override pipeline/train/configs
  training-backward:
    # change based on available training data
    after: 10e
  training-teacher-base:
    # remove for low resource languages or if training without augmentation
    after: 2e
    early-stopping: 20
  training-teacher-finetuned:
    early-stopping: 40
```

### Monitoring

You can check training logs to see Marian output or run Tensorboard to look at training curves (currently requires restarting after a new model was added, because the tool that converts Marian logs to Tensorboard doesn't do it automatically). 

Also, check `models/<lang-pair>/<experiment>/evaluation` folder to see BLEU and chrF numbers on evaluation datasets.

### Out-of-memory issues

Usually, by the time we train the student, it's so much data that it might not fit in 128 GB of RAM. For very high-resource languages like French it can happen in a teacher training state. The workaround is to remove `--shuffle-in-ram` from the [training script](https://github.com/mozilla/firefox-translations-training/blob/main/pipeline/train/train.sh) and add `--shuffle batches` to the student [training script](https://github.com/mozilla/firefox-translations-training/blob/main/pipeline/train/train.sh). More details in the [issue](https://github.com/mozilla/firefox-translations-training/issues/21).
