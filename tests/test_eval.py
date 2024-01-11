import json
import os
import subprocess

from fixtures import DataDir, ca_sample, en_sample, fail_on_error

current_folder = os.path.dirname(os.path.abspath(__file__))
fixtures_path = os.path.join(current_folder, "fixtures")


def shared_setup(env: dict[str, str]):
    # See data/test_data/test_eval_vocab for the artifacts after a failure.
    test_data_dir = DataDir("test_eval")

    # Create the dataset.
    dataset_prefix = test_data_dir.join("wmt09")
    test_data_dir.create_zst("wmt09.en.zst", en_sample),
    test_data_dir.create_zst("wmt09.ca.zst", ca_sample),

    env = {
        **os.environ,
        **env,
        "COMPRESSION_CMD": "zstd",
        "ARTIFACT_EXT": "zst",
        "TEST_ARTIFACTS": test_data_dir.path,
        "PATH": fixtures_path + ":" + os.environ.get("PATH"),
    }

    return test_data_dir, dataset_prefix, env


def run_common_assertions(test_data_dir: DataDir) -> None:
    sacrebleu_args = json.loads(test_data_dir.load("sacrebleu.args.txt"))
    sacrebleu_stdin = test_data_dir.load("sacrebleu.stdin.txt")

    fake_translations = "\n".join([line.upper() for line in en_sample.split("\n")])

    # The data sets should be written out to the artifacts.
    assert test_data_dir.load("artifacts/wmt09.en") == en_sample, "The source corpus was written"
    assert (
        test_data_dir.load("artifacts/wmt09.ca.ref") == ca_sample
    ), "The target (reference) corpus was written"
    assert (
        test_data_dir.load("artifacts/wmt09.ca") == fake_translations
    ), "The target (translated) corpus was written"

    assert sacrebleu_args == [
        # fmt: off
        test_data_dir.join("artifacts/wmt09.ca.ref"),
        "--detail",
        "--format", "text",
        "--score-only",
        "--language-pair", "en-ca",
        "--metrics", "bleu", "chrf",
        # fmt: on
    ], "The sacrebleu arguments matched."

    assert sacrebleu_stdin == fake_translations, "Sacrebleu received the translated corpus"
    assert test_data_dir.load("artifacts/wmt09.metrics") == "12.3\n45.6\n"


def test_eval_sh() -> None:
    test_data_dir, dataset_prefix, env = shared_setup({})

    command = [
        "pipeline/eval/eval.sh",
        test_data_dir.join("artifacts/wmt09"),  # artifacts_prefix
        dataset_prefix,
        "en",  # src
        "ca",  # trg
        fixtures_path,
        test_data_dir.join("fake_config.yml"),
        # Marian args:
        "--models",
        test_data_dir.join("fake_model.npz"),
    ]

    result = subprocess.run(command, env=env, stderr=subprocess.PIPE, check=False)
    fail_on_error(result)

    run_common_assertions(test_data_dir)

    # Marian is passed a certain set of arguments. This can start failing if the marian
    # arguments are adjusted.
    marian_decoder_args = json.loads(test_data_dir.load("marian-decoder.args.txt"))
    assert marian_decoder_args == [
        # fmt: off
        "--config", test_data_dir.join("fake_config.yml"),
        "--quiet",
        "--quiet-translation",
        "--log",    test_data_dir.join("artifacts/wmt09.log"),
        "--models", test_data_dir.join("fake_model.npz"),
        # fmt: on
    ], "The marian arguments matched."


def test_eval_gpu_sh() -> None:
    test_data_dir, dataset_prefix, env = shared_setup(
        {
            "GPUS": "4",
            "MARIAN": fixtures_path,
            "WORKSPACE": "1024",
        }
    )

    command = [
        "pipeline/eval/eval-gpu.sh",
        test_data_dir.join("artifacts/wmt09"),  # artifacts_prefix
        dataset_prefix,
        "en",  # src
        "ca",  # trg
        test_data_dir.join("fake_config.yml"),
        test_data_dir.join("fake_model.npz"),
    ]

    result = subprocess.run(command, env=env, stderr=subprocess.PIPE, check=False)
    fail_on_error(result)

    # Marian is passed a certain set of arguments. This can start failing if the marian
    # arguments are adjusted.
    marian_decoder_args = json.loads(test_data_dir.load("marian-decoder.args.txt"))
    assert marian_decoder_args == [
        # fmt: off
        "--config", test_data_dir.join("fake_config.yml"),
        "--quiet",
        "--quiet-translation",
        "--log", test_data_dir.join("artifacts/wmt09.log"),
        '--workspace', '1024',
        '--devices', '4',
        "--models", test_data_dir.join("fake_model.npz"),
        # fmt: on
    ], "The marian arguments matched."


def test_eval_quantized_sh() -> None:
    test_data_dir, dataset_prefix, env = shared_setup(
        {
            "BMT_MARIAN": fixtures_path,
            "SRC": "en",
            "TRG": "ca",
        }
    )

    command = [
        "pipeline/eval/eval-quantized.sh",
        test_data_dir.join("fake_model.npz"),  # model_path
        test_data_dir.join("fake_shortlist-lex.s2t.pruned"),  # shortlist
        dataset_prefix,
        test_data_dir.join("vocab.spm"),
        test_data_dir.join("artifacts/wmt09"),  # artifacts_prefix
        test_data_dir.join("fake_config.yml"),  # decoder_config
    ]

    result = subprocess.run(command, env=env, stderr=subprocess.PIPE, check=False)
    fail_on_error(result)

    # Marian is passed a certain set of arguments. This can start failing if the marian
    # arguments are adjusted.
    marian_decoder_args = json.loads(test_data_dir.load("marian-decoder.args.txt"))
    assert marian_decoder_args == [
        # fmt: off
        "--config", test_data_dir.join("fake_config.yml"),
        "--quiet",
        "--quiet-translation",
        "--log", test_data_dir.join("artifacts/wmt09.log"),
        "--models", test_data_dir.join("fake_model.npz"),
        '--vocabs',
        test_data_dir.join('vocab.spm'),
        test_data_dir.join('vocab.spm'),
        '--shortlist', test_data_dir.join('fake_shortlist-lex.s2t.pruned'), 'false',
        '--int8shiftAlphaAll',
        # fmt: on
    ], "The marian arguments matched."
