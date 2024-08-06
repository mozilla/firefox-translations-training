import gc
import logging
import os
from typing import Optional

import psutil

from pipeline.common import format_bytes
from pipeline.common.logging import get_logger

_memory_logger: Optional[logging.Logger] = None
_memory_process: Optional[psutil.Process] = None
_memory_last_bytes: Optional[int] = None


def get_memory_string() -> str:
    """
    Get the current string representation of the memory usage.
    """
    global _memory_process
    global _memory_last_bytes

    # Lazily initial everything.
    if not _memory_process:
        _memory_process = psutil.Process(os.getpid())

    gc.collect()
    memory_info = _memory_process.memory_info()
    bytes = memory_info.rss

    if _memory_last_bytes:
        bytes_diff = bytes - _memory_last_bytes
        sign = ""
        if bytes_diff >= 0:
            sign = "+"
        string = f"{format_bytes(bytes)} ({sign}{format_bytes(bytes_diff)})"
    else:
        string = format_bytes(bytes)

    _memory_last_bytes = bytes

    return string


def log_memory() -> None:
    """
    Logs the memory usage of the current Python process.
    """
    global _memory_logger
    if not _memory_logger:
        _memory_logger = get_logger("memory")
    _memory_logger.info(get_memory_string())
