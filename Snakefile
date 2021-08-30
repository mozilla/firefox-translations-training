from snakemake.utils import min_version

min_version("6.6.1")

# Directories structure
#
#├ data
#│   ├ cache
#│   │  ├ corpus
#│   │  │  └ opus
#│   │  │    ├ ada83_v1.en.gz
#│   │  │    └ ada83_v1.ru.gz
#│   │  └ mono
#│   │     └ news-crawl
#│   │       ├ news.2019.ru.gz
#│   │       └ news.2019.en.gz
#│   └ ru-en
#│      └ test
#│        ├ original
#│        │   ├ corpus.ru.gz
#│        │   ├ corpus.en.gz
#│        │   ├ mono.ru.gz
#│        │   ├ mono.en.gz
#│        │   ├ devset.ru.gz
#│        │   └ devset.en.gz
#│        ├ evaluation
#│        │   ├ wmt12.ru
#│        │   ├ wmt12.en
#│        │   ├ wmt20.ru
#│        │   ├ wmt20.en
#│        ├ clean
#│        │   ├ corpus.ru.gz
#│        │   ├ corpus.en.gz
#│        │   ├ mono.ru.gz
#│        │   └ mono.en.gz
#│        ├ biclean
#│        │   ├ corpus.ru.gz
#│        │   ├ corpus.en.gz
#│        ├ translated
#│        │   ├ mono.ru.gz
#│        │   └ mono.en.gz
#│        ├ augmented
#│        │   ├ corpus.ru.gz
#│        │   └ corpus.en.gz
#│        ├ alignment
#│        │   ├ corpus.aln.gz
#│        │   └ lex.s2t.pruned.gz
#│        ├ merged
#│        │   ├ corpus.ru.gz
#│        │   └ corpus.en.gz
#│        └ filtered
#│            ├ corpus.ru.gz
#│            └ corpus.en.gz
#├ model
#│   ├ ru-en
#│   │   └ test
#│   │      ├ teacher
#│   │      ├ student
#│   │      ├ student-finetuned
#│   │      ├ speed
#│   │      └ exported
#│   ├ en-ru
#│      └ test
#│         └ s2s
#│
#├ experiments
#│   └ ru-en
#│      └ test
#│         └ config.sh

configfile: 'config.yml'
# `include` directive is not supported by Pycharm plugin, moved all rules to one file to enable live checks
# https://github.com/JetBrains-Research/snakecharm/issues/195

src = config['src']
trg = config['trg']
experiment = config['experiment']

data_root_dir = config['dirs']['data-root']
log_dir = f"{data_root_dir}/logs/{src}-{trg}/{experiment}"
data_dir = f"{data_root_dir}/data/{src}-{trg}/{experiment}"
models_dir = f"{data_root_dir}/models/{src}-{trg}/{experiment}"
marian_dir = config['dirs']['marian']
bin = config['dirs']['bin']
cuda_dir = config['dirs']['cuda']

clean = f"{data_dir}/clean"
cache_dir = f"{data_dir}/cache"
original = f"{data_dir}/original"
evaluation = f"{data_dir}/evaluation"
translated = f"{data_dir}/translated"

mono_max_sent_src = config['mono-max-sentences-src']
mono_max_sent_trg = config['mono-max-sentences-trg']

train_datasets = config['datasets']['train']
valid_datasets = config['datasets']['devtest']
eval_datasets = config['datasets']['test']
mono_src_datasets = config['datasets']['mono-src']
mono_trg_datasets = config['datasets']['mono-trg']

best_bleu_model = "model.npz.best-bleu-detok.npz"
teacher_dir = f"{models_dir}/teacher"

gpus_num=config['gpus']
gpus = list(range(int(gpus_num)))
workspace = config['workspace']
partitions = config['partitions']
parts=[f'{n:02d}' for n in list(range(partitions))]

ensemble = list(range(config['teacher-ensemble']))


rule all:
    input: f"{translated}/corpus.{trg}.gz"

# setup

rule setup:
    message: "Installing dependencies"
    log: f"{log_dir}/install-deps.log"
    conda: "envs/environment.yml"
    threads: 1
    group: 'setup'
    # specific to local machine
    output: touch("/tmp/flags/setup.done")
    shell: 'bash pipeline/setup/install-deps.sh 2>{log}'

rule marian:
    message: "Compiling marian"
    log: f"{log_dir}/compile-marian.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output: trainer=protected(f"{marian_dir}/marian"), decoder=protected(f"{marian_dir}/marian-decoder"),
            scorer=protected(f"{marian_dir}/marian-scorer"), vocab=protected(f'{marian_dir}/spm_train')
    shell: '''MARIAN={marian_dir} THREADS={threads} CUDA_DIR={cuda_dir} \
                bash pipeline/setup/compile-marian.sh 2>{log}'''

rule fast_align:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-fast-align.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output: protected(f"{bin}/fast_align")
    shell: '''BUILD_DIR=3rd_party/fast_align/build BIN={bin} THREADS={threads} \
                bash pipeline/setup/compile-fast-align.sh 2>{log}'''

rule extract_lex:
    message: "Compiling fast align"
    log: f"{log_dir}/compile-extract-lex.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'setup'
    input: rules.setup.output
    output: protected(f"{bin}/extract_lex")
    shell: '''BUILD_DIR=3rd_party/extract-lex/build BIN={bin} THREADS={threads} \
                bash pipeline/setup/compile-extract-lex.sh 2>{log}'''

# data

rule data_train:
    message: "Downloading training corpus"
    log: f"{log_dir}/data_train.log"
    conda: "envs/environment.yml"
    threads: 4
    group: 'data'
    input: rules.setup.output
    output: src=f"{original}/corpus.{src}.gz", trg=f"{original}/corpus.{trg}.gz"
    params: prefix=f"{original}/corpus"
    shell: '''SRC={src} TRG={trg} \
                bash pipeline/data/download-corpus.sh \
                "{params.prefix}" "{cache_dir}" "train" {train_datasets} 2>{log}'''

rule data_val:
    message: "Downloading validation corpus"
    log: f"{log_dir}/data_val.log"
    conda: "envs/environment.yml"
    threads: 4
    group: 'data'
    input: rules.setup.output
    output: src=f"{original}/devset.{src}.gz", trg=f"{original}/devset.{trg}.gz"
    params: prefix=f"{original}/devset"
    shell: '''SRC={src} TRG={trg} \
                bash pipeline/data/download-corpus.sh \
                "{params.prefix}" "{cache_dir}" "valid" {valid_datasets} 2>{log}'''

rule data_test:
    message: "Downloading test corpus"
    log: f"{log_dir}/data_test.log"
    conda: "envs/environment.yml"
    threads: 4
    group: 'data'
    input: rules.setup.output
    output: expand(f"{evaluation}/{{dataset}}.{{lng}}",dataset=eval_datasets,lng=[src, trg])
    shell: '''SRC={src} TRG={trg} \
                bash pipeline/data/download-eval.sh \
                "{evaluation}" "{cache_dir}" {eval_datasets} 2>{log}'''

rule data_mono_src:
    message: "Downloading monolingual dataset for source language"
    log: f"{log_dir}/data_mono_src.log"
    conda: "envs/environment.yml"
    threads: 4
    group: 'data'
    input: rules.setup.output
    output: f'{original}/mono.{src}'
    shell: '''bash pipeline/data/download-mono.sh \
                "{src}" "{mono_max_sent_src}" "{original}/mono" "{cache_dir}" {mono_src_datasets} 2>{log}'''

if mono_trg_datasets:
    rule data_mono_trg:
        message: "Downloading monolingual dataset for target language"
        log: f"{log_dir}/data_mono_trg.log"
        conda: "envs/environment.yml"
        threads: 4
        group: 'data'
        input: rules.setup.output
        output: f'{original}/mono.{trg}'
        shell: '''bash pipeline/data/download-mono.sh \
                  "{trg}" "{mono_max_sent_trg}" "{original}/mono" "{cache_dir}" {mono_trg_datasets} 2>{log}'''

# cleaning

rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: rules.data_train.output.src, rules.data_train.output.trg, rules.setup.output
    output: src=f"{clean}/corpus.{src}.gz", trg=f"{clean}/corpus.{trg}.gz"
    params: prefix_input=f"{original}/corpus", prefix_output=f"{clean}/corpus"
    shell: '''SRC={src} TRG={trg} CLEAN_TOOLS=pipeline/clean/tools \
              bash pipeline/clean/clean-corpus.sh "{params.prefix_input}" "{params.prefix_output}" 2>{log}'''

rule clean_mono:
    message: "Cleaning monolingual dataset"
    log: f"{log_dir}/clean_mono_{{lang}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: rules.setup.output, f'{original}/mono.{{lang}}'
    output: f"{clean}/mono.{{lang}}.gz"
    params: lang='{lang}'
    shell: '''CLEAN_TOOLS=pipeline/clean/tools \
                bash pipeline/clean/clean-mono.sh "{params.lang}" "{original}/mono" "{clean}/mono" 2>{log}'''


# model training

rule train_vocab:
    message: "Training spm vocab"
    log: f"{log_dir}/train_vocab.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=1
    input: rules.marian.output.vocab, corpus_src=rules.clean_corpus.output.src, corpus_trg=rules.clean_corpus.output.trg
    output: f"{models_dir}/vocab/vocab.spm"
    params: prefix_train=f"{clean}/corpus", prefix_test=f"{original}/devset"
    shell: '''MARIAN={marian_dir} \
              bash pipeline/train/spm-vocab.sh "{input.corpus_src}" "{input.corpus_trg}" "{output}" 2>{log}'''


# augmentation

rule backward:
    message: "Training backward model"
    log: f"{log_dir}/train_backward.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    input: rules.clean_corpus.output.src, rules.clean_corpus.output.trg, rules.marian.output.trainer,
            rules.data_val.output.src, rules.data_val.output.trg
    output: f'{models_dir}/s2s'
    params: prefix_train=f"{clean}/corpus", prefix_test=f"{original}/devset"
    shell: '''
        bash ./pipeline/train/train-s2s.sh "{output}" "{params.prefix_train}" "{params.prefix_test}" 2>{log}
    '''


rule split_mono_trg:
    message: "Splitting monolingual trg dataset"
    log: f"{log_dir}/split_mono_trg.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: f"{clean}/mono.{trg}.gz"
    output: expand(f"{translated}/mono_trg/file.{{number}}", number=parts)
    shell: 'bash pipeline/translate/split-mono.sh {input} {translated}/mono_trg {partitions} 2>{log}'

rule translate_mono_trg:
    message: "Translating monolingual trg dataset with backward model"
    log: f"{log_dir}/translate_mono_trg/{{part}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=gpus_num
    input:
        rules.marian.output.trainer, file=f'{translated}/mono_trg/file.{{part}}',
        vocab=rules.train_vocab.output, model=f'{rules.backward.output}/{best_bleu_model}'
    output: f'{translated}/mono_trg/file.{{part}}.out'
    shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash pipeline/translate/translate.sh \
                "{input.file}" "{input.model}" "{input.vocab}" 2>{log}'''

rule collect_mono_trg:
    message: "Collecting translated mono trg dataset"
    log: f"{log_dir}/collect_mono_trg.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: expand(f"{translated}/mono_trg/file.{{part}}.out", part=parts)
    output: f'{translated}/mono.{src}.gz'
    params: src_mono=f"{clean}/mono.{trg}.gz"
    shell: '''bash pipeline/translate/collect.sh "{translated}/mono_trg" "{output}" "{params.src_mono}" 2>{log}'''


rule teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher{{ens}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=gpus_num
    input:
        rules.clean_corpus.output.src, rules.clean_corpus.output.trg, rules.marian.output.trainer,
        rules.data_val.output.src, rules.data_val.output.trg, vocab=rules.train_vocab.output
    output: dir=directory(f'{teacher_dir}{{ens}}'), model=f'{teacher_dir}{{ens}}/{best_bleu_model}'
    params: prefix_train=f"{clean}/corpus", prefix_test=f"{original}/devset"
    shell: '''SRC={src} TRG={trg} MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash pipeline/train/train-teacher.sh \
                "{output.dir}" "{params.prefix_train}" "{params.prefix_test}" "{input.vocab}" 2>{log}'''


### translation with teacher

# corpus

rule split_corpus:
    message: "Splitting the corpus to translate"
    log: f"{log_dir}/split_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: corpus_src=rules.clean_corpus.output.src, corpus_trg=rules.clean_corpus.output.trg
    output: expand(f"{translated}/corpus/file.{{number}}{{ext}}", number=parts, ext=['', '.ref'])
    shell: '''bash pipeline/translate/split-corpus.sh \
                {input.corpus_src} {input.corpus_trg} {translated}/corpus {partitions} 2>{log}'''

rule translate_corpus:
    message: "Translating corpus with teacher"
    log: f"{log_dir}/translate_corpus/{{part}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=gpus_num
    input:
        rules.marian.output.trainer, file=f'{translated}/corpus/file.{{part}}', vocab=rules.train_vocab.output,
        teacher_models=expand(f"{teacher_dir}{{ens}}/{best_bleu_model}", ens=ensemble)
    output: f'{translated}/corpus/file.{{part}}.nbest'
    shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash pipeline/translate/translate-nbest.sh \
                "{input.file}" "{input.teacher_models}" "{input.vocab}" 2>{log}'''

rule extract_best:
    message: "Extracting best translations for the corpus"
    log: f"{log_dir}/extract_best.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'translate_corpus'
    input: expand(f"{translated}/corpus/file.{{part}}.nbest", part=parts)
    output: expand(f"{translated}/corpus/file.{{part}}.nbest.out", part=parts)
    shell: '''bash pipeline/translate/extract-best.sh {translated}/corpus {threads} {input} 2>{log}'''

rule collect_corpus:
    message: "Collecting translated corpus"
    log: f"{log_dir}/collect_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'translate_corpus'
    input: rules.extract_best.output
    output: f'{translated}/corpus.{trg}.gz'
    params: src_corpus=rules.clean_corpus.output.src
    shell: '''bash pipeline/translate/collect.sh {translated}/corpus {output} {params.src_corpus} 2>{log}'''

# mono

rule split_mono_src:
    message: "Splitting monolingual src dataset"
    log: f"{log_dir}/split_mono_src.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: f"{clean}/mono.{src}.gz"
    output: expand(f"{translated}/mono_src/file.{{number}}", number=parts)
    shell: 'bash pipeline/translate/split-mono.sh {input} {translated}/mono_src {partitions} 2>{log}'

rule translate_mono_src:
    message: "Translating monolingual src dataset with teacher"
    log: f"{log_dir}/translate_mono_src/{{part}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores/4
    resources: gpu=gpus_num
    input:
        rules.marian.output.trainer, file=f'{translated}/mono_src/file.{{part}}', vocab=rules.train_vocab.output,
        teacher_models=expand(f"{teacher_dir}{{ens}}/{best_bleu_model}", ens=ensemble)
    output: f'{translated}/mono_src/file.{{part}}.out'
    shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash pipeline/translate/translate.sh \
                "{input.file}" "{input.teacher_models}" "{input.vocab}" 2>{log}'''

rule collect_mono_src:
    message: "Collecting translated mono src dataset"
    log: f"{log_dir}/collect_mono_src.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: expand(f"{translated}/mono_src/file.{{part}}.out", part=parts)
    output: f'{translated}/mono.{trg}.gz'
    params: src_mono=f"{clean}/mono.{src}.gz"
    shell: '''bash pipeline/translate/collect.sh "{translated}/mono_src" "{output}" "{params.src_mono}" 2>{log}'''

