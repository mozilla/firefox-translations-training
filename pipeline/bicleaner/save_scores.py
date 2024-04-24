import zstandard
import sys
import json
scores = []


assert sys.argv[1].endswith('.zst')

print('reading {}'.format(sys.argv[1]))

with zstandard.open(sys.argv[1], 'rt') as fr:
    with open(sys.argv[2], 'w') as fw:
        for line in fr:
            score = float(line.rstrip().split('\t')[-1])
            fw.write(json.dumps({'BicleanerAI': [score]}))
            fw.write('\n')


print('Saved to {}'.format(sys.argv[2]))

