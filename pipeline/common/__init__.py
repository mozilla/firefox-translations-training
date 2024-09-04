import math


# Avoid circular dependencies by placing this in this file.
def format_bytes(bytes: int) -> str:
    """Convert bytes into a human readable string."""

    if bytes == 0:
        return "0 B"

    size_name = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    size_index = int(math.floor(math.log(abs(bytes), 1000)))
    rounded_size = round(bytes / math.pow(1000, size_index), 1)
    return f"{rounded_size} {size_name[size_index]}"
