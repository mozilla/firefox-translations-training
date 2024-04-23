
import opusfilter

from cache import ScoreCache


class CachedScores(opusfilter.FilterABC):

    def __init__(self, path, threshold, **kwargs):
        self.threshold = threshold
        super().__init__(**kwargs)
        self.cache = ScoreCache()
        self.cache.load(path)

    def score(self, pairs):
        for src, trg in pairs:
            yield self.cache.get(src, trg) or [0.0]

    def accept(self, scores):
        return all(score < self.threshold for score in scores)


class CachedLaserSimilarity(CachedScores):
    # todo: double check this
    score_direction = opusfilter.CLEAN_HIGH
    accept_threshold = 0
    reject_threshold = 1 + 10**-6


class CachedBicleanerAi(CachedScores):
    score_direction = opusfilter.CLEAN_HIGH
    accept_threshold = 0
    reject_threshold = 1 + 10**-6
