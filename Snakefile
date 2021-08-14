
configfile: 'config.yml'

src=config['src']
trg=config['trg']


data_dir=f"{config['data-root-dir']}/data/{config['src']}-{config['trg']}/{config['experiment']}"
models_dir=f"{config['data-root-dir']}/models/{config['src']}-{config['trg']}/{config['experiment']}"
log_dir=f"{config['data-root-dir']}/logs/{config['src']}-{config['trg']}/{config['experiment']}"
cache_dir=f"{data_dir}/cache"
original=f"{data_dir}/original"
clean=f"{data_dir}/clean"
# gpus=shell("$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))")
train_datasets=['mtdata_newsdev2017_zhen', 'mtdata_wiki_titles_v1']

teacher_dir=f"{models_dir}/teacher"

OUTPUT=f'{models_dir}/teacher/model.bin'

rule all:
    input: OUTPUT

rule download_corpus:
    message: "Downloading corpus"
    log: f"{log_dir}/donload_corpus.log"
    output: f"{original}/corpus.{src}.gz", f"{original}/corpus.{trg}.gz"
    params: prefix=f"{original}/corpus"
    shell: '''
        bash ./pipeline/data/download-corpus.sh "{params.prefix}" "{cache_dir}" {train_datasets} 2> {log}
    '''


rule clean_corpus:
    message: "Cleaning corpus"
    log: f"{log_dir}/clean_corpus.log"
    input: f"{original}/corpus.{src}.gz", f"{original}/corpus.{trg}.gz"
    output: f"{clean}/corpus.{src}.gz", f"{clean}/corpus.{trg}.gz"
    params: prefix_input=f"{clean}/corpus", prefix_output=f"{clean}/corpus"
    shell: 'bash ./pipeline/clean/clean-corpus.sh "{params.prefix_input}" "{params.prefix_output}" 2> {log}'

rule train_teacher:
    message: "Training teacher"
    log: f"{log_dir}/train_teacher.log"
    input: f"{clean}/corpus.{src}.gz", f"{clean}/corpus.{trg}.gz"
    output: OUTPUT
    params: prefix_corpus=f"{clean}/corpus"
    shell: 'bash ./pipeline/train/train-teacher.sh "{teacher_dir}" "{params.prefix_corpus}" "{original}/devset 2> {log}"'

