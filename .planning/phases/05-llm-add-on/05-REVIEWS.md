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

---

# Cycle 5 — Adversarial Re-Review of Manual Fix (commit 8366ac9)

**Reviewer:** Codex (independent semantic re-review per rule 08, second round)
**Reviewed at:** 2026-05-21
**Subject:** Manual fix in 8366ac9 addressing the 2 cycle-4 HIGHs (verify-block weakness + rglob cwd-leak)
**Trajectory:** ∞ → 8 → 5 → 2 → **1**

## Vectors Hunted

1. Does the new verify block at 05-03 Task 2 actually force the new gate semantics?
2. Did the rglob path correctly anchor on `Path(__file__).parent / "cassettes"` everywhere?
3. Did edits introduce NEW REVIEW-CHECKLIST violations?
4. Cross-plan drift in 05-04 / 05-05?
5. Any HIGH missed by the prior 4 review cycles + 2 manual fix rounds?

## Codex Findings

### HIGH #1 (NEW) — 05-03 Task 2 verify block is still self-defeating

At `05-03-PLAN.md:184-191`, the strengthened verify block is **still too weak**:

- `assert '!=' in text and '"none"' in text or "'none'" in text` is **precedence-broken**: Python evaluates this as `('!=' in text and '"none"' in text) or "'none'" in text`, so any implementation containing the single-quoted `'none'` (e.g. a comment) passes even if it never compares `record_mode != "none"`.
- Even with parentheses, substring checks can be satisfied by **comments** or by **dead/wrong-order code**.
- `pytest --collect-only --record-mode=once` does **not execute autouse fixtures**, so collection-only cannot prove `_skip_when_no_cassette` actually avoids skipping during cassette refresh.

**Adversary's worked counter-example** — the OLD self-defeating shape still passes the new verify block:

```python
if not cassette_path.exists():
    pytest.skip("cassette missing")
record_mode = request.config.getoption("--record-mode")
if record_mode != "none":
    return
```

That string contains `record_mode`, `!=`, and `"none"`, and `--collect-only` succeeds — but `just refresh-cassettes` still skips before recording. The verification gate does not detect the bug it was added to catch.

**Fix:** replace the substring-and-collect-only check with an **executing probe test** in the scratch render:

- write a temporary `tests/llm/test_record_mode_probe.py` with a trivial `@pytest.mark.vcr` test that makes no real network call
- run `uv run pytest -q --record-mode=once tests/llm/test_record_mode_probe.py -rs` and assert it is NOT skipped (autouse fixture must have bypassed the skip)
- run it without `--record-mode=once` and assert it IS skipped when the cassette is absent
- both assertions together force the semantics the plan claims

## Per-Vector Reasoning

1. **Verify-block semantics:** **HIGH found.** Substring checks + `--collect-only` do not force the new semantics. See above.
2. **rglob anchoring:** **CLEAN.** `05-03-PLAN.md:228` explicitly requires `(Path(__file__).parent / "cassettes").rglob("*.yaml")` and the verify block at line ~230 forbids the bare-relative `pathlib.Path("tests/llm/cassettes")` form. No residual cwd-leak found.
3. **New REVIEW-CHECKLIST violations:** The verify-block weakness above is the only new violation. No new dead-code-after-return, no new subprocess-without-cwd, no new broken Jinja patterns introduced by 8366ac9.
4. **Cross-plan drift:** **CLEAN.** 05-04 `just refresh-cassettes` recipe targets `tests/llm/cassettes/` with `--record-mode=once`; 05-05 references `just eval` (not the old `just verify --check=eval`). Both aligned with 05-03's canonical path and mode.
5. **Other missed HIGHs:** **None beyond #1 above.**

## Outcome

The manual fix in 8366ac9 successfully resolved cycle-4 HIGH #2 (rglob cwd-leak) but **only partially resolved cycle-4 HIGH #1** (verify-block weakness). The new verify block tightens the surface area but does not actually force the executable behavior — a sufficiently determined planner-agent regression could re-introduce the old bug and still pass the gate.

**Recommendation:** apply a third surgical fix to 05-03 Task 2 replacing the substring + collect-only check with an **executing probe test** as described in the HIGH above. After that fix, run one more adversarial re-review to confirm closure. Do NOT proceed to `/gsd:execute-phase 5` with current_high=1.

CYCLE_SUMMARY: current_high=1

---

# Cross-AI Plan Review — Phase 5 (Cycle 6, Adversarial)

**Cycle:** 6
**Reviewer:** codex (independent session, adversarial framing)
**Reviewed at:** 2026-05-21T21:30:00Z
**Plans reviewed:** 05-01..05-05 PLAN.md
**Under review:** commit 26625c5 (cycle-5 fix — executing probe test for record_mode gate)
**Trajectory:** infinity → 8 → 5 → 2 → 1 → **3 HIGH (cycle 6)**

## Codex Review

**Verdicts**

1. **Probe soundness, case (a): MEDIUM**  
   The default-mode assertion at [05-03-PLAN.md:200-202](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:200) is mostly sound for “one selected probe test skipped with the cassette reason.” Pytest conftest/collection errors normally exit nonzero, and “no tests ran” exits nonzero. But it does not prove `pytest-recording` is installed; the custom skip fixture can still see `@pytest.mark.vcr` as marker metadata even if the plugin is absent.

2. **Probe soundness, case (b): HIGH**  
   [05-03-PLAN.md:204-209](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:204) accepts any nonzero pytest exit as success as long as “skipped” is absent. That includes usage error for missing `--record-mode`, collection errors, import errors, fixture errors, and zero fixture execution.

3. **Can the old self-defeating shape still pass?: HIGH**  
   With `pytest-recording` absent, `--record-mode=once` is unrecognized before fixture execution. The old broken “always skip when cassette missing” fixture can pass case (a), then case (b) exits nonzero from CLI usage with no “skipped” text, satisfying the current assertions.

4. **cwd / path / env leaks: HIGH**  
   Both probe subprocesses use `uv run --no-project pytest ...` with `cwd` but no clean `env` at [05-03-PLAN.md:200](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:200) and [05-03-PLAN.md:204](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:204). This conflicts with REVIEW-CHECKLIST §8 at [REVIEW-CHECKLIST.md:74](/Users/moiz/Documents/code/verify-kit/.planning/REVIEW-CHECKLIST.md:74). Worse, `--no-project` ignores the scratch pyproject where `pytest-recording` is only planned as a dev optional dependency in [05-01-PLAN.md:169](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-01-PLAN.md:169).

5. **Race conditions and cleanup: LOW**  
   `probe.unlink()` is not in `finally`, so failed assertions leak the probe file within the scratch dir. The next run’s `rm -rf` cleans it, and it does not affect `.gitkeep`; not HIGH.

6. **Vestigial assertion: LOW**  
   [05-03-PLAN.md:206](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:206) is a no-op because of `or True`. It is deceptive and should be removed, but it is not load-bearing.

7. **Cross-plan drift: PASS**  
   `reset_cost_accumulator` is produced by 05-02 at [05-02-PLAN.md:166](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-02-PLAN.md:166) and consumed consistently by 05-03. 05-04’s `refresh-cassettes` uses the same `tests/llm/cassettes` path and `--record-mode=once` at [05-04-PLAN.md:182](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-04-PLAN.md:182). No 05-05 conftest interaction issue found.

8. **REVIEW-CHECKLIST patterns: HIGH**  
   §8 env leak applies directly. §2 dead-code concern applies only as LOW for the no-op assertion. §3/§4 drift, §5/§6 Jinja, and §7 recursive pytest do not add another HIGH here.

**HIGH FOUND**

- [05-03-PLAN.md:204](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:204), [05-03-PLAN.md:207](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:207)  
  Category: probe false-positive.  
  Asserted shape: any nonzero `--record-mode=once` run plus no “skipped” text proves the fixture did not skip.  
  Why HIGH: missing `pytest-recording`, usage errors, collection errors, and import errors all pass without exercising `_skip_when_no_cassette`.  
  Proposed fix shape: install/sync the scratch project with dev extras, assert `pytest --help` contains `--record-mode`, then make case (b) fail via a sentinel body exception and assert that exact sentinel appears.

- [05-03-PLAN.md:200](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:200), [05-03-PLAN.md:204](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:204)  
  Category: scratch dependency/env isolation.  
  Asserted shape: `uv run --no-project pytest` from scratch is a valid test of scratch behavior.  
  Why HIGH: it ignores scratch dependencies and can use ambient pytest/plugins or lack required plugins entirely.  
  Proposed fix shape: use a `_CLEAN_ENV`, run scratch project commands without `--no-project`, install dev dependencies, and reject pytest exit codes 2/3/4/5 explicitly.

## Consensus Summary

Cycle 6 escalates rather than converges. Three independent HIGHs surfaced:

1. **Case (b) probe is a false-positive sieve** — any non-zero exit without the substring "skipped" passes, including `pytest-recording` not installed (returncode 4, usage error), collection errors, ImportErrors, fixture errors. The OLD self-defeating shape can satisfy the assertion without the fixture ever running.
2. **`uv run --no-project`** bypasses scratch's pyproject — `pytest-recording` is declared as a dev optional dependency in 05-01-PLAN.md:169 but `--no-project` ignores it. The probe may be exercising ambient pytest, not the scratch-rendered toolchain.
3. **Env leak** — REVIEW-CHECKLIST §8 (Phase 4 incident). Neither subprocess passes a cleaned `env=`, so outer `VIRTUAL_ENV` / `UV_PROJECT_ENVIRONMENT` leaks in.

### Fix shape proposed by reviewer

- Install scratch project with dev extras (drop `--no-project`).
- Assert `pytest --help` lists `--record-mode` BEFORE running probes (proves pytest-recording is loaded).
- Replace case (b)'s "non-zero exit" assertion with a **sentinel body exception** in the probe (raise a uniquely-named error inside the test body) and grep the output for that exact sentinel — proves the fixture did NOT short-circuit.
- Pass `env=_CLEAN_ENV` to every subprocess.
- Reject pytest exit codes 2/3/4/5 explicitly (collection, usage, internal error, no-tests-collected).

### Recommendation

Per rule 08, two cycles of HIGH≥2 trigger restructure consideration. The substring/probe vector has now produced HIGHs across cycles 4, 5, and 6 — three consecutive cycles of churn on the same gate. Options:

- **Manual fix** (per rule 08 max-cycles=3 guidance): hand-patch the three issues in the verify block of 05-03 Task 2, then run an independent re-review to confirm fix-without-new-drift.
- **Restructure**: move the record-mode gate test from a verify-block probe into a real unit test inside the scratch render (`tests/llm/test_skip_fixture_gates_on_record_mode.py`) that 05-03 Task 3 produces, with the producer (05-03) owning the contract — per REVIEW-CHECKLIST §3 (contracts live with producers). The verify block then just checks that test file exists; the test itself is the gate.

The restructure is the cleaner path because:
- The verify block is a poor place for behavioral assertions — it runs inside the planning pre-flight, not inside the test suite.
- A real test file participates in normal test isolation, env handling, and developer workflow.
- The current churn shows the substring+probe shape is structurally fragile.

User decision required: manual-fix-and-reverify, or restructure-and-replan.
