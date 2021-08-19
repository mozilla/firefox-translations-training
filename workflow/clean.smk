
rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    conda: "../envs/environment.yml"
    threads: workflow.cores
    input:
        rules.data_train.output.src,
        rules.data_train.output.trg,
        rules.setup.output
    output:
        src=f"{clean}/corpus.{src}.gz",
        trg=f"{clean}/corpus.{trg}.gz"
    params:
        prefix_input=f"{original}/corpus",
        prefix_output=f"{clean}/corpus"
    shell: '''
        SRC={src} TRG={trg} CLEAN_TOOLS=pipeline/clean/tools \
        bash pipeline/clean/clean-corpus.sh \
            "{params.prefix_input}" "{params.prefix_output}" 2>&1 | tee {log}'''


rule clean_mono_src:
    message: "Cleaning mono src"
    log: f"{log_dir}/clean_mono_src.log"
    conda: "../envs/environment.yml"
    threads: workflow.cores
    input:
        rules.data_train.output.src,
        rules.data_train.output.trg,
        rules.setup.output
    output:
        src=f"{clean}/corpus.{src}.gz",
        trg=f"{clean}/corpus.{trg}.gz"
    params:
        prefix_input=f"{original}/corpus",
        prefix_output=f"{clean}/corpus"
    shell: '''
        SRC={src} TRG={trg} CLEAN_TOOLS=pipeline/clean/tools \
        bash pipeline/clean/clean-corpus.sh \
            "{params.prefix_input}" "{params.prefix_output}" 2>&1 | tee {log}'''