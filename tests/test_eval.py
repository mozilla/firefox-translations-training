"""
Tests evaluations
"""

import json
import os

from fixtures import DataDir, en_sample, ru_sample

en_fake_translated = "\n".join([line.upper() for line in ru_sample.split("\n")])
ru_fake_translated = "\n".join([line.upper() for line in en_sample.split("\n")])

current_folder = os.path.dirname(os.path.abspath(__file__))
fixtures_path = os.path.join(current_folder, "fixtures")
root_path = os.path.abspath(os.path.join(current_folder, ".."))


def create_test_data() -> DataDir:
    # See /data/test_data/test_eval for the artifacts after a failure.
    data_dir = DataDir("test_eval")
    data_dir.create_zst("wmt09.en.zst", en_sample)
    data_dir.create_zst("wmt09.ru.zst", ru_sample)
    return data_dir


def run_normal_eval_task(data_dir: DataDir, task_name: str) -> None:
    data_dir.run_task(
        task_name,
        env={
            # This is where the marian_decoder_args will get stored.
            "TEST_ARTIFACTS": data_dir.path,
            # Replace marian with the one in the fixtures path.
            "MARIAN": fixtures_path,
            # This is included via the poetry install
            "COMPRESSION_CMD": "zstd",
        },
    )


class Assert:
    """
    A collection of assertions for evaluation tests.
    """

    @staticmethod
    def forward_eval(data_dir: DataDir, metrics: str) -> None:
        """Assert en -> ru (forward translation)"""
        assert data_dir.load("artifacts/wmt09.en") == en_sample
        assert data_dir.load("artifacts/wmt09.ru.ref") == ru_sample
        assert data_dir.load("artifacts/wmt09.ru") == ru_fake_translated
        assert metrics in data_dir.load("artifacts/wmt09.metrics")

    @staticmethod
    def backward_eval(data_dir: DataDir, metrics: str) -> None:
        """Assert ru -> en (back translations)"""
        assert data_dir.load("artifacts/wmt09.ru") == ru_sample
        assert data_dir.load("artifacts/wmt09.en.ref") == en_sample
        assert data_dir.load("artifacts/wmt09.en") == en_fake_translated
        assert metrics in data_dir.load("artifacts/wmt09.metrics")

    @staticmethod
    def base_marian_args(
        data_dir: DataDir, model_name: str = "final.model.npz.best-chrf.npz"
    ) -> None:
        """
        Marian is passed a certain set of arguments. This assertion will need to be
        updated if the Marian configuration changes.
        """
        marian_decoder_args = json.loads(data_dir.load("marian-decoder.args.txt"))

        expected_args = [
            "--config", data_dir.join("final.model.npz.best-chrf.npz.decoder.yml"),
            "--quiet",
            "--quiet-translation",
            "--log", data_dir.join("artifacts/wmt09.log"),
            '--workspace', '12000',
            '--devices', '0',
            "--models", data_dir.join(model_name),
        ]  # fmt: skip

        assert marian_decoder_args == expected_args, "The marian arguments matched."

    @staticmethod
    def quantized_marian_args(data_dir: DataDir) -> None:
        """
        The quantized arguments are somewhat different
        """
        marian_decoder_args = json.loads(data_dir.load("marian-decoder.args.txt"))

        expected_args = [
            "--config", os.path.join(root_path, "pipeline/quantize/decoder.yml"),
            "--quiet",
            "--quiet-translation",
            "--log", data_dir.join("artifacts/wmt09.log"),
            "--models", data_dir.join("model.intgemm.alphas.bin"),
            '--vocabs', data_dir.join("vocab.spm"), data_dir.join("vocab.spm"),
            '--shortlist', data_dir.join("lex.s2t.pruned"), 'false',
            '--int8shiftAlphaAll',
        ]  # fmt: skip

        assert marian_decoder_args == expected_args, "The marian arguments matched."


def test_evaluate_backward() -> None:
    data_dir = create_test_data()
    run_normal_eval_task(data_dir, "evaluate-backward-sacrebleu-wmt09-en-ru")
    Assert.backward_eval(data_dir, "0.4\n0.6")
    Assert.base_marian_args(data_dir)


def test_evaluate_finetuned() -> None:
    data_dir = create_test_data()
    run_normal_eval_task(data_dir, "evaluate-finetuned-student-sacrebleu-wmt09-en-ru")
    Assert.forward_eval(data_dir, "0.4\n0.6")
    Assert.base_marian_args(data_dir)


def test_evaluate_student() -> None:
    data_dir = create_test_data()
    run_normal_eval_task(data_dir, "evaluate-student-sacrebleu-wmt09-en-ru")
    Assert.forward_eval(data_dir, "0.4\n0.6")
    Assert.base_marian_args(data_dir)


def test_evaluate_teacher_ensemble() -> None:
    data_dir = create_test_data()
    run_normal_eval_task(
        data_dir,
        "evaluate-teacher-ensemble-sacrebleu-sacrebleu_wmt09-en-ru",
    )
    Assert.forward_eval(data_dir, "0.4\n0.6")
    Assert.base_marian_args(data_dir, model_name="model*/*.npz")


def test_evaluate_quantized() -> None:
    """
    This test is a little different as the quantized step requires a separate marian
    configuration.
    """
    data_dir = create_test_data()

    data_dir.run_task(
        "evaluate-quantized-sacrebleu-wmt09-en-ru",
        env={
            # This is where the marian_decoder_args will get stored.
            "TEST_ARTIFACTS": data_dir.path,
            # Replace marian with the one in the fixtures path.
            "BMT_MARIAN": fixtures_path,
            # This is included via the poetry install
            "COMPRESSION_CMD": "zstd",
        },
    )

    Assert.forward_eval(data_dir, "0.4\n0.6")
    Assert.quantized_marian_args(data_dir)
