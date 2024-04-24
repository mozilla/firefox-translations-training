import argparse
import hashlib
import logging
import os
import pickle
import json


def hash_sents(src, trg):
    text = f'{src}\t{trg}'
    return hashlib.sha1(text.encode()).hexdigest()


class ScoreCache:
    def __init__(self):
        self.cache = {}

    def load_raw_scores(self, src_path, trg_path, scores_path):
        with open(src_path) as src_f:
            with open(trg_path) as trg_f:
                with open(scores_path) as scores_f:
                    for src, trg, score in zip(src_f,
                                               trg_f,
                                               scores_f):
                        self.cache[hash_sents(src.rstrip(), trg.rstrip())] = [float(score.rstrip())]

    def load_opusfilter_scores(self, src_path, trg_path, scores_path, filter):
        with open(src_path) as src_f:
            with open(trg_path) as trg_f:
                with open(scores_path) as scores_f:
                    for src, trg, score_json in zip(src_f,
                                                    trg_f,
                                                    scores_f):
                        # list
                        scores = json.loads(score_json)[filter]
                        self.cache[hash_sents(src[:-1], trg[:-1])] = scores

    def save(self, output_path):
        with open(output_path, 'wb') as f:
            pickle.dump(self.cache, f)

    def get(self, src, trg):
        hashed = hash_sents(src, trg)
        if hashed not in self.cache:
            logging.warning(f'Sentence pair is not found in cache: {src}, {trg}')
            return None
        return self.cache[hash_sents(src, trg)]

    def load(self, path):
        with open(path, 'rb') as f:
            self.cache = pickle.load(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "src_path", metavar="SRC_PATH", type=str, help="Path to source lang corpus"
    )
    parser.add_argument("trg_path", metavar="TRG_PATH", type=str, help="Path to target lang corpus")
    parser.add_argument("--opus_scores", metavar="OPUS_SCORES", type=str, help="Path to scores file")
    parser.add_argument("--opus_filter_name", metavar="FILTER_SCORES", type=str,
                        help="Name of the opus filter to read opus scores")
    parser.add_argument("--raw_scores", metavar="RAW_SCORES", type=str, help="Path to scores file")
    parser.add_argument("output", metavar="OUTPUT", type=str, help="Write cache file here")

    args = parser.parse_args()

    cache = ScoreCache()
    if args.opus_scores is not None:
        if args.opus_filter_name is None:
            raise ValueError("--opus_filter_name must be provided ")
        cache.load_opusfilter_scores(args.src_path, args.trg_path, args.opus_scores, args.opus_filter_name)
    elif args.raw_scores is not None:
        cache.load_raw_scores(args.src_path, args.trg_path, args.raw_scores)
    else:
        raise ValueError("Either --opus_scores and --opus_filter_name or --raw_scores must be provided ")
    cache.save(args.output)


def test_cache_raw():
    src = 'xxxxxxx'
    trg = 'yyyyy'

    os.makedirs('data/tests_data/test_cache', exist_ok=True)

    with open('data/tests_data/test_cache/test.src', 'w') as f_src:
        for i in range(100):
            f_src.write(src + str(i))
            f_src.write('\n')

    with open('data/tests_data/test_cache/test.trg', 'w') as f_trg:
        for i in range(100):
            f_trg.write(trg + str(i))
            f_trg.write('\n')

    with open('data/tests_data/test_cache/test.scores', 'w') as f_trg:
        for i in range(100):
            f_trg.write(str(float(i)))
            f_trg.write('\n')

    cache = ScoreCache()
    cache.load_raw_scores('data/tests_data/test_cache/test.src', 'data/tests_data/test_cache/test.trg',
                          'data/tests_data/test_cache/test.scores')
    assert len(cache.cache) == 100
    assert cache.get(src + '50', trg + '50') == [50.0]

    cache.save('data/tests_data/test_cache/cache.pickle')
    new_cache = ScoreCache()
    new_cache.load('data/tests_data/test_cache/cache.pickle')

    assert len(new_cache.cache) == 100
    assert cache.get(src + '50', trg + '50') == [50.0]


def test_cache_json():
    src = 'xxxxxxx'
    trg = 'yyyyy'

    os.makedirs('data/tests_data/test_cache', exist_ok=True)

    with open('data/tests_data/test_cache/test.src', 'w') as f_src:
        for i in range(100):
            f_src.write(src + str(i))
            f_src.write('\n')

    with open('data/tests_data/test_cache/test.trg', 'w') as f_trg:
        for i in range(100):
            f_trg.write(trg + str(i))
            f_trg.write('\n')

    with open('data/tests_data/test_cache/test.scores', 'w') as f_trg:
        for i in range(100):
            f_trg.write('{"LengthRatioFilter": [' + str(float(i)) + ']}')
            f_trg.write('\n')

    cache = ScoreCache()
    cache.load_opusfilter_scores('data/tests_data/test_cache/test.src', 'data/tests_data/test_cache/test.trg',
                                 'data/tests_data/test_cache/test.scores', 'LengthRatioFilter')
    assert len(cache.cache) == 100
    assert cache.get(src + '50', trg + '50') == [50.0]

    cache.save('data/tests_data/test_cache/cache.pickle')
    new_cache = ScoreCache()
    new_cache.load('data/tests_data/test_cache/cache.pickle')

    assert len(new_cache.cache) == 100
    assert cache.get(src + '50', trg + '50') == [50.0]
