from snakemake.utils import min_version

min_version("6.6.1")

configfile: 'config.yml'
include: "workflow/common.smk"

rule all:
    input: f"{translated}/corpus.{trg}.gz"


include: "workflow/setup.smk"
include: "workflow/data.smk"
include: "workflow/clean.smk"
include: "workflow/train.smk"
include: "workflow/translate.smk"






