from taskgraph.transforms.base import TransformSequence
from urllib.parse import urljoin
import os

TRAINING_ARTIFACT_NAMES = (
    "devset.out",
    "final.model.npz.best-chrf.npz",
    "final.model.npz.best-chrf.npz.decoder.yml",
    "model.npz",
    "model.npz.best-bleu-detok.npz",
    "model.npz.best-bleu-detok.npz.decoder.yml",
    "model.npz.best-ce-mean-words.npz",
    "model.npz.best-ce-mean-words.npz.decoder.yml",
    "model.npz.best-chrf.npz",
    "model.npz.best-chrf.npz.decoder.yml",
    "model.npz.decoder.yml",
    "model.npz.optimizer.npz",
    "model.npz.progress.yml",
    "model.npz.yml",
    "train.log",
    "valid.log",
)


def generate_training_artifact_mounts(urls, directory):
    for url in urls:
        training_artifact_urls = [
            urljoin(url, training_artifact_name)
            for training_artifact_name in TRAINING_ARTIFACT_NAMES
        ]
        training_artifact_mounts = []
        for training_artifact_name, training_artifact_url in zip(
            TRAINING_ARTIFACT_NAMES, training_artifact_urls
        ):
            training_artifact_mounts.append(
                {
                    "content": {
                        "url": training_artifact_url,
                    },
                    "file": os.path.join(directory, training_artifact_name),
                }
            )
        yield training_artifact_mounts


transforms = TransformSequence()


@transforms.add
def training_continuation(config, jobs):
    pretrained_models = config.params["training_config"]["experiment"].get("pretrained-models", {})
    if not any(pretrained_models):
        for job in jobs:
            yield job
    else:
        teacher_base_config = pretrained_models.get("teacher-base")
        teacher_base_training_artifact_mounts = generate_training_artifact_mounts(
            teacher_base_config["urls"], "./artifacts"
        )
        for job in jobs:
            try:
                mounts = next(teacher_base_training_artifact_mounts)
                job["task"]["payload"]["mounts"].extend(mounts)
                yield job
            except StopIteration:
                yield job
