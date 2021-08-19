
rule translate_corpus:
    message: "Translating corpus with teacher"
    log: f"{log_dir}/translate_corpus.log"
    conda: "../envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=4
    input:
        rules.marian.output.trainer,
        corpus_src=rules.clean_corpus.output.src,
        corpus_trg=rules.clean_corpus.output.trg,
        teacher_dirs=expand(f"{teacher_dir}{{ens}}", ens=ensemble),
        teacher_models=expand(f"{teacher_dir}{{ens}}/{best_bleu_model}", ens=ensemble),
        vocab=rules.train_vocab.output,
    output:
        f"{translated}/corpus.{trg}.gz"
    params:
        prefix_train=f"{clean}/corpus",
        prefix_test=f"{original}/devset"
    shell: '''
        SRC={src} TRG={trg} MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
        bash pipeline/translate/translate-corpus.sh \
            {input.corpus_src} {input.corpus_trg} "{input.teacher_models}" "{input.vocab}" "{output}" \
            2>&1 | tee {log}'''
