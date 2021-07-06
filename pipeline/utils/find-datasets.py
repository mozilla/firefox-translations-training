#!/usr/bin/env python3
"""
Finds all opus datasets for a language pair
and prints them to set in TRAIN_DATASETS config setting
"""

import requests

source='ru'
target='en'
exclude = ['bible', 'CC', 'subtitles', 'Ubuntu', 'Gnome', 'KDE', 'Multi']

datasets = requests.get(f'https://opus.nlpl.eu/opusapi/?source={source}&target={target}&preprocessing=moses&version=latest').json()
print(datasets)
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

print(' '.join(cleaned))