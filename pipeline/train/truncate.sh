#!/bin/bash
set -x
set -euo pipefail

# Quick truncation script.

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

get_seeded_random()
{
  seed="$1"
  openssl enc -aes-256-ctr -pass pass:"$seed" -nosalt \
    </dev/zero 2>/dev/null
}

input_file=$1
num_lines=92218925
num_lines=61479283
num_lines=30739641

temp_file="${input_file%.zst}_sampled.zst"

echo "Size of input file:"
zstdcat "$input_file" | wc -l

# Uncompress, shuffle, truncate, and recompress
zstdcat "$input_file" |
    shuf --random-source=<(get_seeded_random 42) -n "$num_lines" |
    zstd -o "$temp_file"

# Replace the original file with the truncated version
mv "$temp_file" "$input_file"

echo "Sampled $num_lines lines and replaced $input_file with the truncated version"

echo "Size of input file:"
zstdcat "$input_file" | wc -l
