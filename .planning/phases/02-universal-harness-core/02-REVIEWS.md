---
phase: 2
reviewers: [codex]
reviewed_at: 2026-05-18T00:00:00Z
plans_reviewed:
  - 02-01-PLAN.md
  - 02-02-PLAN.md
  - 02-03-PLAN.md
  - 02-04-PLAN.md
  - 02-05-PLAN.md
  - 02-06-PLAN.md
  - 02-07-PLAN.md
---

# Cross-AI Plan Review — Phase 2

## Codex Review

## Summary

The plan set is coherent and mostly executable: it decomposes Phase 2 into sensible dependency waves, starts with stable model/registry primitives, then layers observability, cache/config, runner/checks, emitters, CLI, and final non-functional gates. The architecture aligns well with the phase goal: a real `harness/` package with registry-based checks, multiple output formats, cache, semantic exit codes, and inert-by-default OTel. The biggest risks are not architectural; they are execution risks from over-packed plans, several test/implementation mismatches, a few dependency-order mistakes, and ambitious performance gates that may fail on real machines because subprocess startup and dependency install time dominate.

## Strengths

- Clear layering: models/registry first, then cache/config, runner, emitters, CLI, tests. This reduces circular-import risk and gives each later plan stable contracts.
- Good preservation of locked decisions: inline `ErrorEnvelope`, three result states, dotted error codes, `[tool.verify-kit]`, SQLite WAL cache, OTel lazy import, and six report emitters are all represented.
- Strong dual-audience thinking: pretty output, JSON/JSONL/JUnit/SARIF, `describe`, `list-checks`, and `.verify/report.*` artifacts are planned together rather than bolted on later.
- The OTel inertness gate is correctly treated as a first-class test, not just an implementation claim.
- Cache design is appropriately simple for v0.1: file-hash keys, SQLite, LRU, `--no-cache`, and `verify-clean` only.
- The runner as the central choke point for spans, cache, logging, and exception normalization is the right abstraction.
- The plans explicitly avoid some scope traps: no entry-point plugins, no full Ralph loop, no backend debug endpoints, no full fixer framework.

## Concerns

- **HIGH: Plan 04 depends on Plan 03 interfaces but does not declare `02-03` as a dependency.**
  `runner.py` imports `harness.cache` and uses `CacheStore`, `make_cache_key`, `hash_inputs`, and `get_tool_version`, but Plan 04 only depends on `02-01` and `02-02`. In wave execution, this can break or force implicit ordering.

- **HIGH: The CLI and tests assume rendered-project helpers that may not exist.**
  Several plans reference `template_render`, `tests/test_phase2_*` files, and `tests/_helpers.py` without consistently listing them in `files_modified`. If these helpers are not already present from Phase 1, execution will stall.

- **HIGH: `verify-kit verify --quick` may fail in a fresh scaffold because `just-list.renders` shells out to `just`.**
  The requirements assume mise+just are preinstalled for some UX gates, but the generated project also has a Makefile shim for users without just. If `just` is missing, a required quick check failing hard undermines "first run works" unless this is explicitly documented as a prerequisite or handled as skip/tool-missing.

- **HIGH: The <500ms cache-hit test is likely fragile if it invokes `uv run verify-kit ...` as a subprocess.**
  Even if all checks are cached, `uv run`, Python import time, Typer startup, Rich/structlog imports, and filesystem setup can exceed 500ms on CI or cold machines. The plan should distinguish internal `report.summary.duration_ms` from wall-clock subprocess duration.

- **HIGH: `lint.biome` / `format.biome` using `pnpm dlx` conflicts with offline-first UX.**
  If `pnpm` exists but the network is unavailable, the check may spend time resolving/downloading Biome and fail slowly. This contradicts UX-06 unless the generated scaffold pins Biome as a local dev dependency or the check skips when Biome is not locally available.

- **MEDIUM: `CheckSpec` as a Pydantic model with `fn: Callable` complicates schema generation.**
  Even with `arbitrary_types_allowed=True`, `CheckSpec.model_json_schema()` can fail or produce poor schema unless `fn` is excluded or modeled carefully. Plan 06 says `describe` derives JSON Schema from `CheckSpec`; this needs a serialization-safe public model.

- **MEDIUM: `CheckSpec.inputs: list[str] = field(default_factory=list)` mixes dataclasses and Pydantic vocabulary.**
  The plan says `field(default_factory=list)` but imports are not always specified. In Pydantic models this should be `pydantic.Field(default_factory=list)`, not `dataclasses.field`.

- **MEDIUM: Config loader handling of `[tool.verify-kit.checks.lint.ruff]` is underspecified and easy to get wrong.**
  TOML dotted table keys like `checks.lint.ruff` naturally become nested dicts, but mapping arbitrary nested check IDs back into `per_check["lint.ruff"]` is non-trivial. The plan needs precise normalization rules and tests for multi-segment IDs.

- **MEDIUM: Unknown CLI flag did-you-mean may not work through `typer.testing.CliRunner` as written.**
  Catching `click.UsageError` around `app()` is brittle with Typer console scripts. A custom Click command class or careful `standalone_mode=False` invocation may be needed. The plan recognizes the issue but the proposed wrapper may not catch all paths.

- **MEDIUM: `atexit.register(shutdown)` inside the Typer callback may register repeatedly in tests.**
  Repeated `CliRunner.invoke()` calls can stack atexit handlers. This is mostly test pollution, but it can produce hard-to-debug failures.

- **MEDIUM: Report file writes occur after verification, but write failure mapping can mask check failure.**
  If checks fail and `.verify/report.*` cannot be written, should exit be `12` or `1`? The plan says `12`, which is defensible, but this should be explicitly accepted because it changes CI semantics.

- **MEDIUM: SARIF location fidelity is too weak for "VS Code Problems clickable" goals.**
  Minimal location `uri: "."` satisfies schema shape but not the IDE-clickable experience implied by HARN-02/IDE requirements. Phase 2 may not need perfect locations, but the plan should mark this as partial unless checks carry file/line data.

- **MEDIUM: `otlp.emit` shutdown behavior can terminate the tracer provider before later emits/tests.**
  Calling `shutdown()` inside an emitter is a one-way operation for the OTel provider. If multiple commands or tests run in-process, later spans may not export. Better to centralize flush/shutdown at CLI exit.

- **MEDIUM: The cache stores failed results uniformly, but the UX around cached failures may confuse users.**
  A failed lint result cached until inputs change is consistent with the decision, but there should be visible `cached=True` output in pretty/JSON so users understand why a check failed instantly.

- **LOW: `jsonl` summary line shape diverges from pure one-result-per-line.**
  The final `{"type": "summary"}` object is useful, but it should be documented in `describe` or schema output.

- **LOW: README and Plan 07 add substantial documentation and slow tests before the full system has stabilized.**
  This is acceptable, but it increases churn. Consider landing tests first, README after actual command behavior is verified.

- **LOW: Plan 07's smoke test installing `uv pip install -e .` inside `fake_project` seems wrong.**
  The fake fixture only has a minimal `pyproject.toml` and `.mise.toml`; it likely does not contain the harness package. The test should run from a rendered scaffold project, not the fake fixture alone.

## Suggestions

- Add `02-03` to Plan 04 dependencies. Treat cache/config as a hard dependency for runner work.

- Create a small "test infrastructure" pre-plan or include it in Plan 01: shared render helper, scratch copier invocation, and any `template_render` utility. Do not let every plan invent its own render path.

- Split `CheckSpec` into two models:
  - Internal `CheckSpec` with `fn: Callable`
  - Serializable `CheckCatalogEntry` without `fn`, used by `list-checks`, `describe`, JSON Schema, and tests

- Replace `field(default_factory=list)` with `Field(default_factory=list)` in Pydantic models and explicitly import `Field`.

- Revisit quick-check behavior for missing required tools. Either:
  - document `mise + just + uv` as hard prerequisites for the 30-second path, or
  - make `just-list.renders` skip with exit 0 when `just` is missing and surface a clear install hint.

- Avoid `pnpm dlx` in normal verify checks. Prefer one of:
  - local `pnpm exec biome`
  - skip if `node_modules/.bin/biome` is absent
  - only register Biome checks when the template actually includes a JS toolchain

- Make the cache-hit performance gate two-tiered:
  - hard gate: `report.summary.duration_ms < 500`
  - soft/marked gate: subprocess wall time <500ms only in known-fast CI, or relax to <1s

- Add file/line fields to `ErrorEnvelope` or `CheckResult` now if SARIF/JUnit/pretty output must become clickable:
  - `file: str | None`
  - `line: int | None`
  - `column: int | None`
  - `snippet: str | None`
  This avoids parsing locations out of messages later.

- Centralize OTel shutdown in CLI exit only. Let `otlp.emit` flush if available, but avoid permanently shutting down the provider from an emitter.

- Normalize config with explicit accepted forms and tests:
  - `[tool.verify-kit.cache] max_size_mb = 100`
  - `[tool.verify-kit] cache.max_size_mb = 100`
  - `[tool.verify-kit.checks."lint.ruff"] warn_as_error = false`
  Quoted dotted check IDs are safer than inferring nested TOML paths.

- Make report artifact writing atomic:
  - write to `.tmp`
  - fsync or close
  - rename to final path
  This prevents agents from reading partial JSON/SARIF while `verify` is running.

- Add a very small public schema test for each emitter:
  - JSON validates against internal schema
  - JUnit parses as XML
  - SARIF validates with `jsonschema` against schemastore schema or a minimal local schema subset

- Keep slow tests opt-in and separate from normal unit tests. The 30-second test and `copier copy + install` tests should be marked clearly so normal development remains fast.

## Risk Assessment

**Overall risk: MEDIUM.**

The architecture is sound and well aligned with Phase 2 goals, but the plan set is large and has several integration hazards: dependency-order mismatch, CLI wrapper brittleness, subprocess-driven performance gates, Biome/network behavior, and schema serialization around callable-bearing Pydantic models. None of these require changing the core direction. They do require tightening the contracts before execution, especially around test infrastructure, quick-check prerequisites, serializable models, and what exactly counts toward the <500ms budget.

---

## Consensus Summary

Only one reviewer (Codex) was invoked for this cycle, so "consensus" reflects Codex's findings alone.

### Agreed Strengths

- Clean dependency layering (models/registry → cache/config → runner → emitters → CLI → tests).
- Locked decisions are preserved end-to-end (`ErrorEnvelope`, three result states, dotted error codes, SQLite WAL cache, lazy OTel import, six emitters).
- OTel inertness treated as a first-class test gate, not an implementation claim.
- Cache design intentionally simple for v0.1.
- Scope discipline: no plugin entry points, no Ralph loop, no fixer framework.

### Agreed Concerns (highest priority)

1. **Plan 04 missing `02-03` dependency** — runner imports cache primitives but does not list cache/config plan as a prerequisite.
2. **Test/render helpers (`template_render`, `tests/_helpers.py`) not consistently declared in `files_modified`** — risk of stalled execution in wave runs.
3. **`verify --quick` hard-requires `just`** — undermines "first run works" if scaffold ships a Makefile fallback path.
4. **<500ms cache-hit gate measured via `uv run` subprocess** — likely flaky; needs split between internal `duration_ms` and wall-clock.
5. **Biome via `pnpm dlx`** — network-dependent, violates offline-first UX requirement.

### Divergent Views

N/A — single reviewer.
