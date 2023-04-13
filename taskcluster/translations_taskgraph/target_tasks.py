from taskgraph.target_tasks import _target_task


@_target_task("train-target-tasks")
def train_target_tasks(full_task_graph, parameters, graph_config):
    def filter(label):
        if label in parameters["target_task_names"]:
            return True

    return [label for label in full_task_graph.tasks.keys() if filter(label)]
