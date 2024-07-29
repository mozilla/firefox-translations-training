from copy import deepcopy

from taskgraph.taskgraph import TaskGraph

from translations_taskgraph.parameters import get_defaults

PARAMS = deepcopy(get_defaults(None))
PARAMS["target_tasks_method"] = "train-target-tasks"
PARAMS["training_config"]["experiment"]["pretrained-models"] = {
    "train-backwards": {
        "mode": "use",
        "type": "default",
        "urls": [
            "https://storage.googleapis.com/releng-translations-dev/models/ru-en/better-teacher/student"
        ],
    },
}


def test_artifact_mounts(full_task_graph: TaskGraph):
    task = [t for t in full_task_graph.tasks.values() if t.label == "train-backwards-ru-en"][0]
    # No need to bother looking for _all_ files (we'd just duplicate
    # the full list if we did that...), but we verify that one file
    # is well formed.
    mounted_files = {m["file"]: m for m in task.task["payload"]["mounts"] if "file" in m}
    assert mounted_files["./artifacts/model.npz"]["content"] == {
        "url": "https://storage.googleapis.com/releng-translations-dev/models/ru-en/better-teacher/student/model.npz",
    }
