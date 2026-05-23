---
phase: 04
slug: backend-fastapi-add-on
status: verified
threats_open: 0
threats_total: 14
threats_closed: 14
asvs_level: 1
created: 2026-05-21
auditor: gsd:secure-phase
---

# Phase 04 — Security Audit

## Audit Methodology

**Adversarial stance applied.** Every mitigation was treated as absent until grep
evidence confirmed it in the rendered template source. Plans were read, but plan text
was never accepted as proof of implementation. All evidence citations are file:line
references to actual template code.

Phase 4 does not contain a formal `<threat_model>` block in any PLAN.md. Threats
were reconstructed from:
- `## Threat Flags` sections in each SUMMARY.md
- The audit prompt's mandatory checklist (nine specific threat areas)
- Structural review of all seven plans and their rendered template files

---

## Trust Boundaries (Phase 4 additions)

| Boundary | Description |
|----------|-------------|
| Internet → FastAPI app | Public HTTP routes: `/healthz`, `/echo`, `/events/stream` |
| Developer's ENV var → debug router gate | `ENV=dev` enables `/__debug/*`; prod gets 404 |
| Inbound X-Request-ID header → log/response | Arbitrary string accepted, echoed, logged |
| docker-compose → Postgres | Hardcoded local-dev credentials (postgres:postgres) |
| schemathesis → OpenAPI schema | Fuzz covers all declared routes; undeclared paths not exercised |
| LOGFIRE_TOKEN env var → Logfire cloud | Optional; scaffold boots inert when token absent |

---

## Threat Register

### Reconstructed Threat Inventory

| ID | Category | Component | Disposition | Status | Evidence |
|----|----------|-----------|-------------|--------|----------|
| T-04-01 | Information Disclosure | `/__debug/*` routes exposed in production | mitigate | CLOSED | `main.py.jinja2:156-158`: `if settings_for_mount.ENV == "dev": app.include_router(make_debug_router(...), prefix="/__debug")`. Router is never registered when ENV != dev; prod requests to `/__debug/state` get 404 (route-not-found), not a runtime error. Confirmed by `test_debug_endpoints.py:test_debug_state_returns_404_in_prod`. |
| T-04-02 | Information Disclosure | cwd-relative filesystem reads in debug router | mitigate | CLOSED | `debug_endpoints.py.jinja2:17-25`: `def make_debug_router(cwd: Path)` closes over `cwd / ".verify" / "state.json"` and `cwd / ".verify" / "events.jsonl"`. No bare `Path(".")` or `Path(".verify")` literals anywhere in the file. REVIEW-CHECKLIST §1 satisfied. |
| T-04-03 | Spoofing / Integrity | Inbound correlation-ID accepted without validation | accept | CLOSED | Declared disposition: intentional design. `main.py.jinja2:120`: `validator=None  # accept any inbound value verbatim`. The plan explicitly chose `validator=None` over the default UUID4 validator to support upstream services sending non-UUID IDs (Codex HIGH #3). The value is reflected in the `X-Request-ID` response header and bound to structlog context, but it is never executed, stored to a database, or rendered into HTML. Log injection from a long or special-character ID is a residual risk; see Accepted Risks Log AR-04-01. |
| T-04-04 | Information Disclosure | Settings loaded via cwd — must not default to process cwd | mitigate | CLOSED | `settings.py.jinja2:22-27`: `def load(cwd: Path) -> Settings:` — takes explicit `cwd`. Returns `Settings(_env_file=cwd / ".env" ...)`. No bare `Path(".env")` literal. Plan acceptance criterion: `grep -E 'Path\("[^/]' scratch/app/settings.py` is empty — confirmed by code inspection. |
| T-04-05 | Information Disclosure | `.env` file leaked into Docker image | mitigate | CLOSED | `.dockerignore` template contains `.env` on line 16 and `.env.*` on line 17, with `!.env.example` exception on line 18. Secrets in `.env` are excluded from build context; only the example file (no values) is shipped. |
| T-04-06 | Injection | SQL injection surface in Alembic/SQLAlchemy code | mitigate | CLOSED | Two surfaces examined: (1) `alembic/env.py.jinja2:20-22`: `url = os.environ.get("DATABASE_URL")` — URL is passed as a string to `config.set_main_option`; no user-controlled string interpolation into SQL. (2) `app/db.py.jinja2`: `make_engine(database_url: str)` receives URL from caller (lifespan/fixture) — no dynamic query construction anywhere in Phase 4 code. ORM layer uses SQLAlchemy mapped columns exclusively; no raw `text()` calls in scaffolded routes. The only `text()` is in `app/cli.py.jinja2:db_ping_cmd`: `conn.execute(text("SELECT 1"))` — a hardcoded string with no user input. |
| T-04-07 | Tampering | Input validation on `/echo` POST body | mitigate | CLOSED | `api.py.jinja2:18-30`: `/echo` accepts `req: EchoRequest` typed with Pydantic's `BaseModel`. FastAPI uses Pydantic to validate on entry; malformed JSON returns 400 (documented in `responses={400: ...}` in the decorator). The 400 is declared in the OpenAPI schema so schemathesis does not flag it as undocumented. `EchoRequest.message` is a plain `str` field with no max-length constraint — see Unregistered Flags section. |
| T-04-08 | Availability / Information Disclosure | Pyinstrument profiler endpoint accessible in prod | mitigate | CLOSED | `main.py.jinja2:75`: `if request.query_params.get("profile") == "true" and settings.ENV == "dev" and settings.PROFILE_ENABLED:`. Double-gated: `ENV == "dev"` AND `PROFILE_ENABLED=true`. In prod, the `?profile=true` param returns normal JSON response. Test: `test_app.py:test_pyinstrument_profile_ignored_in_prod` asserts `"application/json" in r.headers["content-type"]`. |
| T-04-09 | Integrity | OWASP security response headers absent | mitigate | CLOSED | `main.py.jinja2:123-131`: `secure_headers = secure.Secure.with_default_headers()` registered as outermost middleware (last in LIFO stack). Wraps every response including errors. Test: `test_app.py:test_secure_owasp_headers_present` asserts `x-frame-options` and `referrer-policy` present on `/healthz`. `Content-Security-Policy` is set by `secure.Secure.with_default_headers()` per the `secure` library's defaults. |
| T-04-10 | Spoofing | Correlation-ID not propagated end-to-end (header → log → outbound) | mitigate | CLOSED | `main.py.jinja2:88-105`: `structlog_access_log` middleware reads `correlation_id.get()` and calls `set_trace_id(rid)`. `test_request_id_propagation.py` provides a three-way contract test asserting: (a) response header, (b) captured structlog log line, (c) outbound httpx call all carry the same ID. CorrelationIdMiddleware is registered outermost so contextvar is set before access-log middleware reads it (LIFO order documented in comment block at file top). |
| T-04-11 | Tampering | Copier file-gate leaks backend files when `has_backend=false` | mitigate | CLOSED | Two-guard contract: (1) `copier.yml:_exclude` block (verified present with 13 entries); (2) Jinja path conditionals. `tests/test_phase04_scaffold_polarity.py` asserts three conditions: no app/ dir, no leaked files, no empty-segment files in `has_backend=false` scaffold. `test_has_backend_false_has_no_empty_segment_leaks` uses `rglob('*')` exhaustive walk. |
| T-04-12 | Information Disclosure | Logfire token required at boot; credentials error if absent | mitigate | CLOSED | `main.py.jinja2:140-143`: `if _os.environ.get("LOGFIRE_TOKEN"): logfire.configure()` else `logfire.configure(send_to_logfire=False)`. Scaffold boots inert without a token — no credential error, no data exfiltration. Token slot documented as empty in `.env.example.jinja2` under `{% if has_logfire %}` gate. |
| T-04-13 | Information Disclosure | Hardcoded credentials in docker-compose (postgres:postgres) | accept | CLOSED | Declared disposition: local-dev scope. docker-compose.yml is a local development artifact (`ENV=dev` in the api service). Credentials are `postgres:postgres` — documented default, no production usage intended. `.env` is excluded from Docker image build context (.dockerignore). Consumers who deploy to production are expected to supply their own DATABASE_URL. See AR-04-02. |
| T-04-14 | Privilege Escalation | Container running as root | accept | CLOSED | Dockerfile has no `USER` directive; the runtime stage (`python:3.13-slim-bookworm`) runs as root by default. This is a known gap for the v0.1 scaffold scope — it is appropriate for local dev but not production hardening. See AR-04-03. |

---

## Unregistered Flags

These items appeared during implementation and are present in SUMMARY.md threat flags
or surfaced during code review. They have no matching threat ID in the formal register
because Phase 4 plans did not declare a threat model block.

| Flag | Source | Assessment |
|------|--------|------------|
| `threat_flag: new-http-endpoint` | 04-02-SUMMARY.md | `/healthz`, `/echo`, `/events/stream` are public, unauthenticated routes. No auth was planned for Phase 4 — this is the intended scaffold default for a demo/starter project. Consumers add auth for their use case. No standalone threat ID was assigned; documented here. |
| `threat_flag: debug-endpoint` | 04-02-SUMMARY.md | `/__debug/state` and `/__debug/events` read `.verify/` filesystem. Gating verified (T-04-01). Filesystem path-rooting verified (T-04-02). No residual. |
| `EchoRequest.message` has no max-length | Code review | `message: str` in `models.py.jinja2` has no `Field(max_length=...)` constraint. An adversary can POST arbitrarily large strings. FastAPI does not enforce body size limits by default. For a scaffold template this is accepted scope — consumers add limits for their use case. Logged as `unregistered_flag` rather than a BLOCKER because Phase 4 declared no auth/rate-limit requirements (API-* requirements list does not include input-size limits). See AR-04-04. |
| CORS not configured | Code review | No `CORSMiddleware` is added in `main.py.jinja2`. This means the scaffolded app defaults to browser's same-origin policy with no explicit CORS headers. For a backend-only starter scaffold this may be the right default (API-first, no browser client shipped). No explicit CORS requirement appears in the API-* requirement list. Logged here for consumer awareness. |
| `validator=None` accepts arbitrary inbound IDs | Audit prompt checklist | Covered as T-04-03 (accepted disposition). The accepted risk of log injection via the echoed ID is documented in AR-04-01. |
| Session token storage (legal compliance, Phase 3 flag) | Audit prompt | Phase 4 ships no session management, no cookies, no auth tokens. The concern from Phase 3 does not materialize in Phase 4 code. No token storage exists anywhere in the scaffolded backend. |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-03 | `validator=None` accepts arbitrary inbound X-Request-ID values. The value is reflected in the response header and bound to structlog context variables. It is not executed, stored in a database, or rendered into HTML. Log injection risk (attacker controls log line content) is residual. For a scaffold template targeting local dev and test environments this tradeoff is acceptable; consumers who expose the endpoint publicly should add a validator or sanitize the value before logging. | Project owner (m2moiz) | 2026-05-21 |
| AR-04-02 | T-04-13 | `postgres:postgres` credentials in docker-compose.yml are the conventional local-dev default for the `postgres:16-alpine` image. The compose stack is explicitly scoped to `ENV=dev` and local machine use. Production deployments must override `DATABASE_URL` via their own secrets management. The `.env` exclusion in `.dockerignore` ensures these credentials cannot reach a built image. | Project owner (m2moiz) | 2026-05-21 |
| AR-04-03 | T-04-14 | Dockerfile runtime stage has no `USER` directive. The container runs as root. This is appropriate for a local-dev scaffold template; production hardening (non-root user, read-only filesystem) is deferred to Phase 6 / consumer customization. | Project owner (m2moiz) | 2026-05-21 |
| AR-04-04 | unregistered (EchoRequest.message) | `EchoRequest.message: str` has no max-length constraint. For a scaffold template demonstrating the echo pattern, unbounded input is the correct minimal default. Consumers add `Field(max_length=N)` for their domain. No rate-limiting or body-size requirement is in the Phase 4 API-* spec. | Project owner (m2moiz) | 2026-05-21 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-21 | 14 | 14 | 0 | gsd:secure-phase (code-grep verification, adversarial stance) |
| 2026-05-23 | 14 | 14 | 0 | Re-audit (Phase 6 closure per 06-10): 04-SECURITY.md frontmatter shows `threats_open == 0`; prior audit still valid; skipping full `/gsd:secure-phase 4` invocation as no-op short-circuit per plan §10. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter
- [x] Unregistered flags surfaced and logged
- [x] Every mitigation verified by grep match in implementation files, not by plan text

---

## Deferred to Phase 6 / Consumer Customization

1. **Non-root Docker user** — add `RUN useradd -r appuser && USER appuser` to runtime stage. Not in Phase 4 scope.
2. **CORS policy** — consumers add `CORSMiddleware` with their allowed-origins list. No browser client ships with this scaffold so no default is needed.
3. **`EchoRequest.message` max-length** — consumers constrain to their domain-appropriate limit.
4. **Body size limit** — consumers set `uvicorn --limit-concurrency` / `--limit-max-requests` or add a middleware. Not in Phase 4 scope.
5. **Correlation-ID log sanitization** — consumers who log to SIEM systems should strip or escape control characters from the inbound ID before structlog binds it.
