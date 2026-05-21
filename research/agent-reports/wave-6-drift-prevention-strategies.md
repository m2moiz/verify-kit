# Wave 6 Research: How Production Multi-Agent Coding Systems Prevent Plan-vs-Codebase Drift

**Research date:** 2026-05-21  
**Triggered by:** Phase 4 execution hit ~12 plan-vs-codebase drift bugs (wrong decorator names, wrong field names, wrong file paths, invented protocol shapes) that evaded 3 Codex review cycles because the reviewer never reads source.  
**Scope:** Survey of production systems, academic literature, and multi-agent frameworks.

---

## Section 1: Per-System Grounding Mechanism Inventory

| System | How they read the repo | What triggers re-reading | What gets passed to the LLM |
|---|---|---|---|
| **Aider** | Tree-sitter AST parse across all files; extract function sigs, class names, call sites. PageRank on file dependency graph to rank by relevance. Disk-cached per mtime. | Any file mtime change invalidates cache entry. Files currently open in chat session get personalization boost (100/N weight). | Hierarchical map: filename → function sigs + class defs + high-reference identifiers. Defaults 1k tokens, configurable via `--map-tokens`. |
| **Cursor Agent** | Semantic chunking (AST-based, ~500 token blocks). Embeddings via custom model trained on agent sessions. Stored in Turbopuffer. Actual code stays local. | Merkle-tree change detection every ~10 min; only modified files re-embed. | Nearest-neighbor retrieved chunks (obfuscated paths + actual code read from disk at query time). Combined with semantic search for agentic tasks. |
| **Claude Code** | Agentic tool-call loop: Explore subagent (read-only: Glob, Grep, Read, limited Bash) runs before any writes. Reads files in parallel across relevant entry points. Plan mode runs this exploration before surfacing implementation strategy. | Every task: Claude reads files autonomously before writing. No pre-indexed state — fresh exploration per task. | Raw file contents as tool-call results in context. Not compressed or summarized — the actual file text. |
| **Cline / Roo-Cline** | Filesystem traversal + AST parsing, following imports in logical order. Explicitly rejected RAG/embeddings: "vector similarity often retrieves fragments that mention the right keywords but miss actual implementation logic." | Tool calls (read_file, replace_in_file) during task execution. Cline re-reads files multiple times per session because it needs latest version after edits. | Full file contents via read_file tool calls. Deduplication attempted because same file appears multiple times as it changes. |
| **Devin (Cognition)** | "DeepWiki" generates always-updating docs + system diagrams across the codebase. Interactive Planning lets humans align on architecture before execution. No public technical detail on symbol resolution mechanism. | Unknown (proprietary). Interactive Planning phase presumably reads repo before planning. | Unknown (proprietary). Presumably code + generated documentation in context. |
| **GitHub Copilot Workspace** | Three strategies by repo size: (1) small = full repo in context, (2) medium = iterative semantic search, (3) large = adaptive search. Semantic index (`#codebase`) builds and maintains embeddings. Workspace orchestrates GPT-4o with explicit file read + plan + edit loop. | Each task: agent "runs multiple tools, reviews results, and performs follow-up searches until it has good understanding." | Relevant code snippets from semantic search + directly read files. Every intermediate artifact (spec, plan, edits) exposed for human approval. |
| **Sourcegraph Cody / Amp** | Evolved from OpenAI embeddings → now BM25 keyword search on Sourcegraph's engine (found embeddings-only insufficient). Amp Agent additionally collects symbols, references, and dependency trees. Can query up to 10 repos simultaneously. | Query-time retrieval per user request. Amp Agent operates as always-on code intelligence layer. | Top-N code snippets from BM25 ranking + local IDE context + remote repo context merged into global ranking. |
| **MetaGPT** | Standardized Operating Procedures (SOPs) as structured prompt sequences. Each agent role produces typed artifacts (PRD → tech design → code → tests). Code reviewer reads actual code. No autonomous codebase-grounding step described in the paper. | SOPs define what each agent reads from the previous stage's output. Verification agents check intermediate outputs. | Structured artifacts from upstream agents (PRD, API design, code). Not raw codebase symbols at planning time — the gap verify-kit hit. |
| **OpenHands / OpenDevin** | CodeAct: agent writes and executes Python code in a sandbox, observes stdout/stderr, and iterates. The execution environment IS the grounding — running code that imports the actual library surfaces real errors. Parallel multi-agent refactors via dependency graphs. | Each iteration of the agentic loop: agent runs code, observes failures, corrects. Reality-check comes from execution, not from static analysis. | Observation (stdout/stderr/exception) from code execution. Errors about missing symbols arrive as runtime feedback. |
| **LangGraph** | State machine where each agent reads/writes a central state object. Agents can call tools (file read, search) as graph nodes. No built-in codebase indexing — the developer wires what gets passed. Durable execution survives crashes. | State transitions: each node explicitly receives and can request re-reads. Conditional routing enables retry on failure. | Whatever the developer puts in the state object — fully explicit, no magic. |
| **CrewAI** | Task-output pipeline: each agent receives the prior agent's output as context. No built-in codebase indexing. Limited to what the developer puts in task context. | Task boundaries. No mid-task re-reading mechanism built in. | Previous agent's output (text). No structural repo grounding unless developer explicitly adds a tool. |
| **Replit Agent** | `replit.md` as a structured project memory file the agent always reads. Sub-agents get minimal context subsets scoped to their task. Dynamic prompt construction with XML structure. Filesystem used as state store (plans + task lists written to files). | Session start (reads replit.md). Sub-agent spawning (receives minimal task-specific context). | replit.md contents + task-relevant file excerpts + compressed prior memory. Not a full symbol index. |
| **Bolt.new** | No codebase symbol grounding described publicly. Designed for greenfield apps from prompts. Has file-lock mechanism to protect files from being rewritten. | Unknown. | Unknown for existing codebases. Likely full project context for small projects. |
| **v0 (Vercel)** | No cross-component awareness by design. Each generation is isolated — does not know what components you've already built, naming conventions, or state management structure. | Per-generation request only. | Prompt + immediate component context only. No repo-wide symbol grounding. |

---

## Section 2: Common Patterns — What Works Across Systems

### Pattern 1: Read Before You Write (Universal)

Every system that scores well on SWE-bench or real-world tasks uses some form of mandatory read-before-write. The specific mechanism varies:

- **Aider**: static map pre-computed from the whole repo, passed in every context
- **Claude Code**: dynamic tool-call exploration per task, Explore subagent runs first
- **Cline**: tool-call traversal following imports, re-reads on every change
- **Cursor**: continuous embedding index, retrieved at query time
- **Copilot Workspace**: iterative search until the agent decides it understands enough

The systems that do NOT do this (MetaGPT's planning phase, v0, bolt.new) produce hallucinated APIs regularly. The correlation is direct.

### Pattern 2: Two-Tier Retrieval (Precision + Recall)

Systems that advance beyond naive RAG use a two-tier approach:

1. **Recall tier** (broad): keyword/BM25 search or embedding similarity to find candidate files
2. **Precision tier** (narrow): full file read of the top candidates, AST/import-aware selection

Sourcegraph evolved away from embeddings-only toward BM25 because pure vector similarity "often retrieves fragments that mention the right keywords but miss actual implementation logic" (Cline team's words, but the observation is echoed in Sourcegraph's architecture change too). Aider combines PageRank graph ranking (recall) with actual function-signature extraction (precision).

### Pattern 3: Dependency-Graph Awareness

The research literature (FSE 2025, "Towards Mitigating API Hallucination with Hierarchical Dependency Aware") shows a 67-73% reduction in hallucinated API calls when generation is constrained by the actual dependency graph rather than keyword retrieval. The mechanism:

1. Mine local + global dependencies of the target function from the actual codebase
2. Use the mined dependency graph to constrain the generation process
3. The LLM can only call APIs that exist in discovered dependencies

This is more effective than post-hoc RAG because it applies during generation, not after.

### Pattern 4: Execution as Ground Truth (CodeAct / OpenHands)

The most robust grounding is actually running the code. OpenHands/CodeAct executes Python in a sandbox and observes real errors. When code references `@register_check` but the actual decorator is `@register`, the import fails and the agent sees the actual exception. This closes the loop entirely — no static analysis needed, no plan review needed.

**Limitation**: this only works for interpreted languages. It also requires a runnable environment (test fixtures, dependencies installed, etc.). It doesn't prevent planning-level hallucinations — it just surfaces them at execution time rather than after human review.

### Pattern 5: Spec as Living Contract (Not a Static Document)

The Augment Code / Intent architecture (spec-driven AI) treats specs as living contracts continuously validated by a Verifier agent against the actual implementation. Key properties:

- Spec includes machine-readable API contracts (OpenAPI / AsyncAPI)
- When specs change, a Coordinator identifies all dependent services that need updates
- Verifier checks each implementation against the spec — mismatches surface during development, not production

This is the multi-agent equivalent of type-checking: the spec becomes a type system that agents are not allowed to violate.

### Pattern 6: Human Checkpoint at the Plan→Code Boundary

Both Devin (Interactive Planning) and Copilot Workspace expose every step — spec, plan, edits — for human approval before execution. This is a soft but effective gate: a human can see "the plan says `@register_check`" and flag it if they know the real decorator is `@register`.

GSD's plan-review-convergence loop provides a similar gate, but with a reviewer agent that never reads source — so it can't catch API-name drift. The human checkpoint is the only current defense in GSD.

---

## Section 3: Multi-Agent Cloud vs Local — Does Shared Workspace Help?

### The Hypothesis

The user's hypothesis: shared workspace/data across agents reduces drift, because agents can read each other's outputs rather than hallucinating from prompts alone.

### Evidence: Shared Workspace Helps, But Not the Way You'd Think

**Where shared workspace reduces drift:**

1. **Execution artifacts as signals**: OpenHands/CodeAct uses a shared execution sandbox. When Agent A writes code that fails, Agent B reads the actual error, not Agent A's description of the error. The shared execution environment is the ground truth.

2. **LangGraph shared state**: All agents read and write a central state object. If Agent A reads file X and puts the actual function signature in state, Agent B reads the actual signature — not a hallucination of it. This works *if* Agent A was explicitly designed to extract and store actual symbols.

3. **Devin's DeepWiki**: Generated across 400k+ repositories in one bank's case. A shared living documentation layer that captures current codebase structure — agents can query it rather than hallucinate.

**Where shared workspace does NOT reduce drift:**

1. **MetaGPT's SOP pipeline** (paper-documented): The planner agent produces a PRD and API design. The coding agent receives this as text context. If the planner hallucinated a function name, the coder inherits it. Shared workspace helps if the coder can also read the actual code repo — but MetaGPT's design doesn't mandate this. The result: plan drift propagates downstream through the pipeline.

2. **CrewAI task-output chaining**: Same problem as MetaGPT. Agent B receives Agent A's text output. If Agent A wrote "use `CheckResult(ok=True)`" but the actual field is `status`, Agent B inherits the hallucination. No mechanism forces grounding in source.

3. **Prompt-based memory** (most frameworks): Shared memory via in-context text is just another source of hallucination if the original content was wrong. Garbage in, garbage out — at scale.

### Verdict: Shared execution sandbox > shared document store > shared text context

The ranking of effectiveness for drift prevention:

| Shared mechanism | Drift reduction | Why |
|---|---|---|
| Shared execution sandbox (CodeAct) | High | Errors are real; interpreter doesn't lie |
| Shared symbol/AST index (Cursor, Aider) | High | Symbols come from source, not LLM generation |
| Shared state with actual file contents (LangGraph) | Medium-High | Depends on whether someone actually extracted real symbols |
| Shared DeepWiki / living docs (Devin) | Medium | One step removed — docs can be stale or wrong |
| Shared task outputs / SOP text (MetaGPT, CrewAI) | Low | Text can contain hallucinations from any prior agent |
| Shared prompt context (most defaults) | Near zero | Hallucinations compound rather than cancel |

---

## Section 4: Anti-Drift Techniques NOT Currently in verify-kit's GSD Workflow

These are concrete techniques identified in the research that GSD's plan-review-convergence loop does not use today:

### Technique 1: Reviewer-Reads-Source Gate

**What it is**: Before review, the reviewer agent explicitly reads the actual source files referenced by the plan. Every symbol, decorator, class, or field name in the plan gets checked against the file contents.

**How other systems do it**: Cursor's agent retrieves actual code before responding. Cline reads actual files via tool calls. Claude Code's Explore subagent reads source before the Plan subagent writes anything.

**What GSD does**: Reviewer (Codex) reads only plan files. Never reads source. This is the single largest gap.

**Proposed GSD addition**: Add a pre-review step — a "Symbol Extraction" pass where an agent reads all source files referenced in the plan, extracts the actual exported symbols (decorators, class names, field names, CLI flags, file paths), and produces a `SYMBOLS.md` artifact. The reviewer then receives both the plan AND `SYMBOLS.md` as context, with an explicit instruction: "Flag any symbol in the plan that does not appear in SYMBOLS.md."

**Implementation complexity**: Low. Grep/AST pass on the harness source, write a JSON or Markdown file, pass it to the reviewer in the prompt.

### Technique 2: Execution-Based Verification at Plan Stage

**What it is**: Run a dry-run import check before code is fully written. For Python: `python -c "from harness.checks import register; print(register.__name__)"`. If the decorator doesn't exist, the plan is wrong before any code generation.

**How other systems do it**: OpenHands/CodeAct does this at code execution time. A variant: run import/symbol checks *at plan validation time* before the executor writes code.

**What GSD does**: Static plan review only. No execution-based check.

**Proposed GSD addition**: In `just verify` or as a plan-gate, add a `check-symbols.sh` that validates plan-referenced symbols against the live harness. If `@register_check` is mentioned in any PLAN.md but `grep -r "def register_check\|register_check =" harness/` returns nothing, the gate fails.

**Implementation complexity**: Medium. Requires parsing PLAN.md for symbol references and running targeted greps against source.

### Technique 3: Dependency-Graph Constrained Generation (FSE 2025)

**What it is**: Before generating code for a plan, extract the actual import graph of the target module and inject it into the executor's context. The executor is instructed: "Only call functions and classes that appear in this dependency map."

**How other systems do it**: FSE 2025 paper shows 67-73% reduction in phantom API calls by constraining generation against the actual dependency graph.

**What GSD does**: Executor reads the plan + codebase freely. No constraint on what symbols it can reference.

**Proposed GSD addition**: Add a "dependency snapshot" step between PLAN.md and execution. Use `python -m ast` or `pyright --outputjson` to produce a machine-readable list of exported names from each harness module. Inject this as a read-only context block into the executor's prompt: "Available symbols from harness.checks: [...]".

**Implementation complexity**: Medium-High. Requires AST tooling for each supported language.

### Technique 4: Living Symbol Contract (Spec-as-Type-System)

**What it is**: Maintain a `CONTRACTS.md` (or YAML/JSON) file that lists the actual exported API surface: decorator names, dataclass fields, CLI flags, file paths, protocol schemas. Every plan must reference only items in CONTRACTS.md. CONTRACTS.md is generated from source (not hand-written) and committed alongside the code.

**How other systems do it**: Augment Code's spec-driven system uses OpenAPI/AsyncAPI as machine-readable contracts. Aider's repo map is the equivalent for code — it's generated from source, not authored by hand.

**What GSD does**: PLAN.md is authored by a planner agent with no contract to check against. There is no machine-readable API surface document generated from the Phase 2 source.

**Proposed GSD addition**: After each phase, run a generator that produces `.planning/phases/NN-PHASE/CONTRACTS.md` from the actual source (using `inspect`, `ast`, or `pyright --outputjson`). Next phase's planner receives CONTRACTS.md as required reading. The plan-review-convergence reviewer gets an explicit rule: "Flag any decorator, class, field, or file path not present in CONTRACTS.md."

**Implementation complexity**: Low-Medium. Python `ast.parse` + walking the tree to extract decorated function names and class definitions is ~50 lines.

### Technique 5: Reviewer Adversarial Symbol Hunt (Process Change)

**What it is**: Give the reviewer an explicit, adversarial instruction targeting symbol names rather than logical correctness. "Read these plans. For every symbol name — every decorator, every field, every CLI flag, every file path — assume it is hallucinated until proven otherwise. List each one and mark it verified or unverified."

**How other systems do it**: GitHub Copilot Workspace exposes intermediate artifacts explicitly; humans catch symbol errors because they see the plan and know the codebase. The adversarial framing is what the `08-plan-convergence-workflow.md` rule calls out for the "adversarial second-Codex pass" but does not specifically target symbols.

**What GSD does**: Reviewer checks for logical consistency, interface contracts, path resolution leaks. It does NOT explicitly hunt for invented symbols because it has no ground truth to compare against.

**Proposed GSD addition**: In the convergence loop's reviewer prompt, add a dedicated "Symbol Verification" section: "For each of the following symbol categories, list every name mentioned in the plans, then mark each as [VERIFY — no source available to confirm] or [KNOWN — appears in CONTRACTS.md]: decorators, dataclass fields, CLI flag names, module paths, protocol fields." This makes the gap visible even without a full CONTRACTS.md pipeline.

**Implementation complexity**: Near zero — it's a prompt change to the reviewer. Highest ROI of all the techniques listed here.

### Technique 6: Separate Planner and Source-Reader (Aider-Style Repo Map)

**What it is**: Before the planner writes PLAN.md, a separate read-only agent (like Aider's repo map or Claude Code's Explore subagent) produces a structured summary of the actual codebase API surface. The planner is required to reference this summary — not invent symbols from training data.

**How other systems do it**: Aider: repo map is always in context when GPT plans. Claude Code: Explore runs first. Cursor: semantic retrieval runs before every edit.

**What GSD does**: Planner (`/gsd:discuss-phase` + `/gsd:plan-phase`) works from the REQUIREMENTS.md and previous PLAN.md files. It does not automatically read the actual source code before writing the new plan.

**Proposed GSD addition**: Add a "pre-planning source scan" step to `/gsd:plan-phase`. Before generating PLAN.md, the planner agent runs `find harness/ -name "*.py" -not -path "*/\.*"` and reads every non-template Python file to extract actual function/class/decorator names. This output becomes a mandatory context block: "Actual harness API surface (extracted from source):". The planner generates the plan using only these names for any reference to existing harness code.

**Implementation complexity**: Medium. Requires modifying the plan-phase skill or adding a pre-step in the GSD workflow.

---

## Summary: Root Cause and Ranked Fixes

**Root cause in verify-kit's Phase 4**: The Codex reviewer is genuinely blind to the codebase — it reviews plans in isolation. The planner invents symbols from training data or from reading other plan files (which themselves may have drifted). No step in the current GSD workflow reads actual source to validate plan symbols before execution.

**Ranked by implementation cost vs impact:**

| Rank | Technique | Cost | Impact |
|---|---|---|---|
| 1 | **Reviewer adversarial symbol hunt** (Technique 5) | Near zero — prompt change | High — surfaces all unverifiable symbols |
| 2 | **CONTRACTS.md generated from source** (Technique 4) | Low (~50 lines Python) | High — gives reviewer ground truth |
| 3 | **check-symbols.sh gate** (Technique 2) | Medium | High — breaks the build on drift |
| 4 | **Pre-planning source scan** (Technique 6) | Medium | High — prevents drift at authoring time |
| 5 | **Dependency-graph constrained generation** (Technique 3) | Medium-High | Very high — proven 67% reduction (FSE 2025) |
| 6 | **Reviewer-reads-source gate** (Technique 1) | Medium | High — but requires giving Codex tool access or a pre-pass |

Start with Technique 5 (tonight) + Technique 4 (next phase). These two together give the reviewer an actual ground truth to compare against, without changing the execution pipeline at all.

---

## Sources

- Aider repo map blog: https://aider.chat/2023/10/22/repomap.html
- Aider repo map docs: https://aider.chat/docs/repomap.html
- Aider DeepWiki (repo mapping system): https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system
- Cursor codebase indexing docs: https://cursor.com/docs/context/codebase-indexing
- Cursor indexing explainer (Towards Data Science): https://towardsdatascience.com/how-cursor-actually-indexes-your-codebase/
- Cline — why no index (HN): https://news.ycombinator.com/item?id=44106944
- Cline bot (context optimization): https://cline.bot/blog/inside-clines-framework-for-optimizing-context-maintaining-narrative-integrity-and-enabling-smarter-ai
- Cline tools reference: https://docs.cline.bot/tools-reference/all-cline-tools
- MetaGPT paper (ICLR 2024): https://arxiv.org/abs/2308.00352
- MetaGPT ICLR oral: https://iclr.cc/virtual/2024/oral/19756
- Cognition Devin 2025 performance review: https://cognition.ai/blog/devin-annual-performance-review-2025
- GitHub Copilot Workspace context explainer: https://aidevme.com/github-copilot-workspace-context-the-complete-developer-guide-to-smarter-ai-coding/
- VS Code workspace context docs: https://code.visualstudio.com/docs/copilot/reference/workspace-context
- Sourcegraph — how Cody understands your codebase: https://sourcegraph.com/blog/how-cody-understands-your-codebase
- OpenHands paper: https://arxiv.org/abs/2407.16741
- OpenHands SDK paper: https://arxiv.org/html/2511.03690v1
- Augment Code spec-driven guide: https://www.augmentcode.com/guides/spec-driven-ai-code-generation-with-multi-agent-systems
- Agent drift paper (arXiv 2601.04170): https://arxiv.org/pdf/2601.04170
- API hallucination mitigation, FSE 2025: https://conf.researchr.org/details/fse-2025/fse-2025-industry-papers/41/Towards-Mitigating-API-Hallucination-in-Code-Generated-by-LLMs-with-Hierarchical-Depe
- Replit Agent LangChain case study: https://www.langchain.com/breakoutagents/replit
- Replit replit.md docs: https://docs.replit.com/replitai/replit-dot-md
- SWE-bench overview: https://www.emergentmind.com/topics/swe-bench
- Awesome repo-level code generation: https://github.com/YerbaPage/Awesome-Repo-Level-Code-Generation
- LangGraph vs CrewAI (DataCamp): https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen
- AutoGen paper: https://arxiv.org/pdf/2308.08155
