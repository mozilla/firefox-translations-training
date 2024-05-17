from pathlib import Path
from urllib.parse import urlparse
import hashlib


# Important! Keep in sync with `Dataset._escape` in pipeline/common/datasets.py.
def sanitize_dataset_name(dataset: str) -> str:
    # URLs can be too large when used as Taskcluster labels. Create a nice identifier for them.
    # See https://github.com/mozilla/firefox-translations-training/issues/527
    if dataset.startswith("https://") or dataset.startswith("http://"):
        url = urlparse(dataset)

        hostname = url.hostname
        if hostname == "storage.googleapis.com":
            hostname = "gcp"

        # Get the name of the file from theh path without the extension.
        file = Path(url.path).stem
        file = file.replace(".[LANG]", "").replace("[LANG]", "")

        # Compute a hash to avoid any name collisions.
        md5 = hashlib.md5()
        md5.update(dataset.encode("utf-8"))
        hash = md5.hexdigest()[:6]

        dataset = f"{hostname}_{file}_{hash}"

    return (
        dataset.replace("://", "_")
        .replace("/", "_")
        .replace(".", "_")
        .replace(":", "_")
        .replace("[", "_")
        .replace("]", "_")
    )
