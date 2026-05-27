---
phase: 07-web-add-on-v0-2
plan: "02"
subsystem: web-scaffold
tags: [vite, react, typescript, mise, pnpm, corepack, baseline, web]
dependency_graph:
  requires:
    - "07-01: has_web prompt, Guard-2 path-shape directories, _exclude entries"
  provides:
    - "template/web/package.json.jinja2 (Vite 7 + React 19 + TS 5.7, packageManager pnpm@9.15.0)"
    - "template/web/pnpm-lock.yaml (shipped verbatim, lockfileVersion 9.0)"
    - "Working Vite + React + TS scaffold under web/ with @ -> ./src path alias"
    - "src/config.ts.jinja2 as the single Jinja extension point (Pitfall §1 firewall)"
    - "vite.config.ts.jinja2 with {% if has_backend %} proxy stub for 07-04"
    - ".mise.toml.jinja2 {% if has_web %} corepack block"
    - "_CLEAN_ENV extended with Node-specific scrubs (07-04..07-07 reuse)"
    - "test_web_baseline_builds smoke test (pnpm install + tsc + build)"
  affects:
    - copier.yml (_tasks corepack enable)
    - template/.mise.toml.jinja2 (corepack tool under has_web)
    - tests/_helpers.py (_CLEAN_ENV Node scrubs)
    - tests/test_web_polarity.py (build-smoke test)
tech_stack:
  added:
    - "vite ^7.1.0"
    - "@vitejs/plugin-react ^4.3.0"
    - "react ^19.2.0 / react-dom ^19.2.0"
    - "typescript ~5.7.0"
    - "@types/node ^22.10.0 / @types/react ^19.2.0 / @types/react-dom ^19.2.0"
    - "packageManager pnpm@9.15.0 (via corepack)"
  patterns:
    - "Single Jinja-templated TS file (src/config.ts.jinja2) re-exported by all .tsx (Pitfall §1)"
    - "TS project references: app tsconfig.json + tsconfig.node.json (composite) for vite.config"
    - "Path alias @ -> ./src declared identically in tsconfig.json paths AND vite.config resolve.alias (Pitfall §4)"
    - "Block-level Jinja conditionals in TOML (REVIEW-CHECKLIST §5)"
key_files:
  created:
    - "template/{% if has_web %}web{% endif %}/package.json.jinja2"
    - "template/{% if has_web %}web{% endif %}/pnpm-lock.yaml"
    - "template/{% if has_web %}web{% endif %}/tsconfig.json"
    - "template/{% if has_web %}web{% endif %}/tsconfig.node.json"
    - "template/{% if has_web %}web{% endif %}/vite.config.ts.jinja2"
    - "template/{% if has_web %}web{% endif %}/index.html.jinja2"
    - "template/{% if has_web %}web{% endif %}/src/main.tsx"
    - "template/{% if has_web %}web{% endif %}/src/App.tsx"
    - "template/{% if has_web %}web{% endif %}/src/config.ts.jinja2"
    - "template/{% if has_web %}web{% endif %}/src/vite-env.d.ts"
    - "template/{% if has_web %}web{% endif %}/.gitignore"
  modified:
    - "template/.mise.toml.jinja2"
    - "copier.yml"
    - "tests/_helpers.py"
    - "tests/test_web_polarity.py"
decisions:
  - "TS project-references require tsconfig.node.json to set composite=true (NOT noEmit) and the app-side tsconfig.json must NOT include vite.config.ts (the reference covers it). Without this, `tsc --noEmit` fails TS6305/TS6306/TS6310. Discovered during build-smoke verification; fixed as a Rule 1 bug."
  - "Existing .mise.toml.jinja2 already pins node=24 and pnpm=latest unconditionally (Phase 1), so the has_web addition is only `\"npm:corepack\" = \"latest\"` — not a second node= entry which would be a TOML key collision. STACK.md's node@22 recommendation was superseded by the live template's node@24 base pin; node@24 supersets the >=20.19 requirement of Vite 7 / React 19 / TS 5.7."
requirements: [WEB-04, WEB-05, DEV-W04]
metrics:
  duration: ~80m (interrupted by session limit mid-task-3, resumed)
  completed: "2026-05-27T05:38:31Z"
  tasks_completed: 3
  files_changed: 15
---

# Phase 7 Plan 02: Vite + React + TypeScript Baseline Summary

One-liner: A renderable Vite 7 + React 19 + TS 5.7 scaffold under `template/web/` that installs, typechecks, and `pnpm build`s to `dist/index.html` cleanly — guarded by a 6th polarity test (`test_web_baseline_builds`) and gated by the Pitfall §1 single-Jinja-TS-file firewall.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Package legitimacy gate + package.json.jinja2 + pnpm-lock.yaml | 0949f48 | package.json.jinja2, pnpm-lock.yaml |
| 2 | tsconfig + vite.config + index.html + src/ files (one Jinja TS file) | 4609e86 | tsconfig.json, tsconfig.node.json, vite.config.ts.jinja2, index.html.jinja2, src/main.tsx, src/App.tsx, src/config.ts.jinja2, src/vite-env.d.ts, .gitignore |
| 3 | Wire .mise.toml corepack + Copier _tasks + build-smoke polarity test | f1863af | .mise.toml.jinja2, copier.yml, tests/_helpers.py, tests/test_web_polarity.py, tsconfig.json (auto-fix), tsconfig.node.json (auto-fix) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TS project-references misconfiguration broke `tsc --noEmit`**

- **Found during:** Task 3 (build-smoke test execution)
- **Issue:** The Task 2 `tsconfig.json` / `tsconfig.node.json` pair (authored from the plan's intent of "separate config for vite.config.ts so the main config can target DOM without Node ambient types polluting app code") failed `tsc --noEmit` with three errors: `TS6305` (output file `vite.config.d.ts` not built from source), `TS6306` (referenced project must have `composite: true`), `TS6310` (referenced project may not disable emit). The root cause: TypeScript project references require the referenced sub-project to be `composite: true` and to emit, AND the referencing project must not also include the referenced file in its own `include`.
- **Fix:** (a) `tsconfig.node.json`: replaced `"noEmit": true` with `"composite": true`. (b) `tsconfig.json`: removed `"vite.config.ts"` from the app-side `include` array (the project reference covers it). This is the canonical Vite + TS scaffold shape; `vite build` itself runs its own pre-bundle typecheck, and `pnpm exec tsc --noEmit` now exits 0.
- **Files modified:** `template/{% if has_web %}web{% endif %}/tsconfig.json`, `template/{% if has_web %}web{% endif %}/tsconfig.node.json` (committed atomically with Task 3 since they were discovered during Task 3's verification step).
- **Commit:** f1863af

### Plan-vs-reality reconciliations (not bugs, documented for traceability)

**2. .mise.toml already pins node + pnpm; only corepack added under has_web**

The plan's Task 3 said "add a conditional block ... `node = \"22\"` ... `corepack = \"latest\"`" under `{% if has_web %}`. The live `template/.mise.toml.jinja2` (from Phase 1) already declares `node = "24"` and `pnpm = "latest"` unconditionally in the base `[tools]` table. Adding a second `node =` key inside the same table would be a TOML key collision. The correct minimal change — and what the plan's Pitfall §3 actually requires — is the corepack enablement, so the conditional block adds only `"npm:corepack" = "latest"`. Node 24 supersets the `>=20.19` floor that Vite 7 / React 19 / TS 5.7 need, so the STACK.md node@22 recommendation is satisfied (and exceeded) by the existing base pin. No functional gap.

**3. slopcheck not invoked (advisory gate, all packages [VERIFIED])**

Task 1 step 3 said to run `slopcheck install ...` "or equivalent — if `slopcheck` is unavailable, document the skip." `slopcheck` is not on PATH in this execution environment. Per the plan, all 8 packages are `[VERIFIED]` in 07-RESEARCH.md §Package Legitimacy Audit (vite, @vitejs/plugin-react, react, react-dom, typescript, @types/node, @types/react, @types/react-dom), so the gate is informational here and was skipped. The shipped `pnpm-lock.yaml` pins exact transitive versions (lockfileVersion 9.0) so consumers install a content-addressed dependency tree.

## Verification Results

All 6 polarity tests pass (observed in this session, not predicted):

```
tests/test_web_polarity.py::test_web_polarity_directory_presence[True]  PASSED
tests/test_web_polarity.py::test_web_polarity_directory_presence[False] PASSED
tests/test_web_polarity.py::test_web_false_no_dotfile_leaks             PASSED
tests/test_web_polarity.py::test_web_false_no_literal_jinja_brace_filenames PASSED
tests/test_web_polarity.py::test_web_true_no_literal_jinja_brace_filenames  PASSED
tests/test_web_polarity.py::test_web_baseline_builds                    PASSED
6 passed in 23.56s
```

`test_web_baseline_builds` ran the full pipeline against a freshly-rendered scratch scaffold: `pnpm install --frozen-lockfile` (exit 0), `pnpm exec tsc --noEmit` (exit 0), `pnpm build` (exit 0, `vite v7.3.3 ... ✓ built in 888ms`), and asserted `dist/index.html` is a file. Build observed producing `dist/index.html` (0.32 kB) + `dist/assets/index-*.js` (193 kB / 60.6 kB gzip).

Plan verification criteria (observed):
- `find template -name '*.tsx.jinja2'` returns 0 (Pitfall §1 firewall holds).
- Exactly two `.jinja2`-suffixed TS/TSX files under web/: `vite.config.ts.jinja2` and `src/config.ts.jinja2`.
- `@` alias declared identically in `tsconfig.json` (`paths: {"@/*": ["./src/*"]}`) AND `vite.config.ts.jinja2` (`resolve.alias: {"@": ...}`) — Pitfall §4 parity.
- `copier.yml` parses as valid YAML.
- `.mise.toml.jinja2` `{% if has_web %}` conditional spans its own lines (REVIEW-CHECKLIST §5 — no inline Jinja in TOML).

## Known Stubs

- `vite.config.ts.jinja2` contains a `{% if has_backend %} // proxy block populated by Plan 07-04 {% endif %}` comment stub. Intentional — 07-04 fills it with the actual `proxy` object. The conditional shape lands now to prove both polarities render (has_backend true/false). This is a documented forward-dependency, not a blocking stub.
- `src/App.tsx` renders a minimal "Hello {PROJECT_NAME}" placeholder. Intentional — 07-03 replaces it with the real shadcn component gallery. Imports `PROJECT_NAME` from `./config` to exercise the Pitfall §1 single-Jinja-file pattern end-to-end.

## Threat Surface Scan

STRIDE register items from the plan addressed:
- **T-07-04 (supply-chain tampering, package.json deps):** All 8 packages `[VERIFIED]`; caret/tilde ranges from STACK.md; `pnpm-lock.yaml` shipped verbatim so consumers install pinned transitives via `--frozen-lockfile`.
- **T-07-05 (env leak into scratch subprocess):** `_CLEAN_ENV` extended to drop `NODE_*`, `npm_config_*`, `PNPM_HOME`, `NVM_*` so outer Node/pnpm installs don't false-pass the build smoke.
- **T-07-06 (info disclosure, src/config.ts.jinja2):** accept — only `project_name`/`project_description` (user-public) + `HAS_BACKEND` build-bool land here; no secrets.

No new network endpoints, auth paths, or trust boundaries introduced beyond what the plan's threat model anticipated. No threat flags raised.

## Self-Check: PASSED

(see appended Self-Check section below)
