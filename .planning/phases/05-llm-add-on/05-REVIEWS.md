---
phase: 5
cycle: 3
reviewers: [codex]
reviewed_at: 2026-05-21T19:25:00Z
plans_reviewed:
  - 05-01-PLAN.md
  - 05-02-PLAN.md
  - 05-03-PLAN.md
  - 05-04-PLAN.md
  - 05-05-PLAN.md
adversarial: true
---

# Cross-AI Plan Review — Phase 5 (Cycle 3, Adversarial)

Cycle 3 is the independent semantic re-review required by `rules/08-plan-convergence-workflow.md` after cycle-2 HIGHs were addressed via manual Edit (the planner had no Agent tool). The reviewer was instructed to be adversarial — assume the prior reviewer and the manual editor missed something — and to hunt explicitly for cwd leaks, post-`return` dead code, missing `cwd=` on subprocess calls, cross-plan contract drift, two-guard path-gating violations, D-21 reflection, and every pattern in `.planning/REVIEW-CHECKLIST.md`.

Trajectory: cycle 1 (8 HIGHs) → cycle 2 (5 HIGHs) → cycle 3 (2 HIGHs). Still monotone-decreasing.

## Codex Review (Adversarial)

**Summary**

Risk level **HIGH**. The cycle-2 HIGHs are mostly addressed on paper, but the VCR cassette lifecycle is still broken: the plan's clean-render skip guard prevents the only cassette refresh command from ever recording, and the credential scrub test scans a different cassette tree than the one used by the LLM tests.

**Newly Raised HIGHs (cycle 3)**

- **HIGH #1 (cycle-3) — `just refresh-cassettes` cannot populate missing cassettes.**
  05-03 Task 2 requires the `_skip_when_no_cassette` autouse fixture to call `pytest.skip(...)` whenever a `@pytest.mark.vcr`-marked test's cassette is absent ([05-03-PLAN.md:164](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md)). 05-04 Task 2 then defines `refresh-cassettes` as `rm -rf tests/llm/cassettes/` followed by `uv run pytest tests/llm/ --record-mode=once` ([05-04-PLAN.md:182](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-04-PLAN.md)). That deletes the cassette, then the autouse fixture skips the test before VCR can record — the very tests that should be re-recording are skipped first. The plan claims the skip "dissolves" after `refresh-cassettes` ([05-03-PLAN.md:231](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md)), but no cassette can be created under this flow. Fix shape: gate the skip on `record_mode == "none"` (read from the vcr_config fixture or via a recording-mode env var), or have `refresh-cassettes` set `VERIFY_KIT_RECORDING=1` that the autouse fixture honors as an override.

- **HIGH #2 (cycle-3) — credential scrub test scans `tests/cassettes`, but LLM cassettes live under `tests/llm/cassettes`.**
  `test_no_plaintext_credentials_in_cassettes` walks `tests/cassettes/*.yaml` ([05-03-PLAN.md:218](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md)), while the skip fixture and refresh recipe use `tests/llm/cassettes/<module>/<test>.yaml` ([05-03-PLAN.md:230](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md), [05-04-PLAN.md:182](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-04-PLAN.md)). The actual recorded LLM cassettes live outside the secret-leak assertion — a leaked Authorization header in a real LLM cassette would never trip the scrub test. Fix shape: canonicalize on `tests/llm/cassettes/**/*.yaml` everywhere (recipe + scrub test + skip fixture), OR have the scrub test walk both `tests/cassettes/**` and `tests/llm/cassettes/**`. The two cassette roots cannot diverge in scope.

**Prior HIGH Status (cycle 2 → cycle 3)**

| Cycle-2 HIGH | Status | Evidence |
|---|---:|---|
| Missing backend `.env.example` template | FULLY | 05-01 has explicit precondition: `ls` the backend env file and recreate Phase 4 baseline if absent before appending ([05-01-PLAN.md:209](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-01-PLAN.md)). |
| Unsafe `tests/{% if has_llm %}llm{% endif %}` path shape | FULLY | 05-03 frontmatter + tasks use hard-coded `tests/llm/` plus filename-level gates ([05-03-PLAN.md:10](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md), [05-03-PLAN.md:195](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md)). |
| Root `.env.example` lacks primary `_exclude` gate | FULLY | 05-01 requires `{% if not has_llm %}.env.example{% endif %}` in `_exclude` ([05-01-PLAN.md:140](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-01-PLAN.md), [05-01-PLAN.md:154](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-01-PLAN.md)). |
| `@llm_call` span contract under-specified | FULLY | 05-02 now requires full `gen_ai.*`, token usage, retry count, and model attrs ([05-02-PLAN.md:143](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-02-PLAN.md), [05-02-PLAN.md:220](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-02-PLAN.md)). |
| pydantic-ai role conflicts with call routing | FULLY | D-21 explicitly defines pydantic-ai as consumer-facing typed-call layer, NOT verify-kit's routing entry point ([05-CONTEXT.md:61](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-CONTEXT.md), [05-CONTEXT.md:65](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-CONTEXT.md)); README task documents that split ([05-05-PLAN.md:246](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-05-PLAN.md)). |

**MEDIUM / LOW concerns**

- **MEDIUM — verification snippets repeatedly use `subprocess.run(...)` without `cwd=`.** Most use absolute source/destination paths, so practical risk is lower than helper/test code that would inherit process CWD, but it violates the explicitly-requested cwd-leak discipline from REVIEW-CHECKLIST §1.
- **LOW — 05-01 Task 2 prose says "eleven entries" but describes `harness/llm.py` twice and vaguely references "corresponding gitkeep"** ([05-01-PLAN.md:138](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-01-PLAN.md)). The acceptance criteria list is clearer than the narrative; the prose should be tightened.

**Risk Assessment**

**HIGH.** Verdict: do not execute as-is. The remaining blocker is concentrated in the cassette lifecycle: first-run cleanliness, refresh, and secret scrubbing do not form a coherent contract. Once both cycle-3 HIGHs are fixed, the rest of the cycle-2 HIGHs look resolved and the phase is executable.

---

## Consensus Summary

Single adversarial reviewer (Codex). Cycle 3 confirms all 5 cycle-2 HIGHs are FULLY resolved, but exposes 2 newly-introduced HIGHs in the cassette lifecycle that prior cycles missed:

### Agreed Concerns (single reviewer)
1. `just refresh-cassettes` is self-defeating: the autouse skip fires before VCR records (HIGH #1).
2. Credential scrub test and LLM cassette directory diverge — secrets in `tests/llm/cassettes/**` are never scanned (HIGH #2).

### Divergent Views
N/A (single reviewer).

### Trajectory
cycle 1 (8 HIGH) → cycle 2 (5 HIGH) → cycle 3 (2 HIGH). Still monotone-decreasing — not the oscillation signal from rule 08. Both HIGHs are surgical fixes to 05-03 / 05-04 (not structural coupling), so plan-coupling restructure is NOT indicated.

### Recommended Path
Per the cycle-3 escalation gate (max 3 cycles), the convergence loop exits here. Options:
- **Manual fix** (recommended): both HIGHs are local edits in 05-03 (skip fixture predicate) and 05-04 (recipe env var) plus a one-line scrub-test path change. Estimated 10–15 min of Edit operations. Per rule 08, run an independent semantic re-review after the manual fix to confirm it didn't introduce new drift — but that re-review is a one-shot, NOT a fourth convergence cycle.
- **Accept and execute** (NOT recommended): both HIGHs are real execution blockers — `just refresh-cassettes` will silently no-op and credential leaks in LLM cassettes will not be caught.

---

# Cross-AI Plan Re-Review — Phase 5 (Cycle 4, Post-Manual-Fix Adversarial)

**Reviewed:** 2026-05-21 (post-commit 823b71c)
**Reviewer:** Codex CLI
**Framing:** Adversarial — assume the manual editor missed something. Mandated by rule 08 ("grep is not verification — after manual fixes, must spawn an independent semantic re-review").

## Codex Review

CYCLE_SUMMARY: current_high=2

### Current HIGH Concerns

- **HIGH #1 (verification gap, not semantic gap):** 05-03-PLAN.md L165 describes the correct `record_mode != "none"` bypass, but the verify/acceptance block at L181 only checks that a skip fixture exists and calls `pytest.skip`. The old self-defeating implementation would still pass this verification. Add a forcing test/assertion that rendered `tests/llm/conftest.py` reads `--record-mode`, reads `vcr_config` via fixture fallback, and that `pytest tests/llm/ --record-mode=once` with a missing cassette does NOT skip before VCR records. (pytest-recording docs: `--record-mode=once` is the intended recording path.)

- **HIGH #2 (REVIEW-CHECKLIST §1 cwd-leak violation introduced by the manual fix):** 05-03-PLAN.md L219 now instructs `pathlib.Path("tests/llm/cassettes").rglob("*.yaml")` — a bare relative path. If pytest is invoked from a parent directory, the scrub test scans the wrong tree and silently misses real cassettes. The same task later directs file IO relative to `Path(__file__).parent`, so the plan is internally inconsistent. **Fix:** use `(Path(__file__).parent / "cassettes").rglob("*.yaml")` and make the verify block assert both `.rglob("*.yaml")` AND anchoring on `Path(__file__).parent`.

### Lower-Stakes Drift Noted (not HIGH)

- L347 threat-model row still says `tests/cassettes/*.yaml -> git repo` — descriptive, not an executor step, but should be canonicalized to `tests/llm/cassettes/**/*.yaml` to prevent future-reviewer confusion.

### Cross-Plan Drift Checks Performed

- 05-04 `just refresh-cassettes` recipe + nightly-eval workflow: ALIGNED on `tests/llm/cassettes/` and `--record-mode=once`. No drift.
- 05-05 docs/copier vars: NO cassette-path drift found.

## Outcome

The manual fix in commit 823b71c **partially resolved** the two cycle-3 HIGHs:
- HIGH #1 (record_mode gate): plan prose is correct, but verification does not force the new shape — the old buggy shape would still pass.
- HIGH #2 (cassette path glob): the canonical-path direction is right, but the manual edit introduced a NEW REVIEW-CHECKLIST §1 violation (bare relative `Path("tests/llm/cassettes")`).

**Recommendation:** apply a second surgical manual fix to (a) tighten the 05-03 verify block for HIGH #1 and (b) anchor the rglob on `Path(__file__).parent` for HIGH #2; then re-run this adversarial pass. Do NOT proceed to `/gsd:execute-phase 5` with current_high=2.
