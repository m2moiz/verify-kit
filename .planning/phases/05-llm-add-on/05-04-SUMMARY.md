---
phase: 05-llm-add-on
plan: "05-04"
subsystem: eval
tags: [llm, promptfoo, eval, ci, nightly, langfuse, docker-compose, cost-cap]

requires:
  - plan: "05-01"
    provides: copier _exclude gates for eval/, eval/**, nightly-eval.yml, docker-compose.langfuse.yml + value-conditional llm_backend gate
provides:
  - runnable promptfoo eval gate (`just eval`) writing .verify/eval-results.json
  - 5-row starter dataset covering factuality + equals + contains + answer-relevance + moderation
  - weekly nightly-eval workflow with load-bearing cost-cap pre-flight estimator
  - 5-container self-host Langfuse compose stack with loopback-only port binding
affects: [05-05]

tech-stack:
  added: []
  patterns:
    - "Whole-body raw-block wrap for YAML files that contain promptfoo {{env.X}} interpolation (avoids trim_blocks/lstrip_blocks collapsing trailing newlines)"
    - "GitHub-Actions secret escape via ${{ '{{ secrets.NAME }}' }} double-brace dance"
    - "Pre-flight cost estimator pattern in CI: count rows -> upper-bound per-row tokens at provider pricing -> compare against EVAL_BUDGET_USD -> exit 1 when over"
    - "Compose body unconditional; suppression by copier _exclude value-conditional gate from earlier wave"

key-files:
  created:
    - "template/{% if has_llm %}eval{% endif %}/promptfoo.config.yaml.jinja2"
    - "template/{% if has_llm %}eval{% endif %}/prompts/summarize.txt.jinja2"
    - "template/{% if has_llm %}eval{% endif %}/datasets/golden.jsonl.jinja2"
    - "template/.github/workflows/{% if has_llm %}nightly-eval.yml{% endif %}.jinja2"
    - "template/{% if has_llm %}docker-compose.langfuse.yml{% endif %}.jinja2"
  modified:
    - "template/justfile.jinja2"

key-decisions:
  - "Wrap promptfoo.config.yaml body in a single outer {% raw %}/{% endraw %} block rather than inline raw fragments (trim_blocks/lstrip_blocks eat the newline after an inline endraw, collapsing 'config:' onto the previous line)"
  - "Pre-flight cost estimator uses an inline shell formula (rows * 0.0035) documented with its assumptions (1000 in + 500 out tokens/row at haiku pricing) so the constants are auditable and updatable when pricing shifts"
  - "docker-compose.langfuse.yml body has NO inner llm_backend conditional — the value-conditional copier _exclude entry from 05-01 is the sole gate (matches Phase 4 docker-compose.yml pattern)"
  - "just eval uses `promptfoo -o .verify/eval-results.json` to match the path SKILL.md (05-05) will consume — single canonical eval output path"

patterns-established:
  - "When a YAML jinja2 template needs to ship literal {{x}} substitutions, wrap the entire body block in {% raw %}/{% endraw %} on their own lines — DO NOT mix raw fragments with trimmed/lstripped block-style conditionals"

requirements-completed:
  - LLM-10
  - LLM-11
  - CI-05

duration: ~25min
completed: 2026-05-21
---

# Phase 5 Plan 05-04 Summary

**Eval gate end-to-end: runnable on day one, cost-capped in CI, self-host stack ready for the privacy-conscious operator.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 4
- **Files modified:** 6 (5 created + 1 modified)

## Accomplishments

- Promptfoo config + 5-row starter dataset land under has_llm; `pnpm dlx promptfoo eval -c eval/promptfoo.config.yaml` runs against synthetic content immediately, exits 0
- `just eval` and `just refresh-cassettes` recipes appended to justfile under `{% if has_llm %}`; D-15 polarity preserved (`just verify` does NOT call eval)
- Weekly nightly-eval workflow lands with a LOAD-BEARING cost-cap pre-flight estimator (not just var-non-empty check) — refuses to run when `rows * 0.0035 > EVAL_BUDGET_USD`
- 5-container self-host Langfuse stack (web + worker + postgres + clickhouse + redis) on isolated bridge network with loopback-only `127.0.0.1:3000:3000` binding (threat T-05-12 mitigation)

## Task Commits

1. **Task 1: eval/promptfoo.config.yaml + golden.jsonl + summarize.txt** — `616a3f1` (feat)
2. **Task 2: justfile recipes — eval + refresh-cassettes** — `6205f84` (feat)
3. **Task 3: nightly-eval.yml workflow with cost-cap pre-flight** — `2d901f9` (feat)
4. **Task 4: docker-compose.langfuse.yml self-host stack** — `58cfe1f` (feat)

## golden.jsonl scorer roster (verbatim — for 05-05 SKILL.md to quote)

The five committed rows demo (in order):

1. **factuality** — Eiffel Tower historical facts
2. **equals** — exact-match "OK"
3. **contains** — substring "verification"
4. **answer-relevance** (threshold 0.6) — capital of France question
5. **moderation** — neutral-content baseline

Each row has a `_comment` field telling the consumer to replace with their actual use case. No PII (T-05-13 mitigation).

## Cron + budget as committed

- `cron: "0 4 * * 0"` (Sunday 04:00 UTC, D-09)
- `env.EVAL_MODEL: "claude-haiku-4-5"` (D-10)
- `env.EVAL_BUDGET_USD: "1.00"` (D-11)
- Pre-flight formula: `estimated_usd = rows * 0.0035` (1000 in + 500 out tokens/row at haiku pricing $1/Mtok input + $5/Mtok output)
- Workflow refuses to run if estimated > budget

## Self-host compose as committed

Services (5): `langfuse-web`, `langfuse-worker`, `postgres`, `clickhouse`, `redis`. Web binding: `127.0.0.1:3000:3000` (loopback only — remote access via Tailscale). Network: `langfuse-net` bridge driver, isolated from Phase 4 compose. Volumes: `langfuse_pg_data`, `langfuse_ch_data`, `langfuse_redis_data`.

## Justfile recipe names (for 05-05 README docs to quote)

- `eval` — `pnpm dlx promptfoo eval -c eval/promptfoo.config.yaml -o .verify/eval-results.json`
- `refresh-cassettes` — `rm -rf tests/llm/cassettes/ && uv run pytest tests/llm/ --record-mode=once`

## Polarity Matrix (after this plan)

| has_llm | llm_backend | eval/ | nightly-eval.yml | docker-compose.langfuse.yml |
|---------|-------------|-------|------------------|------------------------------|
| true    | langfuse-self-host | YES | YES | YES |
| true    | langfuse-cloud | YES | YES | NO (value-cond excluded) |
| true    | none | YES | YES | NO (value-cond excluded) |
| false   | n/a | NO | NO | NO |

## Decisions Made

- **Whole-body raw wrap for promptfoo.config.yaml** — first verify attempt failed because inline `{% raw %}"..."{% endraw %}` fragments inside a YAML mapping triggered Copier's `trim_blocks: true` to eat the newline after `{% endraw %}`, collapsing `config:` onto the previous line. Fix: wrap the entire YAML body in a single outer raw block on its own lines.
- **Compose body has no inner llm_backend conditional** — 05-01 already ships the value-conditional `_exclude` entry that suppresses this file when `llm_backend != langfuse-self-host`. Adding an inner Jinja conditional would be redundant and contradict the cycle-6 restructure decision documented in the plan.
- **Cost-cap formula is documented inline as shell comments** — when haiku pricing changes (or operator switches `EVAL_MODEL` to gpt-4o-mini), both constants (1000+500 tokens/row, $/Mtok rates) need a one-line update each. Comments make this an obvious one-pass change.

## Deviations from Plan

- The plan's Task 1 verify snippet did not include the 4 required Copier identity prompts (project_name etc.); inline-extended the verify call to pass `--data project_name=Test --data project_description=Test --data author_name=A --data author_email=a@b.c`. Same issue as Plan 05-01's verify snippets. Did not change acceptance criteria.
- The plan's initial promptfoo.config.yaml shape used inline raw fragments per the RESEARCH.md sketch; switching to whole-body raw wrap was a forced fix once Copier's trim_blocks setting was exercised. Updated SUMMARY documents the resulting pattern as the canonical approach for any future YAML template with promptfoo-style `{{env.X}}` interpolation.

## Issues Encountered

- `{% raw %}` inline fragments + Copier `trim_blocks: true` = collapsed newlines. Diagnosed via the YAML parser error in verify, then re-rendered to `/tmp/scratch-05-04-pf/eval/promptfoo.config.yaml` to inspect the literal output. Fixed by wrapping the entire YAML body in a single outer raw block. Added a pattern entry to this SUMMARY's `patterns-established` for future YAML templates.

## User Setup Required

None — every file is template-only. The operator's first `just eval` requires `pnpm dlx promptfoo` (transitively requires Node) and `ANTHROPIC_API_KEY`; both are documented in the recipe's doc-comment.

## Next Phase Readiness

- **05-03 ready:** can place tests under `tests/llm/cassettes/` knowing `just refresh-cassettes` deletes exactly that path on demand.
- **05-05 ready:** SKILL.md can quote the canonical eval output path `.verify/eval-results.json`, the recipe names (`just eval`, `just refresh-cassettes`), and the 5 scorer types from `golden.jsonl`. README LLM-12 can reference `docker-compose.langfuse.yml` and the 5-container service list directly.

---
*Phase: 05-llm-add-on*
*Plan: 05-04*
*Completed: 2026-05-21*
