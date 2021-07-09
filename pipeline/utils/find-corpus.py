#!/usr/bin/env python3
"""
Finds all opus datasets for a language pair
and prints them to set in TRAIN_DATASETS config setting
"""

import requests
import sys

source=sys.argv[1]
target=sys.argv[2]
type=sys.argv[3]

exclude = ['bible', 'CC', 'subtitles', 'Ubuntu', 'Gnome', 'KDE', 'Multi']
names = None

if type == 'opus':
    datasets = requests.get(f'https://opus.nlpl.eu/opusapi/?source={source}&target={target}&preprocessing=moses&version=latest').json()

    cleaned = set()
    for d in datasets['corpora']:
        name = d['corpus']
        version = d['version']

        filter=False
        for ex in exclude:
            if ex.lower() in name.lower():
                filter=True
                break
        if not filter:
            cleaned.add(f'opus_OPUS-{name}/{version}')
    names = cleaned
elif type == 'sacrebleu':
    import sacrebleu
    names = [f'sacrebleu_{name}' for name, meta in sacrebleu.DATASETS.items()
             if f'{source}-{target}' in meta or f'{target}-{source}' in meta]
elif type == 'mtdata':
    from mtdata.main import LangPair
    from mtdata.data import get_entries
    entries = get_entries(LangPair(f'{source}-{target}'), None, None)
    names = [f'mtdata_{entry.name}' for entry in entries]
else:
    print(f'Importer type {type} is unsupported. Supported importers: opus, mtdata, sacrebleu')

print(' '.join(names))