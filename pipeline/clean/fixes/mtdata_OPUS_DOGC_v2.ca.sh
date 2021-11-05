#!/bin/bash

# Detokenize Catalan apostrophe, dates and laws, and ending period
# detokenize middle dot
sed "s/\([lndsLNDS]\) ' \([a-zA-Z1]\)/\1'\2/g" \
    | sed "s#\([0-9]\) \?/ \?\([0-9]\)#\1/\2#g" \
    | sed "s/\([a-z]\) .\$/\1./g" \
    | sed "s/l · l/l·l/g"
