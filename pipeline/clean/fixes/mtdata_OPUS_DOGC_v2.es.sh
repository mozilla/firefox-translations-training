#!/bin/bash

# Detokenize dates and laws, and ending period
sed "s#\([0-9]\) \?/ \?\([0-9]\)#\1/\2#g" \
    | sed "s/\([a-z]\) .\$/\1./g"
