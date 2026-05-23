#!/usr/bin/env bash
# ROADMAP SC5: confirm template-selftest.yml runs end-to-end via `act` locally.
# Default: `base` combo only (cheapest, fastest sanity check, ~5 min).
# --full: all 5 combos sequentially (SC5 literal — "full matrix in <10 min via act locally").
#         Operator runs --full once before release; routine PR-local checks stay fast.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

FULL=0
if [[ "${1:-}" == "--full" ]]; then FULL=1; fi

if ! command -v act >/dev/null 2>&1; then
  echo "ERROR: act is not installed. Install: brew install act"
  exit 2
fi

echo "Listing workflows triggered by pull_request..."
act -l pull_request

if [[ "$FULL" -eq 1 ]]; then
  COMBOS=(base backend llm backend-llm full)
  echo
  echo "Running template-selftest.yml FULL matrix (${#COMBOS[@]} combos) under act..."
  START=$(date +%s)
  for combo in "${COMBOS[@]}"; do
    echo
    echo "=== combo: $combo ==="
    act pull_request \
      -W .github/workflows/template-selftest.yml \
      -j selftest \
      --matrix "combo:${combo}"
  done
  ELAPSED=$(( $(date +%s) - START ))
  echo
  echo "Full matrix elapsed: ${ELAPSED}s (SC5 budget: 600s for the 10-min target)"
  if [[ "$ELAPSED" -gt 600 ]]; then
    echo "WARNING: full matrix exceeded 10-minute SC5 budget"
  fi
else
  echo
  echo "Running template-selftest.yml combo=base under act (default fast path)..."
  echo "Use --full to run all 5 combos for the SC5 release check."
  act pull_request \
    -W .github/workflows/template-selftest.yml \
    -j selftest \
    --matrix combo:base
fi
