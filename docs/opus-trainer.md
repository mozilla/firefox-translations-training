# OpusTrainer


[OpusTrainer](https://github.com/hplt-project/OpusTrainer) is a training tool developed by the HPLT project. 
It feeds training data to Marian and provides ability to do useful manipulations with the data, 
such as shuffling, mixing multiple datasets in the specified proportion, splitting training into multiple stages and augmentation.

## Data augmentation

Data augmentation helps with making translation models more robust which is especially useful for usage with the noisy internet pages.

OpusTrainer augments data on the fly, which means it will generate unique data for each epoch of training. 

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

Ability to split training into multiples stages. Each stage is configurable to use a mix of different datasets.

We use it to pretrain the teacher model on the augmented dataset that includes the original parallel corpus and 
back-translaitons and then continue training on the original parallel corpus only
(see [teacher config](/pipeline/train/configs/opustrainer/teacher.yml)).

## Configuration

OpusTrainer configuration files for the trained models are located in 
[/pipeline/train/configs/opustrainer/](/pipeline/train/configs/opustrainer/) directory.

`<dataset0>`, `<dataset1>` and `<vocab>` will be replaced by the training datasets passed in `trains.sh` script.

See more details on configuration in the OpusTrainer [readme](https://github.com/hplt-project/OpusTrainer).

Example config:
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
