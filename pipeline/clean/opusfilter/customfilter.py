import re

from opusfilter import FilterABC, CLEAN_HIGH, CLEAN_LOW
import math

from opusfilter.util import check_args_compability

from opusfilter import ConfigurationError
from cache import ScoreCache

CHARS = {
    'ar': r'[\u0600-\u06FF]', # This is not entirely right, as it also includes farsi symbols and whatnot
    'bg': r'[АаБбВвГгДддЕеЖжЗзИиЙйКкkasЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЬьЮюЯя]',
    'bn': r'[\u0980-\u09FF]', # bangla
    'ca': r'[a-zÀàÈèÉéÍíÒòÓóÚúÇç]',
    'cs': r'[a-zÁáČčĎďÉéěÍíŇňÓóŘřŠšŤťÚúůÝýŽž]',
    'da': r'[a-zÆæØøÅå]',
    'de': r'[a-zÄäÖöÜüß]',
    'en': r'[a-z]',
    'el': r'[a-zΑαΒβΓγΔδΕεΖζΗηΘθΙιΚκΛλΜμΝνΞξΟοΠπΡρΣσςΤτΥυΦφΧχΨψΩω]',
    'es': r'[a-zÁáÉéÍíÓóÚúñÑ]',
    'et': r'[a-zÕõÄäÖöÜü]',
    'eu': r'[a-zñÑ]',
    'fi': r'[a-zÅåÄäÖö]',
    'fr': r'[a-zÂâÁáÀàâÇçÉéÈèÊêÓóÒòÔôŒœÜüÛûŸÿ]',
    'ga': r'[abcdefghilmnoprstuáéíóúÁÉÍÓÚ]',
    'gl': r'[a-zÁáÉéÍíÓóÚúÑñ]',
    'hi': r'[\u0900-\u097F]', # devanagari
    'hr': r'[abcčČćĆdđĐefghijklmnoprsšŠtuvzžŽ]',
    'hu': r'[a-zÁáÉéÍíÓóÖöŐőŰű]',
    'hy': r'[\u0530-\u058F]',
    'is': r'[abdefghijklmnoprstuvxyÁáðÐÉéÍíÓóÚúÝýÞþÆæÖö]',
    'it': r'[a-zàÀèÈéÉìÌíÍîÎòÒóÓùÙúÚ]',
    'ko': r'[\uac00-\ud7af]|[\u1100-\u11ff]|[\u3130-\u318f]|[\ua960-\ua97f]|[\ud7b0-\ud7ff]',
    'lt': r'[aąbcČčdeĘęĖėfghiĮįyjklmnoprsŠštuŲųŪūvzŽž]',
    'lv': r'[aĀābcČčdeĒēfgĢģhiĪījkĶķlĻļmnŅņoprsŠštuŪūvzŽž]',
    'mt': r'[abĊċdefĠġghĦħiiejklmnopqrstuvwxŻżz]',
    'nb': r'[a-zÂâÁáÀàâÉéÈèÊêÓóÒòÔôÜüÆæØøÅå]',
    'nl': r'[a-zÂâÁáÀàâÉéÈèÊêÓóÒòÔôÚú]',
    'no': r'[a-zÂâÁáÀàâÉéÈèÊêÓóÒòÔôÜüÆæØøÅå]',
    'nn': r'[a-zÂâÁáÀàâÉéÈèÊêÓóÒòÔôÜüÆæØøÅå]',
    'pl': r'[a-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]',
    'pt': r'[a-zÂâÁáÀàÃãÇçÉéÈèÊêÍíÌìÓóÒòÔôÕõÚúÙù]',
    'ro': r'[a-zĂăÂâÎîȘșȚț]',
    'ru': r'[а-я]',
    'sk': r'[a-záäÁÄčČďĎžéÉíÍĺĹľĽňŇóÓôÔŕŔšŠťŤúÚýÝžŽ]',
    'sl': r'[abcčČdđĐefghijklmnoprsšŠtuvzžŽ]',
    'sv': r'[a-zÅåÄäÖö]',
    'uk': r'[А-ЩЬЮЯҐЄІЇа-щьюяґєії\'`’ʼ]',
    'zh': r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]',
}


class CachedScores(FilterABC):

    def __init__(self, path, threshold=0.5, **kwargs):
        self.threshold = threshold
        super().__init__(**kwargs)
        self.cache = ScoreCache()
        self.cache.load(path)

    def score(self, pairs):
        for src, trg in pairs:
            yield self.cache.get(src, trg) or [0.0]

    def accept(self, scores):
        return all(score >= self.threshold for score in scores)


class CustomCachedLaserSimilarity(CachedScores):
    # todo: double check this
    score_direction = CLEAN_HIGH
    accept_threshold = 0
    reject_threshold = 1 + 10**-6


class CustomCachedBicleanerAi(CachedScores):
    score_direction = CLEAN_HIGH
    accept_threshold = 0
    reject_threshold = 1 + 10**-6


class CustomAlphaRatioFilter(FilterABC):
    """Similar to OpusCleaner alpha_ratio"""

    score_direction = CLEAN_HIGH
    accept_threshold = 0
    reject_threshold = 1 + 10**-6

    def __init__(self, thresholds=None, languages=None, unit='word', **kwargs):
        if languages is None:
            raise ConfigurationError("A list of languages needs to be defined")
        self.languages = languages
        self.thresholds = [0.5] * len(languages) if thresholds is None else thresholds
        self.unit = check_args_compability(
            unit, required_types=[str], choices=[('word', 'char', 'character')], names=['unit'])
        self.regexes = [re.compile(CHARS[lang], re.IGNORECASE) if lang in CHARS else None
                        for lang in languages]
        super().__init__(**kwargs)

    def get_ratio(self, segment, idx):
        lang = self.languages[idx]
        if lang not in CHARS:
            return 1.0

        if self.unit[idx] == 'word':
            tokens = segment.split()
            length = float(len(tokens))
            if length == 0:
                return 1.0
            num_words = sum(
                [1 if self.regexes[idx].match(tok) else 0 for tok in tokens])
            return num_words / length
        else:
            char_alpha = len(self.regexes[idx].findall(segment))
            length = float(len(segment.replace(' ', '')))
            if length == 0:
                return 1.0
            return char_alpha / length

    def score(self, pairs):
        for pair in pairs:
            ratios = [self.get_ratio(segment, idx) for idx, segment in enumerate(pair)]
            yield ratios

    def accept(self, score):
        return all(ratio >= threshold for ratio, threshold in zip(score, self.thresholds))
