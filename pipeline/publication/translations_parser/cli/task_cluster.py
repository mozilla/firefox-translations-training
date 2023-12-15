import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import CSVExport, WandB


def get_args():
    parser = argparse.ArgumentParser(description="Extract information from Marian execution on Task Cluster")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input-file",
        "-i",
        help="Path to the Task Cluster log file.",
        type=Path,
        default=Path(__file__).parent.parent / "samples" / "KZPjvTEiSmO--BXYpQCNPQ.txt",
    )
    input_group.add_argument(
        "--from-stream",
        "-s",
        help="Read lines from stdin stream.",
        action="store_true",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory to export training and validation data as CSV.",
        type=Path,
        default=Path(__file__).parent.parent / "output",
    )
    parser.add_argument(
        "--wandb-project",
        help="Publish the training run to a Weight & Biases project.",
        default=None,
    )
    parser.add_argument(
        "--wandb-artifacts",
        help="Directory containing training artifacts to publish on Weight & Biases.",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--wandb-group",
        help="Add the training run to a Weight & Biases group e.g. by language pair or experiment.",
        default=None,
    )
    parser.add_argument(
        "--wandb-run-name",
        help="Use a custom name for the Weight & Biases run.",
        default=None,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        help="Print debug messages.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    return parser.parse_args()


def task_cluster_log_filter(headers):
    """
    Check TC log contain a valid task header ('task', <timestamp>)
    """
    for values in headers:
        if not values or len(values) != 2:
            continue
        base, timestamp = values
        if base != "task":
            continue
        try:
            datetime.fromisoformat(timestamp.rstrip("Z"))
            return True
        except ValueError:
            continue
    return False


def main():
    args = get_args()

    if args.loglevel:
        logger.setLevel(args.loglevel)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.from_stream:
        lines = sys.stdin
    else:
        with args.input_file.open("r") as f:
            lines = (line.strip() for line in f.readlines())
    publishers = [CSVExport(output_dir=args.output_dir)]
    if args.wandb_project:
        publishers.append(
            WandB(
                project=args.wandb_project,
                artifacts=args.wandb_artifacts,
                group=args.wandb_group,
                tags=["cli"],
                name=args.wandb_run_name,
                config={
                    "logs_file": args.input_file,
                },
            )
        )

    parser = TrainingParser(
        lines,
        publishers=publishers,
        log_filter=task_cluster_log_filter,
    )
    parser.run()
