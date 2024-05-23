import argparse
import re
import subprocess
import sys
from io import StringIO
from pathlib import Path

import ruamel.yaml

from utils.find_corpus import (
    fetch_mtdata,
    fetch_news_crawl,
    fetch_opus,
    fetch_sacrebleu,
    get_remote_file_size,
)

"""
Generate a training config for a language pair based on the latest production
training config, taskcluster/configs/config.prod.yml.
"""

root_dir = Path(__file__).parent.parent
prod_config_path = root_dir / "taskcluster/configs/config.prod.yml"

pretrained_student_models = {
    ("ru", "en"): "https://storage.googleapis.com/releng-translations-dev/models/ru-en/better-teacher/student"
}  # fmt: skip

skip_datasets = [
    # The NLLB dataset is based off of the CCMatrix dataset, and is mostly duplicated.
    "CCMatrix",
    # Skip Multi* datasets as they are generally multilingual versions of the original datasets.
    "MultiMaCoCu",
    "MultiHPLT",
    # In Russian, the WikiTitles data had its direction reversed. The `LinguaTools-WikiTitles`
    # version is fine.
    "WikiTitles",
]

# Do not include small datasets. This works around #508, and minimizes dataset tasks that
# won't bring a lot more data.
minimum_dataset_sentences = 200

flores_101_languages = {
    "af", "amh", "ar", "as", "ast", "az", "be", "bn", "bs", "bg", "ca", "ceb", "cs", "ckb", "cy",
    "da", "de", "el", "en", "et", "fa", "fi", "fr", "ful", "ga", "gl", "gu", "ha", "he", "hi",
    "hr", "hu", "hy", "ig", "id", "is", "it", "jv", "ja", "kam", "kn", "ka", "kk", "kea", "km",
    "ky", "ko", "lo", "lv", "ln", "lt", "lb", "lg", "luo", "ml", "mr", "mk", "mt", "mn", "mi",
    "ms", "my", "nl", "nb", "npi", "nso", "ny", "oc", "om", "or", "pa", "pl", "pt", "pus", "ro",
    "ru", "sk", "sl", "sna", "snd", "so", "es", "sr", "sv", "sw", "ta", "te", "tg", "tl", "th",
    "tr", "uk", "umb", "ur", "uz", "vi", "wo", "xh", "yo", "zh", "zh", "zu"
}  # fmt: skip


def get_git_revision_hash() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()


def update_config(prod_config: any, name: str, source: str, target: str) -> dict[str, str]:
    experiment = prod_config["experiment"]

    # Update the prod config for this language pair.
    experiment["name"] = name
    experiment["src"] = source
    experiment["trg"] = target
    experiment["bicleaner"]["dataset-thresholds"] = {}

    pretrained_model = pretrained_student_models.get((source, target))
    if pretrained_model:
        experiment["teacher-mode"] = "two-stage"
        experiment["pretrained-models"]["train-backwards"]["urls"] = [pretrained_model]
    else:
        experiment["pretrained-models"] = {}

    datasets = prod_config["datasets"]

    # Clear out the base config.
    datasets["train"].clear()
    datasets["devtest"].clear()
    datasets["test"].clear()
    datasets["mono-src"].clear()
    datasets["mono-trg"].clear()

    # ruamel.yaml only supports inline comments. This dict will do string matching to apply
    # comments too the top of a section.
    comment_section = {}

    add_train_data(source, target, datasets["train"], comment_section)
    add_test_data(
        source,
        target,
        datasets["test"],
        datasets["devtest"],
        comment_section,
    )
    add_mono_data(source, datasets["mono-src"], "  mono-src:", comment_section)
    add_mono_data(target, datasets["mono-trg"], "  mono-trg:", comment_section)

    return comment_section


def add_train_data(
    source: str, target: str, train_datasets: list[str], comment_section: dict[str, str]
):
    print("Fetching opus")
    opus_datasets = fetch_opus(source, target)
    total_sentences = 0
    skipped_datasets = []
    visited_corpora = set()

    for dataset in opus_datasets:
        sentences = dataset.alignment_pairs or 0
        # Some datasets are ignored or too small to be included.
        if dataset.corpus in skip_datasets:
            skipped_datasets.append(f"{dataset.corpus_key()} - ignored datasets ({sentences:,} sentences)")
            continue
        if (dataset.alignment_pairs or 0) < minimum_dataset_sentences:
            skipped_datasets.append(f"{dataset.corpus_key()} - not enough data  ({sentences:,} sentences)")
            continue

        visited_corpora.add(normalize_corpus_name(dataset.corpus))
        total_sentences += sentences
        corpus_key = dataset.corpus_key()
        train_datasets.append(corpus_key)
        train_datasets.yaml_add_eol_comment(
            f"{sentences:,} sentences".rjust(70 - len(corpus_key), " "),
            len(train_datasets) - 1,
        )

    print("Fetching mtdata")
    entries = fetch_mtdata(source, target)

    for corpus_key, entry in entries.items():
        corpus_name = normalize_corpus_name(entry.did.name)
        group_corpus_name = normalize_corpus_name(entry.did.group + entry.did.name)
        if corpus_name in visited_corpora or group_corpus_name in visited_corpora:
            skipped_datasets.append(f"{corpus_key} - duplicate with opus")
            continue

        if entry.did.name in skip_datasets:
            skipped_datasets.append(f"{entry.did.name} - ignored datasets")
            continue

        train_datasets.append(corpus_key)
        byte_size, display_size = get_remote_file_size(entry.url)
        if byte_size:
            # Don't add the sentences to the total, as these will be commented out by default.
            sentences = estimate_sentence_size(byte_size)
            train_datasets.yaml_add_eol_comment(
                f"~{sentences:,} sentences ".rjust(70 - len(corpus_key), " ")
                + f"({display_size})",
                len(train_datasets) - 1,
            )

    train_comment = "\n".join(
        [
            "The training data contains:",
            f"  {total_sentences:,} sentences",
            "",
            "Skipped datasets:",
            *[f" - {d}" for d in skipped_datasets],
        ]
    )

    comment_section["  train:"] = train_comment


def normalize_corpus_name(corpus_name: str):
    """Normalize the corpus name so that it's easy to deduplicate between opus and mtdata."""

    # Remove the language tags at the end.
    # mtdata_ELRC-vnk.fi-1-eng-fin
    #                     ^^^^^^^^
    corpus_name = re.sub(r"-\w{3}-\w{3}$", "", corpus_name)

    corpus_name = corpus_name.lower()

    # Remove numbers anything that is not a letter. This is a little aggressive, but should help
    # deduplicate more datasets. For example:
    #   opus: 725-Hallituskausi_2011_2
    #   mtdata: hallituskausi_2011_2015-1-eng-fin
    corpus_name = re.sub(r"[^a-z]", "", corpus_name.lower())

    # Ignore train/test/dev splits.
    #   opus: NeuLab-TedTalks/v1
    #   mtdata: Neulab-tedtalks_train-1-eng-fin
    #   mtdata: Neulab-tedtalks_test-1-eng-fin
    #   mtdata: Neulab-tedtalks_dev-1-eng-fin
    corpus_name = re.sub(r"train$", "", corpus_name)
    corpus_name = re.sub(r"test$", "", corpus_name)
    corpus_name = re.sub(r"dev$", "", corpus_name)

    return corpus_name


def add_test_data(
    source: str,
    target: str,
    test_datasets: list[str],
    devtest_datasets: list[str],
    comment_section: dict[str, str],
):
    skipped_datasets = []
    print("Fetching flores")
    if source in flores_101_languages and target in flores_101_languages:
        test_datasets.append("flores_devtest")

        # Add augmented datasets to check performance for the specific cases
        test_datasets.append("flores_aug-mix_devtest")
        test_datasets.append("flores_aug-title_devtest")
        test_datasets.append("flores_aug-upper_devtest")
        test_datasets.append("flores_aug-typos_devtest")
        test_datasets.append("flores_aug-noise_devtest")
        test_datasets.append("flores_aug-inline-noise_devtest")

        devtest_datasets.append("flores_aug-mix_dev")

    is_test = True  # Flip between devtest and test.
    print("Fetching sacrebleu")
    for d in fetch_sacrebleu(source, target):
        # Work around: PLW2901 `for` loop variable `dataset_name` overwritten by assignment target
        dataset_name = d
        if "/" in dataset_name:
            # This could be a dataset with a variant design.
            skipped_datasets.append(f"{dataset_name} - variant dataset")
        else:
            dataset_name = dataset_name.replace("sacrebleu_", "")
            if is_test:
                test_datasets.append(f"sacrebleu_{dataset_name}")
            else:
                devtest_datasets.append(f"sacrebleu_aug-mix_{dataset_name}")
            is_test = not is_test

    test_comment = "\n".join(
        [
            "Skipped test/devtest datasets:",
            *[f" - {d}" for d in skipped_datasets],
        ]
    )

    comment_section["  devtest:"] = test_comment


def estimate_sentence_size(bytes: int) -> int:
    """Estimate the sentences based on the compressed byte size"""
    # One dataset measured 113 bytes per sentence, use that as a rough estimate.
    bytes_per_sentence = 113
    return bytes // bytes_per_sentence


def add_mono_data(
    lang: str,
    datasets: list[str],
    comment_key: str,
    comment_section: dict[str, str],
):
    print("Fetching newscrawl for", lang)
    sentence_count = 0
    for dataset in fetch_news_crawl(lang):
        datasets.append(dataset.name)
        if dataset.size:
            sentences = estimate_sentence_size(dataset.size)
            sentence_count += sentences
            datasets.yaml_add_eol_comment(
                f"~{sentences:,} sentences ".rjust(50 - len(dataset.name), " ")
                + f"({dataset.display_size})",
                len(datasets) - 1,
            )

    comment = "\n".join(
        [
            "The monolingual data contains:",
            f"  ~{sentence_count:,} sentences",
        ]
    )

    comment_section[comment_key] = comment


def strip_comments(yaml_text: str) -> list[str]:
    """
    ruamel.yaml preserves key ordering and comments. This function strips out the comments

    """
    result = ""
    for l in yaml_text.splitlines():
        # Work around: PLW2901 `for` loop variable `line` overwritten by assignment target
        line = l
        if line.strip().startswith("#"):
            continue

        # Remove any comments at the end.
        line = re.sub(r"#[\s\w\-.]*$", "", line)

        # Don't add any empty lines.
        if line.strip():
            result += line.rstrip() + "\n"

    return result


def apply_comments_to_yaml_string(yaml, prod_config, comment_section) -> str:
    """
    ruamel.yaml only supports inline comments, so do direct string manipulation to apply
    all the comments needed.
    """
    # Dump out the yaml to a string so that it can be manipulated.
    output_stream = StringIO()
    yaml.dump(prod_config, output_stream)
    yaml_string: str = output_stream.getvalue()
    yaml_string = apply_comment_section(comment_section, yaml_string)

    script_args = " ".join(sys.argv[1:])
    return "\n".join(
        [
            "# The initial configuration was generated using:",
            f"# task config-generator -- {script_args}",
            "#",
            "# The documentation for this config can be found here:",
            f"# https://github.com/mozilla/firefox-translations-training/blob/{get_git_revision_hash()}/taskcluster/configs/config.prod.yml",
            yaml_string,
        ]
    )


def apply_comment_section(comment_section: dict[str, str], yaml_string: str) -> str:
    for key, raw_comment in comment_section.items():
        # Find the indent amount for the key.
        match = re.search(r"^(?P<indent>\s*)", key)
        if not match:
            raise Exception("Could not find regex match")
        indent = match.group("indent")

        # Indent the lines, and add the # comment.
        comment = "\n".join([f"{indent}# {line}" for line in raw_comment.splitlines()])

        yaml_string = yaml_string.replace(f"\n{key}", f"\n\n{comment}\n{key}")
    return yaml_string


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        # Preserves whitespace in the help text.
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("source", metavar="SOURCE", type=str, help="The source language tag")
    parser.add_argument("target", metavar="TARGET", type=str, help="The target language tag")
    parser.add_argument(
        "--name",
        metavar="name",
        type=str,
        required=True,
        help="The name of the config, which gets constructed like so: configs/{source}-{target}-{name}.yml",
    )

    args = parser.parse_args()

    # Validate the inputs.
    langtag_re = r"[a-z]{2,3}"
    if not re.fullmatch(langtag_re, args.source):
        print("The source language should be a 2 or 3 letter lang tag.")
    if not re.fullmatch(langtag_re, args.target):
        print("The target language should be a 2 or 3 letter lang tag.")
    if not re.fullmatch(r"[\w\d-]+", args.name):
        print(
            "The name of the training config should only contain alphanumeric, underscores, and dashes.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ruamel.yaml preserves comments and ordering unlink PyYAML
    yaml = ruamel.yaml.YAML()

    # Load the prod yaml.
    with prod_config_path.open() as f:
        yaml_string = f.read()
    yaml_string = strip_comments(yaml_string)
    prod_config = yaml.load(StringIO(yaml_string))

    comment_section = update_config(prod_config, args.name, args.source, args.target)
    final_config = apply_comments_to_yaml_string(yaml, prod_config, comment_section)
    final_config_path = root_dir / "configs" / f"{args.source}-{args.target}-{args.name}.yml"

    print("Writing config to:", str(final_config_path))
    final_config_path.write_text(final_config)


if __name__ == "__main__":
    main()
