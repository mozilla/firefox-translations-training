import pytest

from pipeline.alignments.tokenizer import IcuTokenizer, TokenizerType, tokenize
from fixtures import zh_sample, en_sample, ru_sample, DataDir

tokenized_first_lines = {
    "en": "The ▁ little ▁ girl , ▁ seeing ▁ she ▁ had ▁ lost ▁ one ▁ of ▁ her ▁ pretty ▁ shoes , ▁ grew ▁ angry , ▁ and ▁ said ▁ to ▁ the ▁ Witch , ▁ “ Give ▁ me ▁ back ▁ my ▁ shoe ! ”",
    "ru": "Маленькая ▁ девочка , ▁ увидев , ▁ что ▁ потеряла ▁ одну ▁ из ▁ своих ▁ красивых ▁ туфелек , ▁ рассердилась ▁ и ▁ сказала ▁ Ведьме : ▁ « Верни ▁ мне ▁ мою ▁ туфельку ! »",
    "zh": "小 女孩 看到 自己 丢 了 一只 漂亮 的 鞋子 ， 生气 了 ， 对 女巫 说 ： “ 把 我的 鞋子 还给 我 ！ ”",
}


@pytest.mark.parametrize(
    "lang,sample,first_line",
    [
        ("en", en_sample, tokenized_first_lines["en"]),
        ("ru", ru_sample, tokenized_first_lines["ru"]),
        ("zh", zh_sample, tokenized_first_lines["zh"]),
        ("zh", "这是一个简单的测试语句 🤣 。", "这 是 一个 简单 的 测试 语 句 ▁ 🤣▁ 。"),
    ],
    ids=["en", "ru", "zh", "zh2"],
)
def test_icu_tokenize_detokenize(lang, sample, first_line):
    lines = sample.splitlines()
    tokenizer = IcuTokenizer
    icu_tokenizer = tokenizer(lang)
    tok_lines = []
    detok_lines = []

    for line in lines:
        tokens = icu_tokenizer.tokenize(line)
        detokenized = icu_tokenizer.detokenize(tokens)
        tok_lines.append(" ".join(tokens))
        detok_lines.append(detokenized)

    assert lines == detok_lines
    assert tok_lines[0] == first_line


@pytest.mark.parametrize(
    "lang,sample",
    [
        (
            "en",
            en_sample,
        ),
        (
            "ru",
            ru_sample,
        ),
        ("zh", zh_sample),
    ],
    ids=["en", "ru", "zh"],
)
def test_tokenizer(lang, sample):
    data_dir = DataDir("test_tokenizer")
    input_path = data_dir.create_file(f"input.{lang}.txt", sample)
    output_path = data_dir.join(f"output.{lang}.txt")

    tokenize(
        input_path=input_path,
        output_path=output_path,
        lang=lang,
        tokenizer=TokenizerType.icu,
        sentences_per_chunk=3,
    )

    with open(output_path) as f:
        lines = f.read().splitlines()

    assert len(lines) == len(sample.splitlines())
    assert lines[0] == tokenized_first_lines[lang]
