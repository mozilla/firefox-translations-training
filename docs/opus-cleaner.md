# OpusCleaner

The instructions on using the [OpusCleaner](https://github.com/hplt-project/OpusCleaner) tool.

## Custom filter configs
The idea behind the OpusCleaner is customizing filter rules for each language pair and dataset 
to get a training corpus with less noise and train higher quality translation models.

Filtering rules can be tuned in an interactive UI.

### Installation

Install the OpusCleaner UI on a server. 
See the installation instructions in the [OpusCleaner readme](https://github.com/hplt-project/OpusCleaner).

For local usage: run from a poetry shell `make opuscleaner-ui`.
Then go to `http://0.0.0.0:8000`.

### Making filters

Choose a language pair and download the required OPUS datasets. 
They will correspond to `opus_...` training datasets in the training pipeline config.

Configure cleaning rules for the datasets in the UI.

Copy JSON files for the produced filters `data/train-parts/*.filter.json` to 
`pipeline/clean/opuscleaner/configs/<src-lang-code>-<trg-lang-code>/`.

## Default config

If no custom config was specifed for the dataset, 
the [default config template](pipeline/clean/opuscleaner/configs/default.filters.json) will be used.

Modify if needed. Some rules require specifying source or target language. 
The `<src>` and `<trg>` in the template will be automatically replaced with the trained language pair.
The generated default config will be copied to the target dataset cleaning directory.

## Running 

Enable OpusCleaner in the training pipeline config
```
experiment:
  ...
  use-opuscleaner: true
```

Run the pipeline as usual. OpusCleaner will replace the default [clean-corpus](pipeline/clean/clean-corpus.sh) script.
