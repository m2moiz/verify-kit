# Phase 5: LLM Add-on - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

When a consumer answers `has_llm=true` to the Copier prompt, the scaffolded project ships with a complete, opinionated LLM stack: pydantic-ai + instructor + litellm + tokencost + tokenx + autoevals + vcrpy + pytest-recording + opentelemetry-instrumentation-httpx, `@llm_call` and `@cost_budget` decorators emitting OTel `gen_ai.*` spans, Langfuse Cloud / self-host / none backend wiring, Promptfoo eval gate via `just eval`, and a weekly cost-capped nightly-eval CI workflow. `has_llm=false` produces zero LLM artifacts and zero new dependencies (per polarity contract from Phase 4 plan 04-01 §3).

**In scope:** LLM-01 through LLM-12, plus CI-05 (`nightly-eval.yml`). 13 requirements total.
**Out of scope:** Web/audio/game add-ons (v0.2). Multi-tenant key management. Streaming response decorator (single-call only in v0.1; `pydantic-ai` already supports streaming for users who need it manually).
</domain>

<decisions>
## Implementation Decisions

### Default LLM provider + authentication path

- **D-01:** Default local-dev path is **`claude-agent-sdk`** (PyPI 0.2.83, released 2026-05-20). Routes `@llm_call` through Claude Code's existing OAuth session — uses the operator's Claude Max subscription quota, no API key required. Eliminates per-machine API key purchase for development.
- **D-02:** Production fallback is **`ANTHROPIC_API_KEY`** via litellm/pydantic-ai standard path. Deployed consumers (no Claude Code installed, no OAuth session) set the API key env var as usual. `.env.example` ships `ANTHROPIC_API_KEY=` as the canonical credential slot.
- **D-03:** Adapter routing logic in `harness/llm.py`: if `USE_CLAUDE_CODE_SDK=1` env var is set OR `ANTHROPIC_API_KEY` is unset AND `claude-agent-sdk` is importable, route through `claude_agent_sdk.query()`. Otherwise, use litellm with `ANTHROPIC_API_KEY`. Both paths emit the same OTel `gen_ai.*` span shape so downstream observability is identical.
- **D-04:** README (LLM-12 doc target) covers both paths explicitly with a "Personal setup vs. consumer setup" section.

### Default observability backend

- **D-05:** Default `llm_backend` Copier prompt value is **`langfuse-cloud`**. Free tier (50k events/month at `cloud.langfuse.com`) is effectively unlimited at solo-dev volume — 500+ LLM calls/day every day to even approach the cap.
- **D-06:** Solo-dev credential-sharing pattern is **shell env vars in `~/.zshrc`** (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`). One sign-up at cloud.langfuse.com → one paste into shell profile → every verify-kit-scaffolded project picks them up automatically without touching `.env`. README LLM-12 documents this pattern explicitly.
- **D-07:** Self-host alternative ships as `docker-compose.langfuse.yml` (5 containers: langfuse-web + langfuse-worker + postgres + clickhouse + redis, ~900 MB RAM). Documented as the privacy / no-third-party path. Operator's hardware (M2 base, 16-24 GB RAM) is comfortable for self-host but cloud remains the default per D-05.
- **D-08:** `llm_backend=none` is the "no third-party at all" option. Spans go to Jaeger (already shipped by Phase 4 when `has_backend=true`) or stdout (when `has_backend=false`). Documented as the minimal-dependency option.

### Nightly-eval CI

- **D-09:** Schedule is **weekly, Sunday 04:00 UTC** (cron: `0 4 * * 0`). Weekly cadence is cheap enough to leave on for portfolio scope without daily-API-burn anxiety.
- **D-10:** Default eval model is a **cheap one** (Haiku for Anthropic / GPT-4o-mini for OpenAI), not the production model. Eval runs check prompt+scaffolding correctness, not best-quality output. Model is configurable via `EVAL_MODEL` env var in `nightly-eval.yml`.
- **D-11:** Default cost cap is **`EVAL_BUDGET_USD=1.00`**. Per-run hard ceiling. Workflow refuses to start if cap is unset.

### Phase 4 × Phase 5 composition

- **D-12:** When both `has_backend=true` AND `has_llm=true`, the FastAPI app ships **`POST /summarize`** — a working example endpoint that takes `{text: str}`, runs an `@llm_call`-decorated summarize function, and returns `{summary: str, cost_usd: float, latency_ms: float}`. Demonstrates `@llm_call` over HTTP with cost reporting in the response body. Consumer can delete the route by editing `app/api.py` if they don't want it.
- **D-13:** Tests for `/summarize` use vcrpy cassettes so the integration suite remains offline-replayable. First cassette recording happens on the operator's machine via the `claude-agent-sdk` path (D-01) so no API key is needed to seed cassettes.

### Eval skill + just verify integration

- **D-14:** `template/.claude/skills/verify-kit-eval/SKILL.md.jinja2` is **filled in fully** (no longer a stub from Phase 3). Content covers: when to run evals, how to interpret `.verify/eval-results.json`, how to use `fix_propose` MCP tool to propose prompt edits, when to escalate to the human. The consumer's agent uses this when an LLM-quality question comes up.
- **D-15:** `just verify` does NOT automatically call `just eval`. Eval stays opt-in via `just eval` to keep the umbrella check free and fast (sub-2s per TOOL-05). Cost discipline preserved.
- **D-16:** Eval drift catching happens via the weekly `nightly-eval.yml` CI workflow (D-09 / D-10 / D-11). Drift is detected without making every commit expensive.

### README LLM-12 migration story

- **D-17:** README LLM-12 section is **Jinja-rendered per consumer project** (template-aware). Shows the consumer's actual project name, their actual docker-compose snippet, their actual env-var names. Covers Cloud Hobby → Hetzner CX32 self-host migration with concrete steps (backup, restore, DNS, env-var migration).
- **D-18:** README LLM section also covers the D-04 personal-vs-consumer setup distinction, the D-06 shell-env-var pattern, and the D-08 `none` option for privacy-conscious consumers.

### Promptfoo starter dataset

- **D-19:** `eval/datasets/golden.jsonl` ships with **5-10 starter rows** demonstrating each Promptfoo scorer type: factuality (1 row), relevance (1 row), safety (1 row), exact-match (1-2 rows), regex-match (1-2 rows). `just eval` runs against real content on first build, exits 0. Each row has a comment explaining the scorer it demos and the consumer is expected to replace rows with their actual use case.
- **D-20:** Starter rows use the cheap eval model (Haiku / GPT-4o-mini per D-10) so first-build cost is negligible (<$0.005).

### pydantic-ai role clarification (cycle-2 HIGH #5)

- **D-21:** **Resolves cycle-2 HIGH #5.** LLM-02 says verify-kit "ships pydantic-ai as primary agent/typed-call framework". This is satisfied at the *dependency / ergonomic-layer* level, not at the *call-site routing* level. Concretely:
  - `pydantic-ai>=1.100,<2` IS installed in the has_llm dependency block (05-01 Task 3) — consumers `import pydantic_ai` and use `Agent("...")` in their own code freely, exactly as LLM-02 contemplates.
  - But `harness/llm.py.call_llm()` (05-02) is the canonical *routing* entry point that every verify-kit-shipped call site uses (e.g. `/summarize` in 05-05). `call_llm()` routes via `_routing_path()` to either the claude-agent-sdk adapter (D-01/D-03) or the litellm adapter (D-02). `pydantic-ai.Agent` is NOT the routing entry point — using it directly would bypass D-03's USE_CLAUDE_CODE_SDK switch and the OTel span emission contract.
  - 05-02 `call_via_litellm` uses LiteLLM directly for the provider call rather than `pydantic_ai.Agent.run()` because (a) LiteLLM is the provider-abstraction layer named in LLM-04, (b) routing through `pydantic_ai.Agent` adds a second framework hop without ergonomic benefit when verify-kit owns the response shape, and (c) it keeps the call_llm() adapter return shape (`dict` with `content` / `usage` / `cost_usd` / `model` / `response_model` / `retry_count`) under verify-kit's control rather than pydantic-ai's `AgentRunResult.output`.
  - **Net contract:** pydantic-ai is the *shipped, importable, documented* typed-call framework — README LLM-12 (D-17/D-18) MUST cover `pydantic_ai.Agent` as the consumer-facing pattern for typed-response use cases. verify-kit's own call sites use `call_llm()` for routing-aware observability. Both can coexist; both will be exercised by the 05-03 `test_pydantic_ai_agent_constructs` test (proves pydantic-ai is installed and usable) and the 05-05 `test_summarize_uses_call_llm_not_pydantic_ai_directly` test (proves /summarize routes through call_llm, not pydantic_ai.Agent directly).
  - Roadmap follow-up (deferred): in v0.2 or a Phase 5 patch, `call_via_litellm` could optionally be reimplemented to wrap `pydantic_ai.Agent` for typed-response paths while preserving the dict return shape. Out of scope for v0.1 — the LiteLLM path is the simpler, fewer-moving-parts choice.

### Claude's Discretion

- Cache strategy and TTL for litellm's SQLite cache — planner picks sensible defaults.
- OTel exporter target details when `llm_backend=none` (configuration knobs for OTLP endpoint) — planner picks the right default.
- Cost-budget accumulator scope (per-process via contextvar, per-test via fixture, both) — planner picks.
- VCR cassette file location convention (`tests/cassettes/<test_name>.yaml` is conventional) — planner picks.
- Exact `claude-agent-sdk` adapter implementation details — research will surface the right API surface.
- Exact `@llm_call` decorator implementation (sync vs async, generator support, retry policy) — planner figures out from research findings.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase research already done
- `research/agent-reports/wave-1-llm-eval-frameworks.md` — Promptfoo / autoevals / Braintrust comparison; rationale for shipping Promptfoo as the eval gate.
- `research/agent-reports/wave-2-llm-hosting.md` — Langfuse Cloud Hobby tier limits, Hetzner CX32 self-host economics, migration path.
- `research/agent-reports/wave-4-ai-sdk-ergonomics.md` — pydantic-ai vs instructor vs litellm comparison; rationale for shipping all three with clear roles.
- `research/tools/pydantic-ai.md` — agent framework quick reference.
- `research/tools/instructor.md` — single-call typed-response quick reference.
- `research/tools/litellm.md` — provider abstraction quick reference; cache/retry/fallback config.
- `research/tools/autoevals.md` — scorer surface for pytest-native LLM testing.
- `research/tools/vcrpy.md` — cassette recording + `before_record_request` header scrubbing pattern.
- `research/tools/langfuse.md` — Langfuse SDK + OTel integration; env-var convention; Cloud vs self-host operational differences.
- `research/tools/promptfoo.md` — Promptfoo config schema, dataset format, CLI surface.
- `research/tools/openllmetry.md` — OTel `gen_ai.*` semantic conventions for LLM spans.

### Decision records
- `research/00-decision-log.md` D-001..D-020 — locked architectural decisions across the project.

### Cross-phase contracts to honor
- `.planning/REVIEW-CHECKLIST.md` §1-§8 — all eight drift patterns. §4 (plan API-surface drift) is especially relevant since Phase 5 builds heavily on Phase 2 harness APIs and Phase 4 backend integration points. The local drift-guard fork applied to `~/.claude/get-shit-done/workflows/review.md` will hunt for symbol-drift during plan-review-convergence.
- `.planning/phases/04-backend-fastapi-add-on/04-01-SUMMARY.md` — the two-guard path-gating contract. Phase 5 paths follow the same shapes: `template/{% if has_llm %}eval{% endif %}/...` for LLM-only directories, filename-level gating where parent dirs are universal.
- `.planning/phases/04-backend-fastapi-add-on/04-02-SUMMARY.md` — FastAPI app skeleton. Phase 5's `POST /summarize` endpoint (D-12) appends to `app/api.py` using the same router pattern as `/healthz` / `/echo`.
- `.planning/phases/02-universal-harness-core/` SUMMARY files — harness package API. `@register` decorator (NOT `@register_check`) and `CheckResult(status=..., envelope=...)` (NOT `CheckResult(ok=...)`). Phase 4 04-07 hit this exact drift; do not repeat.

### Upstream API references the planner must verify (drift-guard targets)
- Real `claude_agent_sdk` API: `query(prompt: str, options: Options = None) -> AsyncIterator[Message]`. Confirm against pypi.org/project/claude-agent-sdk before authoring decorator code.
- Real `langfuse` SDK env var names: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`. Confirm against langfuse.com docs.
- Real `schemathesis` 4.x already verified in Phase 4: `schema.config.generation.update(max_examples=N)` — referenced here only because the in-process fuzz pattern (`backend_inprocess_fuzz.py`) is a precedent for any LLM-side in-process testing Phase 5 might add.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `harness/observability.py` — OTel scaffold already in place from Phase 2. `@llm_call` builds on this — it adds LLM-specific span attributes (`gen_ai.*`) but the tracer provider and exporter wiring already exist.
- `harness/trace_id.py` — correlation-ID middleware. LLM spans get the request_id via the existing `set_trace_id()` contextvar.
- `harness/logging.py` — structlog dispatch. `@llm_call` binds LLM context (cost, latency, retry) into the existing logger.
- `template/harness/checks/__init__.py.jinja2` — check registry. Phase 5 may add an `eval` check that the registry picks up (for `verify-kit verify --check=eval`).
- `template/app/api.py.jinja2` — FastAPI router. The `POST /summarize` endpoint (D-12) appends here when `has_backend=true AND has_llm=true`.
- `template/justfile.jinja2` — recipe registry. `just eval`, `just refresh-cassettes`, `just docker-up` (extended with langfuse profile if self-host) are added here.

### Established Patterns
- Two-guard path gating (Phase 4 04-01 contract): `template/{% if has_llm %}eval{% endif %}/...` for LLM-unique directories; filename-level gating for files inside universal directories.
- Append, don't rewrite: when a Phase 5 plan modifies a file owned by an earlier phase (e.g., `app/api.py.jinja2`), use Read + Edit with precise old_string/new_string, never rewrite the file wholesale.
- VCR cassette + offline-replay testing: `template/tests/backend/conftest.py.jinja2` already shows the pattern (testcontainers skip-on-no-docker) — apply same shape to LLM tests.
- `before_record_request` for header scrubbing: ship in `template/tests/conftest.py` or `template/eval/conftest.py` so cassettes never contain authorization or x-api-key headers.

### Integration Points
- `template/.env.example.jinja2` (existing from Phase 4 when has_backend=true): Phase 5 appends LLM-relevant env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `EVAL_BUDGET_USD`, `EVAL_MODEL`, `USE_CLAUDE_CODE_SDK`).
- `template/pyproject.toml.jinja2`: Phase 5 adds the 9-package LLM dep block under `{% if has_llm %}`.
- `template/justfile.jinja2`: Phase 5 adds `eval`, `refresh-cassettes` recipes under `{% if has_llm %}`.
- `template/.github/workflows/`: Phase 5 adds `nightly-eval.yml` under `{% if has_llm %}` gating.
- Phase 4's `docker-compose.yml` (when both has_backend and has_llm): may need an OTel collector service if `llm_backend != none` (TBD by planner — Langfuse Cloud doesn't need it, self-host might).

</code_context>

<specifics>
## Specific Ideas

- The operator (`m2moiz`) is the primary first-user. Their Claude Code Max subscription is the canonical local-dev credential source — D-01 / D-03 ensure `@llm_call` works out of the box on their machine without an API key purchase.
- The operator uses `~/.zshrc` for shell-level env var sharing. D-06's pattern (Langfuse keys in `~/.zshrc`) matches their existing workflow — no new tooling required.
- Hardware is M2 (base) with 16 / 24 GB RAM. Self-host fits comfortably but cloud is the documented default per D-05.
- Operator explicitly framed verify-kit as a tool for "hackathon speed" earlier in this session. Phase 5's defaults bias toward zero-friction first-run experience (langfuse-cloud default, free tier, claude-agent-sdk dev path).

</specifics>

<deferred>
## Deferred Ideas

- **Streaming-response decorator**: pydantic-ai already supports streaming natively for users who need it. A `@llm_stream` decorator in `harness/llm.py` could wrap streaming with OTel span emission across chunks. Defer to v0.2 or a Phase 5 follow-up.
- **Multi-tenant LLM key rotation**: out of scope for solo-dev portfolio v0.1.
- **A `verify-kit auth langfuse` CLI command** that opens browser → OAuth → Keychain storage → auto-load on shell start. Better UX than `~/.zshrc` paste, but Langfuse SDK doesn't natively support OAuth for SDK access (only dashboard login). Would require a custom verify-kit-side proxy. Defer to v0.2 if cloud signup friction becomes a complaint.
- **Local LLM via Ollama / LM Studio** as a fourth provider option: the model-string swap pattern (LLM-02) supports this in principle (litellm has Ollama adapter). Defer to v0.2.
- **Eval-as-gate on PRs** (a third nightly-eval-style workflow that runs on every PR): considered for Q3 but rejected per D-15 (eval stays opt-in). Could be added later as `pr-eval.yml` if drift detection proves insufficient.

</deferred>

---

*Phase: 05-llm-add-on*
*Context gathered: 2026-05-21*
