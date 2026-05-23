# Contributing to verify-kit

verify-kit is a Copier-based scaffold template. The contributor experience is unusual: most "code changes" are template edits whose effect is only visible after `copier copy` renders a scratch consumer project and `just verify` exits 0 inside it. This document explains the loop, the two most common extension shapes (a new check, a new add-on slot), and the commit-message contract that drives our SemVer releases.

If anything below is unclear, file an issue — the loop should be obvious or it isn't doing its job.

## Smoke-test loop

Every PR to verify-kit runs the self-test workflow (see `.github/workflows/template-selftest.yml`, landed by Plan 06-08). The workflow `copier copy`s the template onto a scratch directory for each meaningful add-on combination and asserts `just verify` exits 0 inside the generated project. A regression in any matrix entry fails the PR before merge.

The matrix is five entries on Linux per-PR, plus a weekly nightly rerun on macOS (see Phase 6 research §5 for the matrix shape). Per-PR wall-clock budget is under 10 minutes (ROADMAP SC5). The matrix combinations cover: a baseline scaffold with no add-ons, plus combinations that exercise the backend, LLM, Logfire, and fastapi-mcp surfaces.

When you add or change anything that affects rendered output, your change is only considered correct once the matrix is green. Don't rely on local `just verify` inside the template repo alone — that only exercises the template's own meta-tests, not the rendered consumer's experience.

### Running the matrix locally

Use `act` to run the workflow on your machine before pushing:

```bash
act -W .github/workflows/template-selftest.yml -j selftest --matrix combo:base
```

Substitute `combo:base` for any matrix entry (`+backend`, `+llm`, etc.) to reproduce a single cell.

## Adding a new check in 10 lines

A "check" is a verification step the harness runs as part of `just verify`. The registration surface is intentionally small: one decorator, one return type.

Create a new file under `template/harness/checks/` (the `.jinja2` extension is required because the template renders into the consumer project):

```python
# template/harness/checks/my_check.py.jinja2
from harness.registry import register
from harness.models import CheckResult

@register("my-check", tier="standard", category="example")
def my_check(cwd) -> CheckResult:
    # ... actual logic ...
    return CheckResult(status="pass", check_id="my-check", duration_ms=0)
```

That's the entire surface. Notes on the API (grep-extracted from `template/harness/registry.py.jinja2:19-29` and `template/harness/models.py.jinja2:22,61` — match these exactly):

- `register` is exported from `harness.registry` — not `harness.checks`.
- `CheckResult` is exported from `harness.models` — not `harness.checks`.
- The first argument to `register` is a positional `check_id` string. Do not pass it as a keyword.
- Valid `tier` values are `"quick"`, `"standard"`, `"slow"` (a `Literal` type at `harness/models.py.jinja2:22`). Anything else fails type-check.
- `CheckResult` requires `check_id` and `status` (one of `"pass"`, `"fail"`, `"skip"`); `duration_ms` defaults to 0; an `error: ErrorEnvelope | None` field carries the structured failure detail when `status="fail"`.

The decorator's full signature accepts additional keyword arguments (`description`, `inputs`, `fixable`, `tool`, `skip_if_unavailable`) — see `template/harness/registry.py.jinja2` for the live signature. Start with the four-field invocation above; reach for the optional kwargs only when the check needs them.

After adding the file, re-render a scratch consumer (`copier copy . /tmp/scratch`), `cd` in, run `just verify`, and confirm your check appears in the report.

## Adding a new add-on slot

**This section is speculative until v0.2 actually adds a new add-on slot (Web/Audio/Game). Treat as a starting point; the canonical procedure will be locked when the first v0.2 slot lands.**

The shape below mirrors the procedure used by `has_backend` (Phase 4) and `has_llm` (Phase 5). Each step is a literal copy of what those slots do today.

1. **Add the Copier prompt.** Open `copier.yml` and add a boolean prompt for the new slot (e.g. `has_web: bool`). Default to `false`. Place it alongside the existing add-on toggles so the prompt order stays grouped.

2. **Gate the paths.** Use `_exclude` patterns plus bounded `{% if has_web %}` directory names in the template tree so the entire add-on tree disappears when the flag is off. The two-guard rule from `.planning/REVIEW-CHECKLIST.md` §3 applies: both the `_exclude` glob AND the `{% if %}` directory must agree, or you'll get partial renders.

3. **Add Jinja conditionals to shared files.** Files like `pyproject.toml.jinja2` and `justfile.jinja2` need `{% if has_web %} … {% endif %}` blocks for the dependencies, scripts, and `just` recipes specific to the slot. Keep the conditional on its own lines, not inline inside a YAML/TOML value (REVIEW-CHECKLIST §5 — inline conditionals break line boundaries).

4. **Add a polarity test.** Create `tests/test_phaseNN_polarity.py` that renders the scratch scaffold with `has_web=true` AND with `has_web=false`, then asserts the slot's artifacts exist (or don't) and the rendered config parses cleanly. Polarity tests catch the most common scaffolding bugs in one shot.

When v0.2 ships its first new slot, this section will be rewritten against that concrete experience.

## Commit-message contract

Releases are automated by [release-please](https://github.com/googleapis/release-please-action). The bot watches `main`, parses commit subjects, and opens a release PR with a generated `CHANGELOG.md` and a SemVer-correct version bump. Use the prefixes below — release-please ignores anything else.

| Prefix | Effect (pre-1.0) | Example |
|---|---|---|
| `feat:` | minor bump (0.1 → 0.2) | `feat(llm): add streaming summarize` |
| `fix:` | patch bump (0.1.0 → 0.1.1) | `fix(matrix): cron fires twice` |
| `feat!:` or `BREAKING CHANGE:` footer | minor bump + breaking-change footer parsed | `feat!: rename has_backend` |
| `chore:`, `docs:`, `refactor:`, `perf:`, `test:` | no release PR triggered | `chore(deps): bump copier to 9.x` |

After release-please opens the release PR, the operator hand-edits the **"Breaking changes for consumers"** block in the PR body before merging (D-11). This block is the consumer-facing migration recipe — what to change in a downstream project running `copier update` to absorb the breaking change. Release-please's auto-generated `BREAKING CHANGE:` footer parser provides the starting list; the operator rewrites it as a step-by-step migration before merge. The same "Breaking changes for consumers" wording appears in the PR template (see `.github/pull_request_template.md`) so contributors flag the need for that block at PR-author time.
