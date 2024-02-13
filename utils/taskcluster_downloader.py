"""
Downloads Marian training logs and evaluation results for a Taskcluster task group
"""

import argparse
import csv
import enum
import os
import re

import requests

import taskcluster
from taskcluster.download import downloadArtifactToBuf

TC_MOZILLA = "https://firefox-ci-tc.services.mozilla.com"

# to parse evaluation task tag
# examples:
# evaluate-teacher-flores-flores_aug-title_devtest-lt-en-1_2
# evaluate-teacher-mtdata-mtdata_aug-mix_Neulab-tedtalks_test-1-eng-lit-lt-en-1_2
# evaluate-finetuned-student-sacrebleu-wmt19-lt-en
eval_regex = re.compile(
    r"evaluate-"
    r"(?P<model>finetuned-student|teacher-ensemble|teacher|student|quantized|backward)"
    r"-"
    r"(?P<importer>flores|mtdata|sacrebleu)"
    r"(?P<extra_importer>-flores|-mtdata|-sacrebleu)?"
    r"[_-]"
    r"(?P<aug>aug-[^_]+)?"
    r"_?"
    r"(?P<dataset>[-\w_]*?)"
    r"-"
    r"(?P<extra_lang>([a-z]{3}-[a-z]{3})?"
    r"-?"
    r"(?P<lang>[a-z]{2}-[a-z]{2}))"
    r"-?"
    r"(?P<suffix>[\d_]+)?"
)


class Mode(enum.Enum):
    logs = "logs"
    evals = "evals"


def donwload_logs(group_id, output):
    options = {"rootUrl": TC_MOZILLA}
    queue = taskcluster.Queue(options=options)
    group = queue.listTaskGroup(group_id)

    for task in group["tasks"]:
        if task["status"]["state"] not in ("completed", "running"):
            continue

        label = task["task"]["tags"]["kind"]
        if ("train" not in label and "finetune" not in label) or "vocab" in label:
            continue

        task_id = task["status"]["taskId"]

        task_obj = queue.task(task_id)
        task["status"]["runs"][-1]["runId"]
        task_obj_label = task_obj["tags"]["label"].replace("/", "_")

        os.makedirs(output, exist_ok=True)
        output_path = os.path.join(output, f"{task_obj_label}.log")

        url = queue.buildUrl("getLatestArtifact", task_id, "public/logs/live.log")
        resp = requests.get(url, stream=True, timeout=5)
        print(f"Downloading {url}")

        log_lines = []
        start_writing = False
        try:
            for line in resp.iter_lines():
                line_str = line.decode()

                if "[marian]" in line_str:
                    start_writing = True

                if start_writing:
                    log_lines.append(re.sub(r"\[task .*Z\] ", "", line_str))
        except requests.exceptions.ConnectionError:
            pass

        print(f"Writing to {output_path}")
        with open(output_path, "w") as f:
            f.write("\n".join(log_lines))


def donwload_evals(group_id, output):
    options = {"rootUrl": ("%s" % TC_MOZILLA)}
    queue = taskcluster.Queue(options=options)
    group = queue.listTaskGroup(group_id)

    results = []

    for task in group["tasks"]:
        if task["status"]["state"] != "completed":
            continue

        label = task["task"]["tags"]["kind"]
        if "evaluate" not in label:
            continue

        task_id = task["status"]["taskId"]

        task_obj = queue.task(task_id)
        task["status"]["runs"][-1]["runId"]
        task_obj_label = task_obj["tags"]["label"].replace("/", "_")

        artifacts = queue.listLatestArtifacts(task_id)["artifacts"]
        artifact_name = [
            artifact["name"] for artifact in artifacts if artifact["name"].endswith(".metrics")
        ][0]

        print(f"Downloading {artifact_name} for {task_obj_label}")
        content, _ = downloadArtifactToBuf(
            taskId=task["status"]["taskId"],
            name=artifact_name,
            queueService=queue,
        )
        bleu, chrf, _, _ = content.tobytes().decode().split("\n")

        match = eval_regex.match(task_obj_label)
        if not match:
            print(f"Cannot match {task_obj_label}")
            raise ValueError(f"Cannot match {task_obj_label}")

        groups = match.groupdict()
        model = groups["model"]
        importer = groups["importer"]
        augmentation = groups.get("aug", "") or ""
        dataset = groups["dataset"]
        groups["lang"]
        suffix = groups.get("suffix", "") or ""

        result = (model + suffix, f"{importer}_{dataset}", augmentation, bleu, chrf)
        print(f"Result: {result}")
        results.append(result)

    os.makedirs(output, exist_ok=True)
    output_path = os.path.join(output, f"{group_id}-metrics.csv")
    with open(output_path, "w") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Model", "Dataset", "Augmentation", "BLEU", "chrF"])
        for res in results:
            csv_writer.writerow(res)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", metavar="OUTPUT", type=str, help="Output directory to save logs"
    )
    parser.add_argument(
        "--task-group-id", metavar="TASK_GROUP_ID", type=str, help="ID of a Taskcluster task group"
    )

    parser.add_argument(
        "--mode", metavar="MODE", type=Mode, help="Downloading mode: logs or evals"
    )

    args = parser.parse_args()
    output = args.output
    group_id = args.task_group_id
    mode = args.mode

    if mode == Mode.logs:
        donwload_logs(group_id, output)
    elif mode == Mode.evals:
        donwload_evals(group_id, output)


if __name__ == "__main__":
    main()
