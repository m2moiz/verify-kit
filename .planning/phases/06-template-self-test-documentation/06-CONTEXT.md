# Phase 6: Template Self-Test & Documentation - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 delivers two coupled outcomes:

1. **Repo-level self-verification.** A GitHub Actions workflow (`.github/workflows/template-selftest.yml`) that, on every PR to verify-kit itself, runs `copier copy` onto a scratch directory for each meaningful add-on combination and asserts `just verify` exits 0 inside the generated project. A regression in the template fails the PR before merge.
2. **Documentation set + OSS-launch readiness.** The repo ships a README (philosophy, quickstart, add-on inventory, copier-update path, troubleshooting, dual-audience checklist), CHANGELOG (release-please-driven SemVer + hand-edited "Breaking changes for consumers" callouts), CONTRIBUTING.md (smoke-test loop + add-a-check guide + add-an-add-on-slot guide), architecture diagram (inline Mermaid in README), plus OSS boilerplate (LICENSE, SECURITY.md, CODE_OF_CONDUCT.md, ISSUE_TEMPLATE/*), and PR-template-driven dual-audience checklist enforcement. The "OSS launch" scope-expansion (D-16) folds in 4 OSS-blocker beads and 2 deferred Phase 4 audits so v0.1 ships truly OSS-ready.

**In scope:** DOC-01 through DOC-05 + 4 OSS-blocker beads (verify-kit-3u2 / -yr7 / -93h / -1v6) + Phase 4 deferred ceremonies (secure-phase, validate-phase).
**Out of scope:** v0.2 add-on slots (web, audio, game). Multi-contributor PR governance beyond the basic templates. Pre-1.0 versioning policy beyond SemVer (covered by release-please defaults).

</domain>

<decisions>
## Implementation Decisions

### Self-test CI matrix

- **D-01:** Matrix is **5 rows on Linux per-PR + nightly macOS rerun** of the same 5 rows on a weekly schedule. Matches ROADMAP SC1 exactly without burning macOS-runner minutes on every PR.
- **D-02:** The 5 matrix entries are: `base` (no add-ons), `+backend`, `+llm`, `+backend+llm`, `+backend+llm+logfire+fastapi_mcp`. Each Copier answer-set is a job that runs `copier copy --data ... /tmp/scratch-<entry>` → `cd /tmp/scratch-<entry>` → `just verify` → assert exit 0.
- **D-03:** Wall-clock budget per PR is **< 10 minutes** (ROADMAP SC5). Runner-minute budget is well under GitHub free-tier monthly cap (5 jobs × ~3 min × ~40 PRs/month ≈ 600 of 2000 free minutes).
- **D-04:** Nightly macOS schedule mirrors Phase 5 D-09 cadence shape (weekly cron). Planner picks the exact cron value during planning; precedent is `0 4 * * 0` (Sunday 04:00 UTC).

### README structure & voice

- **D-05:** README opens **quickstart-first, then philosophy**. Above-the-fold: tagline → asciinema cast → one-line `copier copy ...` command → 2-sentence "why this exists" lead-in. Philosophy paragraph appears after.
- **D-06:** **asciinema cast of `just verify` running** is the headline visual. Cast file lives in-repo (planner picks exact path under `docs/casts/` or similar) and is embedded via GitHub-native player or asciinema.org URL — planner discretion based on what renders cleanly.
- **D-07:** **Architecture diagram is inline Mermaid in README** — single source of truth, satisfies DOC-05 in the same file. Source: `research/00-architecture-overview.md`. Layered view: Universal Foundation + four add-on slots.
- **D-08:** **IDE Problems-panel PNG screenshot** included in README to show the dual-audience promise (humans see clickable errors). PNG in `docs/img/`. Caption notes which IDE.
- **D-09:** **Dual-audience six-row checklist lives in README** as its own section (not a separate file). ~50 lines added.

### CHANGELOG + release tooling

- **D-10:** **release-please (Google) is the release automation.** Conventional-commits-driven; release-please bot opens a release PR with auto-generated CHANGELOG entries.
- **D-11:** Per-release **"Breaking changes for consumers" callout is mandatory** in every release entry (may be empty). The release-please-generated section is overridden / supplemented by a hand-edited block before merging the release PR. This is the consumer-facing migration instruction; it must read like a recipe, not a commit log.
- **D-12:** **SemVer is enforced via the release-please commit-message contract** (`feat!:` / `fix:` / `chore:` / etc.). Documented in CONTRIBUTING.md.

### CONTRIBUTING.md scope

- **D-13:** **Expanded scope** — covers (a) the smoke-test loop (every PR triggers the matrix in DOC-04), (b) "add a new check in 10 lines" with code snippet, AND (c) "how to add a new add-on slot" (Copier prompt + path-gating + jinja conditional + tests). Section (c) is partly speculative until v0.2 actually does it; CONTRIBUTING flags this with a "may evolve" note.

### Dual-audience checklist enforcement

- **D-14:** **PR template checkbox** (`.github/pull_request_template.md`) — the six dual-audience rows appear as checkboxes the author ticks. No automated CI grep gate (deferred per Deferred Ideas).

### OSS-launch boilerplate

- **D-15:** Phase 6 ships **LICENSE (MIT), SECURITY.md, CODE_OF_CONDUCT.md (Contributor Covenant 2.1), .github/ISSUE_TEMPLATE/bug.md, .github/ISSUE_TEMPLATE/feature.md.** LICENSE was pre-decided in PROJECT.md; the rest are conventional OSS boilerplate.

### Scope: hardening roll-in

- **D-16:** Phase 6 **also closes 4 OSS-blocker beads + 2 deferred Phase 4 audits**, expanding the original 5-DOC scope so v0.1 ships truly OSS-ready:
  - `verify-kit-3u2` — Phase 4/5 route auth scaffold (token-gate `/__debug/*` and `/summarize` / `/echo` so a public consumer doesn't ship open endpoints).
  - `verify-kit-yr7` — Phase 5 `/summarize` input-length cap + basic prompt-injection defenses.
  - `verify-kit-93h` — Phase 4 `/echo` route hardening (same shape as `/summarize`).
  - `verify-kit-1v6` — Phase 5 README LLM section human-read pass (prose sanity check; not just AI-generated).
  - Phase 4 `secure-phase` audit (threat-model ceremony skipped at Phase 4 close).
  - Phase 4 `validate-phase` audit (Nyquist coverage ceremony skipped at Phase 4 close).
- **D-17:** **Each bead/audit becomes its own dedicated Phase 6 plan** for atomic execution and clean audit trail. Estimated plan count: 5 DOC-driven plans + 4 bead plans + 2 audit-ceremony plans ≈ **8–11 plans total** for Phase 6.

### Claude's Discretion

- Exact asciinema asset hosting (in-repo `.cast` file vs asciinema.org embed URL) — planner picks based on what GitHub renders cleanly.
- Mermaid diagram exact box-and-arrow layout — planner derives from `research/00-architecture-overview.md`.
- release-please config knobs (monorepo vs single-package, which changelog sections, header text) — planner picks defaults from release-please docs.
- Exact route auth scaffold mechanism (header token, signed request, per-route guard, middleware-based) — research surfaces options; planner chooses lowest-friction shape compatible with the `/__debug/*` env-gate already in Phase 4.
- Exact prompt-injection defenses for `/summarize` beyond the locked input-length cap (strip control chars, ban known injection patterns, content-type validation) — planner picks based on Phase 5 SECURITY.md threat model.
- Nightly macOS cron exact value (precedent `0 4 * * 0` from Phase 5 D-09) — planner picks.
- CHANGELOG sections beyond mandatory "Breaking changes for consumers" — release-please convention applies (Added / Changed / Fixed / Deprecated / Removed / Security); planner picks the subset.
- CONTRIBUTING.md "add an add-on slot" depth — planner balances usefulness vs. speculative-rot risk; flags speculative content with a "may evolve" note per D-13.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + requirements
- `.planning/ROADMAP.md` — Phase 6 section (lines 114–127): goal + 5 success criteria
- `.planning/REQUIREMENTS.md` — DOC-01 through DOC-05 (lines 162–166)
- `.planning/PROJECT.md` — overall verify-kit vision + MIT license decision + constraints

### Prior phase artifacts (locked decisions to honor)
- `.planning/phases/05-llm-add-on/05-CONTEXT.md` — D-04, D-06, D-17, D-18 (locked README LLM section content); D-22 (11 packages, not 12 — README and dependency-inventory must reflect)
- `.planning/phases/05-llm-add-on/05-SECURITY.md` — Phase 5 threat model; informs `/summarize` injection defenses
- `.planning/phases/05-llm-add-on/05-SUMMARY.md` files — Phase 5 deliverable inventory
- `.planning/phases/04-backend-fastapi-add-on/` SUMMARY files — Phase 4 deliverable inventory; informs `/echo` hardening and `secure-phase` / `validate-phase` audit scope

### Reference docs (source-of-truth for diagrams + decisions)
- `research/00-architecture-overview.md` — source for the Mermaid architecture diagram (DOC-05)
- `research/00-decision-log.md` — D-001 through D-022 history; consumer-facing breaking-changes callouts should reconcile against this

### Project review knowledge (mandatory reading for planner + reviewer)
- `.planning/REVIEW-CHECKLIST.md` — review patterns to hunt for during plan-review-convergence (cwd leaks, dead-code-via-narrative-ordering, cross-plan contract drift)
- `.planning/STATE.md` — current project state + Phase 4/5 deferred todos
- `.planning/learnings/DRIFT-PREVENTION.md` — drift-guard learnings
- `.planning/learnings/PHASE-02-RETRO.md`, `PHASE-03-RETRO.md` — prior-phase retrospectives

### External docs (planner consumes during research)
- release-please GitHub Action — https://github.com/googleapis/release-please-action
- Contributor Covenant 2.1 — https://www.contributor-covenant.org/
- asciinema embed docs — https://docs.asciinema.org/
- GitHub Actions matrix strategy — https://docs.github.com/actions/using-jobs/using-a-matrix-for-your-jobs

</canonical_refs>

<specifics>
## Specific Ideas

- **README skeleton** (top → bottom): repo title + tagline → asciinema cast → 1-line quickstart command → 2-sentence "why this exists" hook → philosophy paragraph → add-on inventory table (Copier prompts × generated files) → Mermaid architecture diagram → dual-audience six-row checklist section → IDE Problems-panel screenshot → `copier update` walkthrough → troubleshooting → link to CONTRIBUTING.md.

- **CI matrix entries** (per ROADMAP SC1): `base`, `+backend`, `+llm`, `+backend+llm`, `+backend+llm+logfire+fastapi_mcp`. Five entries.

- **Nightly macOS workflow** is a sibling workflow (`.github/workflows/template-selftest-macos.yml`) that re-runs the same 5 entries on `macos-latest` weekly. Failure opens (does not block) — surfaces macOS-only regressions without per-PR cost.

- **release-please config** lives at `.release-please-config.json` + `.release-please-manifest.json`. Generates `CHANGELOG.md` sections: Added / Changed / Fixed / Breaking changes for consumers (the last is hand-edited on every release PR; release-please's "BREAKING CHANGE" footer parser provides the starting list).

- **PR template** mirrors the six dual-audience rows verbatim as Markdown checkboxes; planner pulls the canonical row labels from PROJECT.md / CLAUDE.md.

- **OSS boilerplate file locations:** `LICENSE` (root), `SECURITY.md` (root), `CODE_OF_CONDUCT.md` (root), `.github/ISSUE_TEMPLATE/bug.md`, `.github/ISSUE_TEMPLATE/feature.md`, `.github/pull_request_template.md`.

- **6 hardening plans** (D-17): one plan per item — `06-XX-auth-scaffold-PLAN.md` (verify-kit-3u2), `06-XX-summarize-input-defenses-PLAN.md` (verify-kit-yr7), `06-XX-echo-hardening-PLAN.md` (verify-kit-93h), `06-XX-llm-readme-pass-PLAN.md` (verify-kit-1v6), `06-XX-phase4-secure-audit-PLAN.md`, `06-XX-phase4-validate-audit-PLAN.md`. Each closes its bead/todo on execution.

- **Plan ordering hypothesis** (planner refines): OSS boilerplate + LICENSE first → README + diagram + CHANGELOG + CONTRIBUTING → PR template + dual-audience enforcement → CI self-test workflows (linux per-PR + nightly macOS) → 4 bead plans (auth + injection + echo + readme-pass) → 2 audit ceremonies. Total: ~10 plans.

</specifics>

<deferred>
## Deferred Ideas

- **Audio / web / game add-on slots** — v0.2.
- **Automated CI grep gate for dual-audience checklist** — current trust model is PR-template checkbox + reviewer eye. Revisit if checkbox gets gamed.
- **"How to add a new add-on slot" CONTRIBUTING section** is speculative until v0.2 actually does it; document the current shape but flag as "may evolve".
- **release-please monorepo migration** — only relevant if verify-kit grows sibling repos.
- **macOS-only failure-isolation deep-dive** — Phase 6 nightly catches regressions; deeper investigation deferred to when a regression surfaces.
- **GitHub Security Advisory workflow integration** — SECURITY.md will name the contact path but full GHSA workflow is post-v0.1.
- **Pre-commit hook enforcement of conventional-commits** — release-please will parse what it parses; deeper enforcement is post-v0.1.

</deferred>

---

*Phase: 06-template-self-test-documentation*
*Context gathered: 2026-05-22 via /gsd:discuss-phase*
