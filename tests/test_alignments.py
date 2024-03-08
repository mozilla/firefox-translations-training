import os

import sh
from fixtures import DataDir

current_folder = os.path.dirname(os.path.abspath(__file__))
fixtures_path = os.path.join(current_folder, "fixtures")
root_path = os.path.abspath(os.path.join(current_folder, ".."))
bin_dir = os.environ["BIN"] if os.getenv("BIN") else os.path.join(root_path, "bin")

# "|||" in the text can cause issues if joint fast_align style input is used
en_sample = """The little girl, seeing she had lost one of her pretty shoes, grew angry, and said to the Witch, “Give me back my shoe!” ||| one
“I will not,” retorted the Witch, “for it is now my shoe, and not yours.”
“You are a wicked creature!” cried Dorothy. “You have no right to take my shoe from me.”
“I shall keep it, just the same,” said the Witch, laughing at her, “and someday I shall get the other one from you, too.”
This made Dorothy so very angry that she picked up the bucket of water that stood near and dashed it over the Witch, wetting her from head to foot.
Instantly the wicked woman gave a loud cry of fear, and then, as Dorothy looked at her in wonder, the Witch began to shrink and fall away.
“See what you have done!” she screamed. “In a minute I shall melt away.”
“I’m very sorry, indeed,” said Dorothy, who was truly frightened to see the Witch actually melting away like brown sugar before her very eyes.
"""

ru_sample = """Маленькая девочка, увидев, что потеряла одну из своих красивых туфелек, рассердилась и сказала Ведьме: «Верни мне мою туфельку!» ||| один
«Я не буду, — парировала Ведьма, — потому что теперь это моя туфля, а не твоя».
«Ты злое существо!» - воскликнула Дороти. «Ты не имеешь права забирать у меня туфлю».
«Я все равно сохраню его, — сказала Ведьма, смеясь над ней, — и когда-нибудь я получу от тебя и другой».
Это так разозлило Дороти, что она взяла стоявшее рядом ведро с водой и облила им Ведьму, обмочив ее с головы до ног.
Мгновенно злая женщина громко вскрикнула от страха, а затем, когда Дороти с удивлением посмотрела на нее, Ведьма начала сжиматься и падать.
«Посмотри, что ты наделал!» она закричала. «Через минуту я растаю».
«Мне действительно очень жаль», — сказала Дороти, которая была по-настоящему напугана, увидев, что Ведьма тает, как коричневый сахар, у нее на глазах.
"""

def verify_aln(data_dir, dataset, src_corpus, trg_corpus):
    aln_path = os.path.join(data_dir.path, "artifacts", f"{dataset}.aln.zst")
    assert os.path.exists(aln_path)

    sh.zstd("-d", aln_path)
    with open(aln_path[:-4], "r") as f:
        aln_lines = f.readlines()

    src_lines = src_corpus.strip().split("\n")
    trg_lines = trg_corpus.strip().split("\n")
    assert len(aln_lines) == len(src_lines)
    assert len(aln_lines) == len(trg_lines)

    # verify alignment indices
    for aln_line, src_line, trg_line in zip(aln_lines, src_lines, trg_lines):
        alns = [pair.split("-") for pair in aln_line.split()]
        src_tokens_num = len(src_line.split())
        trg_tokens_num = len(trg_line.split())

        assert all(
            int(src_idx) < src_tokens_num and int(trg_idx) < trg_tokens_num
            for src_idx, trg_idx in alns
        )


def test_space_tokenized_aln():
    data_dir = DataDir("test_alignments")
    data_dir.create_zst("corpus.en.zst", en_sample),
    data_dir.create_zst("corpus.ru.zst", ru_sample),
    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": bin_dir,
        "COMPRESSION_CMD": "zstd",
        "ARTIFACT_EXT": "zst",
        "SRC": "en",
        "TRG": "ru",
    }

    data_dir.run_task("alignments-student-en-ru", env=env)

    verify_aln(data_dir, "corpus", en_sample, ru_sample)


def test_space_tokenized_aln_merged():
    data_dir = DataDir("test_alignments")
    data_dir.create_zst("corpus.en.zst", en_sample),
    data_dir.create_zst("corpus.ru.zst", ru_sample),
    mono_en_sample = "\n".join(en_sample.split("\n")[1:-1])
    mono_ru_sample = "\n".join(ru_sample.split("\n")[1:-1])
    data_dir.create_zst("mono.en.zst", mono_en_sample),
    data_dir.create_zst("mono.ru.zst", mono_ru_sample),
    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": bin_dir,
        "COMPRESSION_CMD": "zstd",
        "ARTIFACT_EXT": "zst",
        "SRC": "en",
        "TRG": "ru",
    }

    data_dir.run_task("alignments-teacher-en-ru", env=env)

    for dataset, src_corpus, trg_corpus in (
        ("corpus", en_sample, ru_sample),
        ("mono", mono_en_sample, mono_ru_sample),
    ):
        verify_aln(data_dir, dataset, src_corpus, trg_corpus)


# TODO: need to pull marian and spm vocab
# def test_shortlist():
#     data_dir = DataDir("test_alignments")
#     data_dir.create_zst("corpus.en.zst", en_sample),
#     data_dir.create_zst("corpus.ru.zst", ru_sample),
#     env = {
#         "TEST_ARTIFACTS": data_dir.path,
#         "BIN": bin_dir,
#         "COMPRESSION_CMD": "zstd",
#         "ARTIFACT_EXT": "zst",
#         "SRC": "en",
#         "TRG": "ru",
#     }
#
#     data_dir.run_task("shortlist-en-ru", env=env)

