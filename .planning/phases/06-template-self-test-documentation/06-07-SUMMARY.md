---
phase: 06-template-self-test-documentation
plan: "06-07"
plan_name: contributing-and-pr-template
subsystem: documentation
tags: [docs, contributing, pr-template, dual-audience, release-please]
requires: ["06-05-PLAN.md"]
provides:
  - "CONTRIBUTING.md (DOC-03)"
  - ".github/pull_request_template.md (D-14)"
affects:
  - "Future contributor onboarding flow"
  - "PR review surface (six-row checklist enforcement via reviewer eye)"
tech_stack:
  added: []
  patterns:
    - "release-please conventional-commit contract documented at the producer site (CONTRIBUTING.md commit-message table) — single source of truth for downstream docs"
    - "Dual-audience six rows duplicated VERBATIM across REQUIREMENTS.md, README (06-06), and PR template — no rewording allowed (§9 research)"
key_files:
  created:
    - "CONTRIBUTING.md (81 lines)"
    - ".github/pull_request_template.md (26 lines)"
  modified: []
decisions:
  - "Used grep-extracted harness API names (`register` from `harness.registry`, `CheckResult` from `harness.models`, `tier` Literal of `quick|standard|slow`) in the 'add a check' snippet — verified against template/harness/registry.py.jinja2:19-29 and template/harness/models.py.jinja2:22,61. Cycle-3 anti-drift gate (REVIEW-CHECKLIST §4) enforced."
  - "PR template's six dual-audience rows quoted byte-for-byte from REQUIREMENTS.md lines 13-18 (each row gains a trailing period for prose flow, content otherwise identical)."
  - "Add-on-slot section opens with the literal speculative/may-evolve note per D-13c."
metrics:
  duration_min: 8
  completed: 2026-05-23
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 6 Plan 06-07: contributing-and-pr-template Summary

CONTRIBUTING.md (DOC-03) and `.github/pull_request_template.md` (D-14) landed: the contributor onboarding document covers the smoke-test loop, a 10-line add-a-check walkthrough using the real `@register` / `CheckResult` API, a speculative add-an-add-on-slot section (flagged "may evolve" per D-13c), and the release-please conventional-commit contract; the PR template surfaces the dual-audience six rows verbatim from REQUIREMENTS.md as advisory checkboxes alongside Conventional-commit and Breaking-changes-for-consumers prompts that mirror the release-please CHANGELOG hand-edit convention (D-11).

## What landed

### CONTRIBUTING.md (root)

Four H2 sections plus a "Running the matrix locally" helper:

1. **Smoke-test loop (D-13a)** — references `.github/workflows/template-selftest.yml` from 06-08 (forward reference; planner explicitly allows naming the workflow without inventing line-level details). Documents the 5-entry Linux per-PR matrix + nightly macOS rerun shape from §5 research, the <10 min wall-clock budget (ROADMAP SC5), and that a regression in any cell fails the PR.
2. **Adding a new check in 10 lines (D-13b)** — concrete code snippet using the grep-extracted harness API surface. The snippet appears at lines 33–42 of CONTRIBUTING.md.
3. **Adding a new add-on slot (D-13c)** — opens with the canonical speculative note; sketches the four-step procedure (Copier prompt → `_exclude` + `{% if %}` path gating → Jinja conditionals in shared files → polarity test) using `has_backend` (Phase 4) and `has_llm` (Phase 5) as concrete precedents. References REVIEW-CHECKLIST §3 two-guard rule and §5 inline-Jinja-line-boundary rule.
4. **Commit-message contract (D-12)** — quotes §1 research table verbatim (feat → minor pre-1.0; fix → patch; feat!:/BREAKING CHANGE: → minor + breaking footer parsed; chore/docs/refactor/perf/test → no release). Cross-references the D-11 hand-edit of the "Breaking changes for consumers" block and the matching wording in the PR template.

### .github/pull_request_template.md

Five sections: Summary, Test plan, Dual-audience checklist (six markdown checkboxes), Conventional-commit type, Breaking changes for consumers. The six rows are byte-for-byte from REQUIREMENTS.md lines 13–18 (with a trailing period appended for prose flow on each bulleted row). No automated CI gate — D-14 advisory-checkbox + reviewer-eye policy.

## Harness API surface used (REVIEW-CHECKLIST §4 audit trail)

The "add a check" snippet was grep-extracted from the landed harness, NOT invented:

| Symbol used in snippet | Source file (verified) | Line |
|---|---|---|
| `from harness.registry import register` | `template/harness/registry.py.jinja2` | 19 |
| `from harness.models import CheckResult` | `template/harness/models.py.jinja2` | 61 |
| `@register("my-check", tier="standard", category="example")` | matches `register(check_id: str, *, tier: CheckTier = "standard", category: str = "misc", ...)` | 19–29 |
| `CheckTier` valid values `"quick" / "standard" / "slow"` | `Literal["quick", "standard", "slow"]` | 22 |
| `CheckResult(status="pass", check_id="my-check", duration_ms=0)` | `BaseModel` with required `check_id` + `status: CheckStatus`, optional `duration_ms: int = 0` | 61–69 |

Anti-drift negative assertions (verified by Task 1 gate): no `@register_check`, no `CheckResult(ok=`, no `tier="universal"`, no `from harness.checks import`.

## Six-row REQUIREMENTS.md ↔ PR template parity

Each row's substantive content (everything from "Pretty colorized..." through "...so human can `cat` while agent runs") was confirmed byte-identical via `grep -F` against both files. The PR template formats each row as a markdown checkbox with a bolded row number + audience-question prefix + a trailing period; the underlying answer text is unmodified.

## Cross-references

- **06-05** (release-please config) — the producer of the conventional-commit contract documented in CONTRIBUTING.md's commit-message table. The prefixes and SemVer effects in CONTRIBUTING.md match `release-please-config.json`'s changelog-sections shape.
- **06-06** (README) — independently documents the same six dual-audience rows (per D-09). 06-06's README footer links to CONTRIBUTING.md (this plan's artifact). Both plans ran in parallel as Wave 4 siblings; the six rows were pulled from REQUIREMENTS.md as the single producer per REVIEW-CHECKLIST §3, so 06-06 and 06-07 cannot drift from each other unless REQUIREMENTS.md itself changes.
- **06-08** (self-test workflow) — CONTRIBUTING.md's "Smoke-test loop" section names this workflow as a forward reference; the planner explicitly permitted forward-referencing the workflow path without locking detail since 06-08 is the producer.

## Deviations from Plan

None. Plan executed exactly as written; both Task 1 and Task 2 verify gates passed on first run.

## Commits

- `4dfb954` — docs(contrib): scaffold CONTRIBUTING.md with smoke-test loop + add-a-check + add-on-slot + commit-message contract
- `07ad8a3` — chore(pr-template): add dual-audience six-row checkbox PR template

## Self-Check: PASSED

- `[ ] test -f CONTRIBUTING.md` → FOUND (81 lines, ≥80 min)
- `[ ] test -f .github/pull_request_template.md` → FOUND (26 lines)
- Commit `4dfb954` exists on `feat/phase-5-llm` → FOUND
- Commit `07ad8a3` exists on `feat/phase-5-llm` → FOUND
- Six rows match REQUIREMENTS.md byte-for-byte (Task 2 grep loop) → CONFIRMED
- CONTRIBUTING.md anti-drift gate (no `@register_check` / `CheckResult(ok=` / `tier="universal"` / `from harness.checks import`) → CONFIRMED
