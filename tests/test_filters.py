import json
import os
import pathlib

import pytest
from fixtures import DataDir

from pipeline.clean.opuscleaner.generate_filters import Mode, generate


@pytest.fixture(scope="function")
def data_dir():
    return DataDir("test_filters")


@pytest.mark.parametrize(
    "params",
    [
        # verify defaults
        ("en", "ru", "mtdata_Tilde-airbaltic-1-eng-rus", Mode.custom, "default.filters.json"),
        ("fr", "en", "mtdata_Tilde-airbaltic-1-eng-rus", Mode.custom, "default.filters.json"),
        ("fr", "en", "opus_ELRC-3075-wikipedia_health/v1", Mode.custom, "default.filters.json"),
        # verify langauge specific config is used for any direction
        (
            "ru",
            "en",
            "opus_ELRC-3075-wikipedia_health/v1",
            Mode.custom,
            "ru-en/opus_ELRC-3075-wikipedia_health-v1.filters.json",
        ),
        (
            "en",
            "ru",
            "opus_ELRC-3075-wikipedia_health/v1",
            Mode.custom,
            "ru-en/opus_ELRC-3075-wikipedia_health-v1.filters.json",
        ),
        # verify dataset specific config is used for different language pairs
        ("ru", "en", "opus_UNPC/v1.0", Mode.custom, "opus_UNPC-v1.0.filters.json"),
        ("fr", "en", "opus_UNPC/v1.0", Mode.custom, "opus_UNPC-v1.0.filters.json"),
        # verify the "defaults" mode always uses the default config
        (
            "ru",
            "en",
            "opus_ELRC-3075-wikipedia_health/v1",
            Mode.defaults,
            "default.filters.json",
        ),
        ("fr", "en", "opus_UNPC/v1.0", Mode.defaults, "default.filters.json"),
    ],
    ids=[
        "default-en-ru",
        "default-fr-en",
        "default-fr-en-elrc",
        "lang-ru-en",
        "lang-backward",
        "dataset-ru-en",
        "dataset-fr-en",
        "override-with-default-ru-en-elrc",
        "override-with-default-fr-en-unpc",
    ],
)
def test_generate_filters(params, data_dir):
    """
    Make sure the generated filters correspond to the right custom configs
    and the template values were replaced properly
    """
    src, trg, dataset, mode, config_path = params
    output_path = data_dir.join("output-config.json")
    config_path = pathlib.Path(os.path.abspath(__file__)).parent.parent.joinpath(
        "pipeline", "clean", "opuscleaner", "configs", config_path
    )

    generate(dataset=dataset, output=output_path, src=src, trg=trg, mode=mode)

    with open(output_path, "r") as f_out:
        with open(config_path, "r") as f_conf:
            actual = json.load(f_out)
            expected = json.load(f_conf)
    assert len(actual["filters"]) == len(expected["filters"])
    assert {f["filter"] for f in actual["filters"]} == {f["filter"] for f in expected["filters"]}
    assert {f["language"] for f in actual["filters"] if f["filter"] == "normalize_whitespace"} == {
        src,
        trg,
    }
    # max length value is slightly changed in opus_ELRC-3075-wikipedia_health/v1 to verify that this is the same config
    assert [f for f in actual["filters"] if f["filter"] == "max_length"][0]["parameters"][
        "MAXLENGTH"
    ] == [f for f in expected["filters"] if f["filter"] == "max_length"][0]["parameters"][
        "MAXLENGTH"
    ]
