
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
bin="bin"
marian="3rd_party/marian-dev/build"
teacher_dir=f"{models_dir}/teacher"
OUTPUT=f'{models_dir}/teacher/model.bin'

rule all:
    input: OUTPUT

rule setup:
    message: "Installing dependencies"
    log: f"{log_dir}/install-deps.log"
    conda: "pipeline/setup/environment.yml"
    output: touch("flags/setup.done")
    shell: 'bash pipeline/setup/install-deps.sh 2> {log}'

rule marian:
    message: "Compiling marian"
    log: f"{log_dir}/compile-marian.log"
    conda: "pipeline/setup/environment.yml"
    input: "flags/setup.done"
    output: f"{marian}/marian"
    shell: 'bash pipeline/setup/compile-marian.sh 2> {log}'

rule download_corpus:
    message: "Downloading corpus"
    log: f"{log_dir}/donload_corpus.log"
    conda: "pipeline/setup/environment.yml"
    input: "flags/setup.done"
    output: f"{original}/corpus.{src}.gz", f"{original}/corpus.{trg}.gz"
    params: prefix=f"{original}/corpus"
    shell: '''
        bash pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" {train_datasets} 2> {log}
    '''


rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    conda: "pipeline/setup/environment.yml"
    input: f"{original}/corpus.{src}.gz", f"{original}/corpus.{trg}.gz", "flags/setup.done"
    output: f"{clean}/corpus.{src}.gz", f"{clean}/corpus.{trg}.gz"
    params: prefix_input=f"{clean}/corpus", prefix_output=f"{clean}/corpus"
    shell: 'bash ./pipeline/clean/clean-corpus.sh "{params.prefix_input}" "{params.prefix_output}" 2> {log}'

rule train_teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher.log"
    conda: "pipeline/setup/environment.yml"
    input: f"{clean}/corpus.{src}.gz", f"{clean}/corpus.{trg}.gz", f"{marian}/marian"
    output: OUTPUT
    params: prefix_corpus=f"{clean}/corpus"
    shell: 'bash ./pipeline/train/train-teacher.sh "{teacher_dir}" "{params.prefix_corpus}" "{original}/devset 2> {log}"'

