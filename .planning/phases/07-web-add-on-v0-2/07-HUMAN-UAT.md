---
status: partial
phase: 07-web-add-on-v0-2
source: [07-VERIFICATION.md]
started: 2026-05-27
updated: 2026-05-27
---

## Current Test

[awaiting human testing]

## Tests

### 1. OTel Jaeger waterfall (end-to-end trace)
expected: With a rendered `has_web=true` + `has_backend=true` project, the dev env running, and `VITE_OTEL_EXPORTER_OTLP_ENDPOINT` set + Jaeger up, a button click → fetch → FastAPI → DB appears as a single connected waterfall span in Jaeger. (SDK ships inert-by-default; this verifies it activates correctly when enabled.)
result: [pending]

### 2. Lost Pixel visual-regression baseline acceptance
expected: With Docker available, `just verify --web` (or the Lost Pixel step) runs against the gallery, produces baseline PNGs on first run, and the `lost-pixel-approve` CLI shim (`--dry-run` then `--confirm`) stages updated baselines via git add. Visual diff inspection of the PNGs confirms the gallery renders as intended.
result: [pending]

### 3. Dark-mode WCAG AA contrast (visual)
expected: The component gallery in dark mode has visually sufficient text/background contrast across all sections and button variants. (Automated axe color-contrast is disabled due to axe-core <=4.11.4 oklch false positives, so this is a manual visual check.)
result: ORCHESTRATOR-VERIFIED (2026-05-27) — gallery screenshotted in both light and dark mode during execution; contrast confirmed strong in both. Re-confirm if the theme tokens change.

## Summary

total: 3
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0
note: item 3 verified visually by the orchestrator during execution (screenshot inspection); items 1-2 need a live dev/Docker environment.

## Gaps
