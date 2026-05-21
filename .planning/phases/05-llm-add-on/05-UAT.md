---
status: passed
phase: 05-llm-add-on
source:
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
  - 05-04-SUMMARY.md
  - 05-05-SUMMARY.md
scope: automated-only (per user request 2026-05-22 — skips human-eye reads of README/SKILL.md; skips API-gated tests)
started: 2026-05-22T00:00:00Z
updated: 2026-05-22T01:00:00Z
completed: 2026-05-22T01:00:00Z
verdict: PASSED (with 2 dep-pin fixes landed during UAT)
---

## Tests

### 1. Cold-start smoke render (has_llm=true, has_backend=true)
expected: copier render completes; uv sync --extra dev exits 0; harness/llm.py + eval/ + tests/llm/ + nightly-eval.yml present
result: **pass** (after fixes)
notes: |
  Initial uv sync FAILED with two transitive-dep conflicts:
    (a) pydantic-ai meta-pkg pulls [mistral] extra → mistralai → otel-semantic-conventions 0.60b1,<0.61 conflicts with Phase 2 otel-sdk==1.41.1 → 0.62b1
    (b) pydantic-ai-slim 1.100 transitively requires fastmcp>=3.3, but Phase 3 had pinned fastmcp>=2.0,<3.0
  Both fixed in commit daba26f. Re-render + uv sync now succeeds; all 11 LLM packages install cleanly (pydantic-ai-slim 1.100, fastmcp 3.3.1, litellm 1.85.1, tokencost 0.1.26, autoevals 0.2.0, langfuse 4.6.1, traceloop-sdk 0.60.0, opentelemetry-instrumentation-httpx 0.62b1, vcrpy 8.1.1, pytest-recording 0.13.4, NO tokenx).

### 2. 12-cell polarity matrix
expected: tests/test_phase05_polarity.py runs to completion; all 16 forcing-function tests pass across the (has_backend, has_llm, llm_backend) parametrize axes
result: **pass**
notes: |
  69 tests passed (16 forcing-functions × parametrize expansion), 0 failed, 70 warnings, 6:25 runtime.
  Every forcing-function tag fired clean:
  - test_llm_artifacts_polarity / _absent_when_no_llm (presence matrix)
  - test_docker_compose_langfuse_only_in_self_host_cell (value-conditional gate)
  - test_summarize_endpoint_polarity / _absent_when_no_llm (Phase 4 × Phase 5 composition)
  - test_no_empty_segment_leaks (REVIEW-CHECKLIST §5)
  - test_pyproject_has_no_tokenx (D-22 regression guard — NO tokenx in any form)
  - test_pyproject_uses_optional_dependencies_not_dependency_groups (REVIEW-CHECKLIST §4)
  - test_no_result_data_anywhere (Pitfall 4 — pydantic-ai v1.x uses .output)
  - test_summarize_uses_call_llm_not_pydantic_ai_directly (D-03 routing wiring, HIGH #2)
  - test_eval_results_path_consistency (HIGH #5 — .verify/eval-results.json everywhere)
  - test_promptfoo_config_has_prompts_section (HIGH #4)
  - test_fix_propose_skill_uses_noarg_form (HIGH #6)
  - test_env_destination_per_cell (HIGH #1)
  - test_golden_jsonl_rows_parse (D-19 dataset sanity)

### 3. Negative polarity (has_llm=false)
expected: scratch render with has_llm=false produces ZERO LLM artifacts
result: **pass** (subsumed by Test 2 — every test_*_when_no_llm and test_*_absent_when_no_llm + the (has_llm=false, *) parametrize cells all passed)

### 4. .env destination polarity (4 cells)
expected: for each (has_llm × has_backend) cell, exactly the right .env.example exists at the right path
result: **pass** (subsumed by Test 2 — test_env_destination_per_cell_llm_true × 3 backend values + test_env_destination_per_cell_llm_false × 2 backend values, all 5 cells PASS)

## Summary

total: 4
passed: 4
issues: 0 (2 transitive-dep conflicts fixed inline during UAT)
pending: 0
skipped: 0

## Gaps

[none — all UAT tests pass after the two dep-pin fixes landed in daba26f]

## Issues fixed during UAT

These were transitive-dep conflicts the planner/research could not have caught (they only manifest under full `uv sync` resolution):

1. **pydantic-ai meta-pkg [mistral] transitive vs Phase 2 otel-sdk pin.** Swap to `pydantic-ai-slim[anthropic,openai]` to avoid pulling the [mistral] extra. Commit `daba26f`.
2. **fastmcp pin Phase 3 vs Phase 5.** Phase 3 had speculatively pinned `>=2.0,<3.0`; pydantic-ai-slim 1.100 transitively requires `>=3.3`. Bumped to `>=3.3,<4`. Phase 3 plans flagged to validate against 3.x APIs when executed (filed as beads `verify-kit-fastmcp-3x`). Commit `daba26f`.

## What's next

Verification PASSED. Remaining gates per project config:
- `/gsd:secure-phase 5` — security threat-model verification (security_enforcement is true)
- `/gsd:code-review 5` — source review of changed files (code_review is true)

After both pass, Phase 5 can be marked complete.
