---
title: Learnings Index
aliases: [Atomic Learnings, Learnings MOC, Mistakes & Patterns]
tags: [moc, verify-kit, learnings, atomic]
created: 2026-05-22
last_updated: 2026-05-22
---

# 📚 Atomic Learnings

> [!info] What this is
> Reusable patterns extracted from session retrospectives in `research/synthesis/`. Each note is **one** pattern, grounded in concrete evidence (commit SHAs, file paths, line numbers, conversation citations). Designed to be portable knowledge that survives across projects, not single-session anecdotes.

## How to use

When planning a new phase or working through a problem that feels familiar, scan this index. If a learning note matches, follow its links to the original incident in `research/synthesis/` for the full context.

When writing a new session retro, extract any **reusable pattern** as a standalone note here. Cite the source session at the top via `source_session: [[../synthesis/<file>]]`. The session retro keeps the narrative; the atomic notes hold the lessons.

## Index

### GSD workflow patterns

- [[internal-checker-vs-external-reviewer]] — Internal reviewer (gsd-plan-checker) shares planner's blind spots; external (Codex) catches a different class of bug. First Codex cycle found 8 HIGHs after internal said "0 issues."
- [[convergence-oscillation-restructure-trigger]] — When convergence HIGH count stops trending monotone-decreasing (e.g. 1 → 3), that's rule 08's structural-coupling signal. Restructure, don't grind.
- [[manual-fix-meta-bug-cascade]] — Each manual fix to a fragile verify-block can introduce a fresh meta-bug. Grep is not verification — local "did my new string appear?" checks won't catch semantic drift.
- [[each-gate-catches-different-classes-of-bug]] — Convergence → verify-work → secure-phase → code-review are non-redundant. Each gate finds bugs the others can't see.
- [[heavy-verify-belongs-in-verify-work-not-execute-plan]] — Multi-minute test matrices belong in `/gsd:verify-work`, not in execute-plan's inline `<verify>` blocks. Heavy inline verify hangs executors silently.
- [[sub-agent-false-claims-must-be-grounded]] — Sub-agents are confidently wrong about environmental facts ("X tool not installed" when it is). Verify negative claims before propagating into plans.
- [[state-md-vs-roadmap-checkbox-confusion]] — `.planning/STATE.md` is the source of truth for phase status. ROADMAP checkboxes are stale by design.

### Security & threat-model patterns

- [[accepted-risk-must-match-distribution-intent]] — A `disposition: accept` in a threat register is only defensible against the project's current distribution scope. When scope changes (private → OSS), re-evaluate every `accept`.
- [[keyword-checks-are-not-comprehensibility-checks]] — `assert "X" in text` confirms a string exists, not that the prose is correct. For consumer-facing docs, a human-read pass is mandatory.

### LLM / observability patterns

- [[cost-double-tokenization-pattern]] — `tokencost.calculate_*_cost(string, model)` re-tokenizes; the cost drifts from billed. Use `litellm.completion_cost(completion_response=response)` to read the provider's actual usage block.

### Dependency / packaging patterns

- [[transitive-dep-conflicts-only-uv-sync-catches]] — Planning loops can't catch transitive dep conflicts. The `/gsd:verify-work` cold-start render is where they surface. Prefer `*-slim` packages with explicit extras over meta-packages.

## How these notes were generated

This first batch of atomic learnings came from the Phase 5 LLM Add-on session, written on 2026-05-22. See the source session retro:

- [[session-2026-05-22-phase-5-llm-and-verification]]

Each atomic note links back to the section of the session retro where the original incident is documented, plus to commit SHAs, file paths, and `05-*.md` planning artifacts for grounded evidence.

## Source session retros

- [[session-2026-05-18-phase-1-and-2-buildout]] — Phase 1 build + Phase 2 plan (prior session, atomic notes not extracted here yet)
- [[session-2026-05-22-phase-5-llm-and-verification]] — Phase 5 full session (atomic notes above)
