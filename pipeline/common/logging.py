import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")


def get_logger(name: str):
    """
    Get a logger using the __file__ name.

    For example in pipeline/bicleaner/download_pack.py

        logger = get_logger(__file__)
        logger.info("This is a log.")

    Will log:

        > [download_pack] This is a log.
    """

    logger = logging.getLogger(Path(name).stem)
    logger.setLevel(logging.INFO)
    return logger
