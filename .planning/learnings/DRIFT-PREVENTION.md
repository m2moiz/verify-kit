# Drift Prevention — Plan-vs-Codebase Synthesis

> **Audience:** the operator of this project deciding what to add to the GSD workflow before Phase 5.
> **Inputs:** [[research/agent-reports/wave-6-drift-prevention-strategies.md]], [[research/agent-reports/wave-6-shared-context-mechanisms.md]], the ~12 drift bugs Phase 4 executors auto-fixed at runtime.
> **Goal:** decide which mechanism(s) to bolt onto GSD so Phase 5 doesn't repeat Phase 4's drift cost (10–15 min × 12 = ~2 hours of executor time + the verifier loop that landed 4 more schemathesis fixes).

---

## Part 1 — Why drift happens (the honest story)

The GSD workflow has three roles:

1. **Planner** writes `PLAN.md`. Cites symbols it expects to use: `@register_check`, `CheckResult(ok=False)`, `--only=backend`, `harness/registry.py.jinja2`.
2. **Reviewer** (Codex) reads only plan files and adversarially reviews them. Catches cross-plan contract drift, dead code, cwd leaks.
3. **Executor** reads plan + actual source and writes code. Hits import errors, fixes them inline.

**Drift survives review** because the reviewer never reads the source. The planner's `@register_check` looks coherent in the plan, and the reviewer can only check whether `@register_check` is *internally consistent across plans* — not whether it *exists in the harness*. Three review cycles + adversarial pass-2 missed this in Phase 4 because they were all asking the same question of the same artifact.

In information-theory terms: the channel that produces the plan is **noisy** (LLM hallucinating from training data + other plan files), and the channel that checks the plan is **using the same noisy source as the producer**. No amount of cycles inside that loop tightens the bound. You need an **out-of-band reference signal**: the actual codebase.

---

## Part 2 — Does a multi-agent cloud team help?

**Short answer: not by itself.** The mechanism that prevents drift is "an agent in the loop reads source," not "agents share state in the cloud."

**Long answer with evidence:**

- **CrewAI / AutoGen / LangGraph multi-agent** systems share state via a workspace object. But sharing the PLAN.md between agents doesn't help if none of them open the source. Phase 4's GSD workflow already shares the plan across planner + reviewer + executor — sharing isn't the limiting factor.
- **MetaGPT** is the closest analog to GSD: structured SOPs, typed artifacts passed between roles. The MetaGPT paper reports exactly verify-kit's failure mode — planner hallucinations propagate downstream because the SOP doesn't force a source-reading step.
- **What actually prevents drift in cloud multi-agent**: the system needs a designated "explore" or "read-source" role that runs *before* planning. Anthropic Code's Plan Mode does this (read-only Glob/Grep/Read subagent runs first). Devin's Interactive Planning does this. Copilot Workspace does this iteratively. The shared-cloud aspect is incidental — what matters is whether the workflow forces a source-reading step.
- **The exception that proves the rule** is **OpenHands / CodeAct**: agents iterate `write code → run → observe failure → correct`. The runtime IS the grounding mechanism. This works in cloud OR local. The 67–73% hallucination reduction reported in FSE 2025 comes from constraining the LLM to call only symbols mined from the actual dependency graph — again, "read source" is the mechanism, not "share workspace."

**Direct answer to your question:** multi-agent cloud teams help only insofar as they make it easier to *spawn* a read-source agent before planning. The same effect is achievable locally with subagent orchestration (which GSD already has — it just doesn't currently spawn a read-source step before planning).

---

## Part 3 — Why Phase 4 executors caught it but the reviewer didn't

The executor caught all 12 drift bugs because the executor's first action is `read PLAN.md → read source → write code`. The reviewer's first action is `read PLAN.md → write review`. The asymmetry is the bug. Three cycles of "read PLAN.md → write review" can't surface a bug that requires `read source` to detect.

This generalizes: **any reviewer that doesn't read source can only validate intra-plan and inter-plan consistency, never plan-to-source consistency**.

---

## Part 4 — Three GSD supplementation proposals (ranked)

Each proposal is independently shippable. They stack additively. Pick by cost/leverage.

### Proposal A — Adversarial source-grounded reviewer pass (tonight, no infra)

**What:** Add a second reviewer pass to `/gsd:plan-review-convergence` with explicit source-reading instructions:

> "List every decorator, class, function, CLI flag, and file path referenced in the plan. For each, use Grep or Read to confirm it exists in `template/harness/`, `template/{% if has_backend %}app{% endif %}/`, or the relevant phase directory. Mark each VERIFIED, MISSING, or AMBIGUOUS. Plans with any MISSING are REVISE."

**Cost:** prompt change to one workflow file (`~/.claude/get-shit-done/workflows/plan-review-convergence.md`). ~30 lines.
**Coverage:** catches ~80% of Phase 4–style drift (decorator names, class names, CLI flags). Doesn't catch dynamic / runtime-resolved symbols.
**Drawback:** depends on the reviewer actually calling Grep/Read in practice — it's a soft enforcement. Run cost goes up ~30% because the reviewer is now reading source.
**Failure mode:** reviewer might invent a symbol *and* invent a confirmation. Mitigated by requiring the reviewer to quote a file:line for each VERIFIED claim.

### Proposal B — API Surface document, regenerated per phase (one weekend)

**What:** Add a tool `.planning/scripts/extract-api-surface.py` that walks the project's Python source with `ast`, extracts every public function signature, class, decorator, and Typer command, and writes `.planning/API-SURFACE.md`. Run it as a pre-step in `/gsd:plan-phase` and `/gsd:plan-review-convergence`. Inject the file's contents into the planner and reviewer prompts as required reading.

The file looks like:

```
## Decorators (harness/registry.py)
@register(check_id: str, *, name: str | None = None) -> Callable

## Classes (harness/models.py)
class CheckResult(BaseModel):
    check_id: str
    status: Literal["pass", "fail", "skip", "error"]
    duration_ms: float
    envelope: ErrorEnvelope | None = None

## CLI commands (harness/cli.py)
verify-kit verify [--check NAME] [--skip CSV] [--format {json,junit,sarif}]
verify-kit trace [--last] [--id ID]
verify-kit mcp serve [--http :PORT] [--token TOKEN]
```

**Cost:** ~80 lines of Python (`ast` + `inspect.signature`). One-shot integration into the two workflows. ~3 hours total.
**Coverage:** catches 100% of static symbol references. Misses dynamically-registered routes/checks (e.g., `add_api_route` calls at runtime, plugin loaders).
**Drawback:** stale if not regenerated. Fix by running `extract-api-surface.py` as a pre-commit hook on harness/ changes, or as a GSD pre-step.
**Failure mode:** the file becomes large for big projects. Trim by sectioning per-package and only loading sections relevant to the current phase.

### Proposal C — Hard plan-validation gate (a focused day)

**What:** Add `.planning/scripts/check-plan-symbols.sh` that:
1. Greps every `@<word>`, `<Word>.<word>`, `--<word>`, and `<word>.py` reference in the phase's `*-PLAN.md` files.
2. Cross-checks each against the AST-extracted symbol table from Proposal B.
3. Exits 1 with a per-symbol report if any are missing.

Wire into `/gsd:plan-phase` as a hard gate before the phase moves to execution. The plan cannot proceed until every cited symbol exists.

**Cost:** ~120 lines of Python + integration. One day if you stop and write proper tests for it.
**Coverage:** catches 100% of static symbol drift, hard reject. **This is the only mechanism in the catalog that gives deterministic plan-time rejection** without requiring a typed language.
**Drawback:** false positives on quoted code in plan prose ("the old shape `register_check` is BANNED" trips the gate). Fix with a `<code>` fenced-only mode or YAML frontmatter `api_references:` field.
**Failure mode:** dynamic symbols invisible to AST. Same as Proposal B.

### What I'd ship in what order

| Step | Effort | When | Returns |
|------|--------|------|---------|
| Proposal A (adversarial reviewer pass) | 1 hour | Before Phase 5 plan-review-convergence | Catches ~80% of drift at review time. Cheap insurance. |
| Proposal B (API surface doc) | 3 hours | Before Phase 5 plan-phase | Catches 100% of static symbol drift if the planner reads it. Persists between phases. |
| Proposal C (hard plan gate) | 1 day | After Phase 5 if A+B aren't enough | Deterministic rejection. Plan can't ship with hallucinated symbols. |

Skip the multi-agent cloud rabbit hole unless you're scaling to teams. The mechanism that helps is "read source before planning," and that's a local subagent dispatch, not a cloud architecture.

---

## Part 5 — Other mechanisms I considered and rejected (for now)

- **Tree-sitter MCP tool** for the planner. Strongest plan-time grounding but requires the planner to voluntarily call it. Workflow-design risk. Defer until Proposal C proves insufficient.
- **TypeSpec / OpenAPI spec-first**. Strong for typed API boundaries but verify-kit's drift is mostly decorator/class/flag names — not REST endpoints. Wrong tool.
- **Property-based testing as spec**. Catches behavioral drift but requires implementation first. Doesn't help at plan time.
- **CodeAct / OpenHands-style "run code, observe errors"**. Already what the executor does. Moving it earlier (run the plan as code at plan time) is structurally cool but probably premature for a solo-dev portfolio scope.
- **Embedding-based codebase search** (Cursor-style). The Cline maintainers' verdict — embeddings retrieve fragments that mention the right keywords but miss actual implementation logic — applies. AST/tree-sitter wins for symbol lookup.

---

## Part 6 — Open problems that survive all three proposals

1. **Dynamic symbols** — Flask routes, plugin registries, metaclass methods, `setattr` patterns. No static tool catches these. Solution: maintain a hand-curated `DYNAMIC-SYMBOLS.md` per phase if needed.
2. **Semantic drift** — same name, different signature across versions. Caught only if the API-Surface doc includes signatures (it does in Proposal B).
3. **Plan prose vs structured fields** — natural language prose can mention a symbol in a prohibition ("the BANNED `@register_check`"). Regex catches it as a reference. Mitigate with `<code>` fences or a structured `api_references:` frontmatter field.
4. **Long-session context drop** — correct symbol names injected early get evicted from the context window in long sessions. No framework has a principled refresh mechanism. Mitigate by re-injecting the surface doc at every plan/review boundary.

---

## Part 7 — How this connects to existing REVIEW-CHECKLIST patterns

Phase 4 drift mapped onto checklist §4 (plan API-surface drift) and §6 (meta-comments in templates). These additions detect drift **retroactively** via grep. The proposals above **prevent** drift at plan time. They complement, not replace:

- **§4-§9 grep checks**: backstop. Run after every plan-review-convergence cycle.
- **Proposal A (adversarial reviewer)**: catch drift at review time.
- **Proposal B (API surface doc)**: ground the planner at plan time.
- **Proposal C (hard plan gate)**: deterministic rejection at plan time.

Layered defense. Each layer catches what the previous one missed.

---

## Appendix — Concrete next actions if you want to run Proposal A tonight

1. Open `~/.claude/get-shit-done/workflows/plan-review-convergence.md`.
2. Find the reviewer prompt block (search for "you are the reviewer" or similar).
3. Append:
   ```
   ## Source-grounding pass (REQUIRED — do not skip)

   List every symbol referenced in the plan in the categories:
   - Decorators (e.g., `@register_check`)
   - Classes (e.g., `CheckResult`)
   - Function signatures (e.g., `harness.ralph.run`)
   - CLI flags (e.g., `--only=backend`)
   - File paths (e.g., `harness/registry.py.jinja2`)

   For each, use Grep or Read to confirm it exists in the project source.
   Quote a file:line for each VERIFIED claim.
   Mark missing or wrong-named symbols MISSING.
   Any MISSING blocks the plan with severity HIGH.
   ```
4. Run `/gsd:plan-review-convergence 5 --codex --max-cycles 3` and watch what the reviewer turns up that the planner missed. Iterate the prompt based on the false-positive rate.

That's the cheapest experiment that meaningfully reduces drift for Phase 5.
