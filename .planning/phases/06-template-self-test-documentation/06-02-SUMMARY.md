---
phase: 06-template-self-test-documentation
plan: "06-02"
plan_name: auth-scaffold
type: summary
wave: 2
closes_beads: [verify-kit-3u2]
commits:
  - 3935e26 feat(auth): add X-VerifyKit-Token route auth scaffold
  - 3e92ba5 feat(auth): document VERIFYKIT_AUTH_TOKEN slot in root .env.example
  - 96027bf chore(copier): admit root .env.example for backend-only renders
  - 8b3dc30 test(polarity): update Phase 5 env-destination assertions for new auth contract
  - 87de75e test(auth): add Phase 6 auth polarity matrix
files_created:
  - "template/{% if has_backend %}app{% endif %}/auth.py.jinja2"
  - "template/{% if has_backend %}.env.example{% endif %}.jinja2"
  - tests/test_phase06_auth_polarity.py
files_modified:
  - "template/{% if has_backend %}app{% endif %}/main.py.jinja2"
  - "template/{% if has_backend %}app{% endif %}/settings.py.jinja2"
  - copier.yml
  - tests/test_phase05_polarity.py
---

# Plan 06-02: Auth Scaffold — Summary

Closes bead `verify-kit-3u2`. Adds the `X-VerifyKit-Token` route-auth scaffold so any downstream `copier copy` consumer ships a token-gated backend by default (no public-by-default endpoints).

## Producer contract exposed to downstream plans

Downstream plans (06-03 /summarize defenses, 06-04 /echo hardening, 06-06 README, 06-08 self-test CI) must reference these exact symbols:

- **Import path:** `from app.auth import require_auth`
- **Env var:** `VERIFYKIT_AUTH_TOKEN`
- **HTTP header:** `X-VerifyKit-Token`
- **Settings field:** `Settings.VERIFYKIT_AUTH_TOKEN: str | None` (UPPERCASE, matches existing convention)
- **Settings access pattern inside `require_auth`:** `settings = request.app.state.settings` (no `get_settings` factory)
- **Excluded route:** `GET /healthz` — via in-dependency `request.url.path == "/healthz"` short-circuit (NOT route-level `dependencies=[]`, which FastAPI does not honor as an override of app-level dependencies)
- **Dev fallback:** token unset AND `settings.ENV == "dev"` → allowed, one-line warning logged once
- **Non-dev with unset token:** HTTP 503 (config error, distinct from 401 auth error)

### Exact `require_auth` signature (as committed)

```python
def require_auth(
    request: Request,
    presented: Annotated[str | None, Depends(_api_key_header)],
) -> None:
```

`_api_key_header = APIKeyHeader(name="X-VerifyKit-Token", auto_error=False)` at module scope. Token comparison uses `secrets.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))` (constant-time).

## Test coverage matrix

`tests/test_phase06_auth_polarity.py` — 11 tests, all passing in 57.8s:

| Test | Cell |
|------|------|
| `test_has_backend_false_has_no_app_dir` | has_backend=false |
| `test_root_env_example_contains_auth_slot[False]` | has_backend=true, has_llm=false |
| `test_root_env_example_contains_auth_slot[True]` | has_backend=true, has_llm=true |
| `test_root_env_example_has_no_planning_meta_ids` | Pattern 6 forcing function |
| `test_auth_slot_not_at_wrong_path` | Negative: auth slot NOT in app/.env.example |
| `test_main_py_wires_global_dependency` | Producer wiring |
| `test_auth_module_uses_canonical_primitives` | Producer primitives |
| `test_runtime_dev_no_token_allows` | (dev, no token, no header) → 200 |
| `test_runtime_prod_no_token_returns_503` | (prod, no token, *) → 503 |
| `test_runtime_dev_with_token` | (dev, token, header) → 200; missing/wrong → 401 |
| `test_runtime_loader_reads_root_env_file` | Test 1c: .env at root resolves into Settings |

Phase 5 env-destination polarity (`tests/test_phase05_polarity.py -k env_destination`) — 8/8 passing under the rewritten contract. Phase 4 scaffold polarity — 3/3 passing.

## Path-correction reasoning (why root, not `app/`)

`Settings.load(cwd)` at `template/{% if has_backend %}app{% endif %}/settings.py.jinja2:27` reads `cwd / ".env"` — the project root, not `cwd / "app/.env"`. The pre-existing `app/.env.example` is therefore at a path the runtime loader never reads; documenting `VERIFYKIT_AUTH_TOKEN` there would be functionally inert (consumer copies it to `app/.env`, loader still sees an empty token, dev fallback fires silently in prod-like dev environments).

The fix: a NEW file `template/{% if has_backend %}.env.example{% endif %}.jinja2` at the project root. It is mutually exclusive with the existing LLM-only root file (gated `has_llm and not has_backend`) — both file paths can co-exist in the template tree without a copier merge conflict because at most one renders for any given polarity.

The legacy `app/.env.example.jinja2` is left untouched; deprecating it is out of scope for this auth fix (separate hygiene pass after Phase 6).

## copier.yml `_exclude` fix (cycle-6)

Old exclusion rules at lines 49–50 dropped root `.env.example` whenever `has_llm` was false. Under the new contract, the backend root file must ship for the `(+backend, has_llm=false)` matrix row. Rewritten to gate on `(not has_llm and not has_backend)`.

## Phase 5 polarity test update (cycle-7)

The cycle-6 `_exclude` change rewrote the rendered-file contract — root `.env.example` is now canonical whenever `has_backend=true`. Per REVIEW-CHECKLIST §3 (contracts live with producers), the legacy `tests/test_phase05_polarity.py::test_env_destination_per_cell_*` branches were rewritten in this plan (06-02 is the producer of the new env-destination rule). The Phase 5 tests now allow both `root_env` and `app_env` to exist when `has_backend=true`; the contract is that the root file carries the auth slot, and neither file carries LLM keys when `has_llm=false`.

## Deviations from plan

None. All 7 convergence-cycle fixes + 4 manual fixes preserved as authored.

## Bead closure

`verify-kit-3u2` closed with reason: "Token auth scaffold landed in 06-02; APIKeyHeader + global dependency + dev fallback + /healthz exclusion".

## Self-check

- [x] `template/{% if has_backend %}app{% endif %}/auth.py.jinja2` exists
- [x] `template/{% if has_backend %}.env.example{% endif %}.jinja2` exists at root
- [x] All 5 commits visible in `git log` (3935e26, 3e92ba5, 96027bf, 8b3dc30, 87de75e)
- [x] No `VERIFYKIT_AUTH_TOKEN` in `app/.env.example.jinja2` (wrong-path negative assertion)
- [x] No planning IDs in rendered root .env.example (Pattern 6)
- [x] Phase 6 polarity: 11/11 passing
- [x] Phase 5 env_destination polarity: 8/8 passing
- [x] Phase 4 scaffold polarity: 3/3 passing
