---
phase: 6
reviewers: [codex]
reviewed_at: 2026-05-22T21:54:11Z
plans_reviewed:
  - 06-01-PLAN.md
  - 06-02-PLAN.md
  - 06-03-PLAN.md
  - 06-04-PLAN.md
  - 06-05-PLAN.md
  - 06-06-PLAN.md
  - 06-07-PLAN.md
  - 06-08-PLAN.md
  - 06-09-PLAN.md
  - 06-10-PLAN.md
---

# Cross-AI Plan Review — Phase 6

## Codex Review

## Summary

The Phase 6 plan set is strong on documentation, sequencing, cross-plan contracts, and OSS launch coverage. The main risk is not plan structure; it is source drift in the hardening plans. Plans 06-02, 06-03, and 06-04 assume several APIs and file locations that do not match the current template. I would not execute Phase 6 until those are corrected, because the first implementation wave touching auth and `/echo` will fail or silently harden the wrong file.

## Strengths

- The 10-plan / 6-wave breakdown is coherent and mostly dependency-clean.
- DOC-01 through DOC-05 are covered, including the previously flagged README gaps for `copier update` and troubleshooting.
- The self-test CI plan now includes `--full` support for `act`, which resolves the earlier SC5 ambiguity.
- Bead closure is explicit for `verify-kit-3u2`, `verify-kit-yr7`, `verify-kit-93h`, and `verify-kit-1v6`.
- The PR template and README reuse the six-row dual-audience checklist, which is the right enforcement mechanism for this phase.
- The REVIEW-CHECKLIST lessons are mostly reflected in the plan text: top-level tests, clean env use, cross-plan contracts, no `--only=backend`, no `CheckResult(ok=...)`.

## Source-Grounding Pass

**VERIFIED**

- `Settings` exists, but uses uppercase `ENV`, not lowercase `env`: `template/{% if has_backend %}app{% endif %}/settings.py.jinja2:7`, `:15`
- Settings loader is `load(cwd: Path)`, not `get_settings`: `template/{% if has_backend %}app{% endif %}/settings.py.jinja2:22`
- FastAPI app is created in `create_app()` with `FastAPI(title="app", lifespan=lifespan)`: `template/{% if has_backend %}app{% endif %}/main.py.jinja2:55`, `:63`
- `/healthz`, `/echo`, `/summarize` exist in `app/api.py`: `api.py.jinja2:21`, `:27`, `:82`
- `SummarizeRequest` is in `app/api.py`: `api.py.jinja2:57`
- `call_llm` is imported directly into `app.api`, and `_summarize()` calls that local binding: `api.py.jinja2:15`, `:79`
- `EchoRequest` is in `app/models.py`, not `app/api.py`, and the field is `message`, not `text`: `models.py.jinja2:14`
- Echo service reflects `req.message`: `services.py.jinja2:6`
- `@register` exists in `harness.registry` with signature `register(check_id, *, tier, category, ...)`: `template/harness/registry.py.jinja2:19`
- `CheckResult` exists with `check_id`, `status`, `message`, `duration_ms`, `error`, `cached`: `template/harness/models.py.jinja2:61`
- CLI `--check`, `--quick`, `--full`, `--no-cache`, `--format` exist: `template/harness/cli.py.jinja2:153`
- `just eval` exists when `has_llm=true`: `template/justfile.jinja2:110`
- Backend `.env.example` path is `template/{% if has_backend %}app{% endif %}/.env.example.jinja2`
- LLM-only root `.env.example` path is `template/{% if has_llm and not has_backend %}.env.example{% endif %}.jinja2`
- Copier prompt names match the matrix plan: `has_backend`, `has_llm`, `has_logfire`, `has_fastapi_mcp`: `copier.yml:151`

**MISSING / AMBIGUOUS**

- `get_settings` is referenced by 06-02 but does not exist. The source has `load(cwd)`.
- `settings.env` is referenced by 06-02 but the source uses `settings.ENV`.
- 06-04 assumes `EchoRequest` is edited in `api.py`; actual source has it in `models.py`.
- 06-04 assumes `/echo` field is `text`; actual field is `message`.
- 06-02 frontmatter lists `template/{% if has_backend and not has_llm %}.env.example{% endif %}.jinja2`, but that file path does not exist.
- 06-03 test plan says to monkey-patch `harness.llm.call_llm`; because `app.api` imports `call_llm` directly, tests must patch `app.api.call_llm` after import or patch before importing `app.api`.

## Concerns

- **HIGH — FastAPI auth exclusion strategy is incorrect.**
  06-02 says app-level `FastAPI(dependencies=[Depends(require_auth)])` can be bypassed by adding `dependencies=[]` to `/healthz`. FastAPI app-level dependencies are not overridden by route-level empty dependency lists; they still run for every path operation. The plan needs `require_auth(request: Request, ...)` with an early return for `/healthz`, or a different routing strategy.

- **HIGH — 06-02 references non-existent settings APIs.**
  The planned `from app.settings import Settings, get_settings` and `settings.env` do not match source. Current source has `load(cwd)` and `Settings.ENV`. This will break `app/auth.py` import or runtime behavior.

- **HIGH — 06-04 hardens the wrong file and field.**
  `/echo` uses `EchoRequest` from `app.models`, and its field is `message`. Editing `api.py` as planned will not add validation to the actual request model.

- **HIGH — 06-02 `.env.example` file path is wrong.**
  The backend `.env.example` lives under `app/.env.example`, not at a root path gated by `{% if has_backend and not has_llm %}`. The plan should update `template/{% if has_backend %}app{% endif %}/.env.example.jinja2` and the LLM-only root env file.

- **HIGH — 06-03 test monkey-patching target is wrong.**
  Since `app.api` binds `call_llm` at import time, patching `harness.llm.call_llm` after importing the app will not affect `_summarize()`. Patch `app.api.call_llm` or patch before importing `app.main`.

- **HIGH — REVIEW-CHECKLIST Pattern 6: meta-comments in rendered templates.**
  06-02 instructs adding `# Auth token for X-VerifyKit-Token header (D-16 / verify-kit-3u2)` to `.env.example`. `D-16` and bead IDs are internal planning metadata and will render into consumer projects. Use user-facing wording only, e.g. `# Auth token for protected scaffold routes`.

- **MEDIUM — 06-02/03/04 verification snippets hard-code `/Users/moiz/Documents/code/verify-kit`.**
  This works locally for Moiz, but it is not portable and conflicts with the repo's drift-prevention style. Prefer `src = pathlib.Path.cwd()` or `VERIFY_KIT_ROOT`.

- **MEDIUM — README Mermaid validation is still grep-only.**
  06-06 checks the presence of a Mermaid block but does not render it. A syntax error would still pass. This is less risky than code drift but visible on GitHub.

- **MEDIUM — 06-06 and 06-07 can temporarily create a broken README link.**
  Same-wave execution means README can link `CONTRIBUTING.md` before 06-07 lands. Acceptable only if there is a wave-end link check.

## Suggestions

- Patch 06-02 to implement auth as:
  - `require_auth(request: Request, settings: Settings = Depends(...))`
  - early-return for `request.url.path == "/healthz"`
  - source settings from `request.app.state.settings` or add a real `get_settings(request: Request)` dependency.
  - use `settings.ENV`, or deliberately add a lowercase property with tests.
- Move 06-04's implementation target to `template/{% if has_backend %}app{% endif %}/models.py.jinja2`; validate `EchoRequest.message`.
- Update 06-02 files_modified to include the real backend `.env.example` path and remove the nonexistent root backend env path.
- In 06-03 tests, patch `app.api.call_llm`, not `harness.llm.call_llm`, unless the patch happens before importing `app.main`.
- Strip all internal bead/decision IDs from rendered template comments.
- Add a lightweight Mermaid render step or explicit GitHub-preview checkpoint to 06-06.
- Add a W4 completion check: README links resolve after 06-06 and 06-07 have both landed.

## Risk Assessment

**Overall risk: HIGH until the source-drift issues are fixed.** The documentation and CI plans are mostly solid, but the hardening trio contains implementation-breaking assumptions about FastAPI dependency behavior, settings APIs, `/echo` model location, and env file paths. Once 06-02, 06-03, and 06-04 are corrected against the current source, the remaining Phase 6 plan risk drops to **MEDIUM-LOW**.

---

## Consensus Summary

Only one reviewer (Codex) was invoked this cycle, so "consensus" reflects the single reviewer's emphasis.

### Agreed Strengths

- Plan structure and wave dependencies are coherent.
- Documentation coverage (DOC-01..05) matches phase goals.
- Hardening beads are explicitly closed in the right plans.
- REVIEW-CHECKLIST patterns are mostly internalized in plan text.

### Agreed Concerns (HIGH)

1. **FastAPI app-level dependency cannot be bypassed by route-level `dependencies=[]`** (06-02) — auth design is implementation-incorrect.
2. **`get_settings` / `settings.env` do not exist** in source (06-02) — symbols are MISSING/AMBIGUOUS vs. actual `load(cwd)` + `Settings.ENV`.
3. **06-04 targets wrong file and field** — `EchoRequest` lives in `app/models.py` with field `message`, not in `api.py` with field `text`.
4. **06-02 cites nonexistent `.env.example` path** — backend env file is under `app/.env.example.jinja2`.
5. **06-03 monkey-patches wrong import binding** — must patch `app.api.call_llm`, not `harness.llm.call_llm`, due to direct import.
6. **REVIEW-CHECKLIST Pattern 6 violation** — internal IDs (D-16, bead IDs) instructed to render into consumer-facing `.env.example` template.

### Divergent Views

N/A — single reviewer.


---

# Cycle 2 — Adversarial Codex Re-Review (2026-05-22T22:11:06Z)

After commit 97e281f addressed all 6 Cycle 1 HIGHs, a second Codex review was run with adversarial framing ("assume the prior reviewer missed something").

## Codex Review (Cycle 2)

**Findings**

**HIGH — Verification snippets now resolve the template source as `/tmp` when `VERIFY_KIT_ROOT` is unset.**  
[06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:164), [06-03-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-03-PLAN.md:139), and [06-04-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-04-PLAN.md:136) all start with `cd /tmp`, then compute:

```python
src = pathlib.Path(os.environ.get('VERIFY_KIT_ROOT', pathlib.Path.cwd()))
```

If `VERIFY_KIT_ROOT` is not set, `src == /tmp`, so `copier copy ... str(src) ...` tries to copy from `/tmp`, not the verify-kit repo. This means the commit’s “hard-coded path replaced with VERIFY_KIT_ROOT env + Path.cwd fallback” fix does not actually work end-to-end. It converted an operator-specific path into a cwd leak.

Fix shape: do not `cd /tmp` before deriving `src`, or require `VERIFY_KIT_ROOT` explicitly, or derive the repo root before changing cwd.

**HIGH — New auth/summarize/echo scratch tests use bare `TestClient(app)` and skip FastAPI lifespan, which breaks `request.app.state.settings`.**  
06-02 says the polarity test should run `from app.main import app; client = TestClient(app)` at [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:259). 06-03 repeats the same pattern at [06-03-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-03-PLAN.md:193). Existing scaffold tests explicitly document that bare `TestClient(app)` skips lifespan and leaves `app.state.settings` unbound: [conftest.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/tests/backend/{% if has_backend %}conftest.py{% endif %}.jinja2:25). The app only sets `app.state.settings` inside lifespan: [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:41).

This is not just a test-style issue. 06-02’s new `require_auth` reads `request.app.state.settings` at [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:136). The planned tests will fail with `AttributeError` or will be rewritten ad hoc by the executor, weakening the forcing-function coverage.

Fix shape: scratch-side tests must use `create_app(cwd=scratch)` and `with TestClient(app) as client:` after writing the intended `.env`, matching the existing backend fixture pattern.

**MEDIUM — 06-02 still has internal contract drift about the LLM-only `.env.example`.**  
The task title/files/read-first/action still say “both `.env.example` variants” and list the LLM-only root env file at [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:227), then line [249](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:249) says “append” the auth slot after describing both files. Only later does line [255](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:255) say the LLM-only file is skipped. The intended fix summary is correct, but the plan still gives contradictory executor instructions.

**MEDIUM — 06-04 commit strategy still says the implementation commit changes `api.py.jinja2`.**  
The body correctly retargets `models.py.jinja2`, but the commit strategy still says the first commit is “api.py.jinja2 changes” at [06-04-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-04-PLAN.md:240). This is residual symbol/file drift, not execution-blocking by itself.

**Cycle-2 Fix Verification**

1. `/healthz` exclusion moved into `require_auth`: yes, plan text now uses `request.url.path == "/healthz"` and removed `api.py` route edits.
2. Settings access uses `request.app.state.settings.VERIFYKIT_AUTH_TOKEN`: yes.
3. 06-04 retargeted `app/models.py.jinja2`, `EchoRequest.message`, `_CONTROL_CHARS_ECHO`: yes, with stale commit-strategy wording.
4. Backend `.env.example` path corrected: mostly yes, but Task 3 still contradicts itself about the LLM-only root file.
5. Monkeypatch target changed to `app.api.call_llm`: yes in target name, but scratch test instructions import `app` as the FastAPI instance first and need care to avoid shadowing the package.
6. Planning IDs stripped from rendered `.env.example`: yes in the canonical comment and grep guard.

**Hunt Target Summary**

- cwd/path leaks: additional HIGH found in `cd /tmp` + `Path.cwd()` fallback.
- statements after `return`: no additional dead-code-after-return issue found in the changed canonical snippets.
- subprocess missing `cwd=`: present in the verification snippets; combined with `cd /tmp`, it causes the HIGH source-root leak above.
- cross-plan contract drift: no new HIGH, but 06-02 env-file instructions drift internally.
- fixes from `97e281f`: fixes mostly landed, but the path portability fix is broken end-to-end.
- symbol drift: `EchoRequest.message`, `_CONTROL_CHARS_ECHO`, `/healthz` mechanism are corrected; residual `api.py.jinja2` wording remains in 06-04 commit strategy.

---

## Cycle 2 Consensus Summary

### Newly Raised HIGHs (2)

1. **VERIFY_KIT_ROOT cwd-fallback leak in verification snippets** — 06-02/03/04 all do `cd /tmp` then `Path(os.environ.get('VERIFY_KIT_ROOT', Path.cwd()))`. When the env var is unset, `src` resolves to `/tmp`, not the verify-kit repo. The bonus MEDIUM fix from commit 97e281f is broken end-to-end and converted a hard-coded-path issue into a cwd-leak issue (REVIEW-CHECKLIST §1).
2. **Bare `TestClient(app)` skips lifespan; `request.app.state.settings` will be unbound** — 06-02 polarity test and 06-03 monkeypatch test both use `TestClient(app)` directly without the lifespan context manager. The new `require_auth` reads `request.app.state.settings.VERIFYKIT_AUTH_TOKEN`, which is only set inside lifespan (verified in template/.../main.py.jinja2:41 and conftest.py.jinja2:25). Tests will AttributeError or get silently rewritten by the executor, defeating the forcing-function (REVIEW-CHECKLIST §3 cross-plan contract drift between plan tests and existing scaffold fixtures).

### Fix-Verification Outcomes (Cycle 1 HIGHs)

| # | Cycle 1 HIGH | Cycle 2 Verdict |
|---|--------------|-----------------|
| 1 | /healthz exclusion in require_auth body | ✅ FIXED |
| 2 | Settings read via request.app.state.settings.VERIFYKIT_AUTH_TOKEN | ✅ FIXED (but tests don't trigger lifespan — see new HIGH 2) |
| 3 | 06-04 retargeted to models.py.jinja2, EchoRequest.message, _CONTROL_CHARS_ECHO | ✅ FIXED (residual prose drift in commit strategy — MEDIUM) |
| 4 | .env.example path corrected to template/{% if has_backend %}app{% endif %}/.env.example.jinja2 | ✅ FIXED (residual internal contradiction about LLM-only root file — MEDIUM) |
| 5 | Monkeypatch target → app.api.call_llm | ✅ FIXED (test instructions may shadow `app` symbol — caution flagged) |
| 6 | Planning IDs stripped + grep guard | ✅ FIXED |

### Remaining MEDIUMs (2)

- 06-02 internal contract drift about LLM-only `.env.example` (task title vs. line 255 skip)
- 06-04 commit strategy still says first commit is "api.py.jinja2 changes" — residual symbol drift

### Decision

**Cycle 2 surfaces 2 new HIGHs.** Both are concrete bug shapes (cwd-leak, lifespan-skip) that would silently break the test snippets at execute-phase time. The convergence loop should advance to Cycle 3 to address them.

---

# Cycle 3 Review (Codex — Adversarial Final Pass)

**Reviewer:** Codex CLI (gpt-5.5)
**Reviewed at:** 2026-05-22T22:22:30Z
**Framing:** Final adversarial pass; assume cycle-2 reviewer missed something. Source-grounding pass MANDATORY.

## Codex Review

**Final Adversarial Review**

I found additional HIGHs.

### Source-Grounding Pass

**Verified:**
- `create_app(cwd=...)` exists and module-level `app = create_app()` exists: `template/{% if has_backend %}app{% endif %}/main.py.jinja2:55, 171`
- Lifespan sets `app.state.settings`: `template/{% if has_backend %}app{% endif %}/main.py.jinja2:41`
- Settings uses uppercase fields and `load(cwd)`, no `get_settings`: `template/{% if has_backend %}app{% endif %}/settings.py.jinja2:7`
- `/echo` uses `EchoRequest.message`, not `text`: `template/{% if has_backend %}app{% endif %}/models.py.jinja2:14`
- `/summarize` uses `call_llm` bound in `app.api`: `template/{% if has_backend %}app{% endif %}/api.py.jinja2:15`
- Lifespan-aware TestClient convention exists: `template/tests/backend/{% if has_backend %}conftest.py{% endif %}.jinja2:24`
- `_CLEAN_ENV` exists: `tests/_helpers.py:130`
- `just eval` exists: `template/justfile.jinja2:110`

**Missing / drift:**
- `register` is NOT exported from `harness.checks`; it lives in `harness.registry`: `template/harness/registry.py.jinja2:19`
- `CheckResult` is NOT exported from `harness.checks`; it lives in `harness.models`: `template/harness/models.py.jinja2:61`
- `template/harness/llm.py.jinja2` does not exist as a source path. Actual template path is `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2`.

### Cycle-2 Fix Audit

The two cycle-2 fixes look correctly applied in the plan text:
- `VERIFY_KIT_ROOT` is now required before `cd /tmp`; no `Path.cwd()` fallback remains in 06-02/03/04 verify snippets.
- Test snippets use `create_app(cwd=...)` plus `with TestClient(application) as client:` and explicitly forbid bare `TestClient(app)`.
- No new drift from the `application` variable rename detected.

### HIGH Concerns (4 new)

**1. HIGH — 06-07 "add a new check" snippet is source-drifted and will not run.**
Evidence at `.planning/phases/06-template-self-test-documentation/06-07-PLAN.md:91`:
```python
from harness.checks import register, CheckResult
@register(id="my-check", tier="universal")
```
Actual source:
- `register` is `from harness.registry import register`, not `harness.checks`.
- `CheckResult` is `from harness.models import CheckResult`.
- `register()` takes positional `check_id`, not keyword `id` (`template/harness/registry.py.jinja2:19`).
- `tier="universal"` is invalid; `CheckTier` is `quick | standard | slow` (`template/harness/models.py.jinja2:21`).

Fix:
```python
from harness.models import CheckResult
from harness.registry import register

@register("my-check", tier="quick", category="custom")
def my_check(cwd) -> CheckResult:
    return CheckResult(check_id="my-check", status="pass", duration_ms=0)
```

**2. HIGH — 06-08 self-test CI installs Copier without the required template extension.**
Evidence at `06-08-PLAN.md:117`: `uv tool install copier`. But `copier.yml:7` declares `_jinja_extensions` via `copier_templates_extensions.TemplateExtensionLoader` and documents the required install command. The workflow installs a standalone tool without the extension, so `copier copy` can fail before the matrix tests anything.

Fix: `uv tool install copier --with copier-templates-extensions` everywhere Phase 6 invokes Copier on a clean machine / CI runner.

**3. HIGH — 06-06 README quickstart omits the `--trust` requirement.**
Evidence at `06-06-PLAN.md:112`:
```bash
copier copy gh:m2moiz/verify-kit my-project && cd my-project && just verify
```
But `copier.yml:66` has `_tasks`, and Copier 9.15 requires `--trust` for unsafe features (Jinja extensions, migrations, tasks). This threatens ROADMAP SC2 / UX-08: the new reader's first command is not the same command CI uses and may prompt or fail.

Fix:
```bash
uv tool install copier --with copier-templates-extensions
copier copy --trust gh:m2moiz/verify-kit my-project
cd my-project
just verify
```

**4. HIGH — 06-09 references a non-existent source path.**
Evidence at `06-09-PLAN.md:72` says to confirm exports in `template/harness/llm.py.jinja2`, but that file does not exist. Actual path: `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2`. An executor following the plan literally hits a missing file.

### Per-Plan Feedback

- **06-01:** Solid. Static OSS files, YAML parse checks, no source drift. Risk LOW.
- **06-02:** Strong after cycle-2 fixes. Auth contract source-grounded. Risk MEDIUM.
- **06-03:** Strong. Patch target `app.api.call_llm` correct. Risk MEDIUM.
- **06-04:** Strong. Correctly retargeted to `models.py` and uses `message`. Risk LOW/MEDIUM.
- **06-05:** Mostly fine. No HIGH found.
- **06-06:** HIGH quickstart issue (#3 above).
- **06-07:** HIGH API snippet drift (#1 above).
- **06-08:** HIGH CI install drift (#2 above).
- **06-09:** HIGH missing source path (#4 above).
- **06-10:** Acceptable. Risk LOW.

### Risk Assessment

Auth/summarize/echo implementation plans have converged. The remaining blocking risk is "first command / CI command / contributor docs command" drift. Left unfixed, Phase 6 ships documentation and CI that fail before the actual template behavior is exercised. 06-07 would bake a broken extension guide into CONTRIBUTING — exactly matching REVIEW-CHECKLIST Pattern 4.

---

## Cycle 3 Consensus Summary

### Newly Raised HIGHs (4)

| # | Plan | Pattern | Description |
|---|------|---------|-------------|
| 1 | 06-07 | REVIEW-CHECKLIST Pattern 4 (source drift in extension guide) | `harness.checks` imports + `@register(id=..., tier="universal")` decorator signature is wrong on all four fronts; will not run |
| 2 | 06-08 | CI environment drift | `uv tool install copier` omits `--with copier-templates-extensions`; Copier templates fail to render before matrix tests run |
| 3 | 06-06 | UX-08 / SC2 quickstart drift | README `copier copy` command omits `--trust` flag required by Copier 9.15 for `_tasks` + Jinja extensions |
| 4 | 06-09 | Source path drift (REVIEW-CHECKLIST §3) | `template/harness/llm.py.jinja2` referenced but actual path is `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2` |

### Cycle-2 Fix Verification

- VERIFY_KIT_ROOT required-env + sanity-assert pattern: ✅ correctly applied
- `create_app(cwd=scratch) + with TestClient(application) as client:` pattern: ✅ correctly applied
- No drift introduced by `application` variable rename: ✅ confirmed

### Decision

**Cycle 3 surfaces 4 new HIGHs.** All are concrete bug shapes catchable only by adversarial source-grounding: a wrong import path, a missing Copier flag, a missing CI dependency, and a non-existent file reference. Trend is no longer monotone-decreasing (6 → 2 → 4), but the new HIGHs are NOT in the previously-fixed areas — they are in plans (06-06, 06-07, 06-08, 06-09) that the prior cycles' reviewers spent less time on. Per `.claude/rules/08-plan-convergence-workflow.md`, the convergence loop's max-cycles=3 is now exhausted. Recommended path: **manual fix** of the 4 HIGHs, then independent re-review (per "grep is not verification" memory).

---

# Cross-AI Plan Review — Phase 6 (Cycle 4, Final Adversarial Pass)

**Reviewed at:** 2026-05-22T22:56:14Z
**Reviewer:** Codex CLI
**Context:** Post-manual-fix verification per .claude/rules/08-plan-convergence-workflow.md ('grep is not verification'). Adversarial framing: hunt for issues prior 3 cycles + manual fix pass missed.

## Codex Review

## Summary

Final adversarial pass found additional HIGHs. The four manual fixes mostly address their narrow claims, but 06-06 and 06-08 still have command/data drift around Copier, and 06-10 is materially wrong against the current Phase 4 validation artifact.

## Strengths

- Manual fix 06-07 is source-grounded: `register()` is in `harness.registry`, positional `check_id`, and `CheckTier` is `quick | standard | slow`.
- Manual fix 06-08 correctly adds `uv tool install copier --with copier-templates-extensions`, matching `copier.yml`’s `_jinja_extensions`.
- Manual fix 06-09 correctly references the actual gated LLM path: `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2`.
- 06-02/03/04 now explicitly avoid the prior cwd fallback leak by requiring `VERIFY_KIT_ROOT`.

## Concerns

### HIGH — 06-10 assumes Phase 4 validation can short-circuit, but the source says validation has open gaps

06-10 says the ceremony should short-circuit if coverage is complete and claims existing validation is likely complete: [06-10-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-10-PLAN.md:18), [06-10-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-10-PLAN.md:90).

Actual source contradicts that. `04-VALIDATION.md` frontmatter says `status: gaps_identified`, `gap_count: 10`, with `HIGH: 3`: [04-VALIDATION.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/04-backend-fastapi-add-on/04-VALIDATION.md:4). It then lists HIGH gaps starting at [04-VALIDATION.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/04-backend-fastapi-add-on/04-VALIDATION.md:29), [04-VALIDATION.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/04-backend-fastapi-add-on/04-VALIDATION.md:71), and [04-VALIDATION.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/04-backend-fastapi-add-on/04-VALIDATION.md:106).

`STATE.md` also says three Phase 4 validation HIGHs were filed and deferred to Phase 6: [STATE.md](/Users/moiz/Documents/code/verify-kit/.planning/STATE.md:88). 06-10 must reconcile the existing gaps/beads, not treat them as newly surfaced or likely no-op.

### HIGH — 06-08 self-test matrix omits `has_db`, leaving the no-backend rows ambiguous or broken

06-08 says each matrix row only passes JSON for `has_backend`, `has_llm`, `has_logfire`, and `has_fastapi_mcp`: [06-08-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-08-PLAN.md:111). But `copier.yml` defines `has_db` with default `true`: [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:173), and DB file exclusion depends on `not has_db`: [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:37).

Existing polarity tests explicitly set `has_db=False` for no-backend renders, which is strong evidence the answer matters: [test_phase04_scaffold_polarity.py](/Users/moiz/Documents/code/verify-kit/tests/test_phase04_scaffold_polarity.py:92), [test_phase04_scaffold_polarity.py](/Users/moiz/Documents/code/verify-kit/tests/test_phase04_scaffold_polarity.py:161).

Fix: each matrix row should set `has_db` explicitly. Likely `false` for `base` and `llm`, `true` for backend rows unless testing a no-DB backend cell intentionally.

### HIGH — 06-06 README quickstart still omits the required Copier extension install

06-06 quickstart only documents `copier copy --trust gh:m2moiz/verify-kit ...`: [06-06-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-06-PLAN.md:112). But `copier.yml` requires `copier_templates_extensions.TemplateExtensionLoader` and even comments that users must install Copier with `--with copier-templates-extensions`: [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:7), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:10).

06-08 correctly fixes CI with `uv tool install copier --with copier-templates-extensions`: [06-08-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-08-PLAN.md:117). The README must include the same prerequisite or the public quickstart can fail before rendering.

## Source-Grounding Pass

| Item | Status | Evidence |
|---|---:|---|
| `register(check_id, *, tier="standard", ...)` | VERIFIED | [registry.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/registry.py.jinja2:19) |
| `CheckResult(status=..., check_id=...)` | VERIFIED | [models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:61) |
| `CheckTier = quick | standard | slow` | VERIFIED | [models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:22) |
| `Settings.load(cwd)` and no `get_settings` | VERIFIED | [settings.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/settings.py.jinja2:22) |
| `create_app(cwd)` stores `app.state.settings` in lifespan | VERIFIED | [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:41) |
| `/echo` uses `EchoRequest.message`, not `text` | VERIFIED | [models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/models.py.jinja2:14) |
| `/summarize` binds `call_llm` in `app.api` | VERIFIED | [api.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:15) |
| LLM source path gated as `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2` | VERIFIED | [rg output path exists](/Users/moiz/Documents/code/verify-kit/template/harness/{% if has_llm %}llm.py{% endif %}.jinja2:1) |
| `copier-templates-extensions` required | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:7) |
| `has_db` omitted from 06-08 matrix | AMBIGUOUS/HIGH | [06-08-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-08-PLAN.md:111), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:173) |

## Suggestions

- Revise 06-10 to start from the existing `04-VALIDATION.md` gap inventory and linked Beads issues, then define explicit closure criteria for those three HIGHs.
- Add `has_db` to every 06-08 matrix `data` object.
- Add a README prerequisite line before the quickstart: `uv tool install copier --with copier-templates-extensions`, or use an equivalent one-shot `uvx --with copier-templates-extensions copier copy ...` form if that is verified.
- Update 06-08 verification to assert `has_db` appears in every matrix include data string.

## Risk Assessment

Current Phase 6 plan risk remains HIGH. The hardening trio is much improved, but the self-test workflow may exercise the wrong matrix, the README quickstart may fail on a clean machine, and the Phase 4 audit closure plan is contradicted by the existing validation source of truth.

## HIGH Concerns

1. 06-10 Phase 4 validation short-circuit assumption contradicts `04-VALIDATION.md` open HIGH gaps: [06-10-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-10-PLAN.md:90), [04-VALIDATION.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/04-backend-fastapi-add-on/04-VALIDATION.md:4).
2. 06-08 matrix omits `has_db`, despite `has_db` being a live prompt/default and DB file gate: [06-08-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-08-PLAN.md:111), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:173).
3. 06-06 README quickstart omits the required `copier-templates-extensions` install path: [06-06-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-06-PLAN.md:112), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:10).

---

## Cycle 5 — Codex (Adversarial Re-Review, 2026-05-23)

**Framing:** Four prior cycles + two manual-fix passes (latest 24f6ea0) cleared HIGHs. Trend 6 → 2 → 4 → 3. Adversarial prompt instructed Codex to hunt for cycle-4 fix gaps, NEW drift from those edits, missed HIGHs in less-attended plans (06-01, 06-05, 06-WAVES, 06-CONTEXT, 06-RESEARCH), cwd leaks, Pattern 6 leaks in template/*, and producer/consumer contract drift.

**Verdict:** HIGHs FOUND: 2 — both NEW, both in 06-02 and surrounding template/* surface area. Cycle-4 fixes themselves (H1 06-10, H2 06-08, H3 06-06) are VERIFIED in the plans.

**Consolidated HIGHs**

| Severity | Plan | Citation | Finding |
|---|---|---|---|
| HIGH | 06-02 | [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:259), [settings.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/settings.py.jinja2:22) | Auth token is documented in rendered `app/.env.example`, but the app only loads root `.env`; tests write root `.env`, so the plan can pass while the consumer-facing env example is nonfunctional. |
| HIGH | 06-02 / Pattern 6 | [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:296), [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:66) | Pattern 6 enforcement is too narrow: it checks only the new `app/.env.example`, while touched/generated template files already ship planning/review IDs like `cycle-3 HIGH`, `Codex HIGH`, `Plan 04-07`, `REVIEW-CHECKLIST`, etc. |

**06-02 Assessment**

1. **HIGH: auth env example path does not match the app’s settings loader**

06-02 claims the backend env layout is `template/{% if has_backend %}app{% endif %}/.env.example.jinja2`, rendered to `app/.env.example`, and explicitly writes the auth token slot only there: [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:259), [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:269).

But the actual app loader reads only `cwd / ".env"`: [settings.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/settings.py.jinja2:22). The app lifespan uses that loader through `create_app(cwd=...)`: [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:41), [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:55).

The proposed test then writes `tmp/.env`, not `tmp/app/.env`, so it proves the runtime path but not the documented consumer path: [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:273), [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:288).

Fix: document `VERIFYKIT_AUTH_TOKEN=` in a root `.env.example` for every backend render, or change `load(cwd)` to intentionally read `app/.env` too. Add a test that copies the rendered env example to the actual runtime `.env` location and verifies prod auth no longer returns 503.

2. **HIGH: Pattern 6 check misses existing planning-ID leaks in shipped template files**

06-02 only forces Pattern 6 against the new `app/.env.example`: [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:296). It also tells the executor to preserve the existing middleware block: [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:205).

That preserved generated file already contains consumer-visible internal review references: `cycle-3 HIGH C`, `Codex HIGH #2`, `Codex HIGH #3`, and `REVIEWS-RESPONSE.md`: [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:66), [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:87), [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:113), [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:136). Other shipped templates contain `Plan 03-01`, `Plan 04-07`, `REVIEW-CHECKLIST`, and bead IDs, for example [pyproject.toml.jinja2](/Users/moiz/Documents/code/verify-kit/template/pyproject.toml.jinja2:23) and [models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/models.py.jinja2:7).

Fix: add a Phase 6 scrub task or a broad rendered-output assertion for generated consumer files, not just the newly added env example. Keep durable technical comments, but remove planning IDs, review-cycle labels, bead IDs, and reviewer names from `template/*`.

**Source-Grounding Pass**

| Symbol / path / flag | Status | Evidence |
|---|---|---|
| `Settings.load(cwd)` reads root `.env` | VERIFIED | [settings.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/settings.py.jinja2:22) |
| `create_app(cwd)` + lifespan settings binding | VERIFIED | [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:41), [main.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/main.py.jinja2:55) |
| `template/{% if has_backend %}app{% endif %}/.env.example.jinja2` | MISSING currently; planned new file | No match in `rg --files template`; plan references it at [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:242) |
| `VERIFYKIT_AUTH_TOKEN` | MISSING currently; planned producer symbol | Plan adds it; existing `settings.py.jinja2` has only `ENV`, `LOG_LEVEL`, `LOG_FORMAT`, `DATABASE_URL`, `PROFILE_ENABLED`: [settings.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/settings.py.jinja2:15) |
| `X-VerifyKit-Token` / `require_auth` | MISSING currently; planned producer symbols | 06-02 owns them: [06-02-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:112) |
| `has_backend`, `has_llm`, `has_logfire`, `has_fastapi_mcp`, `has_db` | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:151), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:156), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:161), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:167), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:173) |
| `_jinja_extensions` / `copier-templates-extensions` requirement | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:7), [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:10) |
| `_tasks` requiring `--trust` | VERIFIED | [copier.yml](/Users/moiz/Documents/code/verify-kit/copier.yml:66) |
| `EchoRequest.message` | VERIFIED | [models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/models.py.jinja2:14) |
| `/summarize`, `call_llm`, `cost_budget` | VERIFIED | [api.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:15), [api.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:72), [api.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/{% if has_backend %}app{% endif %}/api.py.jinja2:82) |
| `@register`, `CheckResult`, `CheckTier` | VERIFIED | [registry.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/registry.py.jinja2:19), [models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:22), [models.py.jinja2](/Users/moiz/Documents/code/verify-kit/template/harness/models.py.jinja2:61) |
| `just eval` | VERIFIED | [justfile.jinja2](/Users/moiz/Documents/code/verify-kit/template/justfile.jinja2:110) |
| Phase 4 validation beads `verify-kit-plk/c5a/r7v` | VERIFIED in STATE; `bd show` blocked by sandboxed Dolt access | [STATE.md](/Users/moiz/Documents/code/verify-kit/.planning/STATE.md:88) |
| 06-08 cycle-4 `has_db` fix | VERIFIED in plan | [06-08-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-08-PLAN.md:111) |
| 06-06 cycle-4 quickstart fix | VERIFIED in plan | [06-06-PLAN.md](/Users/moiz/Documents/code/verify-kit/.planning/phases/06-template-self-test-documentation/06-06-PLAN.md:114) |

`bd export` could not run because the Dolt server is unreachable under the current sandbox (`127.0.0.1:3307` connection denied).

HIGHs FOUND: 2

---

## Cycle 6 — Codex Adversarial Review (2026-05-22T23:48:11Z)

**Framing:** Five prior reviewers cleared HIGHs across 5 cycles plus 3 manual fix passes. Codex invoked as adversary tasked to find what they missed.

### Codex Review

HIGH FOUND — 06-02’s new root backend `.env.example` is excluded in backend-only renders.

06-02 adds `template/{% if has_backend %}.env.example{% endif %}.jinja2` and says backend renders must expose root `.env.example` with `VERIFYKIT_AUTH_TOKEN=`. But `copier.yml` still excludes root `.env.example` whenever `has_llm=false`:

- `06-02-PLAN.md:241-278` adds backend root `.env.example`
- `copier.yml:49-50` excludes `/.env.example` and `/.env.example.jinja2` under `{% if not has_llm %}`
- `06-08-PLAN.md:111-116` includes a `backend` matrix row with `has_backend=true, has_llm=false`

So the backend-only row, which is one of the required five matrix cells, will not render the new root auth env example. That means the cycle-5 env-path fix does not actually cover `+backend`, and the consumer-facing auth setup is missing in that supported scaffold.

Fix shape: change the root env exclusion from “not has_llm” to a condition that preserves root `.env.example` when either backend or LLM needs it, e.g. exclude only when `not has_llm and not has_backend`, then add a render assertion for `has_backend=true, has_llm=false` that `scratch/.env.example` exists and contains `VERIFYKIT_AUTH_TOKEN=`.

I checked 06-05 release-please, 06-WAVES ordering, 06-10 reconciliation, 06-06 README auth references, and the broadened Pattern 6 scrub. I found MEDIUM/stale-plan drift in Pattern 6 coverage and 06-WAVES metadata, but the only issue I’d raise to HIGH is the `_exclude` conflict above.

### Cycle 6 Summary

- HIGHs found: **1** (06-02 / copier.yml `_exclude` conflict with new root `.env.example` for `+backend` matrix row)
- MEDIUM/LOW: noted but not raised (Pattern 6 coverage drift, 06-WAVES metadata)
- Locations checked: 06-05 release-please, 06-WAVES ordering, 06-10 reconciliation, 06-06 README auth refs, 06-01 Pattern 6 scrub task, copier.yml `_exclude` block (lines 49-50)


---

## Cycle 7 — Codex Adversarial Review (2026-05-23T00:00:00Z)

**Framing:** Six prior reviewers cleared HIGHs across 6 cycles plus 4 manual fix passes. Cycle 6 fix landed (commit f61049f): copier.yml exclude conditions changed from `not has_llm` → `not has_llm and not has_backend`, with render-completeness assertions added across both backend cells. Codex invoked as FINAL adversary for this convergence run.

### Codex Review

**Summary**

One additional HIGH found. The cycle-6 `copier.yml` exclusion fix itself is logically correct across the five 06-08 matrix rows, but it changes the rendered `.env.example` contract and the plans do not update an existing Phase 5 polarity test that still asserts the old contract.

**Concerns**

HIGH: 06-02 changes backend renders to include root `.env.example`, but `tests/test_phase05_polarity.py` still requires root `.env.example` to be absent for backend cells.

Evidence:
- 06-02 requires root `.env.example` for both backend cells: `.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:254`.
- 06-02 changes `copier.yml` exclusions to `not has_llm and not has_backend`: `.planning/phases/06-template-self-test-documentation/06-02-PLAN.md:292`.
- Existing tests still assert old behavior:
  - backend+llm: `assert not root_env.exists()` at `tests/test_phase05_polarity.py:268`
  - backend-only: `assert not root_env.exists()` at `tests/test_phase05_polarity.py:290`
- Later plans still require Phase 5 polarity to pass: `.planning/phases/06-template-self-test-documentation/06-03-PLAN.md:227`, `.planning/phases/06-template-self-test-documentation/06-09-PLAN.md:98`.

Fix: Add `tests/test_phase05_polarity.py` to 06-02 `files_modified` and explicitly update the env-destination assertions to the new contract. If the intended contract is "root `.env.example` is canonical whenever `has_backend=true`," encode that there. If "exactly one `.env.example` per cell" is still required, then 06-02 must also merge backend+LLM env slots into the root file and remove/deprecate the backend `app/.env.example`.

**Cycle-6 Fix Trace**

The proposed `copier.yml` condition is otherwise sound:
- `base` false/false: `not has_llm and not has_backend` is true, root `.env.example` excluded. OK.
- `+backend` true/false: condition false, new backend root `.env.example` admitted. OK.
- `+llm` false/true: condition false, existing LLM-only root `.env.example` admitted. OK.
- `+backend+llm` true/true: condition false, backend root `.env.example` admitted. OK per new 06-02 contract, but conflicts with old Phase 5 test above.
- `full` true/true: same as backend+llm, plus logfire/fastapi_mcp unaffected. OK.

**Medium/Low Notes**

MEDIUM: 06-01 frontmatter `files_modified` omits its Pattern 6 scrub target. Task 3 edits `template/**/*.jinja2`, but the file list only names OSS boilerplate files. This does not create same-wave overlap with 06-02 because 06-02 is W2, but it weakens the wave/ownership metadata. Add the concrete scrubbed files or `template/**/*.jinja2` to 06-01 frontmatter.

**Source Grounding (verified)**

- `copier.yml` prompts `has_backend`, `has_llm`, `has_logfire`, `has_fastapi_mcp`, `has_db`: `copier.yml:151`
- Existing root LLM env file: `template/{% if has_llm and not has_backend %}.env.example{% endif %}.jinja2:1`
- Existing backend app env file: `template/{% if has_backend %}app{% endif %}/.env.example.jinja2:1`
- `Settings.load(cwd)` reads root `.env`: `template/{% if has_backend %}app{% endif %}/settings.py.jinja2:22`
- `create_app` and lifespan settings pattern: `template/{% if has_backend %}app{% endif %}/main.py.jinja2:55`
- `EchoRequest.message`: `template/{% if has_backend %}app{% endif %}/models.py.jinja2:14`
- `SummarizeRequest`, `call_llm`, `cost_budget`: `template/{% if has_backend %}app{% endif %}/api.py.jinja2:57`
- `@register`, `CheckResult`, `CheckTier`: `template/harness/registry.py.jinja2:19`, `template/harness/models.py.jinja2:21`

**Risk Assessment**

Overall risk: HIGH until the legacy Phase 5 polarity test is updated. The implementation plan now correctly admits the backend root env file, but the test suite still encodes the old exclusion contract and will fail in 06-03/06-09.

### Cycle 7 Summary

- HIGHs found: **1** (06-02 plan must update `tests/test_phase05_polarity.py` to match new env-destination contract; otherwise 06-03 verify gate and 06-09 final smoke will fail on backend cells)
- MEDIUM: 06-01 frontmatter `files_modified` should list Pattern 6 scrub target (`template/**/*.jinja2`)
- Cycle-6 copier.yml fix VERIFIED sound across all 5 matrix rows — but contract change has downstream test impact
- Locations checked: 06-02 PLAN lines 241-300, copier.yml:49-50, tests/test_phase05_polarity.py:240-300, 06-03 PLAN, 06-05 release-please, 06-07 PR template, 06-WAVES wave 1, 06-09 LLM README pass, 06-10 reconciliation
