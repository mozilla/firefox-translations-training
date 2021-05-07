##
# Filtering student parallel data with a reversed NMT model.
# This Makefile does not perform any other cleaning, so the provided parallel
# data should be already (relatively) clean.
#
# Requirements:
#   - Marian (GPU)
#   - GNU parallel
#   - python3
#
# Usage/Example:
#   1. Copy parallel corpus to data/yourcorpus.ende.gz.
#   2. Create a config for the reversed model in models/deen.yml.
#   3. Run make GPUS='0 1'.
#   4. Top 95% of the data will be in scored/yourcorpus.best.gz,
#      all sorted sentences (worst to best) in scored/yourcorpus.sorted.gz
#
# Additional options can be passed to make, e.g.:
#   make SRC=en TRG=es REMOVE=0.1 MODEL=model/esen.yml THREADS=32
#
##

SHELL:=/bin/bash
THREADS=16

ROOTDIR=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

SRC=en
TRG=de
GPUS=0 1 2 3

# Part of the data to be removed (0.05 is 5%)
REMOVE=0.05

MARIAN=../../marian-dev/build

SRCTRG=$(SRC)$(TRG)
MODEL=models/$(TRG)$(SRC).yml
PARALLEL=parallel --no-notice --pipe -k -j $(THREADS) --block 50M

.SUFFIXES:
.SECONDARY:


INPUTS=$(wildcard data/*.$(SRCTRG).gz)
SCORES=$(patsubst data/%.$(SRCTRG).gz,scored/%.scores.txt,$(INPUTS))
SORTED=$(patsubst data/%.$(SRCTRG).gz,scored/%.sorted.gz,$(INPUTS))
BESTS=$(patsubst data/%.$(SRCTRG).gz,scored/%.best.gz,$(INPUTS))

all: best
scores: $(SCORES)
sorted: $(SORTED)
best: $(BESTS)


##########################################################################
# SCORING

scored/%.scores.txt: data/%.$(SRCTRG).$(TRG).gz data/%.$(SRCTRG).$(SRC).gz models/$(TRG)$(SRC).yml | scored
	$(MARIAN)/marian-scorer -c $(MODEL) -t $(wordlist 1,2,$^) -d $(GPUS) --log $@.log > $@

scored/%.scores.nrm.txt: scored/%.scores.txt data/%.$(SRCTRG).$(SRC).gz
	paste $< <(pigz -dc $(word 2,$^)) | $(PARALLEL) python3 normalize-scores.py | cut -f1 > $@

scored/%.sorted.gz: scored/%.scores.nrm.txt data/%.$(SRCTRG).gz
	paste $< <(pigz -dc $(word 2,$^)) | LC_ALL=C sort -n -k1,1 -S 10G | pigz > $@

scored/%.best.gz: scored/%.sorted.gz
	$(eval STARTLINE := $(shell pigz -dc $< | wc -l | sed "s|$$|*$(REMOVE)|" | bc | cut -f1 -d.))
	@echo Removing $(REMOVE) removes $(STARTLINE) lines
	pigz -dc $< | tail -n +$(STARTLINE) | cut -f2,3 | pigz > $@


##########################################################################
# DATA

%.$(SRC).gz: %.gz
	pigz -dc $< | cut -f1 | pigz > $@
%.$(TRG).gz: %.gz
	pigz -dc $< | cut -f2 | pigz > $@


###########################################################################
# OTHER

scored:
	mkdir -p $@
models:
	mkdir -p $@
models/%:
	mkdir -p $@


clean:
	rm -f scored/*.scores.txt
