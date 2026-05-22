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
