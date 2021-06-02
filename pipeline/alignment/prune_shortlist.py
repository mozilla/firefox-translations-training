#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

MAX = int(sys.argv[1])
TOP = sys.argv[2]

tops = []

with open(TOP, "r") as f:
    for line in f:
        tops.append(line.strip().split()[0])

tops = tops[:MAX + 2]

vocabTrg = []
vocabSrc = []
pairs = {}

for line in sys.stdin:
    trg, src, prob = line.strip().split()
    if trg == "NULL" or src == "NULL":
        continue

    # sys.stderr.write("{} {} {} \n".format(trg, src, prob))

    vocabTrg.append(trg)
    vocabSrc.append(src)

    prob = float(prob)
    if src in pairs:
        pairs[src][trg] = prob
    else:
        pairs[src] = {trg: prob}

vocabTrg = set(vocabTrg)
vocabSrc = set(vocabSrc)

for src in vocabSrc:
    d = pairs[src]
    topSrc = list(sorted(d, key=d.get, reverse=True)[:MAX])
    for trg in topSrc + tops:
        if trg in d:
            prob = d[trg]
            print("{} {} {:.8f}".format(trg, src, prob))

