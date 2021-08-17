
from snakemake.utils import min_version

min_version("6.6.1")

configfile: 'config.yml'

envvars:
    "CLEAN_TOOLS",
    "WORKDIR",
    "SRC",
    "TRG",
    "BIN",
    "CUDA_DIR",
    "MARIAN",
    "WORKSPACE",
    "WORKDIR",
    "GPUS"

src=config['src']
trg=config['trg']


data_dir=f"{config['data-root-dir']}/data/{config['src']}-{config['trg']}/{config['experiment']}"
models_dir=f"{config['data-root-dir']}/models/{config['src']}-{config['trg']}/{config['experiment']}"
log_dir=f"{config['data-root-dir']}/logs/{config['src']}-{config['trg']}/{config['experiment']}"
cache_dir=f"{data_dir}/cache"
original=f"{data_dir}/original"
clean=f"{data_dir}/clean"
# gpus=shell("$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))")
train_datasets=['opus_ada83/v1', 'opus_UN/v20090831']
valid_datasets=['flores_dev']
bin="bin"
marian="3rd_party/marian-dev/build"
teacher_dir=f"{models_dir}/teacher"
OUTPUT=f'{models_dir}/teacher/model.npz.best-bleu-detok.npz'


rule all:
    input: OUTPUT

rule setup:
    message: "Installing dependencies"
    log: f"{log_dir}/install-deps.log"
    conda: "pipeline/setup/environment.yml"
    threads: 1
    # specific to local machine
    output: touch("/tmp/flags/setup.done")
    shell: 'bash pipeline/setup/install-deps.sh 2>&1 | tee {log}'

rule marian:
    message: "Compiling marian"
    log: f"{log_dir}/compile-marian.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: rules.setup.output
    output: trainer=f"{marian}/marian", decoder=f"{marian}/marian-decoder", scorer=f"{marian}/marian-scorer"
    shell: 'bash pipeline/setup/compile-marian.sh {threads} 2>&1 | tee {log}'

rule fast_align:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-fast-align.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: rules.setup.output
    output: f"{bin}/fast_align"
    shell: 'bash pipeline/setup/compile-fast-align.sh {threads} 2>&1 | tee {log}'

rule extract_lex:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-extract-lex.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: rules.setup.output
    output: f"{bin}/extract_lex"
    shell: 'bash pipeline/setup/compile-extract-lex.sh {threads} 2>&1 | tee {log}'

rule data_train:
    message: "Downloading training corpus"
    log: f"{log_dir}/donload_train_corpus.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores/2
    input: rules.setup.output
    output: src=f"{original}/corpus.{src}.gz", trg=f"{original}/corpus.{trg}.gz"
    params: prefix=f"{original}/corpus"
    shell: '''
        bash pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" "train" {train_datasets} 2>&1 | tee {log}
    '''

rule data_val:
    message: "Downloading validation corpus"
    log: f"{log_dir}/donload_val_corpus.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores/2
    input: rules.setup.output
    output: src=f"{original}/devset.{src}.gz", trg=f"{original}/devset.{trg}.gz"
    params: prefix=f"{original}/devset"
    shell: '''
        bash pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" "valid" {valid_datasets} 2>&1 | tee {log}
    '''

rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: rules.data_train.output.src, rules.data_train.output.trg, rules.setup.output
    output: src=f"{clean}/corpus.{src}.gz", trg=f"{clean}/corpus.{trg}.gz"
    params: prefix_input=f"{original}/corpus", prefix_output=f"{clean}/corpus"
    shell: 'bash ./pipeline/clean/clean-corpus.sh "{params.prefix_input}" "{params.prefix_output}" 2>&1 | tee {log}'

rule teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: rules.clean_corpus.output.src, rules.clean_corpus.output.trg, rules.marian.output.trainer,
            rules.data_val.output.src, rules.data_val.output.trg
    output: OUTPUT
    params: prefix_train=f"{clean}/corpus", prefix_test=f"{original}/devset"
    shell: '''
        bash ./pipeline/train/train-teacher.sh "{teacher_dir}" "{params.prefix_train}" "{params.prefix_test}" 2>&1 | tee {log}
    '''

