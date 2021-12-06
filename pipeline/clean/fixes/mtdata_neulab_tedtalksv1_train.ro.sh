#!/bin/bash

# Detokenize Romanian hyphens
sed -E "s/(\w) - (\w)/\1-\2/g"
