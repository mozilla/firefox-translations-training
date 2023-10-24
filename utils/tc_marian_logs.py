"""
Downloads Marian training logs for a Taskcluster task group
"""

import argparse
import os
import urllib.request

import taskcluster


def donwload_logs(group_id, output):
    options = {"rootUrl": "https://firefox-ci-tc.services.mozilla.com"}
    queue = taskcluster.Queue(options=options)
    group = queue.listTaskGroup(group_id)

    for task in group["tasks"]:
        if task["status"]["state"] != "completed":
            continue

        label = task["task"]["tags"]["kind"]
        if ("train" not in label and "finetune" not in label) or "vocab" in label:
            continue

        task_id = task["status"]["taskId"]

        task_obj = queue.task(task_id)
        run_id = task["status"]["runs"][-1]["runId"]
        task_obj_label = task_obj["tags"]["label"].replace("/", "_")

        os.makedirs(output, exist_ok=True)
        output_path = os.path.join(output, f"{task_obj_label}.log")
        # requires authentication
        # with open(output_path, 'w') as f:
        #     downloadArtifactToFile(f,
        #                            taskId=task['status']['taskId'],
        #                            name='train.log',
        #                            queueService=queue)

        url = f"https://firefoxci.taskcluster-artifacts.net/{task_id}/{run_id}/public/build/train.log"
        print(f"Downloading {url} to {output_path}")
        urllib.request.urlretrieve(url, output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", metavar="OUTPUT", type=str, help="Output directory to save logs"
    )
    parser.add_argument(
        "--task-group-id", metavar="TASK_GROUP_ID", type=str, help="ID of a Taskcluster task group"
    )

    args = parser.parse_args()
    output = args.output
    group_id = args.task_group_id

    donwload_logs(group_id, output)


if __name__ == "__main__":
    main()
