---
title: Session 2026-05-18 — Phase 1 build + Phase 2 plan
aliases: [Session Retro 2026-05-18, Phase 1 Buildout, Phase 2 Planning Retro]
tags: [verify-kit, retro, learnings, mistakes, session-log, synthesis]
created: 2026-05-18
last_updated: 2026-05-18
status: completed-session
phases_touched: [01-template-skeleton-toolchain, 02-universal-harness-core]
---

# 🪞 Session Retrospective — 2026-05-18

> [!abstract] What this is
> Honest record of the work done across one long session: Phase 1 plans reviewed → executed → verified → secured, and Phase 2 planned. Includes mistakes, false confidence moments, surprises, and process gaps so the next session learns from this one. Not a cheerleading doc.

> [!info] About *memory:* references
> Italic refs like *memory: `run_all_gsd_ceremonies`* point to files in `~/.claude/projects/-Users-moiz-Documents-code-verify-kit/memory/` — Claude Code's per-project memory store, outside this vault. They persist across sessions and inform every conversation about this project.

## ⚡ Quick navigation

| Want to know… | Jump to |
|---|---|
| Headline outcome | [[#📊 What shipped]] |
| **Mistakes I made** | [[#❌ Mistakes — what I got wrong]] |
| **Surprises that bit us** | [[#😲 Surprises — what the docs didn't say]] |
| What worked well | [[#✅ Worked well — keep doing]] |
| Process gaps to fix | [[#🛠 Process insights]] |
| Open items for Phase 2+ | [[#📌 Carry-forward for next session]] |

---

## 📊 What shipped

| Phase | Status | Artifacts |
|---|---|---|
| Phase 1 | ✅ Built, verified, secured | 7 source files + 3 test files; ==17/17 threats closed==; ==UAT 10/10 pass== |
| Phase 2 | ✅ Planned | 02-CONTEXT.md (==15 decisions==), 02-RESEARCH.md (==1047 lines==), ==7 PLAN.md files across 5 waves== |
| HARN-06 | Deferred to Phase 4 | Moved in ROADMAP.md + REQUIREMENTS.md |

**Phase 1 commit count on master:** ==10 substantive commits + 5 merge commits = 15 total==.

**Key files now on master:** `copier.yml`, `pyproject.toml`, `uv.lock`, `template/` (12 files), `template_extensions/` (2 files), `tests/` (4 files), `src/verify_kit/` (placeholder).

---

## ❌ Mistakes — what I got wrong

> [!warning] Read this first
> These are the actual errors I made or let through. None were caught by Claude alone. Three were caught by Codex's cross-AI review, two by empirical spike-testing, two by UAT, two by a real end-user `copier copy` invocation. The pattern: paper review and unit tests miss what end-to-end usage finds.

### M-1: Trusted that `_skip_if` was a real Copier key ^M-1

**What happened:** Plan 01-03 originally specified `_skip_if` in `copier.yml` to conditionally render `template/.devcontainer/devcontainer.json.jinja2`. I propagated this into Plan 01-04 for the per-agent files (CLAUDE.md, .cursor/, .windsurf/, .github/copilot-instructions.md). All four plans depended on a key that **does not exist in Copier**.

**How it was caught:** Codex flagged it in cycle 3 of `/gsd:plan-review-convergence 1 --codex` with the literal claim "`_skip_if` is not a documented Copier key." I verified empirically — created a scratch template, rendered it with `_skip_if` present, observed Copier silently ignored it and rendered the gated file anyway. The Copier source (`copier/_template.py:118-122`) confirms only `_exclude`, `_jinja_extensions`, `_secret_questions`, and `_skip_if_exists` are recognized.

**Root cause:** I generated planning text confidently without sanity-checking the API surface against actual Copier source or docs. A real "go look at the code" step was missing.

**Fix:** Switched all conditional paths to **Form B (Jinja-in-directory-name)**: `template/{% if has_devcontainer %}.devcontainer{% endif %}/devcontainer.json.jinja2`. Verified empirically before propagating.

**Lesson:** When the plan invokes a config key, decorator, or framework feature — verify the feature exists in the installed version. "It's documented" isn't enough; documentation lags reality. See [[agent-reports/wave-2-scaffolding-tools]].

---

### M-2: Trusted that `_templates_suffix` defaulted to `.jinja2` ^M-2

**What happened:** All Phase 1 plans used `.jinja2` suffixes (`template/copier.yml.jinja2`, `template/justfile.jinja2`, etc.). The implicit assumption was that Copier strips this suffix at render time. **It doesn't, by default.** Copier 9.15.x's default `_templates_suffix` is `.jinja`. Without overriding it, every `.jinja2` file is copied to the consumer's project *with the suffix retained and the Jinja syntax unrendered*.

**How it was caught:** Codex flagged in cycle 3. Verified at `/tmp/vk-spike/t1-template` — without the directive, files came out as `hello-jinja2.txt.jinja2` containing literal `{{ project_name }}`. With `_templates_suffix: .jinja2` added to `copier.yml`, files rendered correctly.

**Root cause:** Same as M-1 — assumed an obvious-seeming default without checking. The `.jinja2` suffix convention is older and many tutorials use it; modern Copier moved to `.jinja`.

**Fix:** Added `_templates_suffix: .jinja2` to `copier.yml`. Pinned in CONTEXT.md.

**Lesson:** A "convention" you read in a blog post is not a default in the current version. Empirically verify defaults you depend on.

---

### M-3: Assumed Just intercepts `--flag` tokens after the recipe name ^M-3

**What happened:** Codex (cycle 3) flagged `just verify --fix` as broken — claiming Just would intercept `--fix` and try to parse it as a Just-owned flag, requiring `just verify -- --fix` to pass it through. I almost rewrote the plan around this.

**How it was caught:** I tested it empirically at `/tmp/vk-spike/t4-just` before applying any fix. `just verify --fix` correctly captured `--fix` into the `*FLAGS` variadic. Even `just verify --list` (where `--list` IS a Just-owned flag) passed through because Just's parser prioritizes recipe arguments after the recipe name.

**Root cause:** This was Codex's mistake, not mine — but I would have propagated it had I not run the spike. Lesson is for me.

**Fix:** Documented the rejection in `01-02-PLAN.md`'s revision notes so future readers don't reintroduce the workaround.

**Lesson:** Cross-AI review surfaces real bugs *and* confident hallucinations. Always spike-test before replanning around a reviewer's claim — paper-only review is unreliable.

---

### M-4: Shipped a smoke test that depended on the developer's local clutter ^M-4

**What happened:** Phase 1 executor wrote `tests/test_copier_render.py` with `shutil.copytree(template_root, sandbox, ignore=shutil.ignore_patterns(".planning", "research", ".git", ".venv", "__pycache__", "*.pyc"))`. The test passed in the executor agent's worktree because that worktree was a fresh git checkout (no untracked files). On master, the developer's working tree had untracked `CLAUDE.md`, `SESSION-HANDOFF.md`, and `config.yaml` — which `shutil.copytree` happily copied into the test sandbox. Then `git add -A && git commit` inside the sandbox tripped the global pre-commit hook that denylists `CLAUDE.md`. Test failed only on the developer's machine.

**How it was caught:** Running `uv run pytest tests/test_copier_render.py` on master immediately after merging Wave 1's worktree.

**Root cause:** Two compounding issues:
1. The executor agent's worktree was a "clean room" that hid the failure mode
2. `shutil.copytree` + `ignore_patterns` is fragile — every untracked file the developer adds becomes a potential test failure

**Fix (commit `b6ac988`):** Replaced `shutil.copytree(..., ignore=...)` with `git ls-files`-based copy. The test sandbox now contains *only files tracked by git*, regardless of local clutter. Also added `core.hooksPath=/dev/null` to all three sandbox `git config` calls so the developer's global pre-commit hook never fires inside synthetic test repos.

**Lesson:** Tests that copy the repo into a sandbox must be deterministic across "fresh executor worktree" and "developer's working checkout with random files." `git ls-files` is the deterministic option. Also: synthetic git sandboxes should explicitly opt out of host hooks.

---

### M-5: `_jinja_extensions` worked in tests but broke for end users ^M-5

**What happened:** Plan 01-03 wired `_jinja_extensions: [template_extensions.env_detect.EnvDetectExtension]` directly in `copier.yml`. All 17 pytest tests passed because `uv run pytest` uses verify-kit's own project venv, which has `template_extensions` installed via `uv sync`. But when I actually ran `copier copy` as an end user would — using the global `copier` binary installed via `uv tool install copier` — it failed:

```
Copier could not load some Jinja extensions:
No module named 'template_extensions'
```

The global `copier` CLI is in its own isolated venv (per `uv tool` semantics). It doesn't see project-local packages.

**How it was caught:** End-to-end goal-acceptance step: `time copier copy --defaults --trust ... /tmp/scratch-p1`. Would have shipped a v0.1.alpha that didn't actually work for the documented install method.

**Root cause:** I confused "the tests pass" with "the user-facing flow works." The tests exercise the in-tree code; the user runs the tool from a different venv entirely.

**Fix (commit `684726e`):** Switched to the `copier-templates-extensions` loader pattern documented by Copier:
```yaml
_jinja_extensions:
  - copier_templates_extensions.TemplateExtensionLoader
  - template_extensions/env_detect.py:EnvDetectExtension
```
Users now install with `uv tool install copier --with copier-templates-extensions`. The loader auto-handles `sys.path` for template-adjacent extension modules.

**Lesson:** "Passes unit tests" ≠ "works for end users in the supported install path." Every Phase needs a real end-user smoke test that uses the *actual install command* the README documents, not just `uv run pytest`. This is literally what verify-kit exists to enforce.

---

### M-6: Generated project imported PyYAML without declaring it as a runtime dep ^M-6

**What happened:** Phase 1's harness includes a check `copier-answers-valid` that does `import yaml; yaml.safe_load(...)`. The generated project's `template/pyproject.toml.jinja2` listed `pydantic`, `typer`, `rich` as runtime deps but **not pyyaml**. Inside the verify-kit dev venv, pyyaml was present (transitively via Copier), so the unit tests passed. In a freshly-rendered scratch project, the harness crashed with `ModuleNotFoundError: No module named 'yaml'`.

**How it was caught:** UAT Test 4 (`just verify` inside `/tmp/scratch-p1`):
```
✗ [copier-answers-valid]  .copier-answers.yml is not valid YAML: No module named 'yaml'
```

**Root cause:** Same family as M-5 — the dev environment hides missing transitive deps. The unit test for `copier-answers-valid` ran in the dev venv, so it saw yaml. The check author didn't realize yaml wasn't a runtime dep of the *generated* project.

**Fix (commit `1231b77`):** Added `pyyaml>=6` to `template/pyproject.toml.jinja2`'s `dependencies` array.

**Lesson:** Every `import` in the harness needs a corresponding declared dep in the *generated project's* pyproject.toml, not just the verify-kit dev venv. UAT in a fresh `copier copy` output is the only reliable way to find these.

---

### M-7: Committed a `.planning/REVIEWS.md` even though `.planning/` is gitignored ^M-7

**What happened:** During the `/gsd:review` ceremony, the review skill committed `01-REVIEWS.md` to the `review/phase-1-codex` branch. But the project's convention (commit `7b33461`) is `.planning/` is gitignored — all planning artifacts are local-only. The review skill's tooling didn't honor this.

**How it was caught:** When I tried to switch branches to start Phase 1 execution and got "would overwrite local changes."

**Fix:** Untracked the file with `git rm --cached`, recommitted on review branch, switched back to master. From that point on I've passed an explicit "do NOT git add `.planning/`" constraint to every executor agent prompt.

**Lesson:** GSD skills don't all respect project-level gitignore conventions. The orchestrator (me) has to enforce the constraint at every subagent boundary. Saved as part of the *memory: `run_all_gsd_ceremonies`* memory.

---

### M-8: Underused Codex for the entire session ^M-8

**What happened:** The original project intent (saved in *memory: `claude_codex_collab`*) was: Claude plans + architecture-sensitive work, Codex executes boilerplate. In practice this session: **Codex was only invoked during plan-review-convergence**, not during execute-phase. All 4 Phase 1 executor agents and 7 Phase 2 plans were/are slated for Claude Code agents.

**How it was caught:** User asked directly: "where exactly are you leveraging codex?"

**Root cause:** GSD's `cross_ai_execution` is opt-in and the project's `workflow.cross_ai_command` was never configured. The `gsd-executor` agent defaults to Claude Code worktree agents. I didn't pause to wire Codex even though it was the documented intent and would have saved significant Claude usage.

**Fix (in progress):** Wiring `workflow.cross_ai_command "codex"` and `workflow.cross_ai_execution true` next, then tagging Phase 2's boilerplate-heavy plans (02-04 checks migration, 02-05 emitters, 02-07 test scaffold) with `cross_ai: true` while keeping architecture-sensitive plans (02-01 registry design, 02-02 OTel lazy import, 02-03 cache schema, 02-06 CLI rewrite) on Claude.

**Lesson:** Saved project memories about *who does what* don't auto-apply. The orchestrator has to actively design each phase's split. Otherwise Claude does everything by default — burning credits that should have been Codex's. See *memory: `run_all_gsd_ceremonies`*.

---

## 😲 Surprises — what the docs didn't say

> [!info] The "I didn't expect that" log
> These weren't mistakes so much as encounters with reality that the docs didn't fully cover.

### S-1: Copier's `when: false` prompts don't appear in `.copier-answers.yml` ^S-1

**Where:** Phase 1 plan 01-01's slug-derivation test (`test_project_slug_derives_to_pep621_valid_name`).

**The surprise:** I planned to render with `project_name="My Cool App"` then read `.copier-answers.yml` and assert `answers["project_slug"] == "my-cool-app"`. The test failed because `when: false` (computed/hidden) prompts are *not written to the answers file by design* — Copier treats them as internal state.

**Resolution:** Test was rewritten to verify the derivation directly via Python regex mirroring the Jinja expression, plus checking that the slug propagates into the rendered `pyproject.toml`'s `[project] name` field. Documented in Phase 1 SUMMARY as an auto-fix.

**Lesson:** When using `when: false` for derived values, the answers file isn't your verification surface. Look at the *consumed* artifacts (generated files) instead.

---

### S-2: Form (a) vs Form (b) for `.jinja2`-in-filename conditionals ^S-2

**Where:** Phase 1 plan 01-04 for `template/{% if has_claude_code %}CLAUDE.md{% endif %}.jinja2`.

**The surprise:** I assumed both `{% if x %}CLAUDE.md{% endif %}.jinja2` and `{% if x %}CLAUDE.md.jinja2{% endif %}` would work equivalently. They don't:

- Form (a) — suffix OUTSIDE the conditional: ✅ Copier strips `.jinja2` when conditional renders to `CLAUDE.md`; emits nothing when conditional is empty
- Form (b) — suffix INSIDE the conditional: ❌ Copier looks at the *literal filename* (post-Jinja string is just text). When the conditional yields `CLAUDE.md.jinja2`, Copier doesn't recognize the suffix because suffix-stripping happens before Jinja path evaluation

Verified empirically at `/tmp/vk-spike/t-claude-edge/`. Form (b) ships a file named `CLAUDE.md.jinja2` with unrendered `{{ project_name }}` to the consumer's project.

**Lesson:** Copier's file-suffix recognition is purely literal-string. Anywhere Jinja appears in the path, the static `.jinja2` suffix must remain OUTSIDE the templated region.

---

### S-3: `uv tool install <tool>` isolates the tool's venv ^S-3

**Where:** End-to-end smoke test of `copier copy`.

**The surprise:** I knew `uv tool install` installs a CLI in an isolated venv, but I didn't realize how aggressive the isolation was — the tool's venv doesn't see any *project*-installed packages. So `copier`'s `_jinja_extensions` lookup can't find `template_extensions` even when verify-kit's own venv has it.

**Resolution:** Documented `uv tool install copier --with copier-templates-extensions` as the required install command. Connected via [[agent-reports/wave-2-scaffolding-tools]].

**Lesson:** Tool-CLI isolation matters for any framework that loads project-local Python extensions. Either ship the extension as a PyPI package, or use the framework's loader pattern that handles `sys.path` for you.

---

### S-4: SQLite `STRICT` table support landed in Python 3.13's stdlib sqlite3 ^S-4

**Where:** Phase 2 research (02-RESEARCH.md §5).

**The surprise:** SQLite STRICT tables (real type enforcement, not the historical "everything is TEXT" SQLite quirk) are supported in Python 3.13's stdlib sqlite3 without any flag-flipping. I'd assumed we'd need to either (a) use an ORM that wraps STRICT semantics, or (b) drop STRICT and live with affinity quirks. Neither — just write the DDL and it works.

**Lesson:** Python 3.13's stdlib has caught up with modern SQLite. Worth re-checking other "we'll need a library for this" assumptions in Phases 4–5.

---

### S-5: Codex's confident hallucinations *and* genuine catches in the same review ^S-5

**Where:** Cycle 3 of `/gsd:plan-review-convergence 1 --codex`.

**The surprise:** Codex returned 4 HIGH-severity concerns. After empirical spike testing, **3 were real and the 4th was confident hallucination**:
- ✅ `_templates_suffix` default — REAL
- ✅ `_skip_if` not a Copier key — REAL
- ✅ `project_name` as PEP 621 name — REAL (uv build rejects)
- ❌ Just intercepts `--flag` tokens — FALSE (just 1.51 passes through fine)

A 75% true-positive rate from cross-AI review is good but not perfect. The hallucination was confident enough that I might have replanned around it without the spike.

**Lesson:** Cross-AI review is high-leverage but not authoritative. Always spike-verify a HIGH concern before applying a fix to plans — see [[#^M-3]].

---

## ✅ Worked well — keep doing

### W-1: Plan-review-convergence loop saved real bugs ^W-1

**What:** `/gsd:plan-review-convergence 1 --codex --max-cycles 3` ran three review cycles, with Codex finding 6 → 4 → 4 unresolved HIGH concerns across iterations. Even after the loop stalled at 4, the spike-testing on those 4 produced fixes that prevented Phase 1 from shipping broken.

**Why it worked:** External AI review catches design errors that single-author confidence misses. Plan-time fixes are an order of magnitude cheaper than execute-time fixes.

**Keep doing:** Run the convergence loop on every phase. Default, never an upsell. See *memory: `run_all_gsd_ceremonies`*.

---

### W-2: Empirical spikes in `/tmp/vk-spike` resolved every ambiguity ^W-2

**What:** When Codex flagged 4 HIGH concerns, instead of paper-debating each one, I created minimal scratch templates and tested both polarities (`/tmp/vk-spike/t1-template`, `/tmp/vk-spike/t2-template`, etc.). Every spike resolved its question in under 5 minutes.

**Why it worked:** Tool behavior is the ground truth, not documentation. A 3-line `copier.yml` in a tmpdir gave better answers than 10 minutes of reading docs.

**Keep doing:** When in doubt between two plausible technical interpretations, write the minimal failing test in a tmpdir before debating.

---

### W-3: Worktree-isolated parallel executors ^W-3

**What:** Phase 1's Wave 2 ran `01-02` and `01-03` in parallel worktrees. They modified disjoint file sets so the merge was clean — both branches three-way merged into master with zero conflicts.

**Why it worked:** Strict files_modified discipline in plan frontmatter + git's three-way merge for non-overlapping edits.

**Keep doing:** Maintain disjoint files_modified within waves. Plan-checker should auto-warn on overlap. Phase 2's plan has been audited for this.

---

### W-4: discuss-phase prevented unilateral architectural drift ^W-4

**What:** Phase 2's discuss-phase locked 15 specific decisions across 4 areas (error envelope, cache, OTel/registry, --quick/did-you-mean/config) BEFORE the planner ran. The planner then had a sharp constraint surface and produced concrete tasks (not vague "design the registry" placeholders).

**Why it worked:** Multi-option AskUserQuestion with preview code snippets gave the user (you) high-bandwidth design input. The planner consumed a CONTEXT.md with worked code examples and ran with it.

**Keep doing:** Always run discuss-phase before plan-phase for any phase with non-trivial architectural decisions. Don't accept "no CONTEXT.md → use defaults" as an outcome.

---

### W-5: Phase 1 SECURITY.md verified mitigations against actual code ^W-5

**What:** `/gsd:secure-phase 1` enumerated 17 threats from the 4 plans' STRIDE registers and verified each one against the implemented code (grepped justfile for `set shell := ["bash", "-uc"]`, read env_detect.py for `Path.exists()` only, etc.). All 17 closed.

**Why it worked:** STRIDE register at plan time + code-level verification at secure time = no "we'll deal with security later" gap.

**Keep doing:** Threat model in every plan; verify it after execution; this works for small phases (Phase 1 = 17 threats) just as well as large ones.

---

## 🛠 Process insights

### P-1: Default to running every GSD ceremony ^P-1

> [!quote] Direct user feedback (mid-session)
> "Always run the plan review conversion. Like all of the steps or all of the ceremonies and all of the tools that are in the GST skill. We don't skip any of them, okay? Unless you strongly feel that there's no added value."

Saved to *memory: `run_all_gsd_ceremonies`*: never skip plan-review-convergence, secure-phase, verify-work, validate-phase, ui-review, code-review just because a phase looks small. The cost of the ceremony is small; the cost of skipping it (replanning mid-execution, security gaps) is large.

### P-2: Dumb down explanations before asking for decisions ^P-2

> [!quote] Direct user feedback (during Phase 2 discuss)
> "You need to dumb it down and make it easy to understand. As I'm not going to be familiar with all of the design decisions, all of the tech stack and everything. You're helping me as an assistant, so you need to explain it to me in an easy to understand way. Ideally in an interactive way. With examples so that I can have a mental model of what you're trying to ask me and do."

Saved to *memory: `communication_style`*: user is the visionary, not a domain expert in every tech we touch. Wall-of-jargon questions produce bad decisions. Use analogies, worked examples, concrete syntax. The AskUserQuestion `description` field should be plain-language; previews can show code.

### P-3: Track Codex utilization actively ^P-3

> [!quote] Direct user feedback (after Phase 2 plan)
> "Wire up the cross AI so that codex is used a lot more. Because otherwise I'm just heating up my claude code credits and I'm not utilizing codex and I run out of claude code usage and then I just have to wait. So I need to maximize the usage that I have."

Saved Claude+Codex collab intent doesn't auto-apply. Every phase needs a deliberate split decision: which plans are architecture-sensitive (Claude), which are boilerplate (Codex)? See M-8.

### P-4: `.planning/` gitignore discipline ^P-4

The `.planning/` directory is gitignored per project convention but GSD skills don't all respect this. Every executor/agent prompt needs an explicit "do NOT git add `.planning/`" constraint. Already part of standard prompt template after M-7.

### P-5: End-to-end goal acceptance is mandatory ^P-5

`uv run pytest` passing ≠ feature working. Every phase needs a final step that runs the *user-facing command* (`copier copy ...`, `just verify`, etc.) against the supported install path. Phase 1 had two real bugs (M-5, M-6) that only surfaced this way.

---

## 📌 Carry-forward for next session

> [!todo] Open items
> Things flagged during this session that future phases must address.

### From Phase 1 (deferred to Phase 6)

- [ ] **SHA-pin GitHub Actions** — currently tag-pinned (`@v2`, `@v4`); switch to SHA + dependabot policy at release prep
- [ ] **Adversarial `project_name` E2E test** — verify path-traversal inputs (`../etc/passwd`) don't escape the template render
- [ ] **SBOM generation** — uv has tooling; wire into release flow
- [ ] **gitleaks pre-commit budget audit** — confirm ≤3s budget on large repos

### From Phase 2 planning (research-flagged)

- [ ] **HARN-04 scope** — `harness/trace_id.py` is contextvars-only in Phase 2; ASGI middleware wrapper lives in Phase 4 alongside FastAPI (so the universal layer doesn't pull starlette)
- [ ] **OTel `_provider.shutdown()`** — short-lived CLIs need explicit flush via `atexit.register(provider.shutdown)` before `sys.exit()`
- [ ] **`just trace --last` implementation** — Jaeger HTTP query API at `/api/traces?service=verify-kit&limit=1`; render via Rich Tree
- [ ] **`VerifyReport.summary` field** — JUnit emitter needs total `duration_ms`; add `summary: ReportSummary` to the model

### Architectural commitments locked in Phase 2 CONTEXT.md (15 items)
See `.planning/phases/02-universal-harness-core/02-CONTEXT.md`. Highlights for Phase 3+:
- **Error code style** is hierarchical dotted (`category.subcategory.thing`) — Phase 3's MCP tool errors must use this pattern
- **Exit codes 20-29 reserved for Phase 3** — MCP server errors get this block
- **Decorator-based check registry** — Phase 3+ phases add checks by importing `harness.registry.register`, not via entry points
- **Config home is `[tool.verify-kit]` in pyproject.toml** — Phase 3+ adds keys here, no separate config files

### Process improvements to apply going forward

- [ ] Run `/gsd:plan-review-convergence` on every phase after `/gsd:plan-phase` (no skip)
- [ ] Wire Codex via `workflow.cross_ai_execution` + per-plan `cross_ai: true` for boilerplate plans
- [ ] Run a real `copier copy` smoke test as the final step of every UAT (not just `uv run pytest`)
- [ ] Update memory with new mistakes/preferences as they surface

---

## 🔗 Related notes

- [[00-architecture-overview]] — full project picture; this session executed Phase 1 of that
- [[00-decision-log]] — chronological decision history (no new D-numbered entries from this session; all decisions logged at phase CONTEXT level)
- [[00-stack-decisions]] — tool verdicts; verified each in practice during Phase 1 execution
- [[agent-reports/wave-2-scaffolding-tools]] — Copier deep-dive; this session validated several claims and corrected the `_templates_suffix` default
- [[agent-reports/wave-2-polyglot-orchestration]] — mise + just verdicts; both worked exactly as researched
- *memory: `run_all_gsd_ceremonies`* (memory) — preference: never skip GSD steps
- *memory: `communication_style`* (memory) — preference: plain-language explanations with examples
- *memory: `claude_codex_collab`* (memory) — original split intent; underused in this session, fixing now

---

## ⚡ TL;DR for next session

1. Wire up Codex execution before Phase 2 execute (see [[#^M-8]])
2. Always run plan-review-convergence (see [[#^P-1]])
3. Always run real `copier copy` UAT, not just pytest (see [[#^P-5]])
4. Dumb-down explanations when asking for decisions (see [[#^P-2]])
5. `.planning/` is gitignored — never `git add` it (see [[#^M-7]])
6. Spike-test ambiguous tech claims in `/tmp/` before replanning (see [[#^W-2]])

End of session 2026-05-18.
