# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.actions.registry import register_callback_action
from taskgraph.actions.util import create_tasks, fetch_graph_and_labels


@register_callback_action(
    name="rebuild-docker-images-and-toolchains",
    title="Rebuild Docker Images and Toolchains",
    symbol="images-and-toolchains",
    description="Create docker-image and toolchain tasks to rebuild their artifacts.",
    order=1000,
    context=[],
)
def rebuild_docker_images_and_toolchains_action(
    parameters, graph_config, input, task_group_id, task_id
):
    decision_task_id, full_task_graph, label_to_task_id = fetch_graph_and_labels(
        parameters, graph_config, task_group_id=task_group_id
    )
    tasks_to_create = [
        label
        for label, task in full_task_graph.tasks.items()
        if task.kind == "docker-image" or task.kind == "fetch" or task.kind == "toolchain"
    ]
    if tasks_to_create:
        create_tasks(
            graph_config,
            tasks_to_create,
            full_task_graph,
            label_to_task_id,
            parameters,
            decision_task_id,
        )
