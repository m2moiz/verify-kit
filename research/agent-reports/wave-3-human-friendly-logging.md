---
title: Modern Human-Friendly Logging
aliases: [Wave 3 - Logging, Structured Logging, Rich + structlog]
tags: [research, wave-3, logging, structlog, rich, pino, observability]
wave: 3
source_agent: human-friendly-logging
created: 2026-05-17
---

# Modern Human-Friendly Logging for verify-kit — 2024–2026

> [!abstract] Headline
> **Structured-by-default, pretty-by-context.** Emit events once (structlog/slog/tracing), render differently based on environment: pretty TTY in dev, JSON in CI, JSON to file always. Concrete defaults: **Rich + structlog** (Python), **Pino + pino-pretty** (JS services), **consola** (CLI tools). Log levels collapse to 3 in practice (INFO/WARN/ERROR); DEBUG/TRACE behind `-v`/`-vv`. **miette/rustc-style errors** are the error template.

## 1. Logging Libraries — Human Ergonomics

### Python

| Library | Output for humans | License | Bootstrap | Polyglot fit | Catch |
|---|---|---|---|---|---|
| **Rich** ([rich.readthedocs.io](https://rich.readthedocs.io/en/stable/progress.html), v15.0.0 Apr 2026) | Color, tables, syntax-highlighted tracebacks, live progress bars with ETA. Reference visual layer for Python CLIs. | OSS (MIT) | `pip install rich` | Excellent — exposes `RichHandler` for stdlib logging | Rendering cost non-trivial; don't wrap hot paths |
| **Loguru** ([dev.to overview](https://dev.to/leapcell/python-logging-loguru-vs-logging-1f55)) | Pre-configured color, one-line setup, `@logger.catch` decorator, built-in rotation | OSS (MIT) | `pip install loguru` | Good for app code, less so for libraries | Singleton logger; harder to compose in big apps |
| **structlog** ([Last9 guide](https://last9.io/blog/python-logging-with-structlog/)) | Processor pipeline; pretty dev renderer (color, key/value), JSON renderer in prod, switch with one config line | OSS (MIT/Apache) | `pip install structlog` | **Excellent** — single source of truth, dual rendering | Steeper learning curve than Loguru |
| stdlib `logging` + `RichHandler` | Solid default; with Rich gets color and clickable file:line | stdlib | none | Good | Boilerplate-heavy |

**2025 consensus:** for application code, `structlog` is the recommended upgrade when stdlib config feels painful. For pure visual ergonomics, layer **Rich** on top. Loguru is the pick for small scripts.

### Node / TypeScript

| Library | Output for humans | License | Bootstrap | Polyglot fit | Catch |
|---|---|---|---|---|---|
| **Pino** + **pino-pretty** ([pinojs/pino](https://github.com/pinojs/pino)) | JSON in prod; pino-pretty pipes JSON → colored, timestamped, level-tagged lines for dev | OSS (MIT) | `npm i pino pino-pretty` | **Excellent** — fastest, most widely adopted | Pretty-printer separate process; don't enable in prod |
| **consola** ([unjs/consola](https://github.com/unjs/consola)) | Fancy reporter by default, basic reporter in CI/test envs auto-detected, `success/info/warn/error/start/ready` semantics | OSS (MIT) | `npm i consola` | **Excellent for CLI tooling** | Less suited for prod HTTP services |
| Winston | Highly configurable transports; slower, more overhead than Pino | OSS (MIT) | `npm i winston` | Marginal — legacy choice | Outpaced by Pino on every axis |
| signale | Pretty CLI logger | OSS | `npm i signale` | Marginal | Unmaintained-feeling vs consola |

**2025 consensus:** **Pino for services, consola for CLIs/build tools**. Common stack: consola in dev/CLI and Pino in production.

### Rust

- **`tracing` + `tracing-subscriber`** ([tokio-rs/tracing](https://github.com/tokio-rs/tracing)) is the de-facto choice. `EnvFilter` reads `RUST_LOG` for module-scoped filtering, e.g. `RUST_LOG="myapp=debug,sqlx::migrations=error,warn"`. Output layer swappable — pretty `fmt` for dev, JSON for prod.
- `env_logger` / `fern` legacy compared to `tracing`.

### Go

- **`log/slog`** (stdlib since Go 1.21) is consensus default. Structured by default, plug `TextHandler` for dev / `JSONHandler` for prod / third-party handler for zerolog-class speed.
- `zerolog` remains fastest if allocations dominate; `zap` prior-generation pick.

### Shell

No canonical library; working pattern is tiny helper emitting ISO-8601 timestamp + level + message, with `printf '\033[…m'` color codes gated behind `[[ -t 1 ]]` so logs stay clean in pipes/CI.

## 2. Log Levels — Modern Discipline

Classic six-level hierarchy (**TRACE / DEBUG / INFO / WARN / ERROR / FATAL**) still lingua franca, but the 2024 contrarian thread "[The only two log levels you need are INFO and ERROR](https://ntietz.com/blog/the-only-two-log-levels-you-need-are-info-and-error/)" (HN front page) crystallized real shift: **levels not standardized across libraries and break down in distributed systems**.

Pragmatic 2025 discipline:

- **INFO** for normal lifecycle events (start, finish, "verified backend")
- **WARN** for recoverable anomalies you want human to notice tomorrow
- **ERROR** for things that actually broke; tag with structured context
- **DEBUG** for `--verbose`; off by default
- **TRACE** only when you have something genuinely chatty to gate (request/response bodies, span entry/exit). Skippable in most apps
- **FATAL/CRITICAL** ≈ ERROR + process exit; many libraries drop entirely
- Always support **per-module tuning** (`RUST_LOG`, `LOG_LEVEL=myapp:debug,httpx:warn`)

## 3. Structured + Human-Readable — Dual-Format Pattern

Dominant 2025 pattern: **emit structured events once; render differently based on context** ([Better Stack JSON](https://betterstack.com/community/guides/logging/json-logging/), [Uptrace](https://uptrace.dev/glossary/structured-logging)).

- **TTY detected** → pretty (color, aligned columns, timestamps as `HH:MM:SS.mmm`)
- **CI / piped / `NO_COLOR=1`** → plain text
- **`LOG_FORMAT=json`** → newline-delimited JSON for ingestion (Loki, Datadog, OTel)
- **`LOG_FORMAT=logfmt`** → `key=value` pairs, 30–40% smaller and grep-friendly ([brandur.org](https://www.brandur.org/logfmt))

Required structured fields per event: ISO-8601 UTC timestamp, level, logger/module, message, correlation/run id, plus arbitrary kwargs.

**Routing**: same logger fans out to terminal (pretty), `verify.log` (JSON), optional OTel exporter.

Conventional env vars:
- `LOG_LEVEL` (or per-language `RUST_LOG`, `PINO_LOG_LEVEL`)
- `LOG_FORMAT` ∈ {`pretty`, `json`, `logfmt`}
- `NO_COLOR=1` (universally honored, per [no-color.org](https://no-color.org/))
- `DEBUG=app:*` for namespace gating ([npm debug](https://www.npmjs.com/package/debug))

## 4. Progressive Disclosure

The `-v` / `-vv` / `-vvv` convention (Ansible, `gh`, `kubectl`) maps cleanly: 0 = WARN+, `-v` = INFO, `-vv` = DEBUG, `-vvv` = TRACE.

Complementary patterns:
- **Spinners / progress bars** during long steps (Rich `Progress`, indicatif, ora). Auto-disable when not TTY
- **Collapsing**: print "`3 warnings hidden, rerun with -v to see`" instead of dumping — borrowed from `cargo` and `npm`
- **Live regions** (Rich `Live`, `consola.start/ready`) overwrite themselves in TTY but degrade to append-only in CI

## 5. Error Message Design

Rust's compiler is modern gold standard ([Rust blog](https://blog.rust-lang.org/2016/08/10/Shape-of-errors-to-come/), [rustc dev guide](https://rustc-dev-guide.rust-lang.org/diagnostics.html)). The three-part formula:

1. **One-line summary** with error code (`error[E0277]: …`)
2. **Source context** — code snippet with `^^^^` underlines and inline labels
3. **Suggestion** — structured fix with confidence (`MachineApplicable` → auto-apply; `MaybeIncorrect` → human-review)

Always link to long-form explainer (`rustc --explain E0277`, `gh help …`). For verify-kit, every failure should be: failing check name → reproducer command → suggested fix → docs link.

## 6. Print-Debugging Done Well

- **Python `icecream`** (`ic(x)`) and **`pydbg`** ([tylerwince/pydbg](https://github.com/tylerwince/pydbg)) auto-print expression source + value + file:line
- **Rust `dbg!(x)`** ([std docs](https://doc.rust-lang.org/std/macro.dbg.html), [RFC 2361](https://rust-lang.github.io/rfcs/2361-dbg-macro.html)) — same idea, in standard library
- **JS** `console.dir(x, {depth: null})`, `console.table(rows)`, `console.group()/.groupEnd()`
- **`debug` namespace** (`DEBUG=verify:fal,verify:voice` activates only matched scopes; `-` excludes) is cleanest selective-tracing pattern in JS

Use plain `print`/`println!` only for one-shot you'll delete in same commit; reach for `ic`/`dbg!`/namespaced `debug` for anything you'd commit.

## 7. TUIs

Rich `Live`/`Layout`/`Table`, **Textual** (Python), **Bubble Tea** (Go), **Ratatui** (Rust). Beautiful dashboards but: dependency weight, broken in non-TTY CI, accessibility/screen-reader hostility.

For verify-kit: **live progress region during run, scrollback-friendly summary table at end**. Full TUI overkill — Rich's `Live` + `Table` covers experience without complexity.

## 8. Verify-Output Format — Gold Standard

- **`pytest -v`** ([pytest docs](https://docs.pytest.org/en/stable/how-to/output.html)): per-test status char (`.FsxE`), short summary section (`-r`), full traceback on failures only, percentage progress, color when TTY
- **`cargo test`**: per-test `ok`/`FAILED`, then `failures:` block re-printing failing tests with full output, then one-line totals
- **Vitest**: hierarchical tree with tick/cross glyphs, duration per test, dim for skipped, full diff for assertion failures

Common pattern: **headline summary table at end + drill-down only on failures**, plus machine-readable side-channel (JUnit XML, `--json`) for CI.

## Recommendation: verify-kit Default Stack

### Libraries

| Layer | Pick | Why |
|---|---|---|
| Orchestrator (Python — `just verify` driver) | **Rich** for rendering + **structlog** for events | Best visuals + dual JSON/pretty without rewriting call sites |
| Python sub-projects | **structlog** with `RichHandler` in dev, JSON in CI | One config line flips formats |
| JS/TS sub-projects | **Pino** + `pino-pretty` (services) / **consola** (CLI scripts) | Auto-detects CI |
| Rust sub-projects | **`tracing`** + `tracing-subscriber` with `EnvFilter` | `RUST_LOG` already universal |
| Go sub-projects | **`log/slog`** with `TextHandler` (dev) / `JSONHandler` (CI) | Stdlib, zero-dep |
| Shell helpers | Small `log()` function honoring `NO_COLOR` and `LOG_FORMAT` | No deps |

### Log-level discipline
Five levels in theory, **3 in practice** (INFO/WARN/ERROR). DEBUG/TRACE behind `-v`/`-vv`.

### Env-var contract (one set across all languages)

| Var | Meaning | Values |
|---|---|---|
| `LOG_LEVEL` | Global minimum | `trace`/`debug`/`info`/`warn`/`error` |
| `LOG_FORMAT` | Rendering | `pretty` (default if TTY), `json`, `logfmt` |
| `LOG_FILE` | Optional file sink (always JSON) | path |
| `NO_COLOR` | Disable color | any value disables |
| `VERIFY_DEBUG` | Per-module gates, `debug`-style | e.g. `fal,voice,-tavily` |
| `CI` | Auto-detected; forces non-interactive | any value |

### Flag contract
`just verify [--verbose|-v] [-vv] [--json] [--only=fal,voice] [--no-color] [--report=path.xml]`

### Ideal output (TTY, no failures)

```
verify-kit 0.4.2 · Wed 17 May 2026 14:32:08 UTC
────────────────────────────────────────────────────────────
▸ environment
  ✔ python 3.13.2                                       0.04s
  ✔ node    24.1.0                                      0.03s
  ✔ .env keys present (6/6)                             0.01s
▸ backend (python)
  ✔ ruff       no issues                                0.31s
  ✔ pyright    0 errors, 0 warnings                     1.92s
  ✔ pytest     42 passed, 0 failed, 2 skipped           4.18s
▸ frontend (node)
  ✔ tsc        0 errors                                 2.04s
  ✔ vitest     18 passed                                1.55s
  ⚠ eslint     3 warnings hidden — rerun with -v        0.62s
▸ providers (live smoke)
  ✔ pioneer    extract  live · 412ms
  ✔ fal        sprite   live · 1.81s
  ✔ tavily     lore     live · 3 citations · 740ms
  ✔ openai     comment  live · 980ms
  ✔ slng       tts      live · audio/wav · 612ms
  ✔ gradium    tts      live · audio/wav · 533ms
────────────────────────────────────────────────────────────
summary  17 passed · 0 failed · 1 warning · 12.6s
report   .verify/report.json  .verify/report.junit.xml
```

### Ideal output (one failure)

```
▸ backend (python)
  ✔ ruff       no issues                                0.30s
  ✘ pytest     1 failed, 41 passed                      4.40s

  FAIL tests/test_voice.py::test_speak_uses_slng_first
    backend/app/services/voice.py:88 in speak()
       86│     if cfg.slng_key:
       87│         provider = "gradium"          ← expected "slng"
       88│         return _gradium(...)
          │                ^^^^^^^^ used gradium even though slng key set

    fix:  prefer slng when both keys present (see PLAN 01-04 §provider-order)
    docs: docs/voice.md#provider-precedence
    repro: just verify --only=voice -vv

────────────────────────────────────────────────────────────
summary  16 passed · 1 failed · 0 warnings · 12.9s
exit     1
```

Same run with `LOG_FORMAT=json` emits one JSON object per event to stdout (and always to `LOG_FILE` if set) — same data, no ANSI, agent-parseable.

### Catch to flag
- Rich + Live + spinners must be **disabled when `!isatty(stdout) || CI`** — Pino, consola, Rich, tracing-subscriber all support; wire it once in orchestrator
- Dual-output discipline (JSON file + pretty terminal) costs nothing on structlog/slog/tracing, painful to retrofit — design in from day one

## Sources

- [Python Logging Libraries 2026 · Dash0](https://www.dash0.com/guides/python-logging-libraries)
- [Python Logging with Structlog · Last9](https://last9.io/blog/python-logging-with-structlog/)
- [Loguru vs logging · DEV](https://dev.to/leapcell/python-logging-loguru-vs-logging-1f55)
- [Rich Progress Display](https://rich.readthedocs.io/en/stable/progress.html)
- [pinojs/pino on GitHub](https://github.com/pinojs/pino)
- [Complete Guide to Node.js Logging Libraries · Last9](https://last9.io/blog/node-js-logging-libraries/)
- [unjs/consola on GitHub](https://github.com/unjs/consola)
- [npm debug module](https://www.npmjs.com/package/debug)
- [Log Levels Explained · Better Stack](https://betterstack.com/community/guides/logging/log-levels-explained/)
- [The only two log levels you need · ntietz](https://ntietz.com/blog/the-only-two-log-levels-you-need-are-info-and-error/)
- [JSON Logging guide · Better Stack](https://betterstack.com/community/guides/logging/json-logging/)
- [Introduction to Logfmt · Better Stack](https://betterstack.com/community/guides/logging/logfmt/)
- [logfmt · brandur.org](https://www.brandur.org/logfmt)
- [Rust diagnostics · rustc-dev-guide](https://rustc-dev-guide.rust-lang.org/diagnostics.html)
- [Rust dbg! macro](https://doc.rust-lang.org/std/macro.dbg.html)
- [pydbg on GitHub](https://github.com/tylerwince/pydbg)
- [tokio-rs/tracing on GitHub](https://github.com/tokio-rs/tracing)
- [Choosing a Go Logging Library 2026 · Dash0](https://www.dash0.com/guides/golang-logging-libraries)
- [Managing pytest's output](https://docs.pytest.org/en/stable/how-to/output.html)

## Related notes

- [[wave-3-opentelemetry-local]] · [[wave-3-vscode-ide]] · [[wave-3-ease-of-use]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
