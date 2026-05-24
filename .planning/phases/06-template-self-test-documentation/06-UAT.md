---
status: gaps_identified
phase: 06-template-self-test-documentation
source:
  - 06-01-SUMMARY.md through 06-10-SUMMARY.md
started: 2026-05-24T00:00:00Z
updated: 2026-05-24T03:00:00Z
verifier: claude (ran from repo root via /gsd:verify-work)
scratch_dir: /tmp/scratch-phase6-uat-1779580449
---

## Summary

total: 8
passed: 7
failed: 1
issues: 6 (2 CRITICAL/P0, 2 MEDIUM/P2, 2 LOW/P3)
pending: 0
skipped: 0

## Tests

### 1. Cold-Start Smoke Test (scratch project) — FAIL
- copier copy succeeded with full prompt set
- mise install → required `mise trust` first (GAP-4)
- uv sync → required `--extra dev` for pytest/ruff (GAP-5)
- `just verify` → fails (3 of 8 checks):
  - **fail:** backend pytest — 8 of 22 tests return 401 because rendered backend tests don't pass X-VerifyKit-Token (GAP-1)
  - **fail:** schemathesis in-process fuzz — AttributeError on app.state.settings (GAP-2)
  - **fail:** format.ruff — happens because dev extras weren't installed first; resolves with --extra dev
- Also surfaced: app/.env.example contains "Plan 05-01" comments (GAP-3)

### 2. README front-door experience — PASS
- All required sections present in correct order: Quickstart (with uv tool install line + copier --trust), Why this exists, Philosophy, Add-on inventory, Architecture (inline Mermaid), Dual-audience checklist, Security (auth + summarize + echo), Updating an existing project, Troubleshooting (3 symptoms), Releases & contributing
- Key contracts referenced verbatim from 06-02/03/04: X-VerifyKit-Token, VERIFYKIT_AUTH_TOKEN, OWASP LLM01 caveat sentence
- Pattern 6 clean (no planning IDs in README content)

### 3. CHANGELOG.md shape + commit contract — PASS
- release-please-config.json + .release-please-manifest.json present at repo root
- Manifest pinned at version 0.0.0 baseline
- CHANGELOG.md has [Unreleased] section with empty "Breaking changes for consumers" callout
- Convention documented (link to CONTRIBUTING.md for commit-message contract)

### 4. CONTRIBUTING.md add-a-check snippet — PASS
- Uses correct harness API: `from harness.registry import register` + `from harness.models import CheckResult`
- Decorator positional `register("my-check", tier="standard", category="example")` (not kwarg `id=`)
- `tier="standard"` (not invalid `"universal"`)
- Drift-denial grep clean: no @register_check, no CheckResult(ok=, no tier="universal", no harness.checks
- (Cycle-3 manual fix verified)

### 5. Mermaid architecture diagram — PASS
- Block present in README; starts with `flowchart TD` (not `graph TD`)
- `classDef shipped` + `classDef deferred` present
- All 5 add-on slots referenced: Backend, LLM, Web, Audio, Game
- "Universal Foundation" subgraph present

### 6. Self-test CI matrix YAML — PASS
- Linux workflow: ubuntu-latest, fail-fast: false, 5-combo matrix [base, backend, llm, backend-llm, full]
- Each include entry has full 5-key data: has_backend / has_llm / has_logfire / has_fastapi_mcp / has_db (cycle-4 fix verified)
- has_db per row: base=False, backend=True, llm=False, backend-llm=True, full=True
- `--with copier-templates-extensions` install line present (cycle-3 fix) — but see GAP-6 about renamed package
- `--trust` flag on copier copy present
- VERIFYKIT_AUTH_TOKEN + ENV env wired at job level
- macOS sibling: macos-latest, triggers=[schedule, workflow_dispatch] (NO pull_request)

### 7. Phase 6 + Phase 5 polarity tests — PASS
- 96 passed, 1 warning (DeprecationWarning re: copier-templates-extensions rename → GAP-6) in 368s
- All four test files green: test_phase06_auth_polarity (11), test_phase06_summarize_defenses_polarity (9), test_phase06_echo_hardening_polarity (7), test_phase05_polarity (69)
- No regression on Phase 5 from the cycle-7 env-destination contract rewrite

### 8. OSS-launch boilerplate — PASS
- LICENSE (MIT) at root
- CODE_OF_CONDUCT.md (Contributor Covenant 2.1, email m.moiz1995@gmail.com substituted)
- SECURITY.md at root with Security Policy header
- .github/ISSUE_TEMPLATE/{bug,feature,config}.yml all present
- .github/pull_request_template.md present with all 6 dual-audience rows verbatim

## Gaps

### GAP-1 (P0 / CRITICAL): rendered backend tests fail with 401 / app.state.settings
**Bead:** `verify-kit-7uu`
8 of 22 Phase 4 backend tests fail in rendered scratch when VERIFYKIT_AUTH_TOKEN is set. Cycle-2 fix only updated NEW polarity tests; cycle-7 fix only touched template-level test_phase05_polarity.py. Rendered `template/tests/backend/*.py.jinja2` never updated.
Fix: update `template/tests/backend/conftest.py.jinja2` `client_dev`/`client_prod` fixtures to override `require_auth` via `app.dependency_overrides`.

### GAP-2 (P0 / CRITICAL): schemathesis in-process fuzz crashes
**Bead:** `verify-kit-52u`
`harness/checks/backend_inprocess_fuzz.py:64` uses `TestClient(app)` without lifespan; `profile_middleware` reads unbound `app.state.settings`.
Fix: wrap app in `LifespanManager` (asgi-lifespan, already in deps) before passing to schemathesis.

### GAP-3 (P2 / MEDIUM): app/.env.example Pattern 6 leak
**Bead:** `verify-kit-idp`
`template/{% if has_backend %}app{% endif %}/.env.example.jinja2` contains `# LLM credentials (Plan 05-01)` + `# Eval gating (Plan 05-01)` — 06-01 Task 3 scrub missed env-example files.
Fix: rewrite to evergreen wording.

### GAP-4 (P3 / LOW): README quickstart missing `mise trust` step
**Bead:** `verify-kit-ksd`
Fresh scratch project requires `mise trust` before `mise install` works. Quickstart doesn't mention it.
Fix: add `mise trust` step or auto-trust via copier `_tasks`.

### GAP-5 (P3 / LOW): `uv sync` doesn't install dev extras
**Bead:** `verify-kit-9fh`
Quickstart doesn't tell consumers to `uv sync --extra dev` for pytest/ruff.
Fix: move dev to `[dependency-groups]`, OR document, OR make `just verify` self-heal.

### GAP-6 (P2 / MEDIUM): `copier-templates-extensions` renamed to `copier-template-extensions` (singular)
**Bead:** `verify-kit-sjx`
DeprecationWarning emitted on every polarity test run. Old name still works but will be removed in a future copier-template-extensions release.
Fix: search-replace across README, workflow YAML, CONTRIBUTING, copier.yml.

## Verdict

**7/8 tests pass — Test 1 cold-start fails on 2 P0 regressions that the plan-text convergence loop couldn't see.** Phase 6 is functionally close to complete but has real consumer-facing breakage on the auth-token-set path. The 2 P0 gaps are mechanical fixes (~30-45 min combined). The 1 P2 (Pattern 6 leak) is a quick rewrite. The 2 P3s are UX polish. GAP-6 is dependency upgrade + 3-line search-replace.

**Status:** Phase 6 is `gaps_identified`. v0.1 is NOT OSS-ready until at minimum GAP-1, GAP-2, GAP-3 are closed.

## Next steps

Per `/gsd:verify-work` standard exit:
```
/gsd:plan-phase 6 --gaps
```
This reads 06-UAT.md and generates a focused gap-closure plan for the 6 beads.

Alternatively, fix the 2 P0 gaps inline (no need for a full replan — they're mechanical), then re-run /gsd:verify-work to confirm green.
