import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Required

SCHEMA = Schema(
    {
        Required("substitution-fields"): [str],
        Required("provider"): str,
    },
    extra=ALLOW_EXTRA,
)

transforms = TransformSequence()
transforms.add_validate(SCHEMA)


def substitute(item, **subs):
    if isinstance(item, list):
        for i in range(len(item)):
            item[i] = substitute(item[i], **subs)
    elif isinstance(item, dict):
        new_dict = {}
        for k, v in item.items():
            k = k.format(**subs)
            new_dict[k] = substitute(v, **subs)
        item = new_dict
    elif isinstance(item, str):
        item = item.format(**subs)
    else:
        item = item

    return item


def shorten_dataset_name(dataset):
    """Shortens various dataset names. Mainly used to make sure we can have
    useful Treeherder symbols."""
    # TODO: should the replacements live in ci/config.yml?
    return (dataset
        .replace("new-crawl", "nc")
        .replace("news.2020", "n2020")
        .replace("Neulab-tedtalks_train-1", "Ntt1")
    )

@transforms.add
def render_command(config, jobs):
    for job in jobs:
        provider = job.pop("provider")
        substitution_fields = job.pop("substitution-fields")

        for dataset, locale_pairs in config.graph_config["datasets"][provider].items():
            for pair in locale_pairs:
                subjob = copy.deepcopy(job)
                subs = {
                    "provider": provider,
                    "dataset": dataset,
                    "dataset_short": shorten_dataset_name(dataset),
                    "dataset_no_slashes": dataset.replace("/", "."),
                    "src_locale": pair["src"],
                    "trg_locale": pair["trg"],
                }
                for field in substitution_fields:
                    container, subfield = subjob, field
                    while "." in subfield:
                        f, subfield = field.split(".", 1)
                        container = container[f]

                    container[subfield] = substitute(container[subfield], **subs)

                # If the job has command-context, add these values there
                # as well. These helps to avoid needing two levels of
                # substitution in a command.
                if subjob.get("run", {}).get("command-context"):
                    subjob["run"]["command-context"].update(subs)

                yield subjob
