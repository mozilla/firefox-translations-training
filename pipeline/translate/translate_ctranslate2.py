"""
Translate a corpus with a teacher model (transformer-based) using CTranslate2. This is useful
to quickly synthesize training data for student distillation as CTranslate2 is X (TODO) times faster
than Marian.

https://github.com/OpenNMT/CTranslate2/
"""

from typing import Any, TextIO
from enum import Enum
from glob import glob
from pathlib import Path

import ctranslate2
import sentencepiece as spm
from ctranslate2.converters.marian import MarianConverter

from pipeline.common.downloads import read_lines, write_lines
from pipeline.common.logging import (
    get_logger,
    start_gpu_logging,
    start_byte_count_logger,
    stop_gpu_logging,
    stop_byte_count_logger,
)
from pipeline.common.marian import get_combined_config


def load_vocab(path: str):
    logger.info("Loading vocab:")
    logger.info(path)
    sp = spm.SentencePieceProcessor(path)

    return [sp.id_to_piece(i) for i in range(sp.vocab_size())]


# The vocab expects a .yml file. Instead directly load the vocab .spm file via a monkey patch.
if not ctranslate2.converters.marian.load_vocab:
    raise Exception("Expected to be able to monkey patch the load_vocab function")
ctranslate2.converters.marian.load_vocab = load_vocab

logger = get_logger(__file__)


class Device(Enum):
    gpu = "gpu"
    cpu = "cpu"


class MaxiBatchSort(Enum):
    src = "src"
    none = "none"


def get_model(models_globs: list[str]) -> Path:
    models: list[Path] = []
    for models_glob in models_globs:
        for path in glob(models_glob):
            models.append(Path(path))
    if not models:
        raise ValueError(f'No model was found with the glob "{models_glob}"')
    if len(models) != 1:
        logger.info(f"Found models {models}")
        raise ValueError("Ensemble training is not supported in CTranslate2")
    return Path(models[0])


class DecoderConfig:
    def __init__(self, extra_marian_args: list[str]) -> None:
        super().__init__()
        # Combine the two configs.
        self.config = get_combined_config(Path(__file__).parent / "decoder.yml", extra_marian_args)

        self.mini_batch_words: int = self.get_from_config("mini-batch-words", int)
        self.beam_size: int = self.get_from_config("beam-size", int)
        self.precision = self.get_from_config("precision", str)

    def get_from_config(self, key: str, type: any):
        value = self.config.get(key, None)
        if value is None:
            raise ValueError(f'"{key}" could not be found in the decoder.yml config')
        if isinstance(value, type):
            return value
        if type == int and isinstance(value, str):
            return int(value)
        raise ValueError(f'Expected "{key}" to be of a type "{type}" in the decoder.yml config')


def write_single_translation(
    _index: int, tokenizer_trg: spm.SentencePieceProcessor, result: Any, outfile: TextIO
):
    """
    Just write each single translation to a new line. If beam search was used all the other
    beam results are discarded.
    """
    line = tokenizer_trg.decode(result.hypotheses[0])
    outfile.write(line)
    outfile.write("\n")


def write_nbest_translations(
    index: int, tokenizer_trg: spm.SentencePieceProcessor, result: Any, outfile: TextIO
):
    """
    Match Marian's way of writing out nbest translations. For example, with a beam-size of 2 and
    collection nbest translations:

    0 ||| Translation attempt
    0 ||| An attempt at translation
    1 ||| The quick brown fox jumped
    1 ||| The brown fox quickly jumped
    ...
    """
    for hypothesis in result.hypotheses:
        line = tokenizer_trg.decode(hypothesis)
        outfile.write(f"{index} ||| {line}\n")


def translate_with_ctranslate2(
    input_zst: Path,
    artifacts: Path,
    extra_marian_args: list[str],
    models_globs: list[str],
    is_nbest: bool,
    vocab: list[str],
    device: str,
    device_index: list[int],
) -> None:
    model = get_model(models_globs)
    postfix = "nbest" if is_nbest else "out"

    tokenizer_src = spm.SentencePieceProcessor(vocab[0])
    if len(vocab) == 1:
        tokenizer_trg = tokenizer_src
    else:
        tokenizer_trg = spm.SentencePieceProcessor(vocab[1])

    if extra_marian_args and extra_marian_args[0] != "--":
        logger.error(" ".join(extra_marian_args))
        raise Exception("Expected the extra marian args to be after a --")

    decoder_config = DecoderConfig(extra_marian_args[1:])

    ctranslate2_model_dir = model.parent / f"{Path(model).stem}"
    logger.info("Converting the Marian model to Ctranslate2:")
    logger.info(model)
    logger.info("Outputing model to:")
    logger.info(ctranslate2_model_dir)

    converter = MarianConverter(model, vocab)
    converter.convert(ctranslate2_model_dir, quantization=decoder_config.precision)

    if device == "gpu":
        translator = ctranslate2.Translator(
            str(ctranslate2_model_dir), device="cuda", device_index=device_index
        )
    else:
        translator = ctranslate2.Translator(str(ctranslate2_model_dir), device="cpu")

    logger.info("Loading model")
    translator.load_model()
    logger.info("Model loaded")

    output_zst = artifacts / f"{input_zst.stem}.{postfix}.zst"

    num_hypotheses = 1
    write_translation = write_single_translation
    if is_nbest:
        num_hypotheses = decoder_config.beam_size
        write_translation = write_nbest_translations

    def tokenize(line):
        return tokenizer_src.Encode(line.strip(), out_type=str)

    five_minutes = 300
    if device == "gpu":
        start_gpu_logging(logger, five_minutes)
    start_byte_count_logger(logger, five_minutes, output_zst)

    index = 0
    with write_lines(output_zst) as outfile, read_lines(input_zst) as lines:
        for result in translator.translate_iterable(
            # Options for "translate_iterable":
            # https://opennmt.net/CTranslate2/python/ctranslate2.Translator.html#ctranslate2.Translator.translate_iterable
            map(tokenize, lines),
            max_batch_size=decoder_config.mini_batch_words,
            batch_type="tokens",
            # Options for "translate_batch":
            # https://opennmt.net/CTranslate2/python/ctranslate2.Translator.html#ctranslate2.Translator.translate_batch
            beam_size=decoder_config.beam_size,
            return_scores=False,
            num_hypotheses=num_hypotheses,
        ):
            write_translation(index, tokenizer_trg, result, outfile)
            index += 1

    stop_gpu_logging()
    stop_byte_count_logger()
