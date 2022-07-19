#!/bin/bash
set -euo pipefail
sed -E 's/\s?<(script|style|code|svg|textarea)[^>]*>.+?<\/\1>//ig' |
sed -E 's/<\/?[^>]+>//g'
