#!/usr/bin/env bash
# Re-record docs/casts/just-verify.cast and re-render docs/casts/just-verify.gif.
# Required tools: asciinema, agg (install: `brew install asciinema agg`).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
asciinema rec \
  --overwrite \
  --cols 100 --rows 28 \
  --idle-time-limit 1.5 \
  --title "just verify — first run on a fresh copier copy" \
  "${HERE}/just-verify.cast"
agg --cols 100 --rows 28 --font-size 14 \
  "${HERE}/just-verify.cast" "${HERE}/just-verify.gif"
echo "Re-recorded: ${HERE}/just-verify.{cast,gif}"
