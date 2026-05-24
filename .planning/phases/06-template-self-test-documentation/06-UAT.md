---
status: gaps_identified
phase: 06-template-self-test-documentation
source:
  - 06-01-SUMMARY.md through 06-10-SUMMARY.md
  - 06-11-SUMMARY.md  # gap-closure sweep closing GAP-1..6
started: 2026-05-24T00:00:00Z
updated: 2026-05-24T05:00:00Z
re_verified_after: 06-11 (commits c12edef → d0f87b9, b172b17)
verifier: claude (re-ran from repo root after 06-11 gap closure)
scratch_dir: /tmp/scratch-reverify-1779615312
---

## Summary (post 06-11 re-verification)

total: 8
passed: 7
failed: 1
issues: 1 (GAP-7 P1 — pre-existing lint/format scaffold defect, unmasked by GAP-5 closure)
gaps_closed_this_round: 6 (verify-kit-7uu, -52u, -idp, -sjx, -ksd, -9fh)
pending: 0
skipped: 0

## Per-check verdict on post-06-11 cold-start (verify-kit verify report)

| Check | Pre-06-11 | Post-06-11 |
|---|---|---|
| mise.toml.valid | pass | pass |
| copier.answers.valid | pass | pass |
| just-list.renders | pass | pass |
| lint.ruff | (masked — ruff missing) | **fail (GAP-7)** |
| lint.biome | skip | skip |
| format.ruff | fail (was: cascading from missing dev extras) | **fail (GAP-7)** |
| format.biome | skip | skip |
| backend | **fail (8 of 22 tests 401)** | **pass (22/22)** ✅ |
| schemathesis in-process fuzz | fail (AttributeError) | pass ✅ |

Backend slice green on BOTH auth paths (token SET and UNSET). The 2 P0 gaps that drove the v0.1-not-OSS-ready verdict are CLOSED.

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

### GAP-7 (P1 / HIGH): rendered scaffold ships unformatted / un-linted code
**Bead:** `verify-kit-ooj` — surfaced by 06-11 Task 6 cold-start gate after GAP-5 was closed.
After the quickstart now installs `--extra dev`, `ruff` actually runs and finds 85 lint issues + 60 files needing reformat across the rendered scaffold (`alembic/versions/0001_initial.py`, `app/api.py`, `app/cli.py`, `app/main.py`, `app/models.py`, `app/settings.py`, etc.). Root cause: `template/*.jinja2` source files were never normalised through `ruff format` / `ruff check --fix` before being committed.
Fix shape: render scratch project, run `uv run ruff format . && uv run ruff check . --fix`, diff back into `template/`, commit. Backend slice (the focus of GAP-1+2) passes cleanly with token both SET and UNSET; this is a separate v0.1 polish gap.

## Verdict (post 06-11 re-verification)

**7/8 tests still pass; Test 1 still fails but on a DIFFERENT bug class than before.** The 2 P0 gaps (auth-broken backend tests + schemathesis lifespan crash) and the 4 P2/P3 gaps from the original verify-work run are CLOSED. The new fail (lint.ruff + format.ruff on 85+60 issues) is a pre-existing scaffold defect that was previously masked because `ruff` wasn't installed in the venv — GAP-5's `--extra dev` fix unmasked it.

**Status:** Phase 6 is **`gaps_identified` (1 remaining: GAP-7 P1)**.

**OSS-ready assessment shift:**
- The 2 ORIGINAL P0 blockers (auth contract broken for consumers) are gone — consumer code-paths through `/summarize`, `/echo`, `/__debug/*`, and the backend test suite all work correctly.
- The remaining GAP-7 is a code-quality issue (un-formatted scaffold output) — a stranger landing on the repo would `copier copy → just verify` and see "85 lint issues" rather than 22 broken test assertions. Embarrassing but not BROKEN.
- v0.1 could ship with GAP-7 documented as "first release of the scaffold needs a one-time formatting pass" — OR closed in a 5-min `ruff format + ruff check --fix` round before tagging.

## Next steps

Per /gsd:verify-work standard exit with 1 P1 gap remaining:
1. **Recommended:** close GAP-7 inline (5-min `ruff format` pass against rendered scratch, diff back to `template/`), then re-run `/gsd:verify-work 6` for the 8/8 PASS verdict that tags v0.1 OSS-ready.
2. **Alternate:** declare v0.1 with GAP-7 documented in CHANGELOG as "known issue — formatting pass in v0.1.1", route to v0.1.1 hardening cycle.
