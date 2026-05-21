---
phase: 4
plan: "04-05"
title: "Dockerfile (multi-stage uv) + docker-compose.yml + just docker-up"
subsystem: docker-stack
tags: [docker, docker-compose, dockerfile, uv, jaeger, postgres, justfile]
dependency_graph:
  requires:
    - "04-01 two-guard contract: copier _exclude block + filename-level gating"
    - "04-02 FastAPI app skeleton: app.main:app entry point, /healthz route"
    - "04-03 DB stack: postgres:16-alpine image pin for Testcontainers contract"
  provides:
    - "template/Dockerfile.jinja2 (has_backend gate): multi-stage uv build + slim runtime"
    - "template/docker-compose.yml.jinja2 (has_backend gate): api + jaeger always; postgres under has_db"
    - "template/.dockerignore (has_backend gate): excludes .env, .planning, .verify"
    - "template/justfile.jinja2: docker-up, docker-down recipes under has_backend"
    - "tests/test_phase04_docker_compose.py: 3-cell polarity test"
  affects:
    - template/justfile.jinja2
    - downstream plan 04-07 (verify-backend: wraps docker-up + just verify-backend)
tech_stack:
  added: []
  patterns:
    - "Multi-stage Dockerfile: uv build image → slim python:3.13-bookworm runtime"
    - "deps-only layer: uv sync --no-install-project --frozen --no-dev BEFORE COPY . ."
    - "project install: uv sync --frozen --no-dev AFTER COPY . . (lockfile-driven)"
    - "fallback: uv pip install . (positional, never -r) when uv.lock absent"
    - "Jinja2 block-level gating for YAML env vars and depends_on (not inline %tag%)"
    - "docker compose config -q as polarity forcing function"
key_files:
  created:
    - "template/{% if has_backend %}Dockerfile{% endif %}.jinja2"
    - "template/{% if has_backend %}docker-compose.yml{% endif %}.jinja2"
    - "template/{% if has_backend %}.dockerignore{% endif %}"
    - "tests/test_phase04_docker_compose.py"
  modified:
    - "template/justfile.jinja2"
decisions:
  - "Block-level Jinja gating for DATABASE_URL/depends_on (not inline single-line %) to produce valid YAML"
  - "Removed explanatory meta-comments from docker-compose.yml template (they contained the bare word 'postgres' which tripped the polarity test's no-DB grep assertion)"
  - "Two separate install layers in Dockerfile: --no-install-project before COPY, full sync after COPY"
metrics:
  duration: "~7 minutes"
  completed: "2026-05-21"
  tasks_completed: 5
  files_count: 5
requirements: [API-17]
---

# Phase 4 Plan 04-05: Docker Stack Summary

## One-liner

Multi-stage uv Dockerfile + conditionally-gated docker-compose (postgres under has_db, jaeger always) + just docker-up recipe, proven by a 3-cell polarity test that runs `docker compose config -q` on rendered output.

## What Was Built

### Dockerfile (`template/{% if has_backend %}Dockerfile{% endif %}.jinja2`)

Two-stage build:
- **Build stage** (`ghcr.io/astral-sh/uv:0.4-python3.13-bookworm`): installs third-party deps into `/opt/venv` using `uv sync --no-install-project --frozen --no-dev` BEFORE `COPY . .` for layer caching; then installs the project itself after `COPY . .` with `uv sync --frozen --no-dev` (lockfile path) or `uv pip install .` (no-lockfile fallback).
- **Runtime stage** (`python:3.13-slim-bookworm`): copies `/opt/venv` from build stage; sets `PATH`, `PYTHONUNBUFFERED=1`, `ENV=prod`; exposes port 8000; HEALTHCHECK via stdlib `urllib.request`; CMD is `uvicorn app.main:app`.

The two-layer install pattern (HIGH D fix): `--no-install-project` allows the dep cache layer to populate before source exists; the project install runs after `COPY . .` when sources are available.

### docker-compose.yml (`template/{% if has_backend %}docker-compose.yml{% endif %}.jinja2`)

Services:
- **api**: always present; healthcheck on `/healthz`; `DATABASE_URL` env var and `depends_on: postgres: service_healthy` are wrapped in `{% if has_db %}` block-level gates (HIGH #6 fix).
- **postgres**: `postgres:16-alpine` (matches Plan 04-03 Testcontainers pin); wrapped in `{% if has_db %}` service block.
- **jaeger**: `jaegertracing/all-in-one:1.76.0` (matches Phase 2 `just trace-up` pin); always present.
- **volumes**: `pg_data` under `{% if has_db %}` gate.

### .dockerignore (`template/{% if has_backend %}.dockerignore{% endif %}`)

Static file (no `.jinja2` suffix). Excludes: `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.verify`, `.planning`, `.env` (secrets gate), `!.env.example` (allowlist for docs), `*.log`, etc.

### justfile additions (`template/justfile.jinja2`)

Two new recipes inside the existing `{% if has_backend %}` block:
- `docker-up`: `docker compose up -d --wait --wait-timeout 120`
- `docker-down`: `docker compose down -v`

### Polarity test (`tests/test_phase04_docker_compose.py`)

Three cells:
1. `has_backend=true, has_db=true`: renders compose, runs `docker compose config -q`, asserts exit 0.
2. `has_backend=true, has_db=false`: renders compose, runs `docker compose config -q`, asserts exit 0 AND asserts `DATABASE_URL`, `depends_on`, and `postgres` (word + service key via `yaml.safe_load`) are absent.
3. `has_backend=false`: asserts `Dockerfile`, `docker-compose.yml`, `.dockerignore` absent from render.

Skip guard uses `docker info` (not `shutil.which`) per Codex HIGH #9.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Inline Jinja `{% if %}` tags for YAML env vars produced malformed YAML**

- **Found during:** T02 verification (render test)
- **Issue:** The plan showed `{% if has_db %}DATABASE_URL: ...{% endif %}` as an inline single-line conditional. When Jinja renders this with `has_db=true`, the whitespace handling produces `DATABASE_URL: postgresql+asyncpg://...    depends_on:` on a single line — `DATABASE_URL` and `depends_on` merge onto one line because Jinja's inline block tags consume trailing newlines without the `{%- -%}` trim markers.
- **Fix:** Changed both `DATABASE_URL` and `depends_on` conditionals to block-level gates (`{% if has_db %}` on its own line, content on next line, `{% endif %}` on its own line). This produces correct YAML indentation in both polarities.
- **Files modified:** `template/{% if has_backend %}docker-compose.yml{% endif %}.jinja2`

**2. [Rule 1 - Bug] Meta-comments in compose template contained the bare word "postgres"**

- **Found during:** T05 polarity test verification
- **Issue:** The plan's template included explanatory comments (cycle-3 sweep notes) inside the docker-compose.yml Jinja2 template. These comments contained the word "postgres" — specifically `"# (cycle-3 sweep: previous comment hard-coded the word "postgres" even when..."`. The T05 test asserts `"postgres" not in compose_text` for the has_db=false polarity. These comments would render in BOTH polarities (they're not gated), causing the grep assertion to fail.
- **Fix:** Removed the explanatory meta-comments from the template. These comments were executor/author notes that do not belong in the consumer's rendered docker-compose.yml. The functional Jinja2 gating (what matters) is unchanged.
- **Files modified:** `template/{% if has_backend %}docker-compose.yml{% endif %}.jinja2`

## Known Stubs

None. All template files are complete. The Dockerfile references `app.main:app` per Plan 04-02's entry point. The healthcheck hits `/healthz` per Plan 04-02's API. The postgres image pin matches Plan 04-03's Testcontainers fixture.

## Threat Flags

None. No new HTTP endpoints introduced. The Dockerfile and compose stack are dev/local infrastructure; no auth paths or schema changes. `DATABASE_URL` credentials in compose use local-only `postgres:postgres` defaults appropriate for local dev.

## Self-Check: PASSED

- [x] `template/{% if has_backend %}Dockerfile{% endif %}.jinja2` exists
- [x] Two-stage build: `AS build` and `AS runtime` present
- [x] HEALTHCHECK directive hits `/healthz`
- [x] `uv sync --no-install-project` appears BEFORE `COPY . .` (line 29 vs line 33)
- [x] `uv pip install -r pyproject.toml` NOT present (zero matches)
- [x] `template/{% if has_backend %}docker-compose.yml{% endif %}.jinja2` exists
- [x] `postgres:16-alpine` image pin matches Plan 04-03
- [x] `jaegertracing/all-in-one:1.76.0` image pin matches Phase 2
- [x] `DATABASE_URL` and `depends_on` wrapped in `{% if has_db %}` block gates
- [x] `template/{% if has_backend %}.dockerignore{% endif %}` exists (static file, no .jinja2)
- [x] `.env` excluded, `!.env.example` allowed in .dockerignore
- [x] `template/justfile.jinja2` contains `docker-up` and `docker-down` inside `{% if has_backend %}`
- [x] `docker-up` uses `--wait --wait-timeout 120`
- [x] `tests/test_phase04_docker_compose.py` exists with 2 test functions (1 parametrized)
- [x] `uv run pytest tests/test_phase04_docker_compose.py -v` → 3 passed
- [x] `docker compose config -q` passes for has_db=true and has_db=false renders
- [x] has_backend=false render: Dockerfile, docker-compose.yml, .dockerignore absent
- [x] Commits c681e29 (production) and 81fe9b5 (test) exist on worktree-agent-a1a2637e0c609d722
