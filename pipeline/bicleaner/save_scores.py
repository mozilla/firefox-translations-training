import zstandard
import sys
import json
scores = []


assert sys.argv[1].endswith('.zst')

print('reading {}'.format(sys.argv[1]))

with zstandard.open(sys.argv[1], 'rt') as f:
    for line in f:
        score = float(line.rstrip().split('\t')[-1])
        scores.append({'BicleanerAI': [score]})

with open(sys.argv[2], 'w') as f:
    json.dump(scores, f)

print('Saved to {}'.format(sys.argv[2]))

