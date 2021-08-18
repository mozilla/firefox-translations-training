from workflow.utils import get_log_dir

marian_dir=config['dirs']['marian']
bin=config['dirs']['bin']
cuda_dir=config['dirs']['cuda']
log_dir=get_log_dir(config)


rule setup:
    message: "Installing dependencies"
    log: f"{log_dir}/install-deps.log"
    conda: "../envs/environment.yml"
    threads: 1
    group: 'setup'
    # specific to local machine
    output: touch("/tmp/flags/setup.done")
    shell: 'bash pipeline/setup/install-deps.sh 2>&1 | tee {log}'

rule marian:
    message: "Compiling marian"
    log: f"{log_dir}/compile-marian.log"
    conda: "../envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output:
        trainer=f"{marian_dir}/marian",
        decoder=f"{marian_dir}/marian-decoder",
        scorer=f"{marian_dir}/marian-scorer",
        vocab=f'{marian_dir}/spm_train'
    shell: '''
        MARIAN={marian_dir} THREADS={threads} CUDA_DIR={cuda_dir} \
        bash pipeline/setup/compile-marian.sh 2>&1 | tee {log}'''

rule fast_align:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-fast-align.log"
    conda: "../envs/environment.yml"
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
    conda: "../envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output: f"{bin}/extract_lex"
    shell: '''
        BUILD_DIR=3rd_party/extract-lex/build BIN={bin} THREADS={threads} \
        bash pipeline/setup/compile-extract-lex.sh 2>&1 | tee {log}'''
