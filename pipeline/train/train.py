"""
Run training using Marian and OpusTrainer.
"""

import argparse
from contextlib import ExitStack
from enum import Enum
import os
from pathlib import Path
import random
import shutil
import tempfile
from typing import Any, Generator, Optional

from pipeline.common.downloads import read_lines, write_lines
from pipeline.common.logging import get_logger
from pipeline.common.command_runner import apply_command_args, run_command_pipeline

logger = get_logger(__file__)
train_dir = Path(__file__).parent


CJK_LANGS = ["zh", "ja", "ko"]


class ModelType(Enum):
    student = "student"
    teacher = "teacher"
    backward = "backward"


class TrainingType(Enum):
    finetune = "finetune"
    train = "train"


class StudentModel(Enum):
    none = "None"
    tiny = "tiny"
    base = "base"


class TeacherMode(Enum):
    none = "None"
    one_stage = "one-stage"
    two_stage = "two-stage"


class BestModelMetric(Enum):
    chrf = "chrf"
    ce_mean_words = "ce-mean-words"
    bleu_detok = "bleu-detok"
    # These are also available in Marian, but not used here:
    #   cross_entropy = "cross-entropy"
    #   perplexity = "perplexity"
    #   valid_script = "valid-script"
    #   translation = "translation"
    #   bleu = "bleu"
    #   bleu_segmented = "bleu-segmented"


def build_dataset_tsv(
    dataset_prefix: str,
    src: str,
    trg: str,
    alignments_file: Optional[Path] = None,
) -> Path:
    """
    Takes as input a dataset prefix, and combines the datasets into a TSV, removing
    the original files. If an alignments file is provided, any empty alignments will
    be discarded.

    For instance:
        Prefix:
          - path/to/corpus

        Files used:
          - path/to/corpus.en.zst
          - path/to/corpus.fr.zst
          - path/to/corpus.aln.zst

        And then builds:
          - path/to/corpus.enfr.tsv
    """
    src_path = Path(f"{dataset_prefix}.{src}.zst")
    trg_path = Path(f"{dataset_prefix}.{trg}.zst")
    # OpusTrainer supports only tsv and gzip
    # TODO: pigz is not installed on the generic Taskcluster worker, so we use datasets in decompressed mode for now
    tsv_path = Path(f"{dataset_prefix}.{src}{trg}.tsv")  # .gz

    with ExitStack() as stack:
        tsv_outfile = stack.enter_context(write_lines(tsv_path))
        src_lines: Generator[str, Any, Any] = stack.enter_context(read_lines(src_path))
        trg_lines: Generator[str, Any, Any] = stack.enter_context(read_lines(trg_path))

        logger.info(f"Generating tsv dataset: {tsv_path}")

        if alignments_file:
            logger.info(f"Using alignments file: {alignments_file}")

            aln_lines: Generator[str, Any, Any] = stack.enter_context(
                read_lines(f"{alignments_file}")
            )
            empty_alignments = []

            for src_line, trg_line, aln_line in zip(src_lines, trg_lines, aln_lines):
                if aln_line.strip():
                    tsv_outfile.write(
                        f"{src_line.strip()}\t{trg_line.strip()}\t{aln_line.strip()}\n"
                    )
                else:
                    # do not write lines with empty alignments to TSV, Marian will complain and skip those
                    empty_alignments.append((src_line, trg_line))

            if empty_alignments:
                logger.info(f"Number of empty alignments is {len(empty_alignments)}")
                logger.info("Sample of empty alignments:")
                random.shuffle(empty_alignments)
                for src_line, trg_line in empty_alignments[:50]:
                    logger.info(f"  src: {src_line.strip()}")
                    logger.info(f"  trg: {trg_line.strip()}")

        else:
            for src_line, trg_line in zip(src_lines, trg_lines):
                tsv_outfile.write(f"{src_line.strip()}\t{trg_line.strip()}\n")

    logger.info("Freeing up disk space after TSV merge.")
    logger.info(f"Removing {src_path}")
    src_path.unlink()
    logger.info(f"Removing {trg_path}")
    trg_path.unlink()
    if alignments_file:
        logger.info(f"Removing {alignments_file}")
        alignments_file.unlink()

    return tsv_path


def get_log_parser_command():
    if shutil.which("parse_tc_logs") is None:
        logger.info("Weight & Biases publication script is not available.")
        return ["cat"]

    if "TEST_ARTIFACTS" in os.environ:
        logger.info("Weight & Biases publication is disabled for unit tests.")
        return ["cat"]

    logger.info("Weight & Biases publication is available.")
    return ["parse_tc_logs", "--from-stream", "--publish-group-logs", "--verbose"]


class TrainCLI:
    def __init__(self, args: Any, temp_dir: Path) -> None:
        self.temp_dir = temp_dir
        self.vocab: Path = args.vocab
        self.src: str = args.src
        self.trg: str = args.trg
        self.seed: int = args.seed
        self.train_set_prefixes: list[str] = args.train_set_prefixes.split(",")
        self.alignments_files: list[Path] = [
            Path(path) for path in args.alignments.split(",") if path != "None"
        ]
        self.validation_set_prefix: str = args.validation_set_prefix
        self.artifacts: Path = args.artifacts
        self.model_type: ModelType = args.model_type
        self.student_model: StudentModel = args.student_model
        self.teacher_mode: TeacherMode = args.teacher_mode
        self.training_type: TrainingType = args.training_type
        self.best_model_metric: BestModelMetric = args.best_model_metric
        self.extra_marian_args: list[str] = args.extra_marian_args
        self.marian_bin = args.marian_dir / "marian"
        self.gpus = args.gpus
        self.workspace = args.workspace
        self.config_variables = {
            "vocab": self.vocab,
            "src": self.src,
            "trg": self.trg,
            "seed": self.seed,
        }
        self.opustrainer_config = self.artifacts / "config.opustrainer.yml"

    def log_config(self):
        logger.info("Running train.py with the following settings:")
        logger.info(f" - temp_dir: {self.temp_dir}")
        logger.info(f" - vocab: {self.vocab}")
        logger.info(f" - src: {self.src}")
        logger.info(f" - trg: {self.trg}")
        logger.info(f" - seed: {self.seed}")
        logger.info(f" - train_set_prefixes: {self.train_set_prefixes}")
        logger.info(f" - alignments_files: {self.alignments_files}")
        logger.info(f" - validation_set_prefix: {self.validation_set_prefix}")
        logger.info(f" - artifacts: {self.artifacts}")
        logger.info(f" - model_type: {self.model_type.value}")
        logger.info(f" - student_model: {self.student_model.value}")
        logger.info(f" - teacher_mode: {self.teacher_mode.value}")
        logger.info(f" - training_type: {self.training_type.value}")
        logger.info(f" - best_model_metric: {self.best_model_metric}")
        logger.info(f" - extra_marian_args: {self.extra_marian_args}")
        logger.info(f" - marian_bin: {self.marian_bin}")
        logger.info(f" - gpus: {self.gpus}")
        logger.info(f" - workspace: {self.workspace}")
        logger.info(f" - opustrainer_config: {self.opustrainer_config}")

    def validate_args(self) -> None:
        if self.extra_marian_args and self.extra_marian_args[0] != "--":
            logger.error(" ".join(self.extra_marian_args))
            raise Exception("Expected the extra marian args to be after a --")

        # Validate input values.
        if not self.vocab.exists():
            raise Exception("Could not find the path to the vocab.")

        if not self.marian_bin.exists():
            raise Exception(f"Marian binary could not be found {self.marian_bin}")

        for alignment_file in self.alignments_files:
            if not alignment_file.exists():
                raise Exception(f"Alignment file could not be found {alignment_file}")

    def build_datasets(self) -> None:
        # Start by building the training datasets, e.g.
        #
        #  corpus.enfr.tsv from:
        #   - fetches/corpus.en.zst
        #   - fetches/corpus.fr.zst
        #   - fetches/corpus.aln.zst
        #
        #  mono.enfr.tsv from:
        #   - fetches/mono.en.zst
        #   - fetches/mono.fr.zst
        #   - fetches/mono.aln.zst

        for index, dataset_prefix in enumerate(self.train_set_prefixes):
            alignments = None
            if self.alignments_files:
                alignments = self.alignments_files[index]
                self.config_variables[f"dataset{index}"] = build_dataset_tsv(
                    dataset_prefix, self.src, self.trg, alignments
                )
            else:
                self.config_variables[f"dataset{index}"] = build_dataset_tsv(
                    dataset_prefix, self.src, self.trg
                )

        # Then build out the validation set, for instance:
        #
        # devset.enfr.tsv from:
        #  - fetches/devset.en.zst
        #  - fetches/devset.fr.zst
        self.validation_set = build_dataset_tsv(self.validation_set_prefix, self.src, self.trg)

    def generate_opustrainer_config(
        self,
    ):
        """
        Generate an OpusTraininer config that points to the current datasets and language
        options.
        """

        config_suffix = "cjk.yml" if self.src in CJK_LANGS or self.trg in CJK_LANGS else "yml"

        if self.model_type == ModelType.teacher:
            teacher_mode = self.teacher_mode.value
            if teacher_mode == TeacherMode.none.value:
                raise ValueError("Teacher mode was not properly set, as it was set to none")

            config_input = (
                train_dir
                / f"configs/opustrainer/{self.model_type.value}.{teacher_mode}.{config_suffix}"
            )
        else:
            config_input = (
                train_dir / f"configs/opustrainer/{self.model_type.value}.{config_suffix}"
            )

        with open(config_input, "rt", encoding="utf-8") as file:
            config_text = file.read()

        logger.info(f"Applying OpusTrainer config variables: {config_input}")
        for key, value in self.config_variables.items():
            logger.info(f" - {key}: {value}")

        with self.opustrainer_config.open("wt", encoding="utf-8") as file:
            config_text = config_text.format(**self.config_variables)
            file.write(config_text)

    def get_opustrainer_cmd(self):
        return [
            "opustrainer-train",
            *apply_command_args(
                {
                    "config": self.opustrainer_config,
                    "log-file": self.artifacts / "opustrainer.log",
                    "log-level": "INFO",
                }
            ),
        ]

    def get_marian_cmd(self):
        all_model_metrics = ["chrf", "ce-mean-words", "bleu-detok"]
        validation_metrics = [
            # Place the best model metric first.
            self.best_model_metric.value,
            # And then the rest of the metrics should follow.
            *[m for m in all_model_metrics if m != self.best_model_metric.value],
        ]

        # Take off the "--" from beginning of the list.
        extra_args = self.extra_marian_args[1:]

        if "USE_CPU" not in os.environ:
            # We run a CPU version of Marian in tests and it does not work with these arguments.
            extra_args.append("--sharding")
            extra_args.append("local")

        if self.model_type == ModelType.student:
            if self.student_model == StudentModel.none:
                raise ValueError("Student configuration is not provided")
            model_name = f"student.{self.student_model.value}"
        else:
            model_name = self.model_type.value

        return [
            str(self.marian_bin),
            *apply_command_args(
                {
                    "model": self.artifacts / "model.npz",
                    "config": [
                        train_dir / f"configs/model/{model_name}.yml",
                        train_dir
                        / f"configs/training/{self.model_type.value}.{self.training_type.value}.yml",
                    ],
                    "tempdir": self.temp_dir / "marian-tmp",
                    "vocabs": [self.vocab, self.vocab],
                    "workspace": self.workspace,
                    "devices": self.gpus.split(" "),
                    "valid-metrics": validation_metrics,
                    "valid-sets": str(self.validation_set),
                    "valid-translation-output": self.artifacts / "devset.out",
                    "valid-log": self.artifacts / "valid.log",
                    "log": self.artifacts / "train.log",
                    "shuffle": "batches",
                    "seed": str(self.seed),
                    "no-restore-corpus": None,
                    "valid-reset-stalled": None,
                    "sync-sgd": None,
                    "quiet-translation": None,
                    "overwrite": None,
                    "keep-best": None,
                    "tsv": None,
                }
            ),
            *extra_args,
        ]

    def run_training(self):
        """
        OpusTrainer pipes augmented data into Marian. Marian handles the training and
        outputs the progress as in its log. The final part of the pipeline is the log
        parser which parses the streamed logs and reports the results to W&B.
        """
        run_command_pipeline(
            [
                [
                    # OpusTrainer controls the marian commands.
                    *self.get_opustrainer_cmd(),
                    *self.get_marian_cmd(),
                ],
                get_log_parser_command(),
            ],
            pipe_stderr=True,
            logger=logger,
        )

        shutil.copy(
            self.artifacts / f"model.npz.best-{self.best_model_metric.value}.npz",
            self.artifacts / f"final.model.npz.best-{self.best_model_metric.value}.npz",
        )
        shutil.copy(
            self.artifacts / f"model.npz.best-{self.best_model_metric.value}.npz.decoder.yml",
            self.artifacts
            / f"final.model.npz.best-{self.best_model_metric.value}.npz.decoder.yml",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        # Preserves whitespace in the help text.
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--model_type",
        type=ModelType,
        choices=ModelType,
        required=True,
        help="The type of model to train",
    )
    parser.add_argument(
        "--student_model",
        type=StudentModel,
        choices=StudentModel,
        required=False,
        default=StudentModel.tiny,
        help="Type of student model",
    )
    parser.add_argument(
        "--training_type",
        type=TrainingType,
        choices=TrainingType,
        help="Type of teacher training",
    )
    parser.add_argument(
        "--gpus",
        type=str,
        required=True,
        help='The indexes of the GPUs to use on a system, e.g. --gpus "0 1 2 3"',
    )
    parser.add_argument(
        "--marian_dir",
        type=Path,
        required=True,
        help="Path to Marian binary directory. This allows for overriding to use the browser-mt fork.",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        required=True,
        help="The amount of Marian memory (in MB) to preallocate",
    )
    parser.add_argument("--src", type=str, help="Source language")
    parser.add_argument("--trg", type=str, help="Target language")
    parser.add_argument(
        "--train_set_prefixes",
        type=str,
        help="Comma separated prefixes to datasets for curriculum learning",
    )
    parser.add_argument("--validation_set_prefix", type=str, help="Prefix to validation dataset")
    parser.add_argument("--artifacts", type=Path, help="Where to save the model artifacts")
    parser.add_argument("--vocab", type=Path, help="Path to vocab file")
    parser.add_argument(
        "--best_model_metric",
        type=BestModelMetric,
        help="Multiple metrics are gathered, but only the best model for a given metric will be retained",
    )
    parser.add_argument(
        "--alignments",
        type=str,
        help="Comma separated alignment paths corresponding to each training dataset, or 'None' to train without alignments",
    )
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument(
        "--teacher_mode",
        type=TeacherMode,
        choices=TeacherMode,
        help="Teacher mode",
    )
    parser.add_argument(
        "extra_marian_args",
        nargs=argparse.REMAINDER,
        help="Additional parameters for the training script",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        train_cli = TrainCLI(parser.parse_args(), Path(temp_dir))
        train_cli.log_config()
        train_cli.validate_args()
        train_cli.build_datasets()
        train_cli.generate_opustrainer_config()
        train_cli.run_training()


if __name__ == "__main__":
    main()
