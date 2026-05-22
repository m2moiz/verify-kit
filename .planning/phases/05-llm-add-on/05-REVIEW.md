---
phase: 05-llm-add-on
reviewed: 2026-05-22T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - copier.yml
  - template/pyproject.toml.jinja2
  - template/justfile.jinja2
  - template/README.md.jinja2
  - template/harness/observability.py.jinja2
  - template/harness/checks/__init__.py.jinja2
  - template/harness/{% if has_llm %}llm.py{% endif %}.jinja2
  - template/harness/checks/{% if has_llm %}eval.py{% endif %}.jinja2
  - template/{% if has_backend %}app{% endif %}/.env.example.jinja2
  - template/{% if has_backend %}app{% endif %}/api.py.jinja2
  - template/{% if has_llm and not has_backend %}.env.example{% endif %}.jinja2
  - template/{% if has_llm %}docker-compose.langfuse.yml{% endif %}.jinja2
  - template/{% if has_llm %}eval{% endif %}/promptfoo.config.yaml.jinja2
  - template/{% if has_llm %}eval{% endif %}/datasets/golden.jsonl.jinja2
  - template/{% if has_llm %}eval{% endif %}/prompts/summarize.txt.jinja2
  - template/.github/workflows/{% if has_llm %}nightly-eval.yml{% endif %}.jinja2
  - template/{% if has_claude_code %}.claude{% endif %}/skills/verify-kit-eval/SKILL.md.jinja2
  - template/tests/conftest.py.jinja2
  - template/tests/cassettes/{% if has_llm %}.gitkeep{% endif %}
  - template/tests/llm/{% if has_llm %}conftest.py{% endif %}.jinja2
  - template/tests/llm/{% if has_llm %}test_skip_fixture_contract.py{% endif %}.jinja2
  - template/tests/llm/{% if has_llm %}test_llm_call.py{% endif %}.jinja2
  - template/tests/llm/{% if has_llm %}test_vcr_scrub.py{% endif %}.jinja2
  - template/tests/llm/{% if has_llm %}test_smoke.py{% endif %}.jinja2
  - template/tests/llm/{% if has_llm %}test_autoevals.py{% endif %}.jinja2
  - template/tests/llm/cassettes/{% if has_llm %}.gitkeep{% endif %}
  - tests/_helpers.py
  - tests/test_phase05_polarity.py
findings:
  critical: 0
  warning: 5
  info: 5
  total: 10
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-05-22
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Phase 5 ships a coherent, defensible LLM add-on. The two-guard polarity gating, decorator-ordering rule, VCR scrub-before-record, OUTER/INNER docstring forcing test, and D-22 tokenx exclusion are all properly upheld by polarity tests at `tests/test_phase05_polarity.py`. The threat register is verified and dependency pins (pydantic-ai-slim, fastmcp 3.3, otel-httpx 0.62b1) align with the Phase 2 OTel SDK 1.41.1 pin.

No Critical defects were found. Five Warnings flag REVIEW-CHECKLIST §6 meta-comment leaks into rendered consumer projects, a dead helper, a weakened drift-guard, a double-counted-cost subtlety in the litellm adapter, and Langfuse self-host defaults that fall back to literal placeholder secrets rather than refusing to start. Five Info items round out style and brittleness observations.

The most important issue is **WR-01** (REVIEW-CHECKLIST §6 violations) — three Phase-5-authored template files render reviewer-meta language ("HIGH #7", "cycle-3..cycle-6 fix", "cycle-3 bug") into the consumer's scaffold tree. Fix is mechanical (strip these comments) but the pattern is exactly what §6 was added to catch.

## Warnings

### WR-01: Reviewer-meta comments leak into consumer-rendered files (REVIEW-CHECKLIST §6)

**Files:**
- `template/tests/llm/{% if has_llm %}conftest.py{% endif %}.jinja2:11` — `"review HIGH #7"`
- `template/tests/llm/{% if has_llm %}test_skip_fixture_contract.py{% endif %}.jinja2:3` — `"forcing-functions the cycle-3..cycle-6 fix"`
- `template/tests/llm/{% if has_llm %}test_skip_fixture_contract.py{% endif %}.jinja2:72` — `"the cycle-3 bug"`

**Issue:** REVIEW-CHECKLIST §6 explicitly prohibits "cycle-N sweep:", "per Codex HIGH #X", and "the cycle-N bug" phrasings inside `.jinja2` templates because they render verbatim into the consumer's scaffolded project. A consumer who reads `tests/llm/conftest.py` is now confronted with verify-kit's internal review history ("Phase 5 review HIGH #7"), which (a) confuses them and (b) makes the template look like it was rushed. Pattern caught by §6 explicitly. Phase 4 had similar offenders already in-tree; Phase 5 adds three new ones in its own files.

**Fix:** Strip the meta-language. Authored rationale belongs in `PLAN.md` / `SUMMARY.md` / commit body, not in template source.

```python
# conftest.py.jinja2 — current
#    ``_skip_when_no_cassette`` — first-run-clean discipline (Phase 5
#    review HIGH #7). For any test marked ``@pytest.mark.vcr``: ...
# Replace with:
#    ``_skip_when_no_cassette`` — first-run-clean discipline. For any
#    test marked ``@pytest.mark.vcr``: ...
```

```python
# test_skip_fixture_contract.py.jinja2 — current
"""Contract test for the _skip_when_no_cassette record-mode gate.

This test forcing-functions the cycle-3..cycle-6 fix: the autouse skip
fixture in tests/llm/conftest.py must skip in default mode AND must NOT
skip under ``--record-mode=once`` ...

# Replace with:
"""Contract test for the _skip_when_no_cassette record-mode gate.

The autouse skip fixture in tests/llm/conftest.py must skip in default mode
AND must NOT skip under ``--record-mode=once`` ...
```

And remove the `(the cycle-3 bug)` parenthetical at line 72 — just keep the assertion message.

### WR-02: `_run` helper is dead code with broken walrus-operator logic

**File:** `template/tests/llm/{% if has_llm %}test_llm_call.py{% endif %}.jinja2:66-70`

**Issue:** The `_run` helper is never referenced (all tests use `_ar`). Its body:

```python
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if (
        loop := asyncio.new_event_loop()
    ) is None else loop.run_until_complete(coro)
```

is also nonsensical: `asyncio.new_event_loop()` never returns `None`, so the ternary always picks the False branch — meaning the `loop` walrus binding never feeds the actual call, and the `asyncio.get_event_loop()` branch is dead within a function whose entire body is itself dead. This is the kind of code that breaks loudly when someone tries to use it later.

**Fix:** Delete the helper.

```python
# Delete lines 66-70 entirely. _ar (lines 73-79) is the live, correct helper.
```

### WR-03: `test_pydantic_ai_uses_output_not_data` has a silent escape hatch that nullifies the drift-guard

**File:** `template/tests/llm/{% if has_llm %}test_smoke.py{% endif %}.jinja2:38-58`

**Issue:** The Pitfall 4 forcing function attempts three different introspections of `AgentRunResult` (`model_fields`, `__dataclass_fields__`, `__annotations__`). If all three fail (e.g., pydantic-ai >=2 changes the surface), the `else` branch falls back to `assert pydantic_ai is not None` — a no-op since import succeeded. The test would therefore pass under any future pydantic-ai refactor that renames the field back to `data` *and* changes the introspection surface. The drift-guard is supposed to break loudly when the field name changes; under this fallback it goes silent.

**Fix:** Fail-loud on the fallback branch — drop the silent escape hatch:

```python
    else:
        pytest.fail(
            "AgentRunResult exposes none of model_fields/__dataclass_fields__/"
            "__annotations__ — introspection surface changed; update this drift-guard"
        )
```

The complementary polarity test `test_no_result_data_anywhere` at `tests/test_phase05_polarity.py:189-198` greps `.py` files for `result.data` — that test still works, but it covers the *template* side, not the *runtime API* side. Both halves need to fail loudly to catch Pitfall 4 future regressions.

### WR-04: `call_via_litellm` double-tokenizes when computing cost

**File:** `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2:236-248`

**Issue:** `call_via_litellm` already receives `usage.prompt_tokens` and `usage.completion_tokens` from the litellm response (lines 219-233), but the cost calculation re-runs tokencost on the raw `prompt` and `content` strings via `calculate_prompt_cost(prompt, requested_model)` / `calculate_completion_cost(content, requested_model)`. tokencost's per-string variants tokenize the input again with their own (potentially different) tokenizer. The reported `cost_usd` therefore reflects tokencost's tokenization, not the provider's billed tokens, and can drift from actual cost. litellm exposes `litellm.completion_cost(completion_response=response)` (already callable per `test_smoke.py:80`) which uses the provider-reported usage block — that path is what `verify_kit.cost_usd` should report.

**Fix:** Use `litellm.completion_cost(completion_response=response)` and fall back to 0.0 only when that raises:

```python
cost_usd = 0.0
try:
    from litellm import completion_cost
    cost_usd = float(completion_cost(completion_response=response) or 0.0)
except Exception:
    # litellm may not have pricing for every model — default to 0.0
    cost_usd = 0.0
```

This also drops the `tokencost` import in this hot path. `tokencost` still belongs in pyproject because the nightly-eval pre-flight may use it (and D-22 retained it as the cost-computation primitive), but it should not be the runtime cost source.

### WR-05: Langfuse self-host docker-compose ships functional placeholder secrets

**File:** `template/{% if has_llm %}docker-compose.langfuse.yml{% endif %}.jinja2:34-36, 59-60`

**Issue:** `SALT`, `ENCRYPTION_KEY`, and `NEXTAUTH_SECRET` default to the literal strings `changeme-please-set-LANGFUSE_SALT` etc. If the operator brings up the stack without setting the env vars, Langfuse starts cleanly with these as actual cryptographic material — sessions get signed with `changeme-please-set-LANGFUSE_NEXTAUTH_SECRET`, and `ENCRYPTION_KEY` (which Langfuse uses to encrypt API keys at rest in postgres) becomes a string that is publicly documented in this template. Threat T-05-12 closes on loopback binding, but secret hygiene on the same component is left to operator vigilance. The placeholder-default pattern is exactly the "silent fallback" that `03-agent-patterns.md` warns against.

**Fix:** Drop the `:-changeme-...` fallback so docker-compose refuses to start when the env var is unset:

```yaml
SALT: ${LANGFUSE_SALT:?LANGFUSE_SALT must be set; generate with: openssl rand -base64 32}
ENCRYPTION_KEY: ${LANGFUSE_ENCRYPTION_KEY:?LANGFUSE_ENCRYPTION_KEY must be set; generate with: openssl rand -hex 32}
NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:?LANGFUSE_NEXTAUTH_SECRET must be set; generate with: openssl rand -base64 32}
```

`${VAR:?msg}` causes docker compose to exit with the message printed, so the operator sees a clear failure rather than a silently-insecure stack. Also append a `.env.example` snippet (or README section) showing the `openssl rand` recipes.

## Info

### IN-01: `_CLEAN_ENV` imported into `test_phase05_polarity.py` but never used

**File:** `tests/test_phase05_polarity.py:27`

**Issue:** `from tests._helpers import _CLEAN_ENV, render_scratch_project  # noqa: F401` imports `_CLEAN_ENV` defensively, but the file never spawns a subprocess so the symbol is dead. The `# noqa: F401` then masks the unused-import lint as intentional, which is misleading.

**Fix:** Drop `_CLEAN_ENV` from the import; remove the `# noqa: F401`. Keep the docstring reference at line 15 (it's still accurate guidance for future authors).

```python
from tests._helpers import render_scratch_project
```

### IN-02: `tests/_helpers.install_scratch_harness` does NOT strip outer-process env vars

**File:** `tests/_helpers.py:108-115`

**Issue:** `install_scratch_harness` runs `uv pip install -e .` with `env = {**os.environ, "VIRTUAL_ENV": str(venv)}`. This sets `VIRTUAL_ENV` correctly but does not strip `UV_PROJECT_ENVIRONMENT`, `PYTHONPATH`, `PYTHONHOME`, etc. REVIEW-CHECKLIST §8 was added precisely for this shape. Phase 5 already defines `_CLEAN_ENV` in the same file (lines 133-145) but `install_scratch_harness` does not use it. Pre-dates Phase 5 so not a regression; flagging for tracking.

**Fix:** Reuse `_CLEAN_ENV` and overlay `VIRTUAL_ENV`:

```python
env = {**_CLEAN_ENV, "VIRTUAL_ENV": str(venv)}
```

### IN-03: `_ar` event-loop helper uses deprecated manual lifecycle

**File:** `template/tests/llm/{% if has_llm %}test_llm_call.py{% endif %}.jinja2:73-79`

**Issue:** `asyncio.new_event_loop()` + manual `.close()` is the pre-3.7 idiom. Python 3.13 (template target) prefers `asyncio.run(coro)` which handles loop lifecycle and warns on certain misuse patterns. Also `pytest-asyncio` is already in dev deps (from Phase 4); switching tests to `async def test_...` + `@pytest.mark.asyncio` would drop the helper entirely.

**Fix (optional refactor):**

```python
def _ar(coro):
    return asyncio.run(coro)
```

Or migrate the four tests that use it to `pytest-asyncio` style.

### IN-04: Pre-flight cost estimator shell-quotes a Python f-string with shell variable interpolation

**File:** `template/.github/workflows/{% if has_llm %}nightly-eval.yml{% endif %}.jinja2:44, 47`

**Issue:** `python -c "print(f'{${rows} * (1000 * 1e-6 + 500 * 5e-6):.4f}')"` interpolates `${rows}` directly into the Python source. `rows` is `grep -c .` output (a non-negative integer) so injection is not feasible, but the pattern is brittle — any future change that pulls a value from a less-trusted source (an env var, an issue label, etc.) will silently inherit the injection vector. Same shape on line 47 for `$estimated_usd` / `$EVAL_BUDGET_USD`.

**Fix:** Pass values via env, not interpolation:

```yaml
estimated_usd=$(rows="$rows" python -c "import os; r = int(os.environ['rows']); print(f'{r * 0.0035:.4f}')")
over_budget=$(est="$estimated_usd" bud="$EVAL_BUDGET_USD" python -c "import os; print('yes' if float(os.environ['est']) > float(os.environ['bud']) else 'no')")
```

### IN-05: `@llm_call` decorator wrapper does not preserve full function metadata

**File:** `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2:356-359, 395-398`

**Issue:** The `_inner` wrapper sets only `__name__`, `__doc__`, and `__wrapped__`. Missing: `__qualname__`, `__module__`, `__annotations__`, and the function signature (`inspect.signature` returns `(*args, **kwargs)`). FastAPI relies on signature introspection to bind request bodies — `_summarize` is called from inside `summarize_route` so it does not directly route, but if a future consumer applies `@llm_call` to a route handler, FastAPI will misbind it. `functools.wraps` does all of this.

**Fix:**

```python
import functools

def _decorator(fn):
    @functools.wraps(fn)
    async def _inner(*args, **kwargs):
        ...
    return _inner
```

Apply identically in `cost_budget`. This is the standard idiom; the manual three-attribute copy is doing a worse job than `functools.wraps` for no reason.

---

## Structural Findings (fallow)

No `<structural_findings>` block was provided in the review prompt; nothing to merge.

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
