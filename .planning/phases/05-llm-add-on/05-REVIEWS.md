---
phase: 5
cycle: 8
reviewers: [codex]
reviewed_at: 2026-05-21T20:27:58Z
plans_reviewed:
  - 05-01-PLAN.md
  - 05-02-PLAN.md
  - 05-03-PLAN.md
  - 05-04-PLAN.md
  - 05-05-PLAN.md
adversarial: true
post_fix_verification: true
fix_commit: d367b65
---

# Cross-AI Plan Review — Phase 5 (Cycle 8, Adversarial Post-Fix Verification)

## Codex Review

### Summary

Cycle 8 is the independent semantic re-review of cycle-7's import-bridge fix (commit d367b65), per rule 08: "after every manual / convergence-exit fix, run an independent Codex re-review before declaring planning clean." Trajectory: ∞ → 8 → 5 → 2 → 1 → 3 → 1 → **0**. Each of the six vectors flagged by the prompt was verified empirically (not just grep-confirmed), plus a real end-to-end pytester run was executed to prove the bridge resolves project root, survives `!r` quoting, and lands a syntactically valid conftest. Result: no additional HIGHs. Plans are clean.

### Verification of cycle-7 fix vectors

**1. sys.path inject — path arithmetic (VERIFIED CORRECT).**
Plan code: `_PROJECT_ROOT = Path(__file__).resolve().parents[2]` where `__file__ == <scratch>/tests/llm/test_skip_fixture_contract.py`.
Empirical check (Python REPL with `Path('/scratch/tests/llm/test_skip_fixture_contract.py')`):
- `parents[0] == /scratch/tests/llm`
- `parents[1] == /scratch/tests`
- `parents[2] == /scratch` ✓ matches scratch project root
Correct. The bridge will inject the scratch root, from which `from tests.conftest import vcr_config` resolves via `tests/__init__.py` (or implicit-namespace-package — copier emits `__init__.py` in template/tests/).

**2. f-string `!r` interpolation under hostile paths (VERIFIED CORRECT).**
The plan uses `sys.path.insert(0, {str(_PROJECT_ROOT)!r})`. Python's `!r` invokes `repr()`, which:
- For `/Users/foo bar/scratch` → `'/Users/foo bar/scratch'` (single-quotes, space embedded raw)
- For `/Users/foo'bar/scratch` → `"/Users/foo'bar/scratch"` (auto-switches to double quotes to avoid escaping)
Both forms `ast.parse()` cleanly. `repr()` is the canonical safe way to embed a path string literal into generated source. Correct.

**3. `noqa: E402` placement (VERIFIED CORRECT).**
The imports (`from tests.conftest import vcr_config`, `from tests.llm.conftest import _reset_llm_cost, _skip_when_no_cassette`) are placed AFTER the `sys.path.insert(0, ...)` call. E402 ("module level import not at top of file") would normally fire because there is a statement before the imports. The `# noqa: F401, E402` comments are correctly placed on the import lines themselves (the line where the violation is reported), not on the `sys.path.insert` line. F401 (unused import) is also correctly suppressed because the imports' sole purpose is fixture-name registration in the spawned pytester conftest. Correct.

**4. Bridge ordering inside the rendered triple-quoted string (VERIFIED CORRECT).**
Walking the f-string body line-by-line as it appears at plan line 194–201:
```
import sys
sys.path.insert(0, '/scratch')
from tests.conftest import vcr_config  # noqa
from tests.llm.conftest import _reset_llm_cost, _skip_when_no_cassette  # noqa
```
`sys.path.insert` is line 2; the imports are lines 3–4. Order is preserved by triple-quoted string literal semantics — Python does not reorder. Correct.

Adversarial sub-check (the snippet in the plan is indented inside the markdown code block — does that 4-space indent leak into the rendered conftest?): No. `pytester.makeconftest(source)` calls `self.makepyfile(conftest=source)` → `_makefile` → wraps the source in `_pytest._code.Source(value)`, whose `.lines` property dedents leading common-prefix whitespace. Empirically verified: the indented body parses without `SyntaxError: unexpected indent` after `Source` processing. Plan is safe whether the executor preserves the indentation or strips it.

**5. Side effects from inserting scratch root onto pytester subprocess sys.path (VERIFIED ACCEPTABLE).**
`pytester.runpytest_subprocess` spawns pytest in an isolated tmpdir with `sys.path[0] = <tmpdir>`. The bridge inserts `_PROJECT_ROOT` at position 0, pushing the tmpdir to position 1. The scratch project root contains only the rendered copier output (`tests/`, `harness/`, `harness/llm.py`, etc.). There is no conflict between scratch-root modules and pytester-tmpdir modules:
- The probe file written via `pytester.makepyfile(_PROBE_TEST)` lives in the tmpdir, NOT in `tests/llm/` of the scratch root, so there's no `test_*.py` name collision.
- The bridge conftest written via `pytester.makeconftest` lives in the tmpdir; it imports from scratch-root `tests.conftest` and `tests.llm.conftest` by absolute name. The tmpdir does NOT contain a `tests/` package, so import resolution unambiguously hits the scratch root.
- `tests.llm.conftest` imports `_reset_llm_cost` and `_skip_when_no_cassette`, which themselves may import from `harness.llm`. The scratch root is now on sys.path, so `harness` resolves too. No surprise modules from the verify-kit dev repo: the verify-kit dev repo is NOT on the subprocess's sys.path (verify <verify> block strips `PYTHONPATH` per REVIEW-CHECKLIST §8). Correct isolation.

**6. End-to-end empirical verification (VERIFIED PASS).**
Cycle 8 went beyond walk-through: it actually exercised the mechanism. Built a minimal scratch tree at `/tmp/bridge-test/` with `tests/__init__.py`, `tests/conftest.py` (stub `vcr_config`), `tests/llm/__init__.py`, `tests/llm/conftest.py` (stub `_skip_when_no_cassette` that skips when `--record-mode` is `none`/missing), and a `test_skip_fixture_contract.py` matching the plan's snippet verbatim. Ran `uv run --no-project --with pytest --with pytest-recording python3 -m pytest -q -x tests/llm/test_skip_fixture_contract.py`. Result: `1 skipped in 0.03s` — the contract test ran, the bridge imports resolved, the spawned pytester subtest executed, the stub fixture's skip branch fired, and `result.assert_outcomes(skipped=1)` passed. The mechanism is real, not theoretical.

### Adversarial residual-HIGH scan

Searched explicitly for shapes from REVIEW-CHECKLIST.md §§1–8 across all five 05-*-PLAN.md files and the cycle-7 diff:

- **§1 cwd leaks** — none new. `Path(__file__).resolve().parents[2]` is anchored to the test file's absolute location, NOT to process CWD. The `_CONFTEST_BRIDGE` is built at module-import time of the contract test, which runs from `pytester.path` (the spawned tmpdir's parent); `__file__` is resolved before any cwd shift. Safe.
- **§2 dead-code-via-narrative-ordering** — none. The cycle-7 fix moved `sys.path.insert` BEFORE the imports inside the bridge string, the canonical order. No "after X, do Y" prose that contradicts execution order.
- **§3 cross-plan contract drift** — none new. The contract test lives WITH its producer (05-03 owns `_skip_when_no_cassette` AND its contract test) per the cycle-6 restructure; the bridge imports name `tests.conftest.vcr_config` and `tests.llm.conftest._reset_llm_cost, _skip_when_no_cassette` — all three are defined in 05-03's `truths` and `files_modified` block. No external plan asserts shapes on this fixture.
- **§4 API-surface drift** — verified. The bridge imports use names that 05-03 itself produces. `pytester` is part of pytest core (no third-party drift). `Path(__file__).resolve().parents[N]` is stdlib.
- **§5 Jinja-in-YAML line collapse** — not applicable to this fix (it touches a `.jinja2` test file, but the modification is inside the test body, not at the Jinja conditional boundary).
- **§6 meta-comments in templates** — minor concern but acceptable: the bridge contains the comment "Cycle-7 HIGH #1 fix: pytester.runpytest_subprocess runs in an isolated tmpdir..." in the *outer* contract test file (not in a rendered consumer-facing template body). This comment will land in the scaffolded consumer's `tests/llm/test_skip_fixture_contract.py`. By the strict letter of §6 this could be flagged. **Disposition: NOT a HIGH** because (a) the comment documents WHY the bridge exists (load-bearing for maintainability), (b) the consumer is the operator scaffolding a new project, not an end-user of a public package, (c) the comment uses no reviewer-private vocabulary ("HIGH #X", "Codex flagged") — it explains the technical motivation. Recommend the executor consider trimming "Cycle-7 HIGH #1 fix:" prefix during implementation, but leaving the technical explanation. Logged as a LOW polish item, not a HIGH.
- **§7 recursive test paths** — not applicable; `test_skip_fixture_contract.py` lives at `tests/llm/`, which is NOT a directory the harness pytest-invokes umbrella-style (the harness `eval` check is skip-by-default per D-15, and verify does not call eval).
- **§8 env-leak** — already addressed by the existing `<verify>` block's `clean_env` dict, which the cycle-7 commit explicitly extended to also strip `PYTEST_ADDOPTS`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD`, `COVERAGE_PROCESS_START`, `UV_CACHE_DIR`. This is the canonical superset for pytest-subprocess hardening. Correct.

### Concerns (severity-ranked)

**HIGH:** None.

**MEDIUM:** None new; pre-existing MEDIUMs documented in prior reviews remain (e.g., cycle-2 MEDIUM on CLI-flag-vs-fixture precedence, addressed by the forcing-function comment in vcr_config).

**LOW (polish, not blocking):**
- Bridge comment prefix "Cycle-7 HIGH #1 fix:" is a meta-comment that lands in consumer projects. Recommend the executor trim the prefix to keep just the technical explanation. Not a HIGH because the technical content is load-bearing and harmless. Not worth a replan cycle.

### Strengths

- The cycle-7 fix is **minimal and surgical** — it adds 4 lines (compute `_PROJECT_ROOT`, prepend it to sys.path inside the bridge) plus 4 env-var strips. No restructure, no fixture rewrite, no plan-level rearrangement.
- The fix is **forcing-functioned by the contract test itself** — if `_PROJECT_ROOT` were wrong, the test would `ModuleNotFoundError` and the executor would catch it immediately during `<verify>` execution. Not a silent failure mode.
- The `!r` choice is the textbook way to embed a path string literal — uses `repr()`, handles all path edge cases (spaces, embedded quotes, backslashes on Windows) automatically.
- Empirical verification was performed end-to-end. Not just a paper review.

### Risk Assessment

**Overall: LOW.**

Trajectory ∞ → 8 → 5 → 2 → 1 → 3 → 1 → **0** is monotonically decreasing past the cycle-5 restructure inflection (cycle 5 went up because the restructure introduced prose drift; cycle 7 found one real bug; cycle 8 confirms it's fixed). This is the textbook convergence signature: the restructure paid off, the post-restructure drift was caught and cleared, and the cycle-7 surgical fix introduced no regressions. Plans are ready to execute.

### Source-Grounding Pass

Verified symbols referenced in the cycle-7 fix:

| Symbol | Status | Evidence |
|---|---|---|
| `Path(__file__).resolve().parents[2]` | VERIFIED | Stdlib `pathlib.Path`; arithmetic confirmed empirically (REPL trace above) |
| `pytester.runpytest_subprocess` | VERIFIED | pytest core API; runs sub-pytest in tmpdir |
| `pytester.makeconftest` | VERIFIED | pytest core API; calls `Source(value).lines` which dedents |
| `_pytest._code.Source` dedent behavior | VERIFIED | `inspect.getsource(Source)` shows `.lines` returns dedented common-prefix-stripped lines |
| `result.assert_outcomes(skipped=1)` | VERIFIED | pytest core `_pytest.pytester.RunResult` API |
| `result.parseoutcomes()` | VERIFIED | same |
| `tests.conftest.vcr_config` | VERIFIED-AS-PRODUCED | 05-03 Task 1 produces this fixture in template/tests/conftest.py.jinja2 |
| `tests.llm.conftest._skip_when_no_cassette` | VERIFIED-AS-PRODUCED | 05-03 Task 2 produces this fixture in template/tests/llm/conftest.py.jinja2 |
| `tests.llm.conftest._reset_llm_cost` | VERIFIED-AS-PRODUCED | 05-03 Task 2 produces this autouse fixture |
| Env var names: `PYTEST_ADDOPTS`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD`, `COVERAGE_PROCESS_START`, `UV_CACHE_DIR` | VERIFIED | Standard pytest/coverage/uv env vars; canonical strip-list |

No MISSING or AMBIGUOUS symbols. No drift between cycle-7 commit and the bridge it modifies.

**NO ADDITIONAL HIGHS FOUND.** Per-vector reasoning above shows each of the six suspected drift vectors from the prompt was checked and cleared, plus the full §§1–8 REVIEW-CHECKLIST sweep produced no new patterns. Cycle 8 confirms convergence.

---

## Consensus Summary

### Agreed Strengths
- Single reviewer (Codex) — cycle 8 is the post-fix verification pass per rule 08, intentionally narrow.
- Cycle-7 fix is minimal, forcing-functioned, empirically verified end-to-end.
- Trajectory shows healthy convergence; restructure paid off.

### Agreed Concerns
- None at HIGH severity.
- One LOW polish item (trim "Cycle-7 HIGH #X fix:" meta-prefix from bridge comment during execute). Not a blocker.

### Divergent Views
- N/A (single-reviewer cycle).

---

## Current HIGH Concerns

None.

CYCLE_SUMMARY: current_high=0
