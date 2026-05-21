---
phase: 5
cycle: 2
reviewers: [codex]
reviewed_at: 2026-05-21T18:40:42Z
plans_reviewed:
  - 05-01-PLAN.md
  - 05-02-PLAN.md
  - 05-03-PLAN.md
  - 05-04-PLAN.md
  - 05-05-PLAN.md
---

# Cross-AI Plan Review — Phase 5 (Cycle 2)

This cycle re-reviews commit `bb201fd` which addressed the 8 HIGH concerns from Cycle 1.

## Codex Review

**Summary**

Overall risk remains **HIGH**. Cycle 2 resolves several prior contract mismatches on paper, especially `tokenx-core`, `promptfoo prompts:`, `.verify/eval-results.json`, and no-arg `fix_propose()`. But the current plan still has execution blockers and new contract drift: it references a missing `.env.example` source file, uses unsafe Jinja path shapes for `tests/llm`, omits primary `_exclude` coverage for the new root `.env.example`, and under-specifies the required LLM span attributes.

**Strengths**

- Prior HIGHs #3, #4, #5, and #6 are substantially addressed.
- 05-02 now introduces a real `call_llm()` routing entry point and makes `/summarize` consume it.
- 05-04 now has a prompt producer file and a consistent `.verify/eval-results.json` path.
- 05-05 adds polarity tests intended to force the prior HIGHs, which is the right direction.

**Concerns**

- **HIGH — 05-01 still references a missing app `.env.example` template.**  
  05-01 Task 4 says to read and append `template/{% if has_backend %}app{% endif %}/.env.example.jinja2`, but `rg --files template | rg 'env|\\.env'` shows no such file exists. The plan says “append, do not rewrite,” so execution will fail or force the executor to invent a new file outside the plan. Source: current template has no `.env.example`; only `template/{% if has_db %}alembic{% endif %}/env.py.jinja2` exists.

- **HIGH — 05-03 uses an unsafe Jinja path shape for `tests/llm`.**  
  Planned paths like `template/tests/{% if has_llm %}llm{% endif %}/test_llm_call.py.jinja2` put the conditional on a directory segment under universal `tests/`. Existing Phase 4 safe pattern uses concrete parent dirs plus filename-level gates, e.g. `template/tests/backend/{% if has_backend %}test_app.py{% endif %}.jinja2`. If `has_llm=false`, the planned shape risks rendering files into `tests/` rather than `tests/llm/`, and `_exclude: tests/llm/**` would not catch that. This violates the two-guard path contract.

- **HIGH — root `.env.example` lacks a primary `_exclude` gate.**  
  05-01 adds `template/{% if has_llm and not has_backend %}.env.example{% endif %}.jinja2`, but Task 2 does not add a matching `_exclude` entry for `.env.example`. This is a new root-level LLM artifact and should be covered by the primary gate in [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:26), not only by a conditional filename.

- **HIGH — 05-02 does not meet the stated `@llm_call` span contract.**  
  The phase success criteria require prompt/response/cost/latency/retry-count and `gen_ai.*` attributes. 05-02 only requires `gen_ai.operation.name`, `verify_kit.cost_usd`, `verify_kit.latency_ms`, and `verify_kit.routing_path`. It omits at least `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, and `verify_kit.retry_count`.

- **HIGH — pydantic-ai is installed but no longer actually used as the primary framework.**  
  05-02’s production path uses raw LiteLLM, and 05-05 explicitly forbids `/summarize` from importing `pydantic_ai.Agent`. That addresses routing, but it conflicts with LLM-02’s “pydantic-ai as primary agent/typed-call framework” requirement. Current plans mostly prove pydantic-ai imports, not that verify-kit scaffolds around it.

- **MEDIUM — cassette skip/recording behavior is underspecified and may fight `refresh-cassettes`.**  
  05-03 sets `vcr_config["record_mode"] = "none"` while 05-04 expects `pytest --record-mode=once` to re-record. That may work depending on pytest-recording precedence, but the plan should explicitly verify that CLI `--record-mode=once` overrides the fixture. Otherwise `just refresh-cassettes` could still skip or refuse recording.

- **MEDIUM — `test_instructor_patch` may depend on an unpinned `anthropic` package.**  
  05-03 plans `instructor.from_anthropic(anthropic.Anthropic())`, but `anthropic` is not explicitly added in 05-01. It may arrive transitively, but this is not grounded in the repo or plan.

- **MEDIUM — README migration verification suggests a skipped check.**  
  05-05 says verify migration with `just verify --check=eval`, but 05-03’s eval check intentionally returns `status="skip"` and only points to `just eval`. That command will not prove a Langfuse trace or eval run.

**Prior HIGH Status**

| Prior HIGH | Status | Evidence |
|---|---:|---|
| LLM `.env.example` missing for `has_llm=true, has_backend=false` | PARTIAL | 05-01 Task 5 adds root `.env.example`, but Task 4 references a missing app env file and root env lacks `_exclude`. |
| 05-02 did not implement D-03 routing | FULLY | 05-02 Task 2 adds `call_llm()` dispatching via `_routing_path()`; 05-05 Task 1 requires `/summarize` to call it. |
| Wrong `[dependency-groups]` table | FULLY | 05-01 Task 3 explicitly uses `[project.optional-dependencies].dev` and forbids `[dependency-groups]`. |
| Promptfoo config lacked `prompts:` | FULLY | 05-04 Task 1 adds `prompts:` and `eval/prompts/summarize.txt`. |
| Eval output path drift | FULLY | 05-04 Tasks 2–3 and 05-05 Task 2 align on `.verify/eval-results.json`. |
| `fix_propose` signature drift | FULLY | 05-05 Task 2 documents no-arg `fix_propose()` matching [tools.py](/Users/moiz/Documents/code/verify-kit/template/harness/mcp/tools.py.jinja2:162). |
| VCR tests fail on clean scaffold | PARTIAL | 05-03 adds skip-when-no-cassette, but path-gating and record-mode precedence remain risky. |
| Nightly cost cap only checked env var | PARTIAL | 05-04 adds an estimator, but it is static/coarse and may not reflect actual prompt/model costs. |

**Source-Grounding Pass**

| Symbol / Path | Status | Evidence |
|---|---:|---|
| `has_llm`, `llm_backend` | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:144), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:167) |
| `_exclude` block | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:26) |
| `[project.optional-dependencies].dev` | VERIFIED | [pyproject](/Users/moiz/Documents/code/verify-kit/template/pyproject.toml.jinja2:59) |
| `[dependency-groups]` | MISSING | Not present; 05-01 correctly avoids it. |
| `template/{% if has_backend %}app{% endif %}/.env.example.jinja2` | MISSING | No `.env.example` template exists under `template/`. |
| Existing `app/api.py.jinja2` route structure | VERIFIED | [api.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:1) |
| `/healthz`, `/echo`, `/events/stream` | VERIFIED | [api.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:12) |
| `tracer`, `_otel_enabled` | VERIFIED | [observability.py](/Users/moiz/Documents/code/verify-kit/template/harness/observability.py.jinja2:26) |
| `log` | VERIFIED | [logging.py](/Users/moiz/Documents/code/verify-kit/template/harness/logging.py.jinja2:120) |
| `get_trace_id`, `set_trace_id` | VERIFIED | [trace_id.py](/Users/moiz/Documents/code/verify-kit/template/harness/trace_id.py.jinja2:25) |
| `@register` | VERIFIED | [registry.py](/Users/moiz/Documents/code/verify-kit/template/harness/registry.py.jinja2:19) |
| `CheckResult(status=...)` | VERIFIED | [models.py](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:61) |
| `CheckTier` values | VERIFIED | [models.py](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:22) |
| `harness/checks/__init__.py` registration side-effect | VERIFIED | [checks __init__](/Users/moiz/Documents/code/verify-kit/template/harness/checks/__init__.py.jinja2:1) |
| CLI `verify --check` | VERIFIED | [cli.py](/Users/moiz/Documents/code/verify-kit/template/harness/cli.py.jinja2:163) |
| MCP `fix_propose()` no args | VERIFIED | [tools.py](/Users/moiz/Documents/code/verify-kit/template/harness/mcp/tools.py.jinja2:162) |
| `_CLEAN_ENV` | MISSING | Not present in [tests/_helpers.py](/Users/moiz/Documents/code/verify-kit/tests/_helpers.py:1); 05-05 plans to add it. |
| `call_llm`, `llm_call`, `cost_budget` | PLANNED | Produced by 05-02. |
| Promptfoo `-o output.json` | VERIFIED EXTERNAL | Context7 Promptfoo docs confirm `promptfoo eval -o results.json` / `--output results.json`. |

**Suggestions**

- Add a 05-01 task to create the missing backend `.env.example` file, or change Task 4 from “append existing” to “create if absent” with source-grounded acceptance criteria.
- Change `tests/llm` paths to the proven Phase 4 shape: `template/tests/llm/{% if has_llm %}test_llm_call.py{% endif %}.jinja2`.
- Add `_exclude` entries for the root `.env.example` artifact and any gated `.gitkeep` that can otherwise collapse into `.jinja2`.
- Update 05-02 span contract to set model, token usage, retry count, and response metadata from adapter results.
- Either actually use pydantic-ai in the standard call path, or revise LLM-02/phase success criteria to say pydantic-ai is shipped as an optional ergonomic layer rather than primary.

**Risk Assessment**

**HIGH.** The replan is materially better than Cycle 1, but it still has execution blockers and path-gating hazards that can leak files into wrong scaffold cells. The missing `.env.example` source and unsafe `tests/{% if has_llm %}llm{% endif %}` shape should be fixed before execution. Also, the LLM span contract needs tightening or the phase will pass structural tests while missing key observability requirements.

I attempted the required beads close commands, but both failed because the local Dolt server is unreachable in this sandbox: `dial tcp 127.0.0.1:3307: connect: operation not permitted`.

---

## Consensus Summary

Single reviewer (Codex). Cycle 2 confirms 4 of 8 prior HIGHs are FULLY resolved (D-03 routing, `[project.optional-dependencies]`, promptfoo `prompts:`, eval output path, `fix_propose` signature). Two are PARTIALLY resolved (LLM `.env.example`, VCR cassette skip), and the replan introduced fresh HIGHs.

### Agreed Concerns (single reviewer)
- 05-01 references a missing `.env.example.jinja2` source file (execution blocker).
- 05-03 uses unsafe Jinja directory-segment gating for `tests/llm/` (violates Phase 4 two-guard pattern).
- Root `.env.example` lacks a matching `_exclude` gate.
- 05-02 LLM span contract is under-specified vs phase success criteria.
- pydantic-ai is installed but not actually used as the primary framework path, conflicting with LLM-02.

### Divergent Views
N/A (single reviewer).
