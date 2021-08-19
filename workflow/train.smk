
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


rule train_vocab:
    message: "Training spm vocab"
    log: f"{log_dir}/train_vocab.log"
    conda: "../envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=4
    input:
        rules.marian.output.vocab,
        corpus_src=rules.clean_corpus.output.src,
        corpus_trg=rules.clean_corpus.output.trg
    output:
        f"{models_dir}/vocab/vocab.spm"
    params:
        prefix_train=f"{clean}/corpus",
        prefix_test=f"{original}/devset"
    shell: '''
        MARIAN={marian_dir} \
        bash pipeline/train/spm-vocab.sh \
            "{input.corpus_src}" "{input.corpus_trg}" "{output}" 2>&1 | tee {log}'''


rule teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher{{ens}}.log"
    conda: "../envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=4
    input:
        rules.clean_corpus.output.src,
        rules.clean_corpus.output.trg,
        rules.marian.output.trainer,
        rules.data_val.output.src,
        rules.data_val.output.trg,
        vocab=rules.train_vocab.output
    output:
        dir=directory(f'{teacher_dir}{{ens}}'),
        model=f'{teacher_dir}{{ens}}/{best_bleu_model}'
    params:
        prefix_train=f"{clean}/corpus",
        prefix_test=f"{original}/devset"
    shell: '''
        SRC={src} TRG={trg} MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
        bash pipeline/train/train-teacher.sh \
            "{output.dir}" "{params.prefix_train}" "{params.prefix_test}" "{input.vocab}" \
             2>&1 | tee {log}'''

