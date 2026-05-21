---
phase: 5
slug: llm-add-on
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-22
---

# Phase 5 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail for the LLM add-on.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Scaffold consumer ↔ verify-kit template | `copier copy` ingests template + answers, renders project | Project name, author info (no secrets) |
| Rendered project ↔ LLM provider (Anthropic / OpenAI via litellm) | `harness.llm.call_llm()` HTTPS dispatch | User prompt + completion (PII potential, set by consumer) |
| Rendered project ↔ Claude Code OAuth session | `claude-agent-sdk` local stdio bridge | User prompt + completion (no API key on wire) |
| Rendered project ↔ Langfuse (cloud or self-host) | OTLP exporter with Basic auth header | Span metadata (`gen_ai.*`, `verify_kit.*`) — prompts NOT included by design |
| CI runner ↔ Anthropic via promptfoo | nightly-eval.yml weekly cron Sun 04:00 UTC | Eval prompts + responses, capped by `EVAL_BUDGET_USD` |
| Operator workstation ↔ self-host Langfuse stack | docker-compose.langfuse.yml bound to 127.0.0.1 | All Langfuse traffic loopback-only |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-01 | Tampering | uv installs of LLM packages | mitigate | Slopcheck Task 1 record (`05-01-SUMMARY.md`); D-22 dropped tokenx-core; regression guard `test_pyproject_has_no_tokenx` in `tests/test_phase05_polarity.py:163-173` | closed |
| T-05-02 | Information Disclosure | `.env.example` documents secret slots | accept | Blank values only — verified at `template/{% if has_backend %}app{% endif %}/.env.example.jinja2:10-19,24-26` and `template/{% if has_llm and not has_backend %}.env.example{% endif %}.jinja2:2-21` (all `ANTHROPIC_API_KEY=`, `LANGFUSE_*=` lines empty) | closed |
| T-05-03 | Spoofing | `claude-agent-sdk` supply chain | mitigate | Slopcheck OK (05-01-SUMMARY.md); pinned `claude-agent-sdk>=0.2.83` at `template/pyproject.toml.jinja2:66` | closed |
| T-05-SC | Tampering | npm/pip installs from upstream | mitigate | Slopcheck Task 1 ran 2026-05-21 (10 OK + 2 SUS reviewed); `.slopcheck` allowlist committed at `/Users/moiz/Documents/code/verify-kit/.slopcheck` (vcrpy allowlisted; tokenx-core dropped per D-22) | closed |
| T-05-04 | Tampering | Decorator stacking order (Pitfall 3) | mitigate | Module docstring + `cost_budget` docstring repeat OUTER/INNER rule at `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2:11-37,374-385`; forcing test `test_decorator_ordering_documentation` at `template/tests/llm/{% if has_llm %}test_llm_call.py{% endif %}.jinja2:160-170` greps source for "OUTER"/"INNER" | closed |
| T-05-05 | Repudiation | LLM call cost reporting | mitigate | `verify_kit.cost_usd` + `verify_kit.routing_path` set unconditionally on every span at `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2:297,340-342`; structlog `llm_call.complete` emission at `:344-353` | closed |
| T-05-06 | Information Disclosure | Prompt/response in span | accept | `gen_ai.prompt.*` and `gen_ai.completion.*` are DELIBERATELY NOT set — confirmed via `grep -rE "gen_ai\.(prompt\|completion)"` returns zero matches across `template/`. Only `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` are emitted (`llm.py.jinja2:296-339`) | closed |
| T-05-07 | DoS (wallet) | Runaway LLM cost | mitigate | `@cost_budget` decorator at `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2:369-400` raises `CostBudgetExceeded` (defined `:83-101`) when `_cumulative_cost_usd.get() > usd` | closed |
| T-05-08 | Information Disclosure | Cassettes leaking Authorization | mitigate | `vcr_config` fixture at `template/tests/conftest.py.jinja2:69-109` filters six headers via `filter_headers` list + `before_record_request` defense-in-depth pass; ordering rule (Task 1 before Task 3) honored — `test_no_plaintext_credentials_in_cassettes` at `template/tests/llm/{% if has_llm %}test_vcr_scrub.py{% endif %}.jinja2:35-47` walks cassette tree for forbidden tokens; `test_vcr_config_lists_required_headers` at `:50-70` asserts all six headers present | closed |
| T-05-09 | Tampering | Decorator-ordering drift | mitigate | `test_decorator_ordering_documentation` greps source for OUTER/INNER (`test_llm_call.py:160-170`); `test_no_result_data_anywhere` polarity at `tests/test_phase05_polarity.py:189-198` | closed |
| T-05-10 | Repudiation | list-checks does not advertise eval gate | mitigate | `template/harness/checks/{% if has_llm %}eval.py{% endif %}.jinja2:18-35` uses `@register('eval', tier='slow', category='llm', ...)` so `verify-kit list-checks` advertises the gate; check returns `status='skip'` with fix hint pointing at `just eval` | closed |
| T-05-11 | DoS (wallet) | nightly-eval cost runaway | mitigate | Pre-flight `Pre-flight cost estimator` step at `template/.github/workflows/{% if has_llm %}nightly-eval.yml{% endif %}.jinja2` enforces `rows × 0.0035 ≤ EVAL_BUDGET_USD`; cron `0 4 * * 0` (Sun 04:00 UTC) per D-09; default `EVAL_BUDGET_USD: "1.00"` | closed |
| T-05-12 | Spoofing | self-host langfuse-web exposed on LAN | mitigate | `docker-compose.langfuse.yml` ports entry `"127.0.0.1:3000:3000"` — verified at `template/{% if has_llm %}docker-compose.langfuse.yml{% endif %}.jinja2` ports section; comment explicitly references threat T-05-12 and warns against `0.0.0.0` | closed |
| T-05-13 | Information Disclosure | `golden.jsonl` real PII | mitigate | 5 synthetic starter rows (Eiffel Tower, "OK", verification keyword, capital of France, peaceful walk) per D-19 at `template/{% if has_llm %}eval{% endif %}/datasets/golden.jsonl.jinja2`; every row carries `_comment` ending "Replace with your actual use case." | closed |
| T-05-14 | Tampering | promptfoo cost-estimate gate displacement | mitigate | `EVAL_BUDGET_USD` enforced in workflow pre-flight step (BEFORE `pnpm dlx promptfoo` invocation), NOT delegated to promptfoo's `--max-concurrency`. Pre-flight refuses to start (`exit 1`) when estimate > budget. See `nightly-eval.yml` pre-flight vs separate `Run promptfoo eval` step | closed |
| T-05-15 | Information Disclosure | `/summarize` prompt injection → exfiltration | accept | Documented as out-of-scope for v0.1 starter scaffold; rationale in `05-05-PLAN.md:366` threat row references RESEARCH.md V4 ASVS-L1 note. Consumer is responsible for adding prompt-injection defenses for their use case | closed |
| T-05-16 | DoS (wallet) | `/summarize` cost runaway | mitigate | `@cost_budget(usd=0.05, on_exceed="raise")` decorates `_summarize` at `template/{% if has_backend %}app{% endif %}/api.py.jinja2:72`; raised `CostBudgetExceeded` propagates → FastAPI 500 (no broad except swallowing it) | closed |
| T-05-17 | Tampering | Future refactor removes Pitfall 3/4 doc | mitigate | `test_no_result_data_anywhere` polarity at `tests/test_phase05_polarity.py:189-198`; OUTER/INNER docstring grep `test_decorator_ordering_documentation` at `test_llm_call.py:160-170` | closed |
| T-05-18 | Information Disclosure | README documents API-key path as personal default | mitigate | README explicit two-section split at `template/README.md.jinja2:236-255` — "Personal / local-dev path uses `claude-agent-sdk` … no API key required" vs "Consumer / deployed path uses `ANTHROPIC_API_KEY` via litellm". `claude-agent-sdk` keyword present | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-05-02 | T-05-02 | `.env.example` files document required secret slots with BLANK values only. Consumer fills them locally; the template never ships real credentials. Pattern continues Phase 4 convention. | Phase 5 planner (PLAN.md threat_model) | 2026-05-21 |
| R-05-06 | T-05-06 | Prompt and completion bodies are deliberately omitted from the OTel span attribute set. This avoids PII leakage to Langfuse and stays compatible with the gen_ai semantic-convention's optional-attribute carve-out. Consumers who need prompt content in their observability backend can extend `harness.llm.llm_call` themselves. | Phase 5 planner | 2026-05-21 |
| R-05-15 | T-05-15 | `/summarize` is a starter endpoint demonstrating the `@cost_budget` + `call_llm` integration. Prompt-injection defenses (allowlists, output validation, system-prompt hardening) are out of scope for the v0.1 starter scaffold. Documented in PLAN.md and RESEARCH.md V4 ASVS-L1 note. Consumer owns prompt-injection mitigation for their use case. | Phase 5 planner | 2026-05-21 |

---

## Unregistered Flags

None. SUMMARY.md files for plans 05-01 through 05-05 do not declare any `## Threat Flags` section, and no new attack surface appeared during implementation that lacks a threat-register mapping.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-22 | 19 | 19 | 0 | gsd-security-auditor (Claude) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-22
