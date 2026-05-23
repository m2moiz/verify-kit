---
phase: 06-template-self-test-documentation
plan: "06-08"
plan_name: template-selftest-ci
type: summary
wave: 5
requirements: [DOC-04]
closes_beads: []
commits:
  - 98ba417 ci(selftest): add Linux template-selftest PR-gating matrix
  - d31f417 ci(selftest): add weekly macOS template-selftest sibling
  - ed4c164 chore(scripts): add act-validate-selftest.sh with --full SC5 mode
files_created:
  - .github/workflows/template-selftest.yml
  - .github/workflows/template-selftest-macos.yml
  - .planning/scripts/act-validate-selftest.sh
files_modified: []
---

# Plan 06-08: Template Self-Test CI — Summary

Lands DOC-04 / ROADMAP SC1: the trust-anchor closure where verify-kit verifies itself. Every PR triggers a 5-combo `copier copy` + `just verify` matrix on Linux; the same matrix re-runs weekly on macOS without blocking merges. A local `act` helper script gives operators a fast PR-local sanity check (default) and an SC5-compliant full-matrix mode (`--full`) with elapsed-time reporting against the 10-min budget.

## Producer contract exposed to downstream

- `.github/workflows/template-selftest.yml` — canonical PR-gating self-test (Linux, 5 combos: base / backend / llm / backend-llm / full)
- `.github/workflows/template-selftest-macos.yml` — weekly macOS sibling (Sun 04:00 UTC + `workflow_dispatch`); matrix byte-for-byte parity with the Linux file
- `.planning/scripts/act-validate-selftest.sh` — local SC5 validation; default runs `base` combo; `--full` runs all 5 sequentially with elapsed vs 600 s budget check
- Combo names (`base / backend / llm / backend-llm / full`) are the canonical identifiers for any future debugging or matrix re-runs

## Key implementation details

### Matrix data shape (5 keys per row)

Each `include` entry sets a JSON `data:` object with all 5 add-on flags:
`has_backend`, `has_llm`, `has_logfire`, `has_fastapi_mcp`, `has_db`.

`has_db` is set explicitly per row even when `has_backend=false` (where copier's `when: has_backend` gate would suppress it) — defensive against silent default acceptance and required because `copier.yml:173` defaults `has_db: true` and `copier.yml:37` gates DB file exclusion on `not has_db`.

| combo        | has_backend | has_llm | has_logfire | has_fastapi_mcp | has_db |
|--------------|-------------|---------|-------------|------------------|--------|
| base         | false       | false   | false       | false            | false  |
| backend      | true        | false   | false       | false            | true   |
| llm          | false       | true    | false       | false            | false  |
| backend-llm  | true        | true    | false       | false            | true   |
| full         | true        | true    | true        | true             | true   |

### Copier install incantation

Both workflows install copier with:

```
uv tool install copier --with copier-templates-extensions
```

`copier.yml:7` declares `_jinja_extensions: [copier_templates_extensions.TemplateExtensionLoader, ...]`. Without `--with copier-templates-extensions`, `copier copy` aborts before rendering any template file — and the matrix would silently test nothing. Both workflows also use `copier copy --trust` because Copier 9.15+ refuses to render `_jinja_extensions` / `_tasks` without it.

### Auth wiring (06-02 contract)

Each job sets both `VERIFYKIT_AUTH_TOKEN: dev-token-for-tests` and `ENV: dev` at the job level — defense-in-depth so the dev-mode fallback path covers any row whose generated app does not explicitly read the token.

### Path discipline (REVIEW-CHECKLIST §1)

Workflow shell `run:` blocks use absolute paths only (`$GITHUB_WORKSPACE`, `/tmp/scratch-${{ matrix.combo }}`). The helper script resolves `ROOT` via `"${BASH_SOURCE[0]}"` and `cd`'s into it so the script is callable from any cwd.

### macOS sibling non-blocking (D-04)

`template-selftest-macos.yml` deliberately omits the `pull_request` trigger. The header comment cross-references the Linux workflow ("Matrix entries must stay in sync with template-selftest.yml (Linux). Per D-04 macOS is weekly-only and non-blocking.") so the cross-plan contract is enforceable on future combo changes (REVIEW-CHECKLIST §3).

## SC5 ground-truth evidence (operator-driven)

`bash .planning/scripts/act-validate-selftest.sh` and `--full` exit codes + runtimes are operator-recorded at release time on a machine with Docker and the `catthehacker/ubuntu` image present. First-run image pull is a multi-GB download (§11 Pitfalls); steady-state runs use the cached image.

Wall-clock per matrix row on actual GHA is also recorded after the first PR runs the workflow — this is the empirical check on D-03's < 10 min target.

## Deviations from plan

None. All three task verify blocks passed on first invocation. No deviations from the cycle-3/4/6/7 corrected plan.

## Self-check

- [x] `.github/workflows/template-selftest.yml` exists (verified via Read tool / file system)
- [x] `.github/workflows/template-selftest-macos.yml` exists
- [x] `.planning/scripts/act-validate-selftest.sh` exists and is executable
- [x] 3 commits visible in `git log` (98ba417, d31f417, ed4c164)
- [x] Matrix YAML parity between Linux and macOS workflows (per-task verify confirmed)
- [x] 5 keys per row in both matrices (`has_backend`, `has_llm`, `has_logfire`, `has_fastapi_mcp`, `has_db`)
- [x] Both workflows install copier with `--with copier-templates-extensions` and pass `--trust` to `copier copy`
- [x] No `pull_request` trigger in macOS sibling
- [x] act helper resolves repo root via `BASH_SOURCE` (no cwd leak)
