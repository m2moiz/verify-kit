---
phase: 5
reviewers: [codex]
reviewed_at: 2026-05-21T18:15:23Z
plans_reviewed:
  - 05-01-PLAN.md
  - 05-02-PLAN.md
  - 05-03-PLAN.md
  - 05-04-PLAN.md
  - 05-05-PLAN.md
---

# Cross-AI Plan Review — Phase 5

## Codex Review

## Summary

Overall risk: **HIGH**. The plans are thoughtful and cover the right Phase 5 surface area, but several load-bearing contracts do not line up with the current repo or with each other. The biggest blockers are: `has_llm=true` without `has_backend=true` has nowhere to render `.env.example`; `harness/llm.py` defines routing helpers but the decorator does not actually route calls through `claude-agent-sdk` vs LiteLLM; Promptfoo artifacts do not produce the `.verify/eval-results.json` that the skill documents; and the nightly “cost cap” only checks that a variable exists, not that estimated cost is under cap.

## Strengths

- Strong polarity discipline overall: most plans explicitly test `has_llm=false` and `llm_backend` branches.
- Good attention to previously caught drift patterns: `@register`, `CheckResult(status=...)`, `result.output`, `tokenx-core`, Jinja line-boundary risks, and cassette secret scrubbing are all called out.
- The phase decomposition is mostly sensible: dependency/path gates first, harness abstraction second, tests/eval artifacts next, integration/docs last.
- Security posture around VCR header scrubbing and Langfuse loopback binding is well specified.

## Concerns

- **HIGH — LLM `.env.example` only exists when `has_backend=true`.** Plan 05-01 modifies [template/{% if has_backend %}app{% endif %}/.env.example.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/.env.example.jinja2:1), but LLM-10 requires `has_llm=true` to write credential slots regardless of backend. In `has_llm=true, has_backend=false`, no LLM env artifact is planned.

- **HIGH — 05-02 does not actually implement D-03 routing.** It adds `_routing_path()` and `call_claude_code_sdk()`, but `@llm_call` still just awaits the wrapped function. The planned `/summarize` function directly uses `pydantic_ai.Agent.run()`, so `claude-agent-sdk` is never used as the call path. That misses D-01/D-03.

- **HIGH — Current pyproject has no `[dependency-groups]` table.** Plan 05-01 says to append dev deps under `[dependency-groups] dev = [...]`, but the actual template uses `[project.optional-dependencies] dev = [...]` at [template/pyproject.toml.jinja2](/Users/moiz/Documents/code/verify-kit/template/pyproject.toml.jinja2:59). Executor will either fail or introduce a second dependency convention.

- **HIGH — Promptfoo config is incomplete for `just eval`.** Plan 05-04 specifies provider + `tests`, but no `prompts` entry. Promptfoo generally needs prompts to evaluate. The research example includes a `prompts:` section; the plan action dropped it, so `just eval` is unlikely to run.

- **HIGH — Eval output path drift: `.verify/eval-results.json` vs `.promptfoo/`.** Plan 05-05 SKILL.md documents `.verify/eval-results.json`, but 05-04 uploads `./.promptfoo/` and never writes/copies `.verify/eval-results.json`. No current source produces that file.

- **HIGH — `fix_propose` signature drift.** Plan 05-05 tells agents to call `fix_propose '{"target": "eval", ...}'`, but current MCP tool is `def fix_propose() -> dict` with no args at [template/harness/mcp/tools.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/mcp/tools.py.jinja2:162).

- **HIGH — VCR tests will fail on a clean scaffold.** 05-03 sets `record_mode="none"` and adds `@pytest.mark.vcr` tests requiring cassettes, but no cassette is seeded before running generated tests. On first clean render, cassette-backed tests should fail loudly, which violates the scaffold “works on first run” goal.

- **HIGH — Nightly eval cost cap is not enforced.** The workflow only checks `EVAL_BUDGET_USD` is non-empty. It does not estimate or cap Promptfoo cost, so it does not satisfy “refusing to start if the cap would be exceeded.”

- **MEDIUM — `template/{% if has_llm %}harness/llm.py{% endif %}.jinja2` is the wrong path-gating shape.** `harness/` is universal, so this should be filename-level gating under `template/harness/`, not a conditional path containing `harness/llm.py`. The safer shape is `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2`.

- **MEDIUM — 05-02 depends on 05-01 but declares no dependency.** It creates gated files whose safety relies on 05-01 `_exclude` entries. That should be an explicit `depends_on: ["05-01"]`.

- **MEDIUM — `_CLEAN_ENV` is referenced but not present.** [tests/_helpers.py](/Users/moiz/Documents/code/verify-kit/tests/_helpers.py:72) exposes `render_scratch_project`, but no `_CLEAN_ENV`. 05-05 says to add it if absent, but `tests/_helpers.py` is not listed in `files_modified`.

- **MEDIUM — 05-02 TDD claims behavior tests but creates no tests.** The actual behavior tests are deferred to 05-03, while 05-02 verification is mostly grep-based. That is okay if intentional, but then mark 05-02 `tdd=false` or make it produce a focused unit test.

## Suggestions

- Add a root-level `template/.env.example.jinja2` or universal env file strategy for LLM-only projects. If backend also needs `app/.env.example`, avoid duplicating conflicting env docs.
- Redesign `harness/llm.py` so routing is an explicit callable API, e.g. `await call_llm(prompt, model=...)`, and make examples use it. The decorator alone cannot route arbitrary wrapped functions.
- Change 05-01 dev deps to append under `[project.optional-dependencies].dev`.
- Add `prompts:` to `promptfoo.config.yaml`, plus a starter `eval/prompts/*.txt` file, or make the config fully inline.
- Decide one eval results location. If the skill should read `.verify/eval-results.json`, make `just eval` write/copy Promptfoo JSON there.
- Either seed safe cassettes in the template or make cassette-backed tests skipped unless cassettes exist. Do not make first-run `pytest` depend on live recording.
- Replace the nightly cost check with a real preflight estimate or set Promptfoo’s native budget/cost controls if available. If unavailable, reword the requirement and plan honestly.
- Update 05-05 to either use current no-arg `fix_propose()` or add a separate plan that extends MCP/CLI fix APIs with the documented arguments.
- Add `tests/_helpers.py` to 05-05 `files_modified` if `_CLEAN_ENV` is required.

## Source-Grounding Pass

| Symbol / Path | Status | Evidence |
|---|---:|---|
| `has_llm`, `llm_backend` Copier prompts | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:144), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:167) |
| `_exclude` existing block | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:26) |
| `[project.optional-dependencies].dev` | VERIFIED | [template/pyproject.toml.jinja2](/Users/moiz/Documents/code/verify-kit/template/pyproject.toml.jinja2:59) |
| `[dependency-groups] dev` | MISSING | No matching table in current template pyproject |
| `tracer` export | VERIFIED | [template/harness/observability.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/observability.py.jinja2:53) |
| `_otel_enabled` block | VERIFIED | [template/harness/observability.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/observability.py.jinja2:34) |
| `log = structlog.get_logger("harness")` | VERIFIED | [template/harness/logging.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/logging.py.jinja2:120) |
| `get_trace_id`, `set_trace_id` | VERIFIED | [template/harness/trace_id.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/trace_id.py.jinja2:25), [template/harness/trace_id.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/trace_id.py.jinja2:30) |
| `@register` signature | VERIFIED | [template/harness/registry.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/registry.py.jinja2:19) |
| `CheckResult(status=...)` | VERIFIED | [template/harness/models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:61) |
| `CheckTier` values | VERIFIED | [template/harness/models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:22) |
| `harness/checks/__init__.py` registration site | VERIFIED | [template/harness/checks/__init__.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/checks/__init__.py.jinja2:11) |
| Existing `/healthz`, `/echo`, `/events/stream` | VERIFIED | [template/app/api.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:12), [api.py](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:18), [api.py](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:33) |
| `render_scratch_project` | VERIFIED | [tests/_helpers.py](/Users/moiz/Documents/code/verify-kit/tests/_helpers.py:72) |
| `_CLEAN_ENV` | MISSING | Not present in [tests/_helpers.py](/Users/moiz/Documents/code/verify-kit/tests/_helpers.py:1) |
| MCP `fix_propose()` | VERIFIED, no args | [template/harness/mcp/tools.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/mcp/tools.py.jinja2:162) |
| MCP `eval_run`, `eval_compare` stubs | VERIFIED | [template/harness/mcp/tools.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/mcp/tools.py.jinja2:206), [tools.py](/Users/moiz/Documents/code/verify-kit/template/harness/mcp/tools.py.jinja2:216) |
| CLI `verify --check` | VERIFIED | [template/harness/cli.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/cli.py.jinja2:163) |
| CLI `trace --last` | VERIFIED | [template/harness/cli.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/cli.py.jinja2:303) |
| `.verify/eval-results.json` producer | MISSING | No source match found |
| `harness/llm.py`, `llm_call`, `cost_budget` | NEW / not source-verifiable | Planned artifact, not currently present |
| `claude_agent_sdk.query`, `pydantic_ai.Agent`, Promptfoo schemas | AMBIGUOUS | External APIs; not verifiable from repo source alone |

I also attempted the required beads session close export, but `bd export` failed because the local Dolt server is unreachable under the current sandbox: `dial tcp 127.0.0.1:3307: connect: operation not permitted`.

---

## Consensus Summary

Single-reviewer (Codex) cycle. Findings below stand as the convergence input until additional reviewers are invoked.

### Agreed Strengths
- Polarity discipline (has_llm / llm_backend branching) is consistently planned.
- REVIEW-CHECKLIST patterns (`@register`, `CheckResult(status=...)`, `result.output`, `tokenx-core`, Jinja line-boundary risks, cassette secret scrubbing) are explicitly hunted for.
- Phase decomposition follows dependency order: dependency/path gates → harness abstraction → tests/eval → integration/docs.
- Security posture around VCR header scrubbing and Langfuse loopback binding is well specified.

### Agreed Concerns (HIGH)
1. `has_llm=true, has_backend=false` has no destination for the LLM `.env.example` (05-01 only edits the backend-gated env file).
2. 05-02 does not actually route through `claude-agent-sdk` vs LiteLLM; `@llm_call` is a passthrough and `/summarize` calls `pydantic_ai.Agent.run()` directly — D-01/D-03 unmet.
3. 05-01 appends dev deps under `[dependency-groups]`, but template uses `[project.optional-dependencies].dev` — wrong table.
4. Promptfoo config lacks a `prompts:` entry — `just eval` likely will not run.
5. Eval output path drift: SKILL.md references `.verify/eval-results.json`, but 05-04 only uploads `./.promptfoo/`. No producer of `.verify/eval-results.json`.
6. `fix_propose` signature drift: 05-05 calls it with args; current MCP tool is no-arg.
7. VCR cassette-backed tests use `record_mode="none"` without seeded cassettes — first clean render will fail.
8. Nightly eval "cost cap" only checks env var existence; does not estimate or enforce a cap.

### Agreed Concerns (MEDIUM)
- `template/{% if has_llm %}harness/llm.py{% endif %}.jinja2` path-gating shape is wrong; should be filename-level gating under `template/harness/`.
- 05-02 lacks explicit `depends_on: ["05-01"]`.
- `_CLEAN_ENV` referenced in 05-05 but not present in `tests/_helpers.py`; `tests/_helpers.py` not in `files_modified`.
- 05-02 marked TDD but produces no tests (deferred to 05-03).

### Divergent Views
N/A — single reviewer this cycle.
