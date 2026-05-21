#!/usr/bin/env bash
# Post-convergence sanity grep — scans plan files for the known-bad shapes
# documented in .planning/REVIEW-CHECKLIST.md.
#
# Usage: bash .planning/scripts/check-plan-shapes.sh <phase-number>
# Example: bash .planning/scripts/check-plan-shapes.sh 2
#
# Exits 0 if nothing suspicious found, 1 otherwise. The 1 exit is advisory —
# patterns can have legitimate uses (e.g. an explicit prohibition like
# "NEVER use `pnpm dlx`"). Eyeball every hit before fixing.

set -euo pipefail

PHASE="${1:?usage: check-plan-shapes.sh <phase-number>}"
PADDED=$(printf "%02d" "$PHASE")

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PHASE_DIR=$(ls -d "$ROOT/.planning/phases/${PADDED}-"*/ 2>/dev/null | head -1)

if [ -z "$PHASE_DIR" ]; then
  echo "error: no phase dir matching ${PADDED}-* under .planning/phases/" >&2
  exit 2
fi

PLANS=$(ls "$PHASE_DIR"/${PADDED}-*-PLAN.md 2>/dev/null || true)
if [ -z "$PLANS" ]; then
  echo "error: no PLAN.md files in $PHASE_DIR" >&2
  exit 2
fi

FOUND=0

echo "Scanning $(echo "$PLANS" | wc -l | tr -d ' ') plan(s) in ${PHASE_DIR}"
echo

# Pattern 1: bare relative Path("...") that isn't anchored to cwd
echo "=== [1] Bare relative paths (potential cwd leak) ==="
HITS=$(grep -nE 'Path\("[^/"][^"]*"\)' $PLANS 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "$HITS"
  FOUND=1
else
  echo "  (clean)"
fi
echo

# Pattern 2: load_config / load_* called with no args (default-relative paths)
echo "=== [2] Loader calls with no cwd argument ==="
HITS=$(grep -nE '\bload_(config|settings|toml|yaml)\(\s*\)' $PLANS 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "$HITS"
  FOUND=1
else
  echo "  (clean)"
fi
echo

# Pattern 3: action steps appearing after a "return X" line within the same
# plan body. This catches the dead-code-via-narrative shape. We look for
# "return ..." followed within 5 lines by a bullet starting with "After"
# or similar imperative narrative.
echo "=== [3] Action steps after return (dead code) ==="
HITS=$(awk '
  /return [A-Za-z_]/ { last_return=NR; file=FILENAME; next }
  last_return && NR - last_return <= 5 && /^[[:space:]]*-?[[:space:]]*(After|Before returning|Once .* is done|Finally,|Then[[:space:],])/ {
    printf "%s:%d: post-return narrative — %s\n", file, NR, $0
  }
' $PLANS 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "$HITS"
  FOUND=1
else
  echo "  (clean)"
fi
echo

# Pattern 4: subprocess.run(...) calls without an explicit cwd=
# (heuristic — may have false positives on multi-line calls)
echo "=== [4] subprocess.run without explicit cwd ==="
HITS=$(grep -nE 'subprocess\.run\([^)]*\)' $PLANS 2>/dev/null | grep -v 'cwd=' || true)
if [ -n "$HITS" ]; then
  echo "$HITS" | head -20
  FOUND=1
else
  echo "  (clean)"
fi
echo

# Pattern 5: cross-plan contract drift heuristic — list every CLI invocation
# (`verify-kit <cmd>`) and every "per Plan NN-NN" reference in test/assertion
# plans. The script can't validate them automatically (it has no semantic
# model of the producer plan), but emitting them lets a human eyeball the
# pairs in one place.
echo "=== [5] Cross-plan contract surface (eyeball check) ==="
HITS=$(grep -nE "verify-kit [a-z][a-z_-]+|per Plan [0-9]{2}-[0-9]{2}" $PLANS 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "$HITS" | head -30
  echo "  (review each: does the CLI command actually exist? does the cited producer plan actually use that field name?)"
  # advisory only — does not set FOUND
else
  echo "  (no cross-plan references found)"
fi
echo

# Pattern 6: plan API-surface drift (Phase 4) — known invented names that
# don't match the producing codebase. Flag any reference to symbols that
# should be checked against the actual harness. The list grows as drift
# is caught; current set seeded from Phase 4 04-04/04-07.
echo "=== [6] Plan API-surface drift (vs landed codebase) ==="
HITS=$(grep -nE '@register_check|CheckSeverity|CheckResult\([^)]*\bok\b|--only=[a-z]|registry\.py\.jinja2' $PLANS 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "$HITS"
  echo "  (these names do not exist in the harness as of Phase 3; real names are @register, CheckResult(status=...), --check=, harness/checks/__init__.py.jinja2)"
  FOUND=1
else
  echo "  (clean)"
fi
echo

# Pattern 7: inline Jinja conditional inside a YAML / TOML key:value pair
# — `{% if X %}key: val{% endif %}` on one line risks line merging when the
# conditional renders empty. Block-form `{% if %}` … `{% endif %}` on
# separate lines is safe.
echo "=== [7] Inline Jinja conditional on a single line (YAML/TOML risk) ==="
HITS=$(grep -nE '\{% if [^%]+%\}[^{]*:[^{]*\{% endif %\}' $PLANS 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "$HITS"
  echo "  (move {% if %} and {% endif %} to their own lines so they span a block, not a line fragment)"
  FOUND=1
else
  echo "  (clean)"
fi
echo

# Pattern 8: meta-comments embedded in jinja templates that would render to
# consumer output. Author-for-reviewer notes ("cycle-N sweep:", "per Codex HIGH")
# belong in PLAN.md, not in .jinja2 files. The grep is intentionally broad —
# review each hit.
echo "=== [8] Meta-comments inside templates (author-for-reviewer leak) ==="
HITS=$(grep -nE '(cycle-[0-9]+ sweep|per Codex HIGH|REPLAN NOTE|TODO\(reviewer\))' $PLANS 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "$HITS" | head -20
  echo "  (if any of these are inside <code-block>...</code-block> describing template content, strip them — they will render literally)"
  FOUND=1
else
  echo "  (clean)"
fi
echo

# Pattern 9: subprocess.run targeting a scratch tmp_path without explicit
# env scrubbing — leaks outer VIRTUAL_ENV / UV_PROJECT_ENVIRONMENT.
echo "=== [9] Scratch-project subprocess without env scrubbing ==="
HITS=$(grep -nE 'subprocess\.run\([^)]*tmp_path' $PLANS 2>/dev/null | grep -vE '\benv=' || true)
if [ -n "$HITS" ]; then
  echo "$HITS" | head -20
  echo "  (subprocess invocations against a scratch scaffold must pass env=<clean_env> stripping VIRTUAL_ENV/UV_PROJECT_ENVIRONMENT/PYTHONPATH)"
  FOUND=1
else
  echo "  (clean)"
fi
echo

if [ "$FOUND" -eq 0 ]; then
  echo "✓ No suspicious shapes detected in Phase $PHASE plans."
  exit 0
else
  echo "⚠ Suspicious shapes above — eyeball each hit, fix the real ones, ignore explicit prohibitions."
  exit 1
fi
