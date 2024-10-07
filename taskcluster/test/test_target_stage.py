from copy import deepcopy

from taskgraph.taskgraph import TaskGraph

from translations_taskgraph.parameters import get_ci_training_config

PARAMS = deepcopy(get_ci_training_config())
PARAMS["target_tasks_method"] = "train-target-tasks"
PARAMS["training_config"]["target-stage"] = "train-teacher"


def test_nothing_downstream_of_target(target_task_graph: TaskGraph):
    # despite being called `reverse_links_dict`, this actually
    # gives us a dict where we can find tasks _downstream_ of
    # each task by label
    links = target_task_graph.graph.reverse_links_dict()
    for task in target_task_graph.graph.nodes:
        if task.startswith("train-teacher"):
            assert links[task] == set()
