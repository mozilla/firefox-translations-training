import logging

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] %(message)s")


def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set the logging level
    return logger
