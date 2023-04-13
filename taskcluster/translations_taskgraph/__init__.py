from importlib import import_module


def register(graph_config):
    _import_modules(
        [
            "actions.train",
            "target_tasks",
        ]
    )


def _import_modules(modules):
    for module in modules:
        import_module(".{}".format(module), package=__name__)
