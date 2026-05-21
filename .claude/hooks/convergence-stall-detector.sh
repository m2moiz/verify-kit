#!/usr/bin/env bash
# Convergence stall detector — fires on PostToolUse of Edit/Write tools that
# touched a REVIEWS.md or PLAN.md file. Extracts the latest CYCLE_SUMMARY HIGH
# count from REVIEWS.md, compares to a per-phase checkpoint, and warns to
# stderr if the count is repeating across cycles (the classic oscillation
# signal documented in REVIEW-CHECKLIST.md and the user-rule).
#
# Honest scope: this is a passive signal only. It cannot stop the workflow,
# only nudge the next prompt to consider restructuring. The hook is wired via
# .claude/settings.json or settings.local.json — see the project README.
#
# Input contract: receives Claude Code's PostToolUse hook JSON on stdin. We
# extract `tool_input.file_path` to decide whether this hook applies.

set -euo pipefail

# Skip silently if jq is missing — don't break the editing workflow.
command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat || true)"
[ -z "$INPUT" ] && exit 0

FILE_PATH="$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')"
[ -z "$FILE_PATH" ] && exit 0

# Only fire for REVIEWS.md and REVIEWS-RESPONSE.md edits — these are the
# files that record cycle outcomes.
case "$FILE_PATH" in
  *REVIEWS.md|*REVIEWS-RESPONSE.md) ;;
  *) exit 0 ;;
esac

# Find the phase directory and resolve the canonical REVIEWS.md path.
PHASE_DIR="$(dirname "$FILE_PATH")"
PHASE_NUM="$(basename "$PHASE_DIR" | grep -oE '^[0-9]+' || echo "")"
[ -z "$PHASE_NUM" ] && exit 0

REVIEWS_FILE="${PHASE_DIR}/${PHASE_NUM}-REVIEWS.md"
[ ! -f "$REVIEWS_FILE" ] && exit 0

# Pull the LATEST HIGH count from the file. REVIEWS.md uses three conventions
# depending on how the review agent wrote it:
#   - Frontmatter: `cycleN_new_highs: <N>` or `cycleN_unresolved_highs: <N>`
#   - Prose:       `Unresolved HIGHs in this cycle: <N>`
#   - Contract:    `CYCLE_SUMMARY: current_high=<N>` (rare — only when the
#                  agent wrote its return contract verbatim into the file)
# Take the LAST match across all three patterns — that's the most recent cycle.
LATEST_HIGH="$(
  {
    grep -oE 'CYCLE_SUMMARY:\s*current_high=[0-9]+' "$REVIEWS_FILE" 2>/dev/null | grep -oE '[0-9]+$'
    grep -oE 'cycle[0-9]+_(new|unresolved)_highs:\s*[0-9]+' "$REVIEWS_FILE" 2>/dev/null | grep -oE '[0-9]+$'
    grep -oE 'Unresolved HIGHs in this cycle:\s*[0-9]+' "$REVIEWS_FILE" 2>/dev/null | grep -oE '[0-9]+$'
  } | tail -1
)"
[ -z "$LATEST_HIGH" ] && exit 0

# Load and update the per-phase checkpoint.
STATE_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/state"
mkdir -p "$STATE_DIR"
STATE_FILE="${STATE_DIR}/convergence-${PHASE_NUM}.json"

if [ -f "$STATE_FILE" ]; then
  PREV_HISTORY="$(jq -r '.history // []' "$STATE_FILE")"
else
  PREV_HISTORY="[]"
fi

NEW_HISTORY="$(echo "$PREV_HISTORY" | jq --argjson n "$LATEST_HIGH" '. + [$n] | .[-5:]')"
echo "{\"phase\":\"${PHASE_NUM}\",\"history\":${NEW_HISTORY}}" > "$STATE_FILE"

# Stall detection. We have a 3+ entry history. The signal is: "we are not
# making progress." Concretely: the latest HIGH count is not strictly less
# than the MINIMUM of the previous two — i.e., we have already seen this
# count or worse recently. Distinguish flat (all same) from oscillating
# (going up and down in the same band) for clearer messaging.
LEN="$(echo "$NEW_HISTORY" | jq 'length')"
if [ "$LEN" -ge 3 ]; then
  LAST3="$(echo "$NEW_HISTORY" | jq -r '.[-3:] | join("->")')"
  N1="$(echo "$NEW_HISTORY" | jq '.[-1]')"
  N2="$(echo "$NEW_HISTORY" | jq '.[-2]')"
  N3="$(echo "$NEW_HISTORY" | jq '.[-3]')"

  if [ "$N1" -gt 0 ]; then
    # Pattern A: flat — same count for 3 cycles
    if [ "$N1" = "$N2" ] && [ "$N2" = "$N3" ]; then
      echo "[CONVERGENCE-STALL] Phase ${PHASE_NUM} HIGH count flat at ${N1} for 3 cycles (${LAST3}). RESTRUCTURE the plans — see .planning/REVIEW-CHECKLIST.md §3 and ~/.claude/rules/08-plan-convergence-workflow.md." >&2
      exit 0
    fi

    # Pattern B: not making progress — latest count is >= min of previous two
    MIN_PREV="$N2"; [ "$N3" -lt "$MIN_PREV" ] && MIN_PREV="$N3"
    if [ "$N1" -ge "$MIN_PREV" ]; then
      echo "[CONVERGENCE-STALL] Phase ${PHASE_NUM} HIGH count not decreasing (${LAST3}). The loop is oscillating, not converging — RESTRUCTURE beats tighten. See ~/.claude/rules/08-plan-convergence-workflow.md \"Oscillation diagnosis\"." >&2
      exit 0
    fi
  fi
fi

# Otherwise: monotone-decreasing or zero — silent (success path).
exit 0
