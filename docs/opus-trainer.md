---
layout: default
title: OpusTrainer
nav_order: 7
---

# OpusTrainer


[OpusTrainer](https://github.com/hplt-project/OpusTrainer) is a training tool developed by the HPLT project. 
It feeds training data to Marian and provides the ability to do useful manipulations with the data, 
such as shuffling, mixing multiple datasets in the specified proportion, splitting training into multiple stages and augmentation.

See [this paper](https://arxiv.org/pdf/2311.14838.pdf) for more details and recommendations on how to set augmentation values.

## Data augmentation

Data augmentation helps make translation models more robust, which is especially useful for usage with noisy internet pages.

OpusTrainer augments data on the fly, meaning it will generate unique data for each epoch of training.

Supported augmentations:
- **Upper case** - make some sentences from the dataset upper case
- **Title case** - use title case for some sentences from the dataset
- **Typos** - add random typos in some words
- **Noise** - inserts lines with random unicode noise 
- **Tags (inline noise)** - add emojis and other random Unicode symbols in the source and target sentences 
  (requires space tokenized alignments for the training corpus)

It is possible to specify the probability of augmentation 
(which will roughly correspond to the percentage of augmented sentences):
```yaml
modifiers:
- UpperCase: 0.1 # Apply randomly to 10% of sentences
```

## Curriculum learning

Ability to split training into multiple stages. Each stage is configurable to use a mix of different datasets.

We use it to pretrain the teacher model on the augmented dataset that includes the original parallel corpus and 
back-translations and then continue training on the original parallel corpus only
(see [teacher config](https://github.com/mozilla/firefox-translations-training/tree/main/pipeline/train/configs/opustrainer/teacher.yml)).

## Configuration

OpusTrainer configuration files for the trained models are located in 
the [/pipeline/train/configs/opustrainer/](https://github.com/mozilla/firefox-translations-training/tree/main/pipeline/train/configs/opustrainer/) directory.

`<dataset0>`, `<dataset1>` and `<vocab>` will be replaced by the training datasets passed in `pipeline/train/train.sh` script.

See more details on configuration in the OpusTrainer [readme](https://github.com/hplt-project/OpusTrainer).

Example OpusTrainer config:
```yaml
datasets:
  original: <dataset0> # Original parallel corpus
  backtranslated: <dataset1> # Back-translated data + Original parallel corpus

stages:
  - pretrain
  - finetune

pretrain:
  - original 0.5
  - backtranslated 0.5
  - until original 2 # General training until 2 epochs of original

finetune:
  - original 1.0
  - until original inf # Fine-tuning only on original until the early stopping

modifiers:
- UpperCase: 0.1 # Apply randomly to 10% of sentences
- TitleCase: 0.1
- Typos: 0.05
- Noise: 0.0005
  min_word_length: 2 # Minimum word length for each word in the noisy sentence
  max_word_length: 5 # Maximum word length for each word in the noisy sentence
  max_words: 6 # Maximum number of words in each noisy sentence
- Tags: 0.05
  augment: 1
seed: 1111

# parallel sentences + token alignments
num_fields: 3
```

## Models

Current strategy is to run as many supported augmentations as possible for the teacher 
and student models and skip augmentaiton entirely for the backward model. 
This is mostly based on the intuition that we do not need the backward model to be robust and would rather prioritize quality that is usually affected by the noisier data.
Even though the student is supposed to learn on the exact output of the teacher model, training on augmented data seems to be working in practice.

We might rethink this strategy in future after running model experiments.


## Evaluation

To test the effects of the data augmentation on the trained models, the data downloader supports augmentation of the evaluation datasets.
It allows running the validation while training and the final evaluation on an augmented datasets.

Add an augmentation modifier to any dataset in the training config in the following format:

`<dataset-importer>_<augmentation-modifier>_<dataset-name>`

For example:

```yaml
- flores_aug-title-strict_devtest
- sacrebleu_aug-mix_wmt19/dev
- opus_aug-typos_ada83/v1
```


### Supported modifiers

`aug-typos` - applies 4 random typos to all sentences in the dataset

`aug-title` - applies title case to the whole dataset

`aug-upper` -  applies upper case to the whole dataset

`aug-noise` -  generates extra lines with noise (1 line of noise for each line of the dataset, so the dataset becomes twice longer)

`aug-mix` - applies all the existing modifiers with 0.1 probability each

### Example training config
```yaml
  devtest:
    - flores_aug-mix_dev
    - sacrebleu_aug-mix_wmt19/dev
  # datasets for evaluation
  test:
    - flores_devtest
    - flores_aug-mix_devtest
    - flores_aug-title_devtest
    - flores_aug-upper_devtest
    - flores_aug-typos_devtest
    - flores_aug-noise_devtest
```

