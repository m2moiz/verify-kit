# Phase 6 Plan 12: GAP-7 closure (ruff format + lint sweep) Summary

**Bead:** `verify-kit-ooj` (closed)
**Follow-up filed:** `verify-kit-xv1` (GAP-8 — pre-existing logfire[fastapi] dep bug)
**Date:** 2026-05-24

## What changed

Closed GAP-7 by extending the template's ruff lint config and porting the
`ruff format` + `ruff check --fix` sweep back into `template/**/*.jinja2`.
Fresh `copier copy` → `uv sync --extra dev` → `just verify` now reports
**lint.ruff PASS** and **format.ruff PASS** for the first time.

## Ruff config diff (`template/pyproject.toml.jinja2`)

Added to `[tool.ruff.lint]`:

```toml
extend-ignore = ["B008"]   # FastAPI Depends/Query and Typer Option/Argument require call-in-default by design

[tool.ruff.lint.per-file-ignores]
"tests/*"                         = ["B017", "F841", "E501", "E402"]
"alembic/env.py"                  = ["E402"]
"alembic/versions/*"              = ["E501"]
"harness/cli.py"                  = ["E501"]   # typer help-string lines
"harness/cache.py"                = ["E501"]   # embedded SQL strings
"harness/mcp/tools.py"            = ["E501"]   # MCP tool docstrings
"app/api.py"                      = ["I001"]   # imports span Jinja conditional blocks
"harness/checks/__init__.py"      = ["I001"]   # imports span Jinja conditional blocks
```

Rationale: the originally-rendered 85 lint issues + 60 reformat files split
into three honest categories:

1. **Auto-fixable formatting / import sort** — applied to template files.
2. **Idiomatic ignores** (FastAPI/Typer call-in-default, test asserts,
   alembic migration conventions, intentionally-long help/SQL/docstrings) —
   handled via narrowly-scoped per-file ignores rather than rewriting working
   code to satisfy linter defaults.
3. **Jinja-conditional boundary safety** — `app/api.py` and
   `harness/checks/__init__.py` have imports that live inside `{% if has_X %}`
   blocks. Ruff's import sorter would rearrange them across the conditional
   boundary, which would change file semantics in the opposite polarity from
   the one being rendered (e.g. hoisting an LLM-gated `import re` to the
   top of the file would import it unconditionally and reference symbols
   that don't exist when `has_llm=false`). Suppressing I001 on just these
   two files is correct.

Plus one source-level fix: `harness/jaeger.py` had a truly unused
`span_by_id` dict comprehension (F841). Deleted.

## Files ported (70 total)

- **61 verbatim copies** — template files with no inline `{% %}` or `{{ }}` in
  body (only path-gating via filename). Scratch's post-format version copied
  byte-for-byte into the template.

- **9 hand-ported templates** — body contains inline Jinja conditionals; ports
  applied ruff's formatting *within* each conditional block while preserving
  every `{% if %} … {% endif %}` boundary:

  | File | What needed care |
  |---|---|
  | `template/{% if has_backend %}app{% endif %}/api.py.jinja2` | `re`/`monotonic`/`pydantic` imports must stay inside `{% if has_llm %}`; ruff in scratch hoisted them to top — reverted that hoist while applying intra-block sort. |
  | `template/{% if has_backend %}app{% endif %}/cli.py.jinja2` | Removed dead `from pathlib import Path`; sorted db_ping imports inside `{% if has_db %}`. |
  | `template/{% if has_backend %}app{% endif %}/main.py.jinja2` | Removed dead `import structlog`; sorted top-level imports; applied line-wrap to long `if (request.query_params... and ...)` clause. Logfire imports stay inside `{% if has_backend and has_logfire %}`. |
  | `template/harness/checks/__init__.py.jinja2` | Sorted the five unconditional imports alphabetically; kept `backend` and `eval` imports inside their `{% if %}` blocks (sorting them into the unconditional list would import them when `has_backend=false`/`has_llm=false`). Added per-file I001 ignore since ruff still sees the rendered output as one block. |
  | `template/harness/observability.py.jinja2` | Blank line after docstring; quoted-forward-ref `"_NullSpanCtx"` → `_NullSpanCtx` (UP fix). |
  | `template/tests/backend/{% if has_backend %}conftest.py{% endif %}.jinja2` | Sorted imports in unconditional block; same in DB-gated block; line-wrapped a long `pytest.skip(...)` call. |
  | `template/tests/backend/{% if has_backend %}test_fastapi_mcp_opt_in.py{% endif %}.jinja2` | Removed unused `import pytest`; added explicit blank lines around `{% if %}/{% else %}/{% endif %}` so rendered output has the two-blank-lines-before-def that ruff format expects. |
  | `template/tests/backend/{% if has_backend %}test_logfire_opt_in.py{% endif %}.jinja2` | Same as above + sorted imports inside each branch. |
  | `template/tests/conftest.py.jinja2` | Blank line after closing docstring. |

## Verification

Fresh scratch rendered with full-on flags (has_backend + has_db + has_llm +
has_logfire + has_fastapi_mcp = all true) at
`/tmp/scratch-gap7-verify2-1779634454`:

```
copier.answers.valid    pass
mise.toml.valid         pass
just-list.renders       pass
lint.ruff               pass    ruff check clean
format.ruff             pass    all Python files are ruff-formatted
lint.biome              skip    (no node biome in scratch — expected)
format.biome            skip    (no node biome in scratch — expected)
backend                 fail    pre-existing logfire[fastapi] dep bug (see GAP-8)
```

Summary: **5 pass, 1 fail, 2 skip** (was 3/3/2 pre-fix).
- GAP-7 lint.ruff + format.ruff are CLOSED.
- The one remaining `backend` failure is verified pre-existing — the
  identical `ImportError: logfire.instrument_fastapi() requires
  opentelemetry-instrumentation-fastapi` fires in pristine scratch with NO
  GAP-7 changes applied. Filed as `verify-kit-xv1` (GAP-8 P1) for a one-line
  dep fix (`logfire>=0.50` → `logfire[fastapi]>=0.50`) which is out of scope
  per user-explicit no-dep-changes constraint on the GAP-7 closure.

## Deviations

- **None inside the closure contract.** Followed the user's three discipline
  rules: stage by name (no `git add -A`), conventional commit prefixes
  without numeric phase scopes, Pattern-6-clean evergreen comments.
- **One scope-adjacent fix:** `harness/jaeger.py` F841 dead-binding deleted
  inline rather than ignored, since the variable is genuinely unused (no
  intentional name-binding pattern to preserve).
- **One escaping bug self-caught:** initial pyproject.toml.jinja2 edit
  embedded literal `{% if %}` text in a comment, which broke Jinja parsing
  at render time. Rewrote the comment to drop the literal Jinja syntax.

## Known stubs

None.

## Self-Check: PASSED

- `template/pyproject.toml.jinja2` extended config present (verified via
  fresh render → ruff check exit 0)
- 70 template files updated (verified via `git status --short` count)
- `verify-kit-ooj` closed (verified via `bd show verify-kit-ooj` → CLOSED)
- `verify-kit-xv1` follow-up created (verified via `bd show verify-kit-xv1` → OPEN P1)
