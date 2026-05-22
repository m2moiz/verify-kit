---
title: Each GSD gate catches a different class of bug — none are redundant
aliases: [non-redundant-gates, gate-coverage-matrix, four-gate-sequence]
tags: [verify-kit, learnings, atomic, gsd, gates]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Each GSD gate catches a different class of bug

> [!abstract] Pattern
> The four-gate sequence — `plan-review-convergence` → `verify-work` → `secure-phase` → `code-review` — looks redundant on the surface ("isn't review review?"). It's not. Each gate exercises a different layer of the system and finds a different class of bug. Skipping any gate leaves that class uncaught.

## The data point this came from

Phase 5 ran all four gates. **Each one found at least one substantive issue the others did not.**

### plan-review-convergence (8 cycles, 11 unique HIGHs)

Catches: **spec drift, cross-plan contract violations, decision references**.

Representative finds:
- `@llm_call` was a passthrough — D-03 routing not actually wired (cycle 1, HIGH #2)
- Promptfoo config missing `prompts:` entry — `just eval` wouldn't run (cycle 1, HIGH #4)
- `.verify/eval-results.json` path drift across justfile + workflow + SKILL.md (cycle 1, HIGH #5)
- `[dependency-groups]` vs `[project.optional-dependencies]` table mismatch (cycle 1, HIGH #3)
- Self-contradicting paragraphs in same `<action>` block (gsd-plan-checker, revision iter 1)
- Mid-path Jinja `tests/{% if has_llm %}llm{% endif %}/...` violates two-guard contract (cycle 2)

### verify-work (cold-start render + polarity matrix)

Catches: **transitive dependency conflicts, full-system render failures, polarity matrix violations**.

Representative finds:
- `pydantic-ai` meta-pkg pulls `[mistral]` → otel conflict with Phase 2 pin (test 1 cold-start)
- `fastmcp<3.0` vs `pydantic-ai-slim 1.100` requirement (test 1 cold-start)
- 69 forcing-function assertions across the 12-cell parametrize matrix (test 2)

> [!quote] Evidence
> `.planning/phases/05-llm-add-on/05-UAT.md` issues fixed during UAT
> Commit [`daba26f`](#) — "fix(deps): swap to pydantic-ai-slim + bump fastmcp for Phase 5 sync"

### secure-phase (threat-register audit)

Catches: **claimed mitigations that aren't actually in code**.

Representative finds in this session:
- All 19 threats SECURED with line-cited evidence (e.g., `template/harness/llm.py.jinja2:340-342` for `verify_kit.cost_usd`)
- Auditor explicitly noted: "verify mitigations EXIST in the committed implementation — do not scan for new threats. (register_authored_at_plan_time = true)"

The audit found **no claimed mitigation was missing**. It did **not** find that the existing mitigation (`verify_kit.cost_usd` attribute on the span) had a bug in its value computation — that's outside secure-phase's scope.

### code-review (source-level read)

Catches: **runtime semantic bugs that prior gates can't see**.

Representative finds:
- **WR-04** (cost double-tokenization) — runtime semantic bug; `cost_usd` drifting from billed. See [[cost-double-tokenization-pattern]].
- **WR-05** (Langfuse functional placeholder secrets `changeme-please-set-LANGFUSE_*`) — security smell that secure-phase couldn't catch because T-05-12's mitigation (loopback binding) wasn't false — but the default-fallback pattern in YAML was independently insecure.
- **WR-01** (meta-comments leaking into consumer code) — REVIEW-CHECKLIST §6 violation, only catchable by reading the rendered code.
- **WR-03** (silent drift-guard fallback) — test that silently passes under future pydantic-ai refactors; only catchable by reading the test's control flow.

## The coverage matrix

| Bug class | convergence | verify-work | secure-phase | code-review |
|---|:---:|:---:|:---:|:---:|
| Cross-plan API drift | ✓ | – | – | – |
| Spec internal contradictions | ✓ | – | – | – |
| Decision reference drift | ✓ | – | – | – |
| Transitive dep conflicts | – | ✓ | – | – |
| Template render polarity | – | ✓ | – | – |
| Full-system smoke | – | ✓ | – | – |
| Claimed mitigation missing | – | – | ✓ | – |
| Threat register coverage | – | – | ✓ | – |
| Runtime semantic bug | – | – | – | ✓ |
| Security smell in defaults | – | – | – | ✓ |
| Drift-guard quality | – | – | – | ✓ |
| Documentation leakage | – | – | – | ✓ |

**Zero overlap between columns.** None of the gates is replaceable by any combination of the others.

## What to do about it

> [!tip] Apply
> - **Default to running all four gates for any non-trivial phase.** Project rule 08 + *memory: `run_all_gsd_ceremonies`* already say this; this learning is the concrete justification.
> - **Don't skip code-review thinking "convergence + verify-work already covered it."** WR-04 was a real cost-reporting bug that polarity tests and threat register both missed.
> - **Don't skip secure-phase thinking "code-review will catch security."** Code-review verifies the code as written; secure-phase verifies the code against an explicit threat register. They are different shapes.
> - **Order matters.** Convergence first (cheapest, plan-level). Then verify-work (catches conflicts that come from spec). Then secure-phase (validates against explicit threats). Then code-review (final read).

## What "trivial phase" carve-out looks like

For a single-file refactor / rename / dependency bump:
- Convergence: skip (rule 08 trivial-phase carve-out)
- Verify-work: maybe skip if no new deps
- Secure-phase: skip if no new trust boundaries
- Code-review: still worth running — catches the runtime-semantic-bug class which exists for any code change

For anything that introduces new files, new contracts, new dependencies, or new external surfaces: **all four**.

## The cost of skipping each gate

This session's evidence:
- Skip convergence → 11 spec-level bugs ship into execution. Each one is a future runtime failure or wasted execution work.
- Skip verify-work → 3 transitive dep conflicts ship to consumers. They get unresolvable `uv sync` errors with no clear hint about which package to pin where.
- Skip secure-phase → unverified threat dispositions; "we said we'd mitigate X" but the code never actually shipped the mitigation.
- Skip code-review → cost-reporting bug + placeholder-secret security smell + reviewer-meta leaking into rendered code. Direct downstream user-facing problems.

## Related patterns

- [[internal-checker-vs-external-reviewer]] — why even just-convergence needs an external reviewer.
- [[transitive-dep-conflicts-only-uv-sync-catches]] — verify-work's unique value.
- [[cost-double-tokenization-pattern]] — concrete WR-04 example.
- [[accepted-risk-must-match-distribution-intent]] — secure-phase's `accept` dispositions are only as good as the scope they were written under.
- *memory: `run_all_gsd_ceremonies`*
- Project rule 08

## Open questions

- For Phase 6 — should there be a 5th gate ("template-self-test in CI matrix") between code-review and shipping? Probably yes; that's effectively what Phase 6 builds. It catches a 5th class: **cross-phase composition failures** where Phase A + Phase B render fine individually but break when combined.
