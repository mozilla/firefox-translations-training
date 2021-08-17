
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
OUTPUT=f'{models_dir}/teacher/model.bin'

# specific to local machine
setup_done=f"/tmp/flags/setup.done"

rule all:
    input: OUTPUT

rule setup:
    message: "Installing dependencies"
    log: f"{log_dir}/install-deps.log"
    conda: "pipeline/setup/environment.yml"
    threads: 1
    output: touch(setup_done)
    shell: 'bash pipeline/setup/install-deps.sh 2> {log}'

rule compile_marian:
    message: "Compiling marian"
    log: f"{log_dir}/compile-marian.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: setup_done
    output: f"{marian}/marian"
    shell: 'bash pipeline/setup/compile-marian.sh {threads} 2> {log}'

rule compile_fast_align:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-fast-align.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: setup_done
    output: f"{bin}/fast_align"
    shell: 'bash pipeline/setup/compile-fast-align.sh {threads} 2> {log}'

rule compile_extract_lex:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-extract-lex.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: setup_done
    output: f"{bin}/extract_lex"
    shell: 'bash pipeline/setup/compile-extract-lex.sh {threads} 2> {log}'

rule download_train_corpus:
    message: "Downloading training corpus"
    log: f"{log_dir}/donload_train_corpus.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores/2
    input: setup_done
    output: f"{original}/corpus.{src}.gz", f"{original}/corpus.{trg}.gz"
    params: prefix=f"{original}/corpus"
    shell: '''
        bash pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" "train" {train_datasets} 2> {log}
    '''

rule download_validation_corpus:
    message: "Downloading validation corpus"
    log: f"{log_dir}/donload_val_corpus.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores/2
    input: setup_done
    output: f"{original}/devset.{src}.gz", f"{original}/devset.{trg}.gz"
    params: prefix=f"{original}/devset"
    shell: '''
        bash pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" "valid" {valid_datasets} 2> {log}
    '''

rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: f"{original}/corpus.{src}.gz", f"{original}/corpus.{trg}.gz", setup_done
    output: f"{clean}/corpus.{src}.gz", f"{clean}/corpus.{trg}.gz"
    params: prefix_input=f"{original}/corpus", prefix_output=f"{clean}/corpus"
    shell: 'bash ./pipeline/clean/clean-corpus.sh "{params.prefix_input}" "{params.prefix_output}" 2> {log}'

rule train_teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher.log"
    conda: "pipeline/setup/environment.yml"
    threads: workflow.cores
    input: f"{clean}/corpus.{src}.gz", f"{clean}/corpus.{trg}.gz", f"{marian}/marian",
            f"{original}/devset.{src}.gz", f"{original}/devset.{trg}.gz"
    output: OUTPUT
    params: prefix_train=f"{clean}/corpus", prefix_test=f"{original}/devset"
    shell: 'bash ./pipeline/train/train-teacher.sh "{teacher_dir}" "{params.prefix_train}" "{params.prefix_test}" 2> {log}"'

