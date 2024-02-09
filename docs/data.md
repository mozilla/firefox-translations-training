---
layout: default
title: Datasets
nav_order: 4
---

# Dataset importers

Dataset importers can be used in `datasets` sections of the [training config](https://github.com/mozilla/firefox-translations-training/tree/main/configs/config.test.yml).

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
:pca; parallel | local-corpus | /tmp/test-corpus | corpus | Local parallel dataset that is already downloaded. The dataset name is an absolute path prefix without ".lang.gz"
[Paracrawl](https://paracrawl.eu/) | paracrawl-mono | paracrawl8 | mono | Datasets that are crawled from the web. Only [mono datasets](https://paracrawl.eu/index.php/moredata) are used in this importer. Parallel corpus is available using opus importer.
[News crawl](http://data.statmt.org/news-crawl) | news-crawl | news.2019 | mono | Some news monolingual datasets from [WMT21](https://www.statmt.org/wmt21/translation-task.html)
[Common crawl](https://commoncrawl.org/) | commoncrawl | wmt16 | mono | Huge web crawl datasets. The links are posted on [WMT21](https://www.statmt.org/wmt21/translation-task.html)
Local mono | local-mono | /tmp/test-mono | mono | Local monolingual dataset that is already downloaded. The dataset name is an absolute path prefix without ".lang.gz"

You can also use [find-corpus](https://github.com/mozilla/firefox-translations-training/tree/main/pipeline/utils/find-corpus.py) tool to find all datasets for an importer and get them formatted to use in config.

Set up a local [poetry](https://python-poetry.org/) environment.
```
make install-utils
python utils/find-corpus.py en ru opus
python utils/find-corpus.py en ru mtdata
python utils/find-corpus.py en ru sacrebleu
```
Make sure to check licenses of the datasets before using them.

## Adding a new importer

Just add a shell script to [corpus](https://github.com/mozilla/firefox-translations-training/tree/main/pipeline/data/importers/corpus) or [mono](https://github.com/mozilla/firefox-translations-training/tree/main/pipeline/data/importers/mono) which is named as `<prefix>.sh` 
and accepts the same parameters as the other scripts from the same folder.
