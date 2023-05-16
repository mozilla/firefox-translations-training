from taskgraph.target_tasks import _target_task


@_target_task("train-target-tasks")
def train_target_tasks(full_task_graph, parameters, graph_config):
    stage = parameters["stage"]
    datasets = parameters["datasets"]
    src_locale = parameters["src_locale"]
    trg_locale = parameters["trg_locale"]
    def filter(task):
        # These attributes will be present on tasks from all stages
        for attr in ("stage", "src_locale", "trg_locale"):
            if task.attributes.get(attr) != parameters[attr]:
                return False

        # Datasets are only applicable to dataset-specific tasks. If these
        # attribute isn't present on the task it can be assumed to be included
        # if the above attributes matched, as it will be a task that is either
        # agnostic of datasets, or folds in datasets from earlier tasks.
        # (Pulling in the appropriate datasets for these task must be handled at 
        # the task generation level, usually by the `find_upstreams` transform.)
        if "dataset" in task.attributes:
            dataset_category = task.attributes["dataset-category"]
            for ds in parameters["datasets"][dataset_category]:
                provider, dataset = ds.split("_", 1)
                if task.attributes["provider"] != provider or task.attributes["dataset"] != dataset:
                    return False

        return True

    return [label for label, task in full_task_graph.tasks.items() if filter(task)]
