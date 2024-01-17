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
- **Tags** - add emojis and other random Unicode symbols in the source and target sentences 
  (requires alignments information for the training corpus)

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
- Tags: 0.05
  augment: 0.05
  replace: 0.05
  spm_vocab: <vocab>
  
seed: 1111

# parallel sentences + token alignments
num_fields: 3
```


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

`aug-typos` - applies typos with a probability of 0.1

`aug-title` - applies title case with probability 0.1

`aug-title-strict` - applies title case to all sentences

`aug-upper` -  applies upper case with probability 0.1

`aug-upper-strict` - applies upper case to all sentences

`aug-mix` - applies, title case and upper case sequentially with 0.1 probability each

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
    - flores_aug-title-strict_devtest
    - flores_aug-upper_devtest
    - flores_aug-upper-strict_devtest
    - flores_aug-typos_devtest
```

