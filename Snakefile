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
reports_dir = f"{data_root_dir}/reports/{src}-{trg}/{experiment}"
marian_dir = config['dirs']['marian']
bin = config['dirs']['bin']
cuda_dir = config['dirs']['cuda']

clean = f"{data_dir}/clean"
biclean = f"{data_dir}/biclean"
cache_dir = f"{data_dir}/cache"
original = f"{data_dir}/original"
evaluation = f"{data_dir}/evaluation"
translated = f"{data_dir}/translated"
augmented = f"{data_dir}/augmented"
merged = f"{data_dir}/merged"

mono_max_sent_src = config['mono-max-sentences-src']
mono_max_sent_trg = config['mono-max-sentences-trg']
bicleaner_threshold=config['bicleaner-threshold']

train_datasets = config['datasets']['train']
valid_datasets = config['datasets']['devtest']
eval_datasets = config['datasets']['test']
mono_src_datasets = config['datasets']['mono-src']
mono_trg_datasets = config['datasets']['mono-trg']

best_bleu_model = "model.npz.best-bleu-detok.npz"
teacher_dir = f"{models_dir}/teacher"

gpus_num = config['gpus']
gpus = list(range(int(gpus_num)))
workspace = config['workspace']
partitions = config['partitions']
parts = [f'{n:02d}' for n in list(range(partitions))]

ensemble = list(range(config['teacher-ensemble']))


rule all:
    input: f'{merged}/corpus.{src}.gz'

localrules: eval_teacher_report

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
    output: trainer=protected(f"{marian_dir}/marian"),decoder=protected(f"{marian_dir}/marian-decoder"),
        scorer=protected(f"{marian_dir}/marian-scorer"),vocab=protected(f'{marian_dir}/spm_train')
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
    output: src=f"{original}/corpus.{src}.gz",trg=f"{original}/corpus.{trg}.gz"
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
    output: src=f"{original}/devset.{src}.gz",trg=f"{original}/devset.{trg}.gz"
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
    input: rules.data_train.output.src,rules.data_train.output.trg,rules.setup.output
    output: src=f"{clean}/corpus.{src}.gz",trg=f"{clean}/corpus.{trg}.gz"
    params: prefix_input=f"{original}/corpus",prefix_output=f"{clean}/corpus"
    shell: '''SRC={src} TRG={trg} CLEAN_TOOLS=pipeline/clean/tools \
              bash pipeline/clean/clean-corpus.sh "{params.prefix_input}" "{params.prefix_output}" 2>{log}'''

rule biclean_corpus:
    message: "Cleaning corpus using Bicleaner"
    log: f"{log_dir}/beclean_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: src=rules.clean_corpus.output.src, trg=rules.clean_corpus.output.trg
    output: src=f"{biclean}/corpus.{src}.gz",trg=f"{biclean}/corpus.{trg}.gz"
    params: prefix_input=f"{clean}/corpus",prefix_output=f"{biclean}/corpus"
    shell: '''SRC={src} TRG={trg} CLEAN_TOOLS=pipeline/clean/tools BICLEANER_THRESHOLD={bicleaner_threshold}\
              bash pipeline/clean/bicleaner.sh "{params.prefix_input}" "{params.prefix_output}" 2>{log}'''

rule clean_mono:
    message: "Cleaning monolingual dataset"
    log: f"{log_dir}/clean_mono_{{lang}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: rules.setup.output,f'{original}/mono.{{lang}}'
    output: f"{clean}/mono.{{lang}}.gz"
    params: lang='{lang}'
    shell: '''CLEAN_TOOLS=pipeline/clean/tools \
                bash pipeline/clean/clean-mono.sh "{params.lang}" "{original}/mono" "{clean}/mono" 2>{log}'''


# augmentation and teacher training

rule train_vocab:
    message: "Training spm vocab"
    log: f"{log_dir}/train_vocab.log"
    conda: "envs/environment.yml"
    threads: workflow.cores / 4
    resources: gpu=1
    input:
        bin=rules.marian.output.vocab,
        corpus_src=rules.clean_corpus.output.src,corpus_trg=rules.clean_corpus.output.trg
    output: f"{models_dir}/vocab/vocab.spm"
    params: prefix_train=f"{clean}/corpus",prefix_test=f"{original}/devset"
    shell: '''MARIAN={marian_dir} \
              bash pipeline/train/spm-vocab.sh "{input.corpus_src}" "{input.corpus_trg}" "{output}" 2>{log}'''


if config['backward-model']:
    backward_model = config['backward-model']
else:
    backward_model = f'{models_dir}/s2s'

    rule backward:
        message: "Training backward model"
        log: f"{log_dir}/train_backward.log"
        conda: "envs/environment.yml"
        threads: workflow.cores / 4
        input:
            train_src=rules.clean_corpus.output.src, train_trg=rules.clean_corpus.output.trg,
            val_src=rules.data_val.output.src, val_trg=rules.data_val.output.trg,
            bin=rules.marian.output.trainer
        output: model=f'{backward_model}/{best_bleu_model}'
        params: prefix_train=f"{clean}/corpus",prefix_test=f"{original}/devset"
        shell: '''
            MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
            bash ./pipeline/train/train-s2s.sh "{output.model}" "{params.prefix_train}" "{params.prefix_test}" 2>{log}
        '''

    rule eval_backward:
        message: "Evaluating backward model"
        log: f"{log_dir}/eval_backward.log"
        conda: "envs/environment.yml"
        resources: gpu=gpus_num
        input: model=f'{backward_model}/{best_bleu_model}', datasets=rules.data_test.output
        output:
            report(directory(f'{backward_model}/eval'), patterns=["{name}.bleu"], caption=f"{reports_dir}/report.rst")
        shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                    bash ./pipeline/train/eval.sh "{backward_model}" "{evaluation}" {trg} {src} 2>{log}'''



if mono_trg_datasets:
    rule split_mono_trg:
        message: "Splitting monolingual trg dataset"
        log: f"{log_dir}/split_mono_trg.log"
        conda: "envs/environment.yml"
        threads: workflow.cores
        input: f"{clean}/mono.{trg}.gz"
        output:
            dir=directory(f'{translated}/mono_trg'),
            files=expand(f"{translated}/mono_trg/file.{{number}}",number=parts)
        shell: 'bash pipeline/translate/split-mono.sh {input} {output.dir} {partitions} 2>{log}'

    rule translate_mono_trg:
        message: "Translating monolingual trg dataset with backward model"
        log: f"{log_dir}/translate_mono_trg/{{part}}.log"
        conda: "envs/environment.yml"
        threads: workflow.cores / 4
        resources: gpu=gpus_num
        input:
            rules.marian.output.trainer,file=f'{translated}/mono_trg/file.{{part}}',
            vocab=rules.train_vocab.output,model=f'{backward_model}/{best_bleu_model}'
        output: f'{translated}/mono_trg/file.{{part}}.out'
        shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                    bash pipeline/translate/translate.sh \
                    "{input.file}" "{input.vocab}" {input.model} 2>{log}'''

    rule collect_mono_trg:
        message: "Collecting translated mono trg dataset"
        log: f"{log_dir}/collect_mono_trg.log"
        conda: "envs/environment.yml"
        threads: workflow.cores
        input:
            files=expand(f"{translated}/mono_trg/file.{{part}}.out",part=parts)
        output: f'{translated}/mono.{src}.gz'
        params: src_mono=f"{clean}/mono.{trg}.gz", dir=directory(f'{translated}/mono_trg')
        shell: '''bash pipeline/translate/collect.sh "{params.dir}" "{output}" "{params.src_mono}" 2>{log}'''

    rule merge_augmented:
        message: "Merging augmented dataset"
        log: f"{log_dir}/merge_augmented.log"
        conda: "envs/environment.yml"
        input:
            src1=rules.clean_corpus.output.src,src2=rules.collect_mono_trg.output,
            trg1=rules.clean_corpus.output.trg,trg2=rules.split_mono_trg.input
        output: res_src=f'{augmented}/corpus.{src}.gz',res_trg=f'{augmented}/corpus.{trg}.gz'
        shell: '''bash pipeline/utils/merge-corpus.sh \
                    {input.src1} {input.src1} {input.trg1} {input.trg2} {output.res_src} {output.res_trg}'''

    teacher_corpus = f'{augmented}/corpus'
else:
    teacher_corpus = f'{augmented}/biclean'


rule teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher{{ens}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores / 4
    resources: gpu=gpus_num
    input:
        train_src=f'{teacher_corpus}.{src}.gz', train_trg=f'{teacher_corpus}.{trg}.gz',
        val_src=rules.data_val.output.src, val_trg = rules.data_val.output.trg,
        bin=rules.marian.output.trainer, vocab=rules.train_vocab.output
    output: dir=directory(f'{teacher_dir}{{ens}}'),model=f'{teacher_dir}{{ens}}/{best_bleu_model}'
    params: prefix_train=teacher_corpus,prefix_test=f"{original}/devset"
    shell: '''SRC={src} TRG={trg} MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash pipeline/train/train-teacher.sh \
                "{output.dir}" "{params.prefix_train}" "{params.prefix_test}" "{input.vocab}" 2>{log}'''



rule eval_teacher:
    message: "Evaluating teacher model"
    log: f"{log_dir}/eval_teacher{{ens}}.log"
    conda: "envs/environment.yml"
    resources: gpu=gpus_num
    input: model=f'{teacher_dir}{{ens}}/{best_bleu_model}', datasets=rules.data_test.output
    output: directory(f'{teacher_dir}{{ens}}/eval')
    shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash ./pipeline/train/eval.sh "{backward_model}" "{evaluation}" {trg} {src} 2>{log}'''

rule eval_teacher_report:
    message: "Adding teacher evaluation to the report"
    input: expand(f'{teacher_dir}{{ens}}/eval', ens=ensemble)
    output:
        report(expand(f'{teacher_dir}{{ens}}/eval', ens=ensemble),
            patterns=["{name}.bleu"],
            caption=f"{reports_dir}/report.rst")



### translation with teacher

# corpus

rule split_corpus:
    message: "Splitting the corpus to translate"
    log: f"{log_dir}/split_corpus.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input: corpus_src=rules.clean_corpus.output.src,corpus_trg=rules.clean_corpus.output.trg
    output: expand(f"{translated}/corpus/file.{{number}}{{ext}}",number=parts,ext=['', '.ref'])
    shell: '''bash pipeline/translate/split-corpus.sh \
                {input.corpus_src} {input.corpus_trg} {translated}/corpus {partitions} 2>{log}'''

rule translate_corpus:
    message: "Translating corpus with teacher"
    log: f"{log_dir}/translate_corpus/{{part}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores / 4
    resources: gpu=gpus_num
    input:
        rules.marian.output.trainer,file=f'{translated}/corpus/file.{{part}}',vocab=rules.train_vocab.output,
        teacher_models=expand(f"{teacher_dir}{{ens}}/{best_bleu_model}",ens=ensemble)
    output: f'{translated}/corpus/file.{{part}}.nbest'
    shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash pipeline/translate/translate-nbest.sh \
                "{input.file}" "{input.vocab}" {input.teacher_models} 2>{log}'''

rule extract_best:
    message: "Extracting best translations for the corpus"
    log: f"{log_dir}/extract_best.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    group: 'translate_corpus'
    input: expand(f"{translated}/corpus/file.{{part}}.nbest",part=parts)
    output: expand(f"{translated}/corpus/file.{{part}}.nbest.out",part=parts)
    params: prefixes=expand(f"{translated}/corpus/file.{{part}}",part=parts)
    shell: '''bash pipeline/translate/extract-best.sh {threads} {params.prefixes} 2>{log}'''

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
    output:
        dir=directory(f'{translated}/mono_src'),
        files=expand(f"{translated}/mono_src/file.{{number}}",number=parts)
    shell: 'bash pipeline/translate/split-mono.sh {input} {output.dir} {partitions} 2>{log}'

rule translate_mono_src:
    message: "Translating monolingual src dataset with teacher"
    log: f"{log_dir}/translate_mono_src/{{part}}.log"
    conda: "envs/environment.yml"
    threads: workflow.cores / 4
    resources: gpu=gpus_num
    input:
        bin=rules.marian.output.trainer,
        file=f'{translated}/mono_src/file.{{part}}',vocab=rules.train_vocab.output,
        teacher_models=expand(f"{teacher_dir}{{ens}}/{best_bleu_model}",ens=ensemble)
    output: f'{translated}/mono_src/file.{{part}}.out'
    shell: '''MARIAN={marian_dir} GPUS="{gpus}" WORKSPACE={workspace} \
                bash pipeline/translate/translate.sh \
                "{input.file}" "{input.vocab}" {input.teacher_models} 2>{log}'''

rule collect_mono_src:
    message: "Collecting translated mono src dataset"
    log: f"{log_dir}/collect_mono_src.log"
    conda: "envs/environment.yml"
    threads: workflow.cores
    input:
        files=expand(f"{translated}/mono_src/file.{{part}}.out",part=parts)
    output: f'{translated}/mono.{trg}.gz'
    params: src_mono=f"{clean}/mono.{src}.gz", dir=f'{translated}/mono_src'
    shell: '''bash pipeline/translate/collect.sh "{params.dir}" "{output}" "{params.src_mono}" 2>{log}'''


rule merge_translated:
    message: "Merging translated datasets"
    log: f"{log_dir}/merge_translated.log"
    conda: "envs/environment.yml"
    input:
        src1=rules.clean_corpus.output.src,src2=f"{clean}/mono.{src}.gz",
        trg1=rules.collect_corpus.output,trg2=rules.collect_mono_src.output
    output: res_src=f'{merged}/corpus.{src}.gz',res_trg=f'{merged}/corpus.{trg}.gz'
    shell: '''bash pipeline/utils/merge-corpus.sh \
                {input.src1} {input.src1} {input.trg1} {input.trg2} {output.res_src} {output.res_trg}'''