# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.actions.registry import register_callback_action
from taskgraph.actions.util import create_tasks, fetch_graph_and_labels


@register_callback_action(
    name="rebuild-toolchains",
    title="Rebuild Toolchains",
    symbol="rebuild-toolchains",
    description="Create toolchain tasks to rebuild their artifacts.",
    order=1000,
    context=[],
)
def rebuild_toolchains_action(parameters, graph_config, input, task_group_id, task_id):
    decision_task_id, full_task_graph, label_to_taskid = fetch_graph_and_labels(
        parameters, graph_config, task_group_id=task_group_id
    )
    toolchains = [
        label for label, task in full_task_graph.tasks.items() if task.kind == "toolchain"
    ]
    if toolchains:
        create_tasks(
            graph_config,
            toolchains,
            full_task_graph,
            label_to_taskid,
            parameters,
            decision_task_id,
        )
