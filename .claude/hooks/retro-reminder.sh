#!/usr/bin/env bash
# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

# Retro reminder — fires at SessionStart. Scans .planning/phases/ for phases
# that have a SUMMARY.md (executed) but no matching RETRO file under
# .planning/learnings/. Emits a context block Claude Code reads at session
# start so the orchestrator gets reminded to fill it in.
#
# Output contract: prints a JSON-wrapped additional-context payload to stdout
# per Claude Code's SessionStart hook spec. Empty output means no reminder.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PHASES_DIR="${REPO_ROOT}/.planning/phases"
LEARNINGS_DIR="${REPO_ROOT}/.planning/learnings"

[ ! -d "$PHASES_DIR" ] && exit 0
[ ! -d "$LEARNINGS_DIR" ] && exit 0

# Collect phases that have been executed (have at least one *-SUMMARY.md)
# but lack a corresponding PHASE-NN-RETRO.md.
missing=()
for phase_dir in "$PHASES_DIR"/*/; do
  [ -d "$phase_dir" ] || continue
  phase_num="$(basename "$phase_dir" | grep -oE '^[0-9]+' || echo "")"
  [ -z "$phase_num" ] && continue

  # Has SUMMARY.md? (any SUMMARY.md in the phase dir means at least one plan
  # was executed)
  if ls "$phase_dir"/*-SUMMARY.md >/dev/null 2>&1; then
    retro_file="${LEARNINGS_DIR}/PHASE-${phase_num}-RETRO.md"
    if [ ! -f "$retro_file" ]; then
      missing+=("$phase_num")
    fi
  fi
done

[ ${#missing[@]} -eq 0 ] && exit 0

# Emit context block. JSON-escape: list is small, manual escape is fine.
joined="$(IFS=, ; echo "${missing[*]}")"
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "REMINDER — Phases ${joined} have been executed but have no retrospective in .planning/learnings/. Copy .planning/learnings/RETRO-TEMPLATE.md → PHASE-NN-RETRO.md, fill in the fields, and run \`bash .planning/scripts/compare-phases.sh\` to see the trend. This is how we know whether the workflow improvements are paying off."
  }
}
EOF
