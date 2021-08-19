

src = config['src']
trg = config['trg']
experiment = config['experiment']

data_root_dir = config['dirs']['data-root']
log_dir = f"{data_root_dir}/logs/{src}-{trg}/{experiment}"
data_dir = f"{data_root_dir}/data/{src}-{trg}/{experiment}"
models_dir = f"{data_root_dir}/models/{src}-{trg}/{experiment}"
marian_dir=config['dirs']['marian']
bin=config['dirs']['bin']
cuda_dir=config['dirs']['cuda']

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

gpus=list(range(int(config['gpus'])))
# \
#     if config['gpus'] != 'all' \
#     else shell("$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))")
workspace=config['workspace']

ensemble=list(range(config['teacher-ensemble']))