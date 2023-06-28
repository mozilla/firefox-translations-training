from typing import List

from taskgraph.task import Task
from taskgraph.transforms.base import TransformConfig
from taskgraph.util.dependencies import group_by
from taskgraph.util.schema import Schema

@group_by("all")
def group_by_all(config: TransformConfig, tasks: List[Task]) -> List[List[Task]]:
    return [[task for task in tasks]]
