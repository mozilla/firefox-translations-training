#!/usr/bin/env python3
"""
Finds all opus datasets for a language pair and prints them to set config settings.

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

# exclude = ['bible', 'Ubuntu', 'Gnome', 'KDE', 'Multi', 'OPUS100v']
exclude = []
names = []

if type == 'opus':
    exclude += ['OPUS100v', 'WMT-News']
    datasets = requests.get(f'https://opus.nlpl.eu/opusapi/?source={source}&target={target}&preprocessing=moses&version=latest').json()
    names = [f'opus_{d["corpus"]}/{d["version"]}' for d in datasets['corpora']]
elif type == 'sacrebleu':
    import sacrebleu
    names = [f'sacrebleu_{name}' for name, meta in sacrebleu.DATASETS.items()
             if f'{source}-{target}' in meta or f'{target}-{source}' in meta]
elif type == 'mtdata':
    from mtdata.entry import LangPair, lang_pair
    from mtdata.index import get_entries
    from mtdata.iso import iso3_code
    source_tricode = iso3_code(source, fail_error=True)
    target_tricode = iso3_code(target, fail_error=True)
    exclude += ['opus', 'newstest', 'UNv1']
    entries = sorted(get_entries(lang_pair(source_tricode + '-' + target_tricode), None, None, True), key=lambda entry: entry.did.group)
    names = [f'mtdata_{entry.did.group}-{entry.did.name}-{entry.did.version}-{entry.did.lang_str}' for entry in entries]
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

print('\n'.join(sorted([f'    - {name}' for name in cleaned])))
