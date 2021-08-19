
rule data_train:
    message: "Downloading training corpus"
    log: f"{log_dir}/data_train.log"
    conda: "../envs/environment.yml"
    threads: 4
    group: 'data'
    input:
        rules.setup.output
    output:
        src=f"{original}/corpus.{src}.gz",
        trg=f"{original}/corpus.{trg}.gz"
    params:
        prefix=f"{original}/corpus"
    shell: '''
        SRC={src} TRG={trg} \
        bash pipeline/data/download-corpus.sh \
            "{params.prefix}" "{cache_dir}" "train" {train_datasets} 2>&1 | tee {log}'''

rule data_val:
    message: "Downloading validation corpus"
    log: f"{log_dir}/data_val.log"
    conda: "../envs/environment.yml"
    threads: 4
    group: 'data'
    input:
        rules.setup.output
    output:
        src=f"{original}/devset.{src}.gz",
        trg=f"{original}/devset.{trg}.gz"
    params:
        prefix=f"{original}/devset"
    shell: '''
        SRC={src} TRG={trg} \
        bash pipeline/data/download-corpus.sh \
            "{params.prefix}" "{cache_dir}" "valid" {valid_datasets} 2>&1 | tee {log}'''


rule data_test:
    message: "Downloading test corpus"
    log: f"{log_dir}/data_test.log"
    conda: "../envs/environment.yml"
    threads: 4
    group: 'data'
    input:
        rules.setup.output
    output:
        expand(f"{evaluation}/{{dataset}}.{{lng}}", dataset=eval_datasets, lng=[src, trg]),
    shell: '''
        SRC={src} TRG={trg} \
        bash pipeline/data/download-eval.sh \
            "{evaluation}" "{cache_dir}" {eval_datasets} 2>&1 | tee {log}'''


if mono_src_datasets:
    rule data_mono_src:
        message: "Downloading monolingual dataset for source language"
        log: f"{log_dir}/data_mono_src.log"
        conda: "../envs/environment.yml"
        threads: 4
        group: 'data'
        input:
            rules.setup.output
        output:
            f'{original}/mono.{src}'
        shell: '''
            bash pipeline/data/download-mono.sh \
                "{src}" "{mono_max_sent_src}" "{original}/mono" "{cache_dir}" {mono_src_datasets} \
                2>&1 | tee {log}'''

if mono_trg_datasets:
    rule data_mono_src:
        message: "Downloading monolingual dataset for target language"
        log: f"{log_dir}/data_mono_trg.log"
        conda: "../envs/environment.yml"
        threads: 4
        group: 'data'
        input:
            rules.setup.output
        output:
            f'{original}/mono.{trg}'
        shell: '''
            bash pipeline/data/download-mono.sh \
                "{trg}" "{mono_max_sent_trg}" "{original}/mono" "{cache_dir}" {mono_trg_datasets} \
                2>&1 | tee {log}'''