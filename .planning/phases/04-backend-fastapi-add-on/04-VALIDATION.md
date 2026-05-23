---
phase: 04-backend-fastapi-add-on
validation_date: 2026-05-21
status: gaps_identified
gap_count: 10
severity_counts: {HIGH: 3, MEDIUM: 4, LOW: 3}
cross_references:
  - 04-VERIFICATION.md  # runtime gaps already documented there (psycopg2 bug, REQUIREMENTS.md tracking)
  - 04-REVIEWS.md       # plan-review concerns, now closed
---

# Phase 4 — Nyquist Coverage Validation

This document identifies **sampling-theory gaps**: places where the existing
test coverage has fewer probe-points than would be needed to detect a regression
in the behavior it claims to protect. It complements `04-VERIFICATION.md`, which
documented goal-completeness failures (the psycopg2 fixture bug and stale
REQUIREMENTS.md). The gaps below are distinct — they are cases where tests
exist or pass but cover only a sub-matrix of the required behavior space,
rely on implicit assertions, or have dead instrumentation paths.

Gaps found in `04-VERIFICATION.md` (psycopg2 URL driver bug, REQUIREMENTS.md
tracking) are **not repeated here**.

---

## Gap Inventory

### GAP-01 — HIGH | Render polarity matrix is 1/4 cells covered for has_backend×has_db

**What is currently tested:**
`test_phase04_scaffold_polarity.py::test_has_backend_true_produces_app_tree`
renders only the `(has_backend=True, has_db=True)` cell. The two remaining
backend-on cells — `(has_backend=True, has_db=False)` — are not rendered in
the polarity file.

**What is missing:**
The `(has_backend=True, has_db=False)` cell must be rendered and asserted:
- `app/db.py`, `app/schema.py`, `alembic/`, `alembic.ini` are ABSENT
  (Jinja gate `{% if has_db %}db.py{% endif %}` renders to empty filename
  when `has_db=False` — if the _exclude block or Jinja gate is broken, a
  root-level empty file or the module leaks in)
- `tests/backend/` exists and contains `conftest.py` but NOT `test_db_integration.py`
- The rendered `conftest.py` contains no `pg_container` fixture block

Only `test_phase04_docker_compose.py` incidentally renders `has_db=false` via
copier subprocess, but it only checks docker-compose YAML parsing — it does NOT
walk the scaffold tree for file-gate violations or check conftest content.

**Suggested test name:**
`test_has_backend_true_has_db_false_no_db_files_in_scaffold`

**Key assertions:**
```python
assert not (scratch / "app" / "db.py").exists()
assert not (scratch / "app" / "schema.py").exists()
assert not (scratch / "alembic").exists()
assert not (scratch / "alembic.ini").exists()
conftest = (scratch / "tests" / "backend" / "conftest.py").read_text()
assert "pg_container" not in conftest
assert "PostgresContainer" not in conftest
assert not (scratch / "tests" / "backend" / "test_db_integration.py").exists()
```

**Do-now vs defer:** DO-NOW. This is the second most important polarity cell
(has_backend with no DB is a primary use case) and a regression here would
silently ship broken scaffolds with leaked db.py or missing fixture gating.

---

### GAP-02 — HIGH | Opt-in polarity only checks text content, not file-gate correctness for the (True, True) cell with has_db=True

**What is currently tested:**
`test_phase04_optin_polarity.py` parametrizes all 4 `(has_logfire × has_fastapi_mcp)`
cells but always uses `has_db=False`. None of the four cells tests the full
`(has_backend=True, has_db=True, has_logfire=True, has_fastapi_mcp=True)` combination.
The optin polarity test only checks `main.py` and `pyproject.toml` string content —
it never checks that `logfire` config is guarded by `has_backend and has_logfire`
(not just `has_logfire` alone).

**What is missing:**
A render with `has_backend=False, has_logfire=True` is not exercised (copier
gates logfire on `when: "{{ has_backend }}"` but the test never forces this
combination to confirm the gate holds). Additionally, the currently tested cells
only assert import strings in `main.py`; they do not assert that the LOGFIRE_TOKEN
guard (`if os.environ.get("LOGFIRE_TOKEN")`) is present when `has_logfire=True`,
meaning a regression that removes the token guard but keeps the import would pass.

**Suggested test name:**
`test_logfire_token_guard_present_when_has_logfire_true`

**Key assertions:**
```python
main_py = (scratch / "app" / "main.py").read_text()
# Not just "import logfire" — must also contain the token guard:
assert "LOGFIRE_TOKEN" in main_py, "logfire must be guarded by LOGFIRE_TOKEN env var"
assert 'send_to_logfire=False' in main_py, "fallback to local sink when token absent"
```

**Do-now vs defer:** DO-NOW. The LOGFIRE_TOKEN guard is a hard requirement (the
scaffold must not send traces without user consent); its absence won't be caught
by the existing string-presence check for `"import logfire"`.

---

### GAP-03 — HIGH | Docker stack lifecycle has no orphan-container assertion after failure

**What is currently tested:**
`test_phase04_integration.py::test_fresh_scaffold_verify_backend_full_path_exits_zero`
runs `just verify-backend` which calls `docker-down` at the end of its recipe.
If the recipe exits non-zero before reaching `just docker-down` (e.g., schemathesis
finds a violation), the integration test does a best-effort teardown
(`subprocess.run(["just", "docker-down"], check=False)`) but does NOT assert
the teardown succeeded or that no containers are orphaned.

**What is missing:**
After any verify-backend run (pass OR fail), assert that no containers from
the scaffold's compose project are still running. A failing schemathesis run
followed by a failing `just docker-down` could leave postgres and jaeger
containers alive on the developer's machine indefinitely — exactly the "orphan
container" regression the phase's MEDIUM concern (04-REVIEWS.md cycle 2)
described but did not add a test for.

**Suggested test name:**
`test_verify_backend_full_path_leaves_no_orphan_containers`

**Key assertions:**
```python
import subprocess
r = subprocess.run(
    ["docker", "compose", "-f", str(scratch / "docker-compose.yml"),
     "ps", "--services", "--filter", "status=running"],
    cwd=scratch, capture_output=True, text=True
)
assert r.stdout.strip() == "", (
    f"Orphan containers still running after verify-backend: {r.stdout}"
)
```

**Do-now vs defer:** DO-NOW for the test. The recipe itself uses a recipe-level
teardown without `trap` semantics (just is not bash; `just recipe-a || just recipe-b`
does NOT guarantee `recipe-b` runs if `recipe-a` fails because `just` stops on
first recipe error). This is also an implementation gap — the recipe needs a
`set -e` / try-finally equivalent — but that is an ESCALATE item, not a test fix.

---

### GAP-04 — MEDIUM | 422 Unprocessable Entity is declared in OpenAPI schema but not behaviorally tested

**What is currently tested:**
`/echo` declares `400` in its `responses={}` dict (for malformed JSON before Pydantic).
FastAPI automatically emits 422 for Pydantic validation failures (missing required
field, wrong type). No test sends a request that triggers 422 and asserts the
response body conforms to FastAPI's `HTTPValidationError` schema.

**What is missing:**
A test that sends a syntactically-valid JSON body that fails Pydantic validation
(e.g., `{"wrong_field": "x"}` to `/echo` which requires `{"message": str}`) and
asserts:
- Status code is 422
- Response body contains `"detail"` key (FastAPI's standard 422 shape)
- Schemathesis would not flag this as undocumented (implicitly covered, but worth
  a direct probe since 422 is auto-emitted without appearing in `responses={}`)

Without this, a change that accidentally removes the `EchoRequest.message` field
declaration (breaking Pydantic validation) would still pass all current tests
because all current tests send well-formed requests.

**Suggested test name:**
`test_echo_invalid_body_returns_422`

**Key assertions:**
```python
r = client_dev.post("/echo", json={"wrong_field": "x"})
assert r.status_code == 422
assert "detail" in r.json()
```

**Do-now vs defer:** DO-NOW. 422 is the most common error path for REST APIs;
zero behavioral coverage of the validation-error path is a pure sampling gap.

---

### GAP-05 — MEDIUM | CLI→models cross-surface contract only tests the happy path

**What is currently tested:**
`test_cli.py::test_cli_echo_outputs_valid_echo_response` sends `--message hello`
and asserts the response deserializes into `EchoResponse`. This confirms the
happy path shares the Pydantic model. Nothing tests what happens when the CLI
receives invalid input — whether it exits non-zero, whether it prints a useful
error, and whether the error path bypasses the shared model correctly.

**What is missing:**
Test `app-cli echo` with a missing required arg (or an illegal flag value) and
assert:
- Exit code is non-zero (Typer should exit 2 for missing arg)
- stderr contains a helpful message (not a Python traceback)
- The `EchoResponse` model is NOT rendered in stdout (error path must not
  produce partial JSON that looks like a valid response)

**Suggested test name:**
`test_cli_echo_missing_message_arg_exits_nonzero_with_usage`

**Key assertions:**
```python
r = subprocess.run(["uv", "run", "app-cli", "echo"], cwd=scratch_root, ...)
assert r.returncode != 0
# Typer usage error, not a Python traceback
assert "Error" in r.stderr or "Usage" in r.stderr
assert "Traceback" not in r.stderr
```

**Do-now vs defer:** DO-NOW. CLI error handling is a common regression target
and the cross-surface sharing of Pydantic models means a model change could
break CLI error rendering in non-obvious ways.

---

### GAP-06 — MEDIUM | in-process schemathesis fuzz: `--max-examples` arg is parsed but silently ignored

**What is currently tested:**
`harness/checks/backend_inprocess_fuzz.py` parses `--max-examples N` via argparse
and stores it in `args.max_examples`. The `schemathesis.engine.from_schema(schema)`
call and the subsequent `engine.execute()` iteration do NOT pass any
`hypothesis.settings(max_examples=N)` configuration. `args.max_examples` only
appears in the final print message (line 88): the engine runs with schemathesis
defaults regardless of what `--max` was requested.

No test asserts that the argument actually changes the number of test cases run.

**What is missing:**
Either:
(a) Pass hypothesis settings to the engine so the argument is honored (implementation
    fix — ESCALATE), OR
(b) Test that confirms the engine respects the argument by mocking/patching the
    hypothesis settings object and asserting `max_examples=N` was passed.

**Suggested test name:**
`test_inprocess_fuzz_max_examples_arg_is_honored`

**Key assertion shape** (after implementation fix):
```python
# Confirm that engine.execute() is called with hypothesis settings reflecting
# the --max-examples flag, not the schemathesis default.
```

**Do-now vs defer:** DEFER to follow-up. The silent ignore means users get less
fuzz coverage than they expect when they pass `--max-examples 5` for a fast
local run. It's a usability gap but not a correctness regression (more tests
run = conservative). File as a Beads issue; fix in a patch after Phase 4 closes.

---

### GAP-07 — MEDIUM | MCP mount probe only checks "not 404" — no actual MCP handshake

**What is currently tested:**
`test_fastapi_mcp_opt_in.py::test_fastapi_mcp_is_mounted` does `GET /mcp` and
asserts `status_code != 404`. `test_mcp_tools_introspection` tries three URL
candidates and asserts "at least one is not 404."

The 04-REVIEWS-RESPONSE.md explicitly deferred "a real MCP `initialize` +
`tools/list` handshake" to Phase 5. However, this constitutes a sampling gap:
`FastApiMCP(app).mount()` could mount successfully at `/mcp` but expose zero tools
(i.e., if `include_router` calls were not made before `mount()`), and neither
test would catch it.

**What is missing:**
A test that issues the MCP `initialize` request and then reads the `tools/list`
response to confirm at least one tool corresponds to an app route (e.g., `healthz`
or `echo`). The fastapi-mcp library follows the JSON-RPC 2.0 / MCP protocol; a
minimal two-request exchange is achievable with `httpx` in the test client.

**Suggested test name:**
`test_mcp_tools_list_contains_app_routes`

**Key assertion shape:**
```python
# POST /mcp with initialize message, then request tools/list
# Assert the response contains at least one tool name matching a known route
assert any(tool["name"] in ("healthz", "echo") for tool in tools_list)
```

**Do-now vs defer:** DEFER to Phase 5 as acknowledged in 04-REVIEWS-RESPONSE.md.
Record here for tracking. The phase-level `just verify-backend` integration test
would surface a total MCP-mount failure anyway.

---

### GAP-08 — LOW | `verify-backend-quick` has no wall-clock time assertion

**What is currently tested:**
`test_fresh_scaffold_verify_backend_quick_skips_live_checks` asserts exit code 0
and checks for "app not running" or "app reachable" in stdout. The test uses a
900-second timeout but makes no assertion that the command completes in under 30
seconds (the stated design intent for "quick" — no docker overhead).

**What is missing:**
A timing assertion that fails if `verify-backend-quick` takes longer than a
threshold (e.g., 90 seconds) without docker. Without this, `verify-backend-quick`
could regress to pull docker images or spin up containers and still exit 0.

**Suggested test name:**
`test_verify_backend_quick_completes_under_time_budget`

**Key assertion shape:**
```python
import time
start = time.monotonic()
r = subprocess.run(["just", "verify-backend-quick"], ...)
elapsed = time.monotonic() - start
assert elapsed < 90, f"verify-backend-quick took {elapsed:.1f}s — exceeds 90s no-docker budget"
```

**Do-now vs defer:** DEFER. The 900-second subprocess timeout already prevents
infinite hang. A CI timing assertion is fragile on slow runners. Log the wall
clock in the test output but do not hard-assert until a baseline is established.

---

### GAP-09 — LOW | harness.registry does not have a polarity test: "backend" check absent when has_backend=False

**What is currently tested:**
`test_phase04_optin_polarity.py` and `test_phase04_scaffold_polarity.py` verify
file-level presence/absence. `harness/checks/__init__.py.jinja2` conditionally
imports `backend` only when `has_backend=True`. No test renders a
`has_backend=False` scaffold and then imports `harness.checks` to confirm that
`harness.registry.get_check("backend")` returns `None`.

**What is missing:**
A test in the outer verify-kit test suite that renders a `has_backend=False`
scratch project, installs it, and asserts:
```python
import importlib
harness_checks = importlib.import_module("harness.checks")
from harness import registry
assert registry.get_check("backend") is None, (
    "backend check must NOT register when has_backend=False"
)
```

**Do-now vs defer:** DEFER. The _exclude block in copier.yml removes the
backend.py file entirely when `has_backend=False`, so the conditional import
in `__init__.py` is belt-and-suspenders. Importing from a non-existent file
would raise `ImportError` visibly, making a silent-false-pass unlikely. File
as a Beads chore for Phase 5 cleanup.

---

### GAP-10 — LOW | `__debug/state` endpoint: malformed state.json returns 500, not a declared error code

**What is currently tested:**
`test_debug_endpoints.py` tests the 200 (file present) and 404 (file absent) paths.
It does NOT test what happens when `.verify/state.json` contains malformed JSON
(e.g., truncated by a mid-write crash). In that case, `json.loads()` raises
`ValueError`, which FastAPI would catch as an uncaught exception and return 500.

**What is missing:**
A test that writes invalid JSON to the state file and asserts either:
- The endpoint returns a graceful 422/500 with a JSON error body (not a raw
  Python traceback), OR
- The endpoint returns the raw text with `Content-Type: text/plain` as a
  documented degraded response

**Suggested test name:**
`test_debug_state_malformed_json_returns_graceful_error`

**Key assertions:**
```python
state_file = tmp_path / ".verify" / "state.json"
state_file.write_text("{broken json")
r = client_dev.get("/__debug/state")
assert r.status_code in (422, 500), "malformed state.json must not return 200"
# Must not be a raw Python traceback in the response
assert "Traceback" not in r.text
```

**Do-now vs defer:** DEFER. The debug endpoint is dev-only and a corrupt state.json
is a developer-visible edge case. Log for Phase 5.

---

## Summary Table

| Gap ID | Severity | Area | Currently Tested | Missing | Recommendation |
|--------|----------|------|-----------------|---------|----------------|
| GAP-01 | HIGH | Render polarity (has_backend×has_db) | (T,T), (F,F) cells only | (T,F) cell: absent db.py, schema.py, alembic; conftest has no pg_container | DO-NOW |
| GAP-02 | HIGH | Opt-in polarity (logfire) | Import string present/absent | LOGFIRE_TOKEN guard + send_to_logfire=False fallback | DO-NOW |
| GAP-03 | HIGH | Docker stack lifecycle | Exit code 0 + schemathesis URL in stdout | Orphan container assertion after pass or fail | DO-NOW |
| GAP-04 | MEDIUM | Error-path coverage (422) | 400 declared, 200 happy path tested | 422 Pydantic validation error behavioral test | DO-NOW |
| GAP-05 | MEDIUM | CLI error path (cross-surface contract) | Happy path (valid message) | Invalid/missing arg → non-zero exit, no traceback | DO-NOW |
| GAP-06 | MEDIUM | in-process fuzz: max_examples | Argument parsed | Argument not passed to hypothesis engine (dead arg) | DEFER (impl bug — escalate) |
| GAP-07 | MEDIUM | MCP handshake depth | Non-404 probe | Actual MCP initialize + tools/list handshake | DEFER (Phase 5) |
| GAP-08 | LOW | verify-backend-quick time budget | Exit code 0 + graceful-degrade message | Wall-clock < 90s assertion | DEFER |
| GAP-09 | LOW | harness.registry polarity | File gate (backend.py absent) | Registry.get_check("backend") is None in rendered scaffold | DEFER |
| GAP-10 | LOW | debug endpoint error path | 200 + 404 paths | Malformed state.json returns graceful error | DEFER |

---

## Do-Now Gap Test Names (for implementation)

| Gap | Test File | Test Function |
|-----|-----------|---------------|
| GAP-01 | `tests/test_phase04_scaffold_polarity.py` | `test_has_backend_true_has_db_false_no_db_files_in_scaffold` |
| GAP-02 | `tests/test_phase04_optin_polarity.py` | `test_logfire_token_guard_present_when_has_logfire_true` |
| GAP-03 | `tests/test_phase04_integration.py` | `test_verify_backend_full_path_leaves_no_orphan_containers` |
| GAP-04 | `template/tests/backend/{% if has_backend %}test_app.py{% endif %}.jinja2` | `test_echo_invalid_body_returns_422` |
| GAP-05 | `template/tests/backend/{% if has_backend %}test_cli.py{% endif %}.jinja2` | `test_cli_echo_missing_message_arg_exits_nonzero_with_usage` |

---

## Implementation Notes: GAP-06 Escalation

`harness/checks/backend_inprocess_fuzz.py.jinja2` lines 26 and 88 parse and echo
`args.max_examples` but never pass it to the schemathesis engine. The engine runs
with hypothesis defaults (`max_examples=100` in schemathesis defaults). The fix is
one call:

```python
from hypothesis import settings as h_settings
# After: engine = schemathesis.engine.from_schema(schema)
# Before: engine.execute()
# Add: engine = schemathesis.engine.from_schema(schema, hypothesis_settings=h_settings(max_examples=args.max_examples))
# (exact API depends on schemathesis version; confirm against docs)
```

This is an **implementation bug in a template file** — it cannot be fixed in this
validation task. Escalate to developer before Phase 5 begins. The consequence is
that passing `--max-examples 5` for fast local iteration is silently disregarded,
which undermines the developer UX the quick-path is meant to provide.

---

_Validation: 2026-05-21_
_Validator: Claude (nyquist-auditor)_
_Cross-reference: 04-VERIFICATION.md (psycopg2 fixture bug documented there, not here)_

---

## Phase 6 Closure Reconciliation (2026-05-23, per 06-10)

`/gsd:validate-phase 4` re-run reconciles the 3 deferred HIGH gaps (originally
filed as beads at Phase 4 close, deferred to "Phase 6 self-test sweep" per
STATE.md:88). Reconciliation does NOT no-op — it inspects each Bead against
post-Phase-5 reality and decides still-applicable vs obsolete.

| Bead ID | Gap | Phase 5 impact? | Decision | Disposition |
|---------|-----|-----------------|----------|-------------|
| verify-kit-plk | GAP-01: missing (has_backend=T, has_db=F) polarity test | None — Phase 5 added llm-add-on code; did not touch backend polarity matrix | still applicable | Leave OPEN; v0.1.1 milestone work |
| verify-kit-c5a | GAP-02: LOGFIRE_TOKEN guard not asserted | None — Phase 5 did not modify logfire opt-in surface | still applicable | Leave OPEN; v0.1.1 milestone work |
| verify-kit-r7v | GAP-03: verify-backend orphan container teardown unasserted | None — Phase 5 did not modify just verify-backend recipe or docker-compose lifecycle | still applicable | Leave OPEN; v0.1.1 milestone work |

**Outcome:** 0 beads closed as obsolete. 0 new gaps surfaced beyond the existing
10. `gap_count` and `severity_counts` in frontmatter remain accurate. Per plan
§10, in-scope generation of the missing tests is OUT of scope for Phase 6 — the
3 HIGHs ship as documented v0.1.1 follow-up work.

| Audit Date | Action | Run By |
|------------|--------|--------|
| 2026-05-21 | Initial Nyquist validation (10 gaps identified) | Claude (nyquist-auditor) |
| 2026-05-23 | Phase 6 closure reconciliation per 06-10: all 3 HIGHs still applicable; deferred to v0.1.1; no new gaps surfaced | Claude (executor agent, per 06-10 Task 2) |
