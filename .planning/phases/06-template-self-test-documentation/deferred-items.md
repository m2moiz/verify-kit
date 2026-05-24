
## 2026-05-24 — 06-13 cold-start gate finding

Plan 06-13 completion checklist included an end-to-end `just verify` cold-start
gate. Result: `just verify` exits 1 with the backend check timing out at 600s.

Drill-down:
- Backend check runs `uv run pytest tests/backend/ -q --tb=short` (harness/checks/backend.py)
- 24 tests collect cleanly in 0.16s; the hang is during execution
- Likely cause: DB integration tests need Testcontainers/Docker daemon stack
  AND the harness check runs pytest WITHOUT bringing the stack up first
  (that's the `verify-backend` recipe's job, not the `verify` umbrella's)

This is NOT the orphan-container bug that r7v was filed against — r7v
specifically addressed `just verify-backend` leaving docker containers
running on failure exits, which IS fixed and asserted by
`test_verify_backend_full_path_leaves_no_orphan_containers` (passing).

The cold-start `just verify` timeout is a separate issue: the umbrella
`verify` harness check for backend should either (a) skip when docker
daemon not initialized, (b) bring up the stack first, or (c) be scoped
to unit-only backend tests with integration tests gated behind a marker.

Suggested follow-up: file a new bead `harness.backend.check-timeout-without-stack`
for v0.1.2 or Phase 7 review.

