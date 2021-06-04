# bergamot-training
Training pipelines for Bergamot machine translation models.

The pipeline is capable of training a model for a language pair end to end.

Quality will depend on chosen datasets and data cleaning procedures. Some settings might require extra cleaning.
It was tested on relatively high resource language pair `ru-en`. Low resource pairs might require pipeline fixes.

## Running

### From the target machine
```
git clone <this repo>
cd bergamot-training
# change settings in config.sh or modify code if needed
bash run.sh
```

### Using Snakepit

See Snakepit installation (https://github.com/mozilla/snakepit-client)

```
git clone <this repo>
cd bergamot-training
# change settings in config.sh or modify code if needed
pit run --log "bergamot-training-ru-en" "[8:g2080]"
```

## System requirements

- Ubuntu 18.04 (it can work on other Linux distributions, but might require `setup` scripts fixes).
- One or several Nvidia GPUs with CUDA drivers installed and at least 8 GB of memory. 
  It was tested with 8 NVIDIA RTX 2080 GPUs with 12 GB of memory and CUDA 11.
- At least 8 CPU cores ( some steps of the pipelines utilize multiple cores pretty well).
  It was tested on 56 core Xeon server.
- 100 GB of disk space ( mostly for datasets and transformations ).

## Conventions

- All scripts work with respect to repo root directory which should be written to `WORKDIR` environment variable. 
  It allows to not think about relative paths and execution folders.
  
- Scripts inside `pipeline` directory are independent and operate only using input arguments 
  and global envs from `config.sh`.
  They don't use any extra knowledge of data naming or locations.
  
- All scripts have a description and definition of input arguments.

- All scripts test expected environment variables early.

- If a script step fails, it can be safely retried.

- Ideally every script should start from the last unfinished step, 
  checking presence of intermediate results of previous steps.

- A script fails as early as possible.

- Maximum bash verbosity is set for easy debugging.

- Input data is always read only.

- Output data is placed to a new folder for script results.
  
- It is expected that the specified output folder might not exist and should be created by the script.

- A script creates a folder for intermediate files and cleans it in the end.

- Network disks are too slow for some operations, so a script can copy and work with intermediate data on a local disk.
  This ability is limited by a local disk size (this is the case for Snakepit cluster).
  An exception is when parallelization across multiple machines is required.
    
- Global variables are upper case, local variable are lower case.

- ALl variables that are global for the whole pipeline are set in `config.sh`.

- Scripts should automatically inspect resources available for computation and utilize them to make things faster
  (number of cores, memory).

## Used projects and tools

### Training
https://marian-nmt.github.io

https://github.com/google/sentencepiece

https://github.com/clab/fast_align

https://github.com/marian-nmt/extract-lex

### Evaluation
https://github.com/mjpost/sacrebleu

### Cleaning
https://github.com/bitextor/bicleaner/

### Pipeline recipes
https://github.com/marian-nmt/marian-examples/tree/master/wmt2017-transformer

https://github.com/browsermt/students/tree/master/train-student

https://github.com/ZJaume/clean

### Workflow
https://github.com/mozilla/snakepit-client

https://github.com/ufal/marian-tensorboard

### Data
https://opus.nlpl.eu/ 

https://paracrawl.eu/

https://commoncrawl.org/

https://www.statmt.org/wmt21/translation-task.html

https://www.statmt.org/wmt20/translation-task.html

https://github.com/thammegowda/mtdata