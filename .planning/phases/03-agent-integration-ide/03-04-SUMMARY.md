---
phase: 3
plan: 03-04
subsystem: ide-integration
tags: [vscode, ide, problem-matchers, launch, tasks, debugpy]
requires: []
provides:
  - template/.vscode/extensions.json (10 recommendations)
  - template/.vscode/settings.json (formatters, pytest, file hygiene)
  - template/.vscode/tasks.json (verify default build + custom problem matchers)
  - template/.vscode/launch.json (debugpy pytest + has_backend-gated uvicorn/compound)
  - README "Other editors" section (JetBrains/Zed/Neovim)
affects:
  - template/README.md.jinja2 (added section)
tech-stack-added: []
patterns:
  - Jinja-conditional JSON blocks inside JSONC (has_backend gate)
  - Custom VS Code problem matchers registered via top-level problemMatchers[]
key-files-created:
  - template/.vscode/extensions.json.jinja2
  - template/.vscode/settings.json.jinja2
  - template/.vscode/tasks.json.jinja2
  - template/.vscode/launch.json.jinja2
  - tests/test_vscode_files.py
  - tests/test_problem_matchers.py
  - tests/fixtures/ruff_sample.txt
  - tests/fixtures/pyright_sample.txt
  - tests/fixtures/biome_sample.txt
key-files-modified:
  - template/README.md.jinja2
decisions:
  - Ship .vscode/ unconditionally (no Copier guard) — files are inert for non-VS-Code users
  - Use top-level problemMatchers[] (VS Code 1.85+) per plan; fallback inline form documented
  - Strip JSONC // comments via simple regex in tests (no full JSON5 parser dep)
metrics:
  duration_min: ~25
  completed: 2026-05-19
  tasks: 6
  files: 9
requirements: [IDE-01, IDE-02, IDE-03, IDE-04, IDE-05]
---

# Phase 3 Plan 04: VS Code integration Summary

One-liner: Shipped `.vscode/{extensions,settings,tasks,launch}.json` into the
Copier template with custom Ruff/Pyright/Biome problem matchers, a default
`Ctrl+Shift+B` → `just verify` build task, has_backend-gated debugpy/FastAPI
launch configs, and a README section pointing non-VS-Code users to LSP/DAP
equivalents in JetBrains/Zed/Neovim.

## Tasks completed

| Task | Description | Commit |
|------|-------------|--------|
| T01 | `extensions.json` with 10 recommendations | 9725354 |
| T02 | `settings.json` with formatters, pytest, file hygiene | 8a4c740 |
| T03 | `tasks.json` with `verify` default build + 3 custom problem matchers | 76a3237 |
| T04 | `launch.json` with Jinja-gated FastAPI/compound entries | 8249730 |
| T05 | README "Other editors (JetBrains, Zed, Neovim)" section | 3b748e9 |
| T06 | `test_vscode_files.py` + `test_problem_matchers.py` + fixtures | 9ab74b6 |

## Test status

```
$ uv run pytest tests/test_vscode_files.py tests/test_problem_matchers.py -v
10 passed in 30.84s
```

All 7 vscode-file tests pass; all 3 problem-matcher regex tests pass against
captured Ruff / Pyright / Biome fixture output.

Manual verification of the launch.json Jinja conditional confirmed:
- `has_backend=true` → 2 configurations + 1 compound, JSON parses cleanly.
- `has_backend=false` → 1 configuration, no `compounds` key, JSON parses cleanly.

## Deviations from Plan

None — plan executed exactly as written.

## Acceptance criteria mapped to requirements

- **IDE-01** (recommended extensions prompt): T01 → `extensions.json` with 10
  recommendations, asserted via `test_extensions_json_has_ten_recommendations`.
- **IDE-02** (`Ctrl+Shift+B` runs `just verify`): T03 → verify task is
  `group.kind=build, isDefault=true`, asserted via
  `test_tasks_json_verify_is_default_build`.
- **IDE-03** (problem matchers surface errors in Problems panel): T03 + T06 →
  three custom matchers with regexes validated against real captured output.
- **IDE-04** (`launch.json` debug configs): T04 → pytest config always present;
  FastAPI uvicorn + Compound: All gated on `has_backend`, both branches parse
  as JSONC, asserted via `test_launch_json_has_backend_{true,false}`.
- **IDE-05** (README documents non-VS-Code setup): T05 → "Other editors"
  section mentions JetBrains, Zed, Neovim, asserted via
  `test_readme_documents_other_editors`.

## Self-Check: PASSED

Files verified to exist:
- template/.vscode/extensions.json.jinja2 — FOUND
- template/.vscode/settings.json.jinja2 — FOUND
- template/.vscode/tasks.json.jinja2 — FOUND
- template/.vscode/launch.json.jinja2 — FOUND
- tests/test_vscode_files.py — FOUND
- tests/test_problem_matchers.py — FOUND
- tests/fixtures/{ruff,pyright,biome}_sample.txt — FOUND

Commits verified in git log:
- 9725354 — FOUND
- 8a4c740 — FOUND
- 76a3237 — FOUND
- 8249730 — FOUND
- 3b748e9 — FOUND
- 9ab74b6 — FOUND
