from snakemake.utils import min_version

min_version("6.6.1")

configfile: 'config.yml'


src=config['src']
trg=config['trg']
experiment = config['experiment']

data_root_dir = config['dirs']['data-root']
marian_dir=config['dirs']['marian']
bin=config['dirs']['bin']
cuda_dir=config['dirs']['cuda']

train_datasets=config['datasets']['train']
valid_datasets=config['datasets']['devtest']
teacher_ensemble=config['teacher-ensemble']

data_dir=f"{data_root_dir}/data/{src}-{trg}/{experiment}"
models_dir=f"{data_root_dir}/models/{src}-{trg}/{experiment}"
log_dir=f"{data_root_dir}/logs/{src}-{trg}/{experiment}"
cache_dir=f"{data_dir}/cache"
original=f"{data_dir}/original"
clean=f"{data_dir}/clean"
translated=f"{data_dir}/translated"

best_bleu_model="model.npz.best-bleu-detok.npz"
teacher_dir=f"{models_dir}/teacher"
vocab=f"{models_dir}/vocab/vocab.spm"

gpus=config['gpus'] \
    if config['gpus'] != 'all' \
    else shell("$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))")
workspace=config['workspace']

ensemble=list(range(teacher_ensemble))


rule all:
    input: f"{translated}/corpus.{trg}.gz"

### setup

include: "workflow/setup.smk"

### data

rule data_train:
    message: "Downloading training corpus"
    log: f"{log_dir}/donload_train_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/2
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
    log: f"{log_dir}/donload_val_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/2
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

rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    conda: "envs/environment.yml"
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

### training

rule train_vocab:
    message: "Training spm vocab"
    log: f"{log_dir}/train_vocab.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=4
    input:
        rules.marian.output.vocab,
        corpus_src=rules.clean_corpus.output.src,
        corpus_trg=rules.clean_corpus.output.trg
    output:
        vocab
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
    conda: "envs/environment.yml"
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



rule translate_corpus:
    message: "Translating corpus with teacher"
    log: f"{log_dir}/translate_corpus.log"
    conda: "envs/environment.yml"
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


