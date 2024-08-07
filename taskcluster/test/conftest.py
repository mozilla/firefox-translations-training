from copy import deepcopy
import pytest
import requests_mock
from typing import Any, Dict, Generator, List, Protocol

from taskgraph.generator import TaskGraph, TaskGraphGenerator
from taskgraph.parameters import Parameters, parameters_loader
from translations_taskgraph.util.substitution import substitute


class CreateTgg(Protocol):
    def __call__(
        self, parameters: Parameters | None = None, overrides: dict | None = None
    ) -> TaskGraphGenerator:
        ...


# These fixtures are largely cribbed from Gecko:
# https://searchfox.org/mozilla-central/source/taskcluster/test
@pytest.fixture(scope="session")
def create_tgg():
    def inner(
        parameters: Parameters | None = None, overrides: dict | None = None
    ) -> TaskGraphGenerator:
        params = parameters_loader(parameters, strict=False, overrides=overrides)
        return TaskGraphGenerator(None, params)

    return inner


@pytest.fixture(scope="module")
def mock_requests() -> Generator[requests_mock.Mocker, None, None]:
    with requests_mock.Mocker() as m:
        yield m


# Scoping this at the module level means that each module will only generate
# a taskgraph one time, no matter how many tests are within it. This is
# beneficial for performance reasons, but forces any tests that need distinct
# parameters to be moved to their own modules.
@pytest.fixture(scope="module")
def tgg(request: pytest.FixtureRequest, create_tgg: CreateTgg) -> TaskGraphGenerator:
    if not hasattr(request.module, "PARAMS"):
        pytest.fail("'tgg' fixture requires a module-level 'PARAMS' variable")

    return create_tgg(overrides=request.module.PARAMS)


@pytest.fixture(scope="module")
def full_task_graph(tgg: TaskGraphGenerator) -> TaskGraph:
    return tgg.full_task_graph


@pytest.fixture(scope="module")
def target_task_graph(tgg: TaskGraphGenerator) -> TaskGraph:
    return tgg.target_task_graph


@pytest.fixture(scope="module")
def target_task_set(tgg: TaskGraphGenerator) -> TaskGraph:
    return tgg.target_task_set


@pytest.fixture(scope="module")
def optimized_task_graph(
    request: pytest.FixtureRequest, mock_requests: requests_mock.Mocker, tgg: TaskGraphGenerator
) -> TaskGraph:
    for resp in getattr(request.module, "MOCK_REQUESTS", {}):
        responses: List[Dict[str, Any]] = deepcopy(resp["responses"])
        digests = {}
        # This is a bit of a terrible hack, but it allows for cached task digests
        # to be substituted into mocked API responses, which is needed to test
        # the optimized and/or morphed task graph. Cached task digests are
        # generated as part of earlier phases, so there's no sensible way for
        # them to defined concretely at the same time as other parts of the
        # MOCK_REQUESTS.
        for label, key in resp.get("substitute_digest", {}).items():
            digests[key] = tgg.full_task_set[label].attributes["cached_task"]["digest"]
        responses = substitute(responses, **digests)
        mock_requests.request(
            resp["method"],
            resp["url"],
            responses,
        )

    return tgg.optimized_task_graph
