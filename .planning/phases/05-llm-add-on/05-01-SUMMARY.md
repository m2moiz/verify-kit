---
phase: 05-llm-add-on
plan: "05-01"
subsystem: infra
tags: [copier, jinja, path-gating, pyproject, env-example, llm, langfuse, otel]

requires:
  - phase: 04-backend-fastapi-add-on
    provides: two-guard path-gating contract (copier.yml _exclude primary + bounded Jinja path shapes defense-in-depth) and existing app/.env.example.jinja2 baseline
provides:
  - copier.yml _exclude entries gating every LLM-only path under {% if not has_llm %}
  - value-conditional _exclude for docker-compose.langfuse.yml gated on llm_backend == "langfuse-self-host"
  - 11-package has_llm dependency block in pyproject.toml.jinja2 (9 runtime + 2 dev; tokenx-core DROPPED per D-22)
  - appended LLM env block in app/.env.example.jinja2 with three llm_backend branches (cloud / self-host / none)
  - root-level .env.example for the (has_llm=true AND has_backend=false) cell using Shape 2 filename-level gate
affects: [05-02, 05-03, 05-04, 05-05]

tech-stack:
  added:
    - pydantic-ai >=1.100,<2
    - instructor >=1.15,<2
    - litellm >=1.85,<2
    - tokencost >=0.1.26
    - autoevals >=0.2,<0.3
    - opentelemetry-instrumentation-httpx >=0.63b1
    - traceloop-sdk >=0.60,<1
    - claude-agent-sdk >=0.2.83
    - langfuse >=4.6,<5
    - vcrpy >=8.1,<9 (dev)
    - pytest-recording >=0.13.4 (dev)
  patterns:
    - "Layered _exclude: separate has_llm gate + value-conditional llm_backend gate (D-12 cell pattern)"
    - "Filename-level Jinja path gate (Shape 2) for value-discriminated env destinations"
    - "Content parity between app/.env.example and root .env.example to prevent cross-plan contract drift"

key-files:
  created:
    - "template/{% if has_llm and not has_backend %}.env.example{% endif %}.jinja2"
  modified:
    - copier.yml
    - template/pyproject.toml.jinja2
    - "template/{% if has_backend %}app{% endif %}/.env.example.jinja2"

key-decisions:
  - "D-22: drop tokenx-core after slopcheck flagged 81 downloads SUS and decorator overlap with @llm_call"
  - "LLM dev deps land under [project.optional-dependencies].dev (NOT [dependency-groups].dev — that table does not exist in this repo)"
  - "Langfuse OTLP uses Basic Auth (NOT Bearer) per RESEARCH.md Pitfall 8"
  - "pydantic-ai pinned >=1.100 (NOT v0.x) per RESEARCH.md Pitfall 4"
  - "Layered _exclude entries instead of composite-condition gates: copier evaluates as list, any single match suppresses"

patterns-established:
  - "Cell-pattern path-gating: ONE filename-level Jinja gate per cell + one _exclude entry per polarity (PRIMARY=_exclude, defense-in-depth=path-gate)"
  - "Append-only edits to Phase 4 baseline files (REVIEW-CHECKLIST section 4): never rewrite, always {% if has_llm %}...{% endif %} block at end"
  - "Three-branch llm_backend wiring (cloud / self-host / none) duplicated verbatim across both env destinations"

requirements-completed:
  - LLM-01
  - LLM-10

duration: ~25min
completed: 2026-05-21
---

# Phase 5 Plan 05-01 Summary

**Foundation laid: every Phase 5 LLM-only artifact is now gated; has_llm=false renders zero LLM dependencies and zero LLM credentials in either env destination.**

## Performance

- **Duration:** ~25 min (across resumed execution; original session interrupted after Task 4)
- **Completed:** 2026-05-21
- **Tasks:** 5
- **Files modified:** 4 (3 modified + 1 created)

## Accomplishments

- Locked the Phase 5 path-gating contract on top of Phase 4's two-guard rule before any LLM-only file lands downstream
- Recorded D-22 (tokenx-core drop) in 05-CONTEXT.md and removed it from every dependency list
- Landed the 11-package LLM baseline (9 runtime + 2 dev) under has_llm in pyproject.toml.jinja2
- Wired three llm_backend branches (Langfuse Cloud / self-host / OTLP-only) into the env example with Basic-Auth idiom comments
- Established the (has_llm × has_backend) 2x2 polarity matrix: exactly one env destination renders per cell, never zero, never two

## Task Commits

1. **Task 1: slopcheck resolution + D-22 record** — `0fd475a` (docs)
2. **Task 2: copier.yml _exclude block** — `718cc8b` (feat)
3. **Task 3: pyproject.toml LLM deps** — `76cbbea` (feat)
4. **Task 4: app/.env.example.jinja2 LLM block** — `2b60b3f` (feat)
5. **Task 5: root .env.example.jinja2 for no-backend cell** — `01edb81` (feat)

## Files Created/Modified

- `copier.yml` — Eleven `{% if not has_llm %}` _exclude entries + one `{% if llm_backend != "langfuse-self-host" %}docker-compose.langfuse.yml{% endif %}` value-conditional entry
- `template/pyproject.toml.jinja2` — Two `{% if has_llm %}` blocks (runtime deps in `[project] dependencies`; dev deps in `[project.optional-dependencies].dev`)
- `template/{% if has_backend %}app{% endif %}/.env.example.jinja2` — Appended `{% if has_llm %}` block with three llm_backend branches
- `template/{% if has_llm and not has_backend %}.env.example{% endif %}.jinja2` — NEW root-level env destination for the LLM-only-no-backend cell

## Version Pins (as committed)

Runtime (under `[project] dependencies`, `{% if has_llm %}`):

| Package | Pin |
|---------|-----|
| pydantic-ai | >=1.100,<2 |
| instructor | >=1.15,<2 |
| litellm | >=1.85,<2 |
| tokencost | >=0.1.26 |
| autoevals | >=0.2,<0.3 |
| opentelemetry-instrumentation-httpx | >=0.63b1 |
| traceloop-sdk | >=0.60,<1 |
| claude-agent-sdk | >=0.2.83 |
| langfuse | >=4.6,<5 |

Dev (under `[project.optional-dependencies].dev`, `{% if has_llm %}`):

| Package | Pin |
|---------|-----|
| vcrpy | >=8.1,<9 |
| pytest-recording | >=0.13.4 |

**Dropped per D-22:** tokenx-core (slopcheck SUS at 81 PyPI downloads + @measure_cost/@measure_latency overlap with our own @llm_call built in 05-02).

## copier.yml _exclude entries added

All under `{% if not has_llm %}<path>{% endif %}` unless noted:

- `harness/llm.py`
- `harness/checks/eval.py`
- `eval`
- `eval/**`
- `tests/llm`
- `tests/llm/**`
- `docker-compose.langfuse.yml` (also has a separate value-conditional entry below)
- `.github/workflows/nightly-eval.yml`
- `.env.example` (primary gate for the root-level env destination per cycle-2 HIGH #3)

Plus one value-conditional entry:

- `{% if llm_backend != "langfuse-self-host" %}docker-compose.langfuse.yml{% endif %}` — fires when has_llm=true but llm_backend is cloud or none

Downstream plans 05-02..05-05 reference these by path when adding LLM-only files.

## Polarity Matrix

The (has_llm × has_backend) cells and their LLM env destinations:

| has_llm | has_backend | LLM deps in pyproject | app/.env.example | root .env.example |
|---------|-------------|-----------------------|------------------|-------------------|
| true    | true        | YES (9 runtime + 2 dev) | YES (with LLM block) | NO (excluded by filename gate `not has_backend`) |
| true    | false       | YES (9 runtime + 2 dev) | NO (path-gated by has_backend) | YES (filename gate active) |
| false   | true        | NO  | YES (baseline only, no LLM block) | NO (excluded by `_exclude` + filename gate `has_llm`) |
| false   | false       | NO  | NO (path-gated by has_backend) | NO (excluded by `_exclude` + filename gate `has_llm`) |

Invariants enforced:
- Every (has_llm=true) cell has exactly ONE env destination carrying the LLM credentials block
- No cell renders BOTH env destinations
- has_llm=false renders contain ZERO LLM environment variables and ZERO LLM dependencies
- The body content of both env destinations is identical when present (no drift; REVIEW-CHECKLIST section 3)

## Decisions Made

- **D-22 (in 05-CONTEXT.md, recorded by Task 1):** drop tokenx-core. Real package, not a typosquat, but slopcheck flagged it SUS at 81 PyPI downloads. More importantly, its `@measure_cost` + `@measure_latency` decorators duplicate the `@llm_call` decorator that 05-02 will own — installing it would create two competing observability surfaces with no unique value-add.
- vcrpy allowlisted in `.slopcheck` as a false positive on the name-similarity-to-scipy heuristic (canonical Python HTTP-cassette library, already used in Phase 4).

## Deviations from Plan

None — plan executed exactly as written. Task 1 was already record-only (D-22 had been resolved before plan execution started), and Tasks 2-5 landed against their stated acceptance criteria.

## Issues Encountered

- Task 5 verify subprocess required additional `--data` flags for the four required Copier strings (project_name, project_description, author_name, author_email). The plan's verify snippet was upgraded inline to include these — they were not in the original snippet because the plan author assumed `--defaults` would supply them, but Copier raises `ValueError: Question "project_name" is required` because that prompt has no default. Did not change the acceptance criteria; the assertions still verify the same four-cell matrix.

## User Setup Required

None — no external service configuration required for this plan. Downstream 05-04 will land the Langfuse self-host docker-compose; until then the env slots are documentation only.

## Next Phase Readiness

- **05-02 ready:** can import against pydantic-ai >=1.100 / instructor / litellm / langfuse / tokencost; can place `harness/llm.py` knowing the _exclude entry will suppress it when has_llm=false.
- **05-03 ready:** can place tests under `tests/llm/` and cassettes under `tests/cassettes/`; the former is gated, the latter remains universal.
- **05-04 ready:** can place `docker-compose.langfuse.yml` knowing both the has_llm gate and the llm_backend value-conditional gate are wired; can place `.github/workflows/nightly-eval.yml` knowing the _exclude covers it.
- **05-05 ready:** has the polarity matrix in scope for the 12-cell test.

---
*Phase: 05-llm-add-on*
*Plan: 05-01*
*Completed: 2026-05-21*
