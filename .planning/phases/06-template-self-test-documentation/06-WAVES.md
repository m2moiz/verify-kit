# Phase 6: Template Self-Test & Documentation — Wave Plan

**Phase:** 06-template-self-test-documentation
**Plans:** 10
**Waves:** 6
**Source ordering hypothesis:** 06-RESEARCH.md §Estimated Plan Count and Ordering (lines 952-985)

This phase has 10 plans grouped into 6 execution waves. Same-wave plans have zero `files_modified` overlap and can execute in parallel. Later waves consume contracts from earlier waves.

---

## Wave structure

| Wave | Plans (parallel) | Concern | Notes |
|------|------------------|---------|-------|
| **W1** | 06-01 (oss-boilerplate), 06-05 (release-please), 06-10 (phase4-audit-ceremonies) | Independent setup work — no producer dependencies | Three parallel plans; all touch disjoint files |
| **W2** | 06-02 (auth-scaffold) | Producer for the hardening trio | Single plan; gates W3 |
| **W3** | 06-03 (summarize-input-defenses), 06-04 (echo-hardening) | Consumers of 06-02's `require_auth` contract; touch the same file (`template/<app>/api.py.jinja2`) inside distinct `{% if %}` blocks | Two plans; both depend on 06-02. **Note:** they share `api.py.jinja2` as a modified file, but operate on disjoint Jinja blocks (06-03 inside `{% if has_llm %}`, 06-04 inside the unconditional `{% if has_backend %}` block, distinct constants `_INJECTION_MARKERS` vs `_CONTROL_CHARS_ECHO`). They can execute in parallel if the executor uses careful Edit operations; if a sequential ordering is safer, run 06-03 then 06-04 (or vice versa) — either order works |
| **W4** | 06-06 (readme-and-arch-diagram), 06-07 (contributing-and-pr-template) | Consumers of W1+W3 contracts (OSS files, hardening artifacts, commit contract) | Two plans; touch disjoint files (README.md + docs/ vs CONTRIBUTING.md + PR template) |
| **W5** | 06-08 (template-selftest-ci) | Exercises 06-02/03/04 hardened endpoints via matrix `+backend` and `+backend+llm` rows | Single plan |
| **W6** | 06-09 (llm-readme-pass) | Operates on the Phase 5 README LLM section after 06-06 has landed the top-level README (cross-reference target exists) | Single plan |

---

## Dependency graph

```
W1: 06-01 ──┐    06-05 ──┐    06-10 (independent)
            │             │
W2:         │   06-02 ────┤
            │             │
W3:         │   06-03, 06-04 (both depend on 06-02; share api.py.jinja2 across disjoint Jinja blocks)
            │             │
W4: 06-06 ──┴── 06-07 (06-06 depends on 06-01/02/03/04/05; 06-07 depends on 06-05)
            │
W5:        06-08 (depends on 06-02/03/04)
            │
W6:        06-09 (depends on 06-06 — Phase 5 README review pass on consumer-facing README)
```

---

## Parallelization summary

| Wave | Plans | Parallel? | Max parallel time | Cumulative |
|------|-------|-----------|-------------------|------------|
| W1 | 3 (06-01, 06-05, 06-10) | yes | longest-of-3 | 1× wave |
| W2 | 1 (06-02) | n/a | single | 2× wave |
| W3 | 2 (06-03, 06-04) | yes (with care on shared file) | longest-of-2 | 3× wave |
| W4 | 2 (06-06, 06-07) | yes | longest-of-2 (06-06 is heavier — checkpoints) | 4× wave |
| W5 | 1 (06-08) | n/a | single | 5× wave |
| W6 | 1 (06-09) | n/a | single | 6× wave |

If all waves run serially (no parallelism): 10 plans sequential.
With max parallelism: 6 waves end-to-end.

---

## Cross-wave contracts (REVIEW-CHECKLIST §3 register)

| Producer plan | Consumer plan(s) | Contract |
|---------------|------------------|----------|
| 06-01 | 06-06 (README footer) | CODE_OF_CONDUCT.md, SECURITY.md, LICENSE paths at repo root |
| 06-02 | 06-03, 06-04, 06-06 (Security H2), 06-08 (matrix env) | `from app.auth import require_auth`, env var `VERIFYKIT_AUTH_TOKEN`, header `X-VerifyKit-Token`, dev-fallback when env=dev + token unset, /healthz excluded |
| 06-03 | 06-06 (Security H2) | `_INJECTION_MARKERS` (3 regex), `SummarizeRequest` Field(max_length=5000) + field_validator, OWASP LLM01 caveat sentence |
| 06-04 | 06-06 (Security H2) | `_CONTROL_CHARS_ECHO` (distinct from 06-03's `_CONTROL_CHARS`), `EchoRequest` Field(max_length=5000) + field_validator, no injection denylist |
| 06-05 | 06-06 (footer CHANGELOG link), 06-07 (commit contract verbatim) | CHANGELOG.md path, conventional-commit contract (feat:/fix:/feat!:), "Breaking changes for consumers" section convention |
| 06-06 | 06-07 (README footer links to CONTRIBUTING.md — bidirectional sibling), 06-09 (cross-reference between top-level + consumer READMEs) | Top-level README.md exists at repo root with documented sections |
| 06-07 | (none in Phase 6) | CONTRIBUTING.md + PR template at canonical paths |
| 06-08 | (none in Phase 6) | Two workflows in .github/workflows/ + act validation script |
| 06-09 | (none in Phase 6) | Closes bead verify-kit-1v6 |
| 06-10 | (none in Phase 6) | Closes 2 deferred-audit STATE.md todos |

---

## Beads closed at phase completion

| Plan | Bead | Reason text shape |
|------|------|-------------------|
| 06-02 | verify-kit-3u2 | "Token auth scaffold landed in 06-02; APIKeyHeader + global dependency + dev fallback + /healthz exclusion" |
| 06-03 | verify-kit-yr7 | "/summarize starter-grade input defenses landed in 06-03: length cap + control-char strip + 3-marker denylist + Content-Type via Pydantic default" |
| 06-04 | verify-kit-93h | "/echo hardening landed in 06-04: length cap + control-char strip (denylist deliberately omitted per §4)" |
| 06-09 | verify-kit-1v6 | "Phase 5 LLM README human-read pass complete (edited / no-op)" |

Plus 06-10 closes the two STATE.md deferred-audit todos.

---

## Deviation from RESEARCH.md ordering hypothesis

**None.** The 10-plan layout and W1-W6 wave structure match §Estimated Plan Count and Ordering exactly. Both files use the same plan numbering (06-01..06-10) and the same wave assignments.

Two minor notes:

1. **W3 shared-file warning:** 06-03 and 06-04 both modify `template/{% if has_backend %}app{% endif %}/api.py.jinja2`. RESEARCH.md describes them as parallel; we keep them as parallel since their changes target distinct Jinja blocks and distinct module-level identifiers (`_INJECTION_MARKERS` vs `_CONTROL_CHARS_ECHO`). If the executor's Edit operations risk overlap during simultaneous execution, run them sequentially in either order — both are independent of each other on contracts.

2. **06-10 is W1 (not W6):** RESEARCH.md hints "Phase 4 audits can run any time (no deps); slotted last as a clean closure." We put them in W1 instead because they genuinely have no dependencies and W1 gets value from parallel execution. The closure narrative still holds: STATE.md flip happens during W1 commit, and the audit-trail rows on 04-SECURITY.md / 04-VALIDATION.md update independently of W2-W6 work.

---

## Per-plan estimated cost

| Plan | Tasks | Files | Estimated context (verify-kit historical avg) |
|------|-------|-------|------------------------------------------------|
| 06-01 | 2 | 6 | ~15-20% (static markdown, no jinja logic) |
| 06-02 | 3 | 6 | ~30-40% (FastAPI scaffolding + auth tests + jinja path-gating) |
| 06-03 | 2 | 2 | ~25-30% (api.py Edit + polarity test) |
| 06-04 | 2 | 2 | ~20-25% (api.py Edit + polarity test, lighter than 06-03 — no denylist) |
| 06-05 | 3 | 4 | ~15-20% (config files + workflow YAML) |
| 06-06 | 6 | 5 | ~40-50% (README authoring + 2 human checkpoints) |
| 06-07 | 2 | 2 | ~20-25% (CONTRIBUTING + PR template — needs to read harness API for §4 anti-drift) |
| 06-08 | 3 | 3 | ~25-30% (two workflow YAMLs + helper script) |
| 06-09 | 2 | 1 | ~10-15% (mostly checkpoint-driven; one optional edit) |
| 06-10 | 3 | 3 | ~10-15% (three checkpoints; SUMMARY-heavy) |

All plans target ≤50% context per execute-plan budget. The heaviest (06-06) is split across 6 tasks (3 auto + 1 author + 2 human-verify checkpoints) to keep each task within the 10-30% per-task envelope.

---

*Phase: 06-template-self-test-documentation*
*Wave plan authored: 2026-05-22*
