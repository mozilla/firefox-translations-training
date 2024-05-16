from opusfilter import FilterABC, ConfigurationError, CLEAN_HIGH
from opusfilter.util import file_open, grouper
from laser_encoders import download_models
import collections
import itertools
import logging
import os
import pickle
import pycountry
from laser_encoders import LaserEncoderPipeline
from sklearn.metrics.pairwise import cosine_similarity

from tqdm import tqdm

logger = logging.getLogger(__name__)

def convert_iso_639_1_to_639_2(lang_code):
    try:
        # Find the language by its ISO 639-1 code (two-letter code)
        language = pycountry.languages.get(alpha_2=lang_code)
        # Return the ISO 639-2 code (three-letter code)
        return language.alpha_3
    except AttributeError:
        # Return None if the language code is not found
        raise ValueError(f'Language code not found: {lang_code}')


class Laser3Filter(FilterABC):
    """Filtering based on multilingual sentence embeddings LASER 2/3

    Similar to LASER1 based
    https://github.com/Helsinki-NLP/OpusFilter/blob/b69f72dd84029a9f815413a0fac0055a1cac76c4/opusfilter/embeddings.py#L62

    """

    score_direction = CLEAN_HIGH
    accept_threshold = 0
    reject_threshold = 1 + 10**-6

    def __init__(self, languages, threshold=0.5, chunksize=200, **kwargs):
        self.threshold = threshold
        self.languages = languages
        for idx, lang in enumerate(languages):
            os.makedirs(f"data/laser_{lang}", exist_ok=True)
            self.laser_encoders[idx] = LaserEncoderPipeline(lang=convert_iso_639_1_to_639_2(lang),
                                                     model_dir=f"data/laser_{lang}")

        self.chunksize = chunksize
        super().__init__(**kwargs)

    # TODO: test this
    def _cosine_similarities(self, pairs):
        """Calculate cosine similarities for the segments"""
        from scipy.spatial.distance import cosine
        input_per_lang = zip(*pairs)
        output_per_lang = [[],[]]
        for idx, segments in enumerate(input_per_lang):
            embeddings = self.laser_encoders[idx].encode_sentences(segments)
            output_per_lang[idx].append(embeddings)

        yield [float(sim) for sim in cosine_similarity(output_per_lang[0], output_per_lang[1])]

    def _score_chunk(self, chunk):
        """Return scores for a chunk of data"""
        return self._cosine_similarities(chunk)

    def score(self, pairs):
        for chunk in grouper(pairs, self.chunksize):
            for score in self._score_chunk(chunk):
                yield score

    def accept(self, score):
        return all(similarity >= self.threshold for similarity in score)

    def filter(self, pairs):
        for chunk in grouper(pairs, self.chunksize):
            for pair, score in zip(pairs, self._score_chunk(chunk)):
                if self.accept(score):
                    yield pair
