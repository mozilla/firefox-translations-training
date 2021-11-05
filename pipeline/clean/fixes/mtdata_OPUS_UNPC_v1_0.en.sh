#!/bin/bash

# Detokenize English possessive
sed "s/\([a-z]\) ' \([s]\)/\1'\2/g"
