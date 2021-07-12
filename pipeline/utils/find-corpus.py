#!/usr/bin/env python3
"""
Finds all opus datasets for a language pair
and prints them to set in TRAIN_DATASETS, DEVTEST_DATASETS or TEST_DATASETS config settings.

Usage:
    python find-corpus.py <src> <trg> <importer>

Params:
    src - source language code
    trg - target language code
    importer - importer type (mtdata, opus, sacrebleu)

"""

import requests
import sys

source=sys.argv[1]
target=sys.argv[2]
type=sys.argv[3]

exclude = ['bible', 'Ubuntu', 'Gnome', 'KDE', 'Multi']
names = []

if type == 'opus':
    datasets = requests.get(f'https://opus.nlpl.eu/opusapi/?source={source}&target={target}&preprocessing=moses&version=latest').json()
    names = [f'opus_OPUS-{d["corpus"]}/{d["version"]}' for d in datasets['corpora']]
elif type == 'sacrebleu':
    import sacrebleu
    names = [f'sacrebleu_{name}' for name, meta in sacrebleu.DATASETS.items()
             if f'{source}-{target}' in meta or f'{target}-{source}' in meta]
elif type == 'mtdata':
    from mtdata.main import LangPair
    from mtdata.data import get_entries
    exclude += 'OPUS'
    entries = get_entries(LangPair(f'{source}-{target}'), None, None)
    names = [f'mtdata_{entry.name}' for entry in entries]
else:
    print(f'Importer type {type} is unsupported. Supported importers: opus, mtdata, sacrebleu')

cleaned = set()
for name in names:
    filter=False
    for ex in exclude:
        if ex.lower() in name.lower():
            filter=True
            break
    if not filter:
        cleaned.add(name)

print(' '.join(cleaned))