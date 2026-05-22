---
title: STATE.md is the source of truth for phase status; ROADMAP checkboxes are stale
aliases: [state-md-vs-roadmap, phase-completion-source-of-truth, dont-trust-roadmap-checkboxes]
tags: [verify-kit, learnings, atomic, gsd, state-management]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# STATE.md is the source of truth, ROADMAP checkboxes are stale

> [!abstract] Pattern
> For verify-kit phase completion status, **always read `.planning/STATE.md`**. The `- [ ]` / `- [x]` checkboxes at the top of `.planning/ROADMAP.md` are commonly stale — they describe original roadmap intent, not current execution status. Trusting ROADMAP checkboxes will lead to wrong claims like "Phase X wasn't done."

## The incident this came from

During Phase 5 close-out, I (Claude) repeatedly told the user that Phases 1, 2, 3 had not been executed yet. My evidence: I had read this snippet from `.planning/ROADMAP.md`:

```markdown
- [ ] **Phase 1: Template Skeleton & Toolchain** — ...
- [ ] **Phase 2: Universal Harness Core** — ...
- [ ] **Phase 3: Agent Integration & IDE** — ...
- [x] **Phase 4: Backend (FastAPI) Add-on** — ...
- [x] **Phase 5: LLM Add-on** — ...
- [ ] **Phase 6: Template Self-Test & Documentation** — ...
```

I concluded: 1/2/3 not done, only 4/5 done.

The user pushed back: *"I'm pretty sure that phase one was we started phase one, then went to two, then one to three, and that's kind of how we proceeded. We didn't skip any of the phases."*

I verified. `STATE.md` showed:

```markdown
1. ✅ Phase 1: Template Skeleton & Toolchain ...
2. ✅ Phase 2: Universal Harness Core ...
3. ✅ Phase 3: Agent Integration & IDE ...
4. ✅ Phase 4: Backend (FastAPI) Add-on ...
5. Phase 5: LLM Add-on ...
6. Phase 6: Template Self-Test & Documentation ...
```

Supporting evidence on disk:
- `.planning/phases/01-template-skeleton-toolchain/` has 4/4 plan SUMMARYs
- `.planning/phases/02-universal-harness-core/02-VERIFICATION.md` exists, dated 2026-05-18, status `gaps_found` (4/5 SC verified)
- `.planning/phases/03-agent-integration-ide/03-VERIFICATION.md` exists, dated 2026-05-19, status `passed` (5/5 must-haves, 62/66 tests)
- `.planning/phases/04-backend-fastapi-add-on/04-VERIFICATION.md` exists

The user's memory was right. My ROADMAP-checkbox read was wrong. The checkboxes had simply never been flipped post-completion.

> [!quote] Evidence
> `.planning/STATE.md` "Phase Plan" section, lines 33-37.
> Existing session retro: `research/synthesis/session-2026-05-18-phase-1-and-2-buildout.md`.

## Why this happens

- **STATE.md is updated automatically** by the GSD tooling (`gsd-sdk query state.advance-plan`, `state.begin-phase`, `state.complete-phase`).
- **ROADMAP.md is updated manually** when the operator (or an agent) happens to remember.
- For multi-phase projects, the manual flip rarely happens — there's no automated step that requires it. The checkboxes drift behind reality.

## What to do about it

> [!tip] Apply
> **Before claiming a phase is "not done" or "skipped," cross-check at least two of:**
> 1. `.planning/STATE.md` "Phase Plan" section — definitive list with ✅ markers
> 2. `.planning/phases/{N}-*/` directory contents — presence of `*-SUMMARY.md` files and `{N}-VERIFICATION.md`
> 3. Git log for `feat({N}-…)` and `docs(phase-{N}):` commits
>
> **If you only check ROADMAP.md and conclude "this phase wasn't done," you will be wrong.**

## What I saved to project memory

To prevent recurrence, two memories landed in `~/.claude/projects/-Users-moiz-Documents-code-verify-kit/memory/`:

- **`state-md-is-source-of-truth.md`** — the rule itself
- **`verify-kit-project.md`** (updated) — explicit note: "ROADMAP.md still shows `[ ]` for phases 1/2/3 because their checkboxes were never flipped post-completion; do not read ROADMAP checkboxes as authoritative"

## Cost of getting it wrong

About 4 messages of back-and-forth before the user pushed back. Wasted maybe 5 minutes of session time + introduced confusion about what to plan next.

The cost is low this time. The cost compounds: if I had proceeded to "plan Phase 1 from scratch" believing it wasn't done, I would have wasted significant time replanning work that was already shipped.

## Adjacent gotcha

Even within `STATE.md`, there can be staleness — the file is "last updated" timestamped. For example, after Phase 5 completed today (2026-05-22), `STATE.md` still shows `last_updated: "2026-05-21T22:50:24.484Z"` because no `gsd-sdk query state.complete-phase` ran for Phase 5 yet. The remediation: when you can't tell from `STATE.md` whether the very latest phase is done, also check the phase directory for `{N}-SUMMARY.md` files and a fully-populated `{N}-UAT.md` / `{N}-SECURITY.md` / `{N}-REVIEW.md` set.

## Related patterns

- [[session-2026-05-22-phase-5-llm-and-verification]] §❌ Mistakes #1
- *memory: `state-md-is-source-of-truth`*
- *memory: `verify-kit-project`*
