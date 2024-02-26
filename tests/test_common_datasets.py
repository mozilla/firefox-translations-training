import io
from typing import Iterator

import pytest
from fixtures import DataDir

from pipeline.common.datasets import shuffle_in_temp_files, shuffle_with_max_lines

ITEMS = 100_000
# ITEMS = 1_000
PERCENTAGE = 0.2
MAX_LINES = int(ITEMS * PERCENTAGE)


def get_total_byte_size(lines: list[str]) -> int:
    total_byte_size = 0
    for line in lines:
        total_byte_size = total_byte_size + len(line.encode())
    return total_byte_size


def compute_distribution(lines: Iterator[str], items=ITEMS, max_lines=MAX_LINES) -> list[float]:
    """
    Computes a histogram (list of 10 items) with a percentage value of 0.0 - 100.0 for each item.
    """
    histogram = [0] * 10
    for line in lines:
        # This assumes the content will be a tab separated list, with the first item to be the
        # initial sorted order in the list.
        key = int(int(line.split("\t")[0]) * 10 / items)
        histogram[key] = histogram[key] + (1 / max_lines)

    # Lower the precision of the ints.
    return [round(value * 1000) / 1000 for value in histogram]


# Test the distributions of the different types of datasets. This shuffler estimates the content
# size as it iterates through the line stream.
shuffle_params = [
    (
        # Each line is the same bytes as the next line. This should create an even distribution.
        # [
        #     "000000000 000000000 000000000 ... 000000000",
        #     "000000001 000000001 000000001 ... 000000001",
        #     ...
        # ]
        "even-distribution",
        [f"{line:09d}\t" * 10 for line in range(ITEMS)],
        [0.102, 0.101, 0.099, 0.1, 0.1, 0.102, 0.099, 0.097, 0.1, 0.1],
    ),
    (
        # The initial lines are low in byte count, and gradually increase. In this case there
        # will be a bias to over-sample the the initial items, but it will eventually even out as
        # more bytes are read in and the average spreads out.
        # [
        #     "0 0 0 ... 0",
        #     "1 1 1 ... 1",
        #     ...
        #     "99997 99997 99997 ... 99997",
        #     "99998 99998 99998 ... 99998",
        #     "99999 99999 99999 ... 99999",
        # ]
        "small-content-at-start",
        [f"{line}\t" * 10 for line in range(ITEMS)],
        [0.114, 0.116, 0.092, 0.095, 0.096, 0.099, 0.097, 0.095, 0.098, 0.098],
        # |     |     |
        # |     |     ^ Lower sample rate.
        # ^^^^^^^ Higher sampling rate.
    ),
    (
        # [
        #     "99999 99999 99999 ... 99999",
        #     "99998 99998 99998 ... 99998",
        #     "99997 99997 99997 ... 99997",
        #     ...
        #     "1 1 1 ... 1",
        #     "0 0 0 ... 0",
        # ]
        "large-content-at-start",
        [f"{line}\t" * 10 for line in range(ITEMS)][::-1],
        [0.101, 0.102, 0.099, 0.102, 0.103, 0.102, 0.101, 0.102, 0.102, 0.086],
        #                                             lower sample rate ^^^^^
    ),
]


@pytest.mark.parametrize("params", shuffle_params, ids=[d[0] for d in shuffle_params])
def test_shuffle_with_max_lines(params):
    description, line_stream, histograph = params
    # [
    #     "0000 0000 0000 ... 0000",
    #     "0001 0001 0001 ... 0001",
    #     "0002 0002 0002 ... 0002",
    #     ...
    # ]

    output = shuffle_with_max_lines(
        line_stream,
        seed="test",
        max_lines=MAX_LINES,
        max_words_in_sentence=100,
        total_byte_size=get_total_byte_size(line_stream),
    )

    assert compute_distribution(output) == histograph, description


def test_shuffle_in_temp_files():
    # [
    #     "0000 0000 0000 ... 0000",
    #     "0001 0001 0001 ... 0001",
    #     "0002 0002 0002 ... 0002",
    #     ...
    # ]
    line_stream = [f"{line:09d}\t" * 10 for line in range(ITEMS)]

    # Total byte size is ~10_000_000
    chunk_bytes = 100_000
    bucket_bytes = 2_000_000
    data_dir = DataDir("test_common_datasets")

    with io.StringIO() as output:
        shuffle_in_temp_files(
            line_stream,
            output=output,
            seed="test",
            chunk_bytes=chunk_bytes,
            bucket_bytes=bucket_bytes,
            chunk_dir=data_dir.path,
            keep_chunks=True,
        )

        data_dir.print_tree()

        output.seek(0)
        text = output.read()
        lines = [*text.splitlines()]
        sample = lines[:MAX_LINES]

        output.seek(0)
        with open(data_dir.join("shuffle.txt"), "w") as file:
            print(output.getvalue(), file=file)

        assert len(lines) == ITEMS
        assert compute_distribution(sample) == [
            0.149,
            0.258,
            0.04,
            0.1,
            0.001,  # The distribution is not perfect with this strategy.
            0.052,
            0.05,
            0.1,
            0.101,
            0.15,
        ]
