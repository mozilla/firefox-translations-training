from snakemake.utils import min_version

min_version("6.6.1")

configfile: 'config.yml'

src=config['src']
trg=config['trg']
train_datasets=config['datasets']['train']
valid_datasets=config['datasets']['devtest']


data_dir=f"{config['data-root-dir']}/data/{config['src']}-{config['trg']}/{config['experiment']}"
models_dir=f"{config['data-root-dir']}/models/{config['src']}-{config['trg']}/{config['experiment']}"
log_dir=f"{config['data-root-dir']}/logs/{config['src']}-{config['trg']}/{config['experiment']}"
cache_dir=f"{data_dir}/cache"
original=f"{data_dir}/original"
clean=f"{data_dir}/clean"
bin="bin"
marian="3rd_party/marian-dev/build"
kenlm='/3rd_party/kenlm'

gpus=config['gpus'] \
    if config['gpus'] != 'all' \
    else shell("$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))")
workspace=config['workspace']



teacher_dir=f"{models_dir}/teacher"
OUTPUT=f'{models_dir}/teacher/model.npz.best-bleu-detok.npz'


rule all:
    input: OUTPUT

rule setup:
    message: "Installing dependencies"
    log: f"{log_dir}/install-deps.log"
    conda: "envs/environment.yml"
    threads: 1
    group: 'setup'
    # specific to local machine
    output: touch("/tmp/flags/setup.done")
    shell: 'bash pipeline/setup/install-deps.sh 2>&1 | tee {log}'

rule marian:
    message: "Compiling marian"
    log: f"{log_dir}/compile-marian.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output: trainer=f"{marian}/marian", decoder=f"{marian}/marian-decoder", scorer=f"{marian}/marian-scorer"
    params: cuda_dir=config['cuda-dir']
    shell: '''
        MARIAN={marian} THREADS={threads} CUDA_DIR={params.cuda_dir} \
        bash pipeline/setup/compile-marian.sh 2>&1 | tee {log}'''

rule fast_align:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-fast-align.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output: f"{bin}/fast_align"
    shell: '''
        BUILD_DIR=3rd_party/fast_align/build BIN={bin} THREADS={threads} \
        bash pipeline/setup/compile-fast-align.sh 2>&1 | tee {log}'''

rule extract_lex:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-extract-lex.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output: f"{bin}/extract_lex"
    shell: '''
        BUILD_DIR=3rd_party/extract-lex/build BIN={bin} THREADS={threads} \
        bash pipeline/setup/compile-extract-lex.sh 2>&1 | tee {log}'''

rule data_train:
    message: "Downloading training corpus"
    log: f"{log_dir}/donload_train_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/2
    group: 'data'
    input: rules.setup.output
    output: src=f"{original}/corpus.{src}.gz", trg=f"{original}/corpus.{trg}.gz"
    params: prefix=f"{original}/corpus"
    shell: '''
        SRC={src} TRG={trg} \
        bash pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" "train" {train_datasets} 2>&1 | tee {log}
    '''

rule data_val:
    message: "Downloading validation corpus"
    log: f"{log_dir}/donload_val_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/2
    group: 'data'
    input: rules.setup.output
    output: src=f"{original}/devset.{src}.gz", trg=f"{original}/devset.{trg}.gz"
    params: prefix=f"{original}/devset"
    shell: '''
        SRC={src} TRG={trg} \
        bash pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" "valid" {valid_datasets} 2>&1 | tee {log}
    '''

rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: rules.data_train.output.src, rules.data_train.output.trg, rules.setup.output
    output: src=f"{clean}/corpus.{src}.gz", trg=f"{clean}/corpus.{trg}.gz"
    params: prefix_input=f"{original}/corpus", prefix_output=f"{clean}/corpus"
    shell: '''
        SRC={src} TRG={trg} CLEAN_TOOLS=pipeline/clean/tools \
        bash ./pipeline/clean/clean-corpus.sh "{params.prefix_input}" "{params.prefix_output}" 2>&1 | tee {log}'''

# rule backward:
#     message: "Training backward model"
#     log: f"{log_dir}/train_backward.log"
#     conda: "envs/environment.yml"
#     threads: workflow.cores/4
#     input: rules.clean_corpus.output.src, rules.clean_corpus.output.trg, rules.marian.output.trainer,
#             rules.data_val.output.src, rules.data_val.output.trg
#     output: f'{models_dir}/s2s'
#     params: prefix_train=f"{clean}/corpus", prefix_test=f"{original}/devset"
#     shell: '''
#         bash ./pipeline/train/train-s2s.sh "{output}" "{params.prefix_train}" "{params.prefix_test}" 2>&1 | tee {log}
#     '''

rule teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    resources:
        gpu=8
    input: rules.clean_corpus.output.src, rules.clean_corpus.output.trg, rules.marian.output.trainer,
            rules.data_val.output.src, rules.data_val.output.trg
    output: OUTPUT
    params: prefix_train=f"{clean}/corpus", prefix_test=f"{original}/devset"
    shell: '''
        SRC={src} TRG={trg} MARIAN={marian} GPUS={gpus} WORKSPACE={workspace} \
        bash ./pipeline/train/train-teacher.sh "{teacher_dir}" "{params.prefix_train}" "{params.prefix_test}" 2>&1 | tee {log}
    '''



