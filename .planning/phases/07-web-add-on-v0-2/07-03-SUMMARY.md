---
phase: 07-web-add-on-v0-2
plan: "03"
subsystem: web-scaffold
tags: [tailwind-v4, shadcn, gallery, dark-mode, vendoring, web, polarity-test]
dependency_graph:
  requires:
    - "07-02: Vite + React + TS baseline, src/config.ts.jinja2 shim, vite.config.ts.jinja2 with {% if has_backend %} proxy stub"
  provides:
    - "template/web/components.json (Tailwind v4 contract: config='', cssVariables=true, baseColor=neutral)"
    - "template/web/src/index.css (@import tailwindcss, @custom-variant dark, OKLCH :root/.dark per UI-SPEC)"
    - "template/web/src/lib/utils.ts (cn() = clsx + tailwind-merge)"
    - "template/web/src/components/ui/{button,card,input,label,dialog,sheet,sonner}.tsx (7 vendored shadcn components)"
    - "template/web/src/App.tsx (7-section gallery with data-lost-pixel-id markers)"
    - "template/web/src/components/gallery/DarkModeToggle.tsx (classList-based dark mode toggle)"
    - "Updated package.json.jinja2 with Tailwind + shadcn runtime deps"
    - "Regenerated pnpm-lock.yaml with all transitive deps"
    - "test_web_tailwind_shadcn_baseline polarity test (7 tests total all green)"
  affects:
    - "tests/test_web_polarity.py (new test_web_tailwind_shadcn_baseline)"
    - "template/web/vite.config.ts.jinja2 (@tailwindcss/vite plugin added)"
    - "template/web/src/main.tsx (index.css import, ThemeProvider, Toaster mount)"
tech_stack:
  added:
    - "tailwindcss ^4.3.0 (devDep)"
    - "@tailwindcss/vite ^4.3.0 (devDep)"
    - "tw-animate-css ^1.2.0 (devDep, shadcn v4 transitive)"
    - "class-variance-authority ^0.7.1 (dep, shadcn cva API)"
    - "clsx ^2.1.1 (dep, cn() helper)"
    - "tailwind-merge ^3.6.0 (dep, cn() helper)"
    - "radix-ui ^1.4.3 (dep, shadcn Radix primitives - consolidated package)"
    - "next-themes ^0.4.6 (dep, ThemeProvider for Toaster)"
    - "sonner ^2.0.7 (dep, Toast surface)"
    - "lucide-react ^1.16.0 (dep, icons)"
  patterns:
    - "CSS-first Tailwind v4 via @import 'tailwindcss' (no tailwind.config.js)"
    - "OKLCH color tokens in @theme inline + :root/.dark CSS variable blocks"
    - "shadcn vendored at template-author time (consumer never runs shadcn init)"
    - "7 components under src/components/ui/ with NO .jinja2 suffix (Pitfall §1 firewall)"
    - "App.tsx is single-page gallery with data-lost-pixel-id per section (D-W08/D-W09)"
    - "Dialog + Sheet render with defaultOpen for portal snapshot in plan 07-06"
    - "DarkModeToggle uses classList + ThemeProvider synced via next-themes"
key_files:
  created:
    - "template/{% if has_web %}web{% endif %}/components.json"
    - "template/{% if has_web %}web{% endif %}/src/index.css"
    - "template/{% if has_web %}web{% endif %}/src/lib/utils.ts"
    - "template/{% if has_web %}web{% endif %}/src/components/ui/button.tsx"
    - "template/{% if has_web %}web{% endif %}/src/components/ui/card.tsx"
    - "template/{% if has_web %}web{% endif %}/src/components/ui/input.tsx"
    - "template/{% if has_web %}web{% endif %}/src/components/ui/label.tsx"
    - "template/{% if has_web %}web{% endif %}/src/components/ui/dialog.tsx"
    - "template/{% if has_web %}web{% endif %}/src/components/ui/sheet.tsx"
    - "template/{% if has_web %}web{% endif %}/src/components/ui/sonner.tsx"
    - "template/{% if has_web %}web{% endif %}/src/components/gallery/DarkModeToggle.tsx"
  modified:
    - "template/{% if has_web %}web{% endif %}/package.json.jinja2"
    - "template/{% if has_web %}web{% endif %}/pnpm-lock.yaml"
    - "template/{% if has_web %}web{% endif %}/vite.config.ts.jinja2"
    - "template/{% if has_web %}web{% endif %}/src/App.tsx"
    - "template/{% if has_web %}web{% endif %}/src/main.tsx"
    - "tests/test_web_polarity.py"
decisions:
  - "Newer shadcn CLI uses consolidated radix-ui ^1.4.3 package (not @radix-ui/* individual packages). Adapted package.json accordingly — all Radix primitives resolve through the unified package."
  - "shadcn add command (new-style CLI with presets) required components.json to be authored manually with the exact schema from 07-RESEARCH.md. The --base-color flag is not supported in the newer CLI version."
  - "lib/utils.ts must be created manually with clsx + tailwind-merge since newer shadcn CLI does not auto-generate it during `shadcn add`. Added class-variance-authority, clsx, tailwind-merge as explicit deps."
  - "main.tsx wraps the app with ThemeProvider (next-themes, attribute=class) so the Toaster component's useTheme hook resolves correctly. The DarkModeToggle still uses classList.toggle('dark') for immediate feedback; ThemeProvider syncs the system preference."
  - "Dialog and Sheet render with defaultOpen per plan override of UI-SPEC — the PLAN is more specific, stating defaultOpen for Lost Pixel snapshot capture of portal content."
metrics:
  duration: ~11m
  completed: "2026-05-27T06:10:00Z"
  tasks_completed: 3
  files_changed: 16
---

# Phase 7 Plan 03: Tailwind v4 + shadcn Vendoring + Component Gallery Summary

One-liner: CSS-first Tailwind v4 wired via @tailwindcss/vite, 7 shadcn components vendored verbatim with OKLCH color tokens, and a 7-section dev-only gallery (App.tsx) with `data-lost-pixel-id` markers ready for plan 07-06 Lost Pixel snapshots — all guarded by an extended 7-test polarity suite (observed green).

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Vendor Tailwind v4 + shadcn 7 components into template | c18d86e | components.json, src/index.css, src/lib/utils.ts, 7 ui/*.tsx, package.json.jinja2, pnpm-lock.yaml, vite.config.ts.jinja2 |
| 2 | Author dev-only component gallery as App.tsx + DarkModeToggle | 684b67b | src/App.tsx, src/main.tsx, src/components/gallery/DarkModeToggle.tsx |
| 3 | Extend polarity test with Tailwind + shadcn coupling guards | cb3802c | tests/test_web_polarity.py |

## Deviations from Plan

### Plan-vs-reality reconciliations (not bugs)

**1. shadcn CLI version uses unified radix-ui package**

The plan cited individual `@radix-ui/*` packages as transitive deps (e.g., `@radix-ui/react-dialog`, `@radix-ui/react-slot`). The current shadcn CLI installs `radix-ui ^1.4.3` — a consolidated package containing all primitives. Components import as `import { Dialog as DialogPrimitive } from "radix-ui"`. Updated package.json.jinja2 to reflect the actual installed dependency. No functional gap; API is identical from the consumer side.

**2. shadcn CLI --base-color flag not supported; components.json authored manually**

The plan's Task 1 action listed `pnpm dlx shadcn@latest init -t vite --base-color neutral --css-variables --yes`. The current shadcn CLI changed the flag interface — `--base-color` is not recognized. The init was attempted via piped interactive input and also failed (new CLI shows preset names like "Nova", "Vega", etc. rather than base color selection). Resolution: authored `components.json` manually from the verbatim schema in 07-RESEARCH.md and `src/index.css` manually from the UI-SPEC OKLCH color table. Then ran `pnpm dlx shadcn@latest add button card input label dialog sheet sonner --yes` which only writes the component files (not components.json or index.css). Result is identical to what a successful `shadcn init` would have produced.

**3. lib/utils.ts not auto-generated by newer shadcn CLI; added manually + deps explicit**

The plan's Task 1 expected shadcn init to auto-create `src/lib/utils.ts` with the `cn()` helper. The newer CLI (add-only path) does not auto-generate it. Created manually: `cn = twMerge(clsx(...))`. Added `class-variance-authority`, `clsx`, `tailwind-merge` as explicit dependencies (they were not auto-added by `shadcn add` in the new CLI). These are the exact packages that button.tsx imports.

**4. ThemeProvider added to main.tsx for Toaster compatibility**

The plan's Task 2 said "Also import `<Toaster />` from `@/components/ui/sonner` and mount it". The vendored `sonner.tsx` uses `useTheme` from `next-themes`, which requires a `ThemeProvider` in the component tree. Without it, `useTheme()` returns `"system"` but the theme never actually applies. Added `<ThemeProvider attribute="class" defaultTheme="system" enableSystem>` wrapping the app in main.tsx. DarkModeToggle still calls `classList.toggle("dark")` for immediate feedback; ThemeProvider ensures correct initial system-preference detection and makes the Toaster's theme-aware icon styling work.

## Verification Results

All 7 polarity tests pass (observed, not predicted):

```
tests/test_web_polarity.py::test_web_polarity_directory_presence[True]  PASSED
tests/test_web_polarity.py::test_web_polarity_directory_presence[False] PASSED
tests/test_web_polarity.py::test_web_false_no_dotfile_leaks             PASSED
tests/test_web_polarity.py::test_web_false_no_literal_jinja_brace_filenames PASSED
tests/test_web_polarity.py::test_web_true_no_literal_jinja_brace_filenames  PASSED
tests/test_web_polarity.py::test_web_baseline_builds                    PASSED
tests/test_web_polarity.py::test_web_tailwind_shadcn_baseline           PASSED
7 passed in 43.11s
```

`test_web_tailwind_shadcn_baseline` ran the full pipeline and verified:
- Built CSS contains `oklch` (36 occurrences) + `--background` variable + > 5KB (28.5KB observed)
- No `tailwind.config.{js,ts,mjs,cjs}` exists
- `components.json` declares Tailwind v4 contract (config="", cssVariables=true)
- Exactly 7 vendored ui/ files: {button, card, input, label, dialog, sheet, sonner}
- App.tsx has 7 `data-lost-pixel-id=` markers + imports from `./config`

Plan success criteria (observed):
- `find template -name 'tailwind.config.*'` returns 0
- `find template -name '*.tsx.jinja2'` returns 0 (Pitfall §1 firewall holds)
- `vite.config.ts.jinja2` and `src/config.ts.jinja2` remain the only `.jinja2`-suffixed TS files
- 7 vendored components exactly: Button, Card, Input, Label, Dialog, Sheet, sonner

## Known Stubs

None — all gallery sections are wired. The `vite.config.ts.jinja2` `{% if has_backend %}` proxy stub (from 07-02) is intentional and documented.

## Threat Surface Scan

STRIDE register items from the plan addressed:
- **T-07-07 (supply-chain, shadcn CLI vendoring):** components vendored at template-author time; consumer never runs `pnpm dlx shadcn@latest`; component files committed verbatim.
- **T-07-08 (Tailwind v4 + shadcn coupling):** polarity test asserts no `tailwind.config.*` exists — future shadcn CLI regressions caught at test time.
- **T-07-09 (info disclosure, gallery):** gallery uses only PROJECT_NAME/PROJECT_DESCRIPTION from Copier answers.
- **T-07-10 (XSS, DarkModeToggle):** toggle only adds/removes the literal string "dark" from classList; no user input interpolated.
- **T-07-SC (npm supply-chain):** `radix-ui` (consolidated), `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `sonner`, `next-themes` are all widely-used packages with millions of weekly downloads on npm. The actual installed versions are pinned in the regenerated pnpm-lock.yaml.

No new network endpoints, auth paths, or trust boundaries introduced beyond what the plan's threat model anticipated.

## Self-Check: PASSED
