# Wave 6 Research: Shared-Context Architectures for Drift Prevention in Multi-Agent Systems

**Date:** 2026-05-21  
**Researcher:** Claude Sonnet 4.6 (autonomous research agent)  
**Mission:** Catalog concrete mechanisms that prevent code-API drift in multi-agent planner-reviewer-executor pipelines, with particular attention to the verify-kit failure mode: a planner inventing `@register_check` when the real decorator is `@register`.

---

## Background: The Drift Problem

In verify-kit's GSD workflow, three agents collaborate via files in `.planning/`:

1. **Planner** writes a `PLAN.md` describing what to build — including specific API names, decorators, function signatures.
2. **Reviewer (Codex)** reads only the plan, not the source, and validates the plan's internal consistency.
3. **Executor** implements against the plan and discovers drift at runtime — ~10–15 min per bug.

The planner's core failure mode: it invents plausible-sounding symbols (e.g., `@register_check`) because it never reads the actual source when authoring the plan. The reviewer can't catch this because it also doesn't read the source. Drift is only detected at execution time.

---

## Section 1: Catalog of Mechanisms

### 1.1 Aider Repo-Map (tree-sitter + PageRank)

**What it is:**  
A structured, token-budget-aware summary of real codebase symbols injected into every LLM context window. Aider parses each source file with tree-sitter's language-specific query files (.scm), extracting two tag types: `def` (definitions — functions, classes, methods) and `ref` (references — usages). These tags form a directed graph where files are nodes and definition-reference relationships are edges. NetworkX PageRank then ranks files by relevance to the current conversation, with edge weights multiplied by: 10x for identifiers mentioned in the user's message, 50x for references from files already in chat, 0.1x for private names. The ranked definitions are rendered as a hierarchical tree:

```
aider/
  repomap.py
    class RepoMap
      def __init__(...)
      def get_repo_map(...)
```

This map is injected into every planner context window before the planner writes anything.

**What bug class it prevents:**  
**API hallucination** — the planner inventing function names, class names, or decorator names that don't exist. Because the planner sees actual extracted signatures from the live codebase, it has factual ground truth rather than relying on training-data patterns.

**Limitations:**  
- Only covers 40+ languages with full tree-sitter query support (90+ languages get "linter only" mode with no definition extraction).
- Binary search over token budget means low-ranked symbols can be dropped. If `@register` is in a rarely-referenced module, it might not make the cut.
- Cannot index dynamically-generated symbols (e.g., decorators that register functions into a dict at import time).
- Rapid programmatic changes might not reflect immediately due to file-mtime-based cache invalidation.

**Computational cost:** Medium. Full tree-sitter parse of changed files on every interaction, plus in-memory PageRank. Aider's default is 1024 tokens for the map; the binary search to fit the budget is the dominant cost.

**Sources:**  
- https://aider.chat/2023/10/22/repomap.html  
- https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system

---

### 1.2 Cursor Codebase Indexing (AST-chunked Embeddings + Turbopuffer)

**What it is:**  
Cursor uses tree-sitter to perform AST-aware chunking — splitting code at semantic boundaries like function and class definitions rather than character offsets. Each chunk is embedded (OpenAI or custom embedding model) and stored in Turbopuffer (vector database) with metadata: file path, line range. At query time, Cursor converts the user's query to an embedding, performs nearest-neighbor search in Turbopuffer, retrieves the actual code locally using the stored line ranges, and injects those chunks as context.

**What bug class it prevents:**  
**Semantic mismatch** — agents referencing APIs in the wrong way (wrong argument order, wrong return type assumption) because they weren't shown the relevant code. Embedding retrieval is better at finding semantically similar code than keyword search. For example, if a planner asks about "registering a check," embedding search is more likely to surface the `@register` decorator than a grep for the literal string.

**Limitations:**  
- Embeddings are trained on semantic similarity, not precision. Two functions with similar purposes but different names may be conflated.
- RAG inherently retrieves only what's semantically close to the query. If the query uses the wrong vocabulary (e.g., planner says "register check" when the code uses "hook"), retrieval misses.
- Does not provide the authoritative symbol table — retrieves chunks, not a comprehensive API surface.
- Stale embeddings between index refreshes.

**Computational cost:** High upfront (index build), low per-query (nearest-neighbor lookup). Cursor caches by chunk content hash.

**Sources:**  
- https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast  
- https://towardsdatascience.com/how-cursor-actually-indexes-your-codebase/

---

### 1.3 Sourcegraph SCIP / Precise Code Intelligence

**What it is:**  
SCIP (Stack Graph Index Protocol) is Sourcegraph's open-source successor to LSIF — a protobuf-encoded, typed format for indexing code with precision-grade symbol resolution. Unlike embedding-based retrieval (probabilistic), SCIP produces exact, deterministic answers: "where is this symbol defined?", "what are all the callers of this function?", "what type does this expression have?". SCIP data is ~8x smaller than LSIF and 3x faster to process. Sourcegraph's Cody assistant uses a hybrid retrieval pipeline: keyword search + embedding search + SCIP-based precise code intelligence ("hard links"). The semantic code graph built from SCIP captures not just definition locations but the full semantic structure — inheritance, interface implementations, type relationships.

**What bug class it prevents:**  
**Cross-file reference drift** — planning assumptions about which files export which symbols, which classes implement which interfaces, which functions are callable on which types. Embeddings find semantically related code; SCIP tells you the ground truth. Sourcegraph claims SCIP-grounded context "reduces the rate of common LLM hallucinations like type errors and imaginary function names."

**Limitations:**  
- Requires a per-language SCIP indexer (available for Go, Java, TypeScript, Python, etc., but coverage is uneven).
- Indexing must be re-run after code changes (not real-time).
- SCIP is the format; consuming it requires Sourcegraph infrastructure or custom tooling — not available out of the box for small projects.
- Does not prevent planners from ignoring the retrieved context.

**Computational cost:** High upfront (full SCIP index build), very low per-query (deterministic symbol lookup). 8x smaller than LSIF means the index can fit in memory.

**Sources:**  
- https://sourcegraph.com/blog/announcing-scip  
- https://arxiv.org/html/2408.05344v1

---

### 1.4 Tree-Sitter as a Planner-Time Tool (SQLite-backed MCP Index)

**What it is:**  
A lighter-weight pattern where tree-sitter parses the codebase into a SQLite database (WAL mode for fast reads) that agents can query via MCP tools. One concrete implementation exposes 27 tools via MCP: "what functions are defined in file X?", "what is the signature of function Y?", "find all callers of Z", "what was modified recently?". Unlike Aider's repo-map (which is always-on context), this is a **tool the planner can call** on demand before writing a plan.

**What bug class it prevents:**  
**Planner-time symbol invention** — directly addresses the verify-kit failure mode. Before writing a plan that mentions `@register_check`, the planner can call a tool like `get_decorators_in_module("checks.py")` and receive the actual list: `[@register, @skip_in_ci]`. Invented names fail the lookup; real names are returned.

**Limitations:**  
- The planner must be prompted or instructed to call the lookup tool before inventing API names — this is a workflow design problem, not a technical one.
- SQLite index must be kept up to date (file-watcher or pre-plan rebuild step).
- Tree-sitter can extract decorators and function names, but cannot resolve them semantically (e.g., `@app.route` vs `@register` — it sees names, not types).

**Computational cost:** Low. Single-pass parse, SQLite writes. Per-query: microsecond SQLite reads.

**Sources:**  
- https://dev.to/uwe_c_39d9ab7d16ff8dfe67e/how-i-cut-ai-context-usage-by-50x-with-a-tree-sitter-code-index-plm  
- https://github.com/justrach/codedb  

---

### 1.5 CodeGraph (Knowledge Graph over Symbols)

**What it is:**  
CodeGraph builds a pre-indexed knowledge graph capturing: symbols (nodes), call edges, import edges, inheritance edges, and code structure. Agents query the graph rather than scanning files. On VS Code's codebase: 52 tool calls with file scanning → 3 tool calls with CodeGraph.

**What bug class it prevents:**  
**Cross-module assumption drift** — a planner assuming function A calls function B when it doesn't, or that class C inherits from D when it doesn't. The call graph is ground truth, extracted from the actual AST.

**Computational cost:** Medium upfront (graph construction), very low per-query.

**Sources:**  
- https://dev.to/arshtechpro/codegraph-stop-your-ai-agent-from-grepping-the-same-files-50-times-3bgm

---

### 1.6 TypeSpec / OpenAPI Spec-First Codegen

**What it is:**  
TypeSpec is a DSL (TypeScript-like) for API design that generates OpenAPI documents, client SDKs, server stubs, and mock servers from a single source of truth. OpenAPI Generator and Smithy take specs further: they generate complete typed implementations in Go, Java, TypeScript, Python, etc. The enforcement mechanism is **build-time diff**: if the generated code differs from what's in the repository, the build fails. CI/CD pipelines run `typespec compile → openapi-generator generate → git diff` and reject PRs with schema drift.

**What bug class it prevents:**  
**API surface drift** — the server implements a different interface than what clients expect. Both sides are generated from the same spec, making it impossible for them to diverge without the spec changing first. The bug class is: "server returns `{ userId: string }` but the client type expects `{ user_id: string }`".

**Limitations:**  
- Does not prevent the spec from being wrong — it only enforces spec-to-implementation consistency.
- Proto/OpenAPI drift from business intent is still possible.
- Requires spec-first discipline; code-first shops need a migration path.
- Does not address planner-time hallucination (the planner could invent an endpoint that doesn't exist in the spec).

**Computational cost:** Medium (code generation), negligible per-check (git diff).

**Sources:**  
- https://evilmartians.com/chronicles/openapi-nestjs-type-safe-controllers-from-the-contract  
- https://www.speakeasy.com/openapi/frameworks/typespec

---

### 1.7 gRPC / Protobuf / Smithy IDL Codegen

**What it is:**  
Protocol Buffer IDL defines service and message contracts. `protoc` generates stubs for both client and server in any supported language. The generated stubs are typed — calling a method that doesn't exist in the .proto file is a compile error. Smithy extends this pattern with richer semantics (traits, constraints, validation rules). Build-time enforcement through `protobuf-net.BuildTools` flags violations at compile time.

**What bug class it prevents:**  
**Method signature drift** — client calling `CreateUser(CreateUserRequest)` when the server expects `CreateUserV2(UserCreationInput)`. Compile-time type checking catches these before deployment. The bug class is resolved at compile time rather than runtime.

**Limitations:**  
- Only covers the API boundary, not internal implementation details.
- Proto schema evolution (adding fields, deprecating fields) can still cause subtle drift.
- Requires committing to IDL-first development.

**Computational cost:** Low (compile-time check, no runtime overhead).

**Sources:**  
- https://johal.in/fastapi-grpcio-tools-stub-code-generation-protos-ml-contracts-2025-13/

---

### 1.8 MetaGPT SOP-Based Multi-Agent Architecture

**What it is:**  
MetaGPT encodes Standardized Operating Procedures (SOPs) as structured role definitions. Each role (ProductManager, Architect, Engineer, QA) produces typed artifacts that feed the next role. The key mechanism: roles communicate via structured documents (PRD → System Design → Code → Tests), not free-form chat. A shared environment (blackboard) makes intermediate artifacts visible to all agents. The QA role catches bugs made by the Engineer before they exit the pipeline.

**What bug class it prevents:**  
**Cascading hallucination** — the failure mode where an incorrect assumption in the planner's output becomes a stated fact in the reviewer's context, which is then accepted as truth by the executor. By separating roles and requiring typed handoffs, MetaGPT reduces the surface area where any single agent's error can silently propagate.

**Limitations:**  
- SOPs don't prevent individual agents from hallucinating — they structure the handoffs, not the thinking.
- The shared environment is only as good as what agents write to it. If the Engineer writes incorrect code, the QA agent only catches bugs it can detect via testing, not logical errors.
- Does not address planner-time symbol invention.

**Computational cost:** High (multiple LLM calls per phase).

**Sources:**  
- https://arxiv.org/pdf/2308.00352  
- https://proceedings.iclr.cc/paper_files/paper/2024/file/6507b115562bb0a305f1958ccc87355a-Paper-Conference.pdf

---

### 1.9 LangGraph StateGraph + Typed State Schema

**What it is:**  
LangGraph models multi-agent workflows as directed graphs where nodes are agents and edges are conditional transitions. The State object is a typed schema (Python TypedDict or Pydantic model) shared across all nodes. Each node reads from and writes to this typed state. LangGraph enforces schema consistency: agent outputs that don't match the expected state shape are rejected. The compilation step validates node connections and identifies cycles before execution. Reducers merge updates deterministically.

**What bug class it prevents:**  
**Agent output shape drift** — agent A produces `{"result": "..."}` but the downstream agent B expects `{"output": "..."}`. Typed state schemas catch this at graph compilation time, not at runtime.

**Limitations:**  
- Typed schemas don't prevent incorrect *values*, only incorrect *shapes*.
- If an agent hallucinates a function name inside a string field, the schema won't catch it.
- The state is mutable by all agents — a hallucinating agent can corrupt shared state.

**Computational cost:** Low (schema validation is O(1) per node transition).

**Sources:**  
- https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/

---

### 1.10 CrewAI Multi-Tier Memory Architecture

**What it is:**  
CrewAI uses three memory tiers: short-term (ChromaDB + RAG for current session context), long-term (SQLite for cross-session insights), and entity memory (RAG for named entities). Shared caching and memory are exposed as crew-level resources. When agents are organized into crews, these memory layers are shared — one agent's discovery about an API becomes available to other agents via retrieval.

**What bug class it prevents:**  
**Session-to-session context loss** — a planner that correctly identified the decorator name `@register` in one session forgets it in the next. Long-term memory allows correct discoveries to persist.

**Limitations:**  
- Memory is approximate (RAG-based retrieval), not authoritative. Storing "I found `@register` in `checks.py`" does not prevent future sessions from hallucinating `@register_check`.
- Memory consistency across agents is an open research problem — CrewAI's architecture doesn't solve it.
- Native memory doesn't evolve well or transfer across projects.

**Computational cost:** Medium (ChromaDB embedding queries per interaction).

**Sources:**  
- https://sparkco.ai/blog/deep-dive-into-crewai-memory-systems  
- https://mem0.ai/blog/crewai-guide-multi-agent-ai-teams

---

### 1.11 OpenHands / CodeAct Event-Stream Architecture

**What it is:**  
OpenHands defines a shared event-sourced state model where every action (file read, code execution, terminal command) and every observation (command output, test result, error) is recorded in an immutable event stream. The stream is deterministically replayable. The CodeAct paradigm means the agent generates executable code as actions and observes the actual results — it cannot claim success without running the code.

**What bug class it prevents:**  
**Silent executor drift** — an executor claiming "I implemented X" without actually running it. The event stream contains the actual terminal output, test results, and error messages. If `@register_check` doesn't exist, the import error is in the stream as an observation.

**Limitations:**  
- Drift is caught at execution time, not plan time. The planner's hallucination is corrected by the executor's observation loop, but only after the code has been written and run.
- "Open-ended feature design without clear specs causes planning drift and looping" — the event stream doesn't prevent planner hallucination, only executor hallucination.

**Computational cost:** Medium (sandboxed code execution per action).

**Sources:**  
- https://arxiv.org/html/2511.03690v1  
- https://arxiv.org/abs/2407.16741

---

### 1.12 AutoGen Group Chat Broadcast

**What it is:**  
AutoGen's GroupChatManager broadcasts each agent's message to all other agents. All participants share a single conversation thread and operate from the same context. A selector (LLM-based or rule-based) chooses the next speaker. The conversation context persists across tasks within a session.

**What bug class it prevents:**  
**Context partitioning drift** — agent A inventing an API that agent B then "confirms" because B wasn't shown the same context. In group chat, all agents see all messages, so if agent A says "I'll use `@register_check`" and agent B knows the codebase, B can correct A before the plan is finalized.

**Limitations:**  
- Effectiveness depends on whether any agent in the group has the correct context. If no agent has read the source, the broadcast propagates the hallucination to everyone.
- Context window limits: as conversations grow, older context is dropped. In long sessions, early correct API names can be forgotten.
- No structured mechanism to force any agent to verify symbols against source.

**Computational cost:** High (all agents receive all messages; quadratic in number of agents × messages).

**Sources:**  
- https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/group-chat.html  
- https://arxiv.org/pdf/2308.08155

---

### 1.13 ContextCov: Executable Constraints from Instruction Files

**What it is:**  
ContextCov transforms passive instruction files (like AGENTS.md or CLAUDE.md) into active executable guardrails. It parses the instruction file into a Markdown AST (preserving hierarchical context through "path-aware slicing"), routes each constraint to one of four enforcement domains: Process (shell command interception), Source (AST pattern matching), Architectural (dependency graphs), and Semantic (LLM-as-judge). Deterministic checks validate file locations, dependency directions, and style patterns.

**What bug class it prevents:**  
**Instruction document violations** — agents writing code that violates documented project constraints even when those constraints are in the context window. The bug class is "agent read the rule but didn't follow it." ContextCov makes the rules executable rather than advisory.

**Limitations:**  
- Does not address symbol-level hallucination. It enforces constraints derived from instruction files, not constraints derived from source code.
- Semantic violations use LLM-as-judge, which introduces its own hallucination risk.
- Extracting constraints from natural-language instruction files is itself an LLM task — can produce incorrect constraint synthesis.

**Computational cost:** Medium (AST parsing + constraint classification per commit/check).

**Sources:**  
- https://arxiv.org/html/2603.00822v1

---

### 1.14 AWS Kiro: Spec-Driven Development with Steering Files and Hooks

**What it is:**  
Kiro is an AWS agentic IDE where every feature is structured as a spec: `requirements.md`, `design.md` (with TypeScript interfaces, database schemas, API endpoints generated by analyzing the codebase), and `tasks.md` (sequenced with dependency links). Steering files provide persistent project context (patterns, libraries, standards) that every agent interaction reads automatically. Hooks trigger automated agent actions on file events (save, create, delete) — keeping specs synchronized with code changes. The key claim: "specs stay synced with your evolving codebase."

**What bug class it prevents:**  
**Spec-reality gap** — a plan that was accurate when written but drifts as implementation evolves. Hooks maintain sync. Task-by-task execution keeps diffs to 50-250 lines, keeping each step auditable.

**Limitations:**  
- Specs are generated by analyzing the codebase, not verified against a formal contract. The sync relies on an LLM re-analyzing the codebase on events, which can still hallucinate.
- Hooks are event-driven, not continuous — rapid development between saves creates windows of drift.
- Design.md's TypeScript interfaces are planner outputs, not verified against the runtime.

**Computational cost:** Medium (LLM calls on file events).

**Sources:**  
- https://kiro.dev/blog/introducing-kiro/  
- https://dev.to/jubinsoni/aws-kiro-the-agentic-ide-that-makes-specs-the-unit-of-work-3eko

---

### 1.15 Property-Based Testing as Executable Specification

**What it is:**  
Property-based testing (PBT) frameworks (Hypothesis for Python, QuickCheck for Haskell) express specifications as properties — invariants that must hold for all inputs. These properties become an executable specification that is linked to requirements. Recent work ("Agentic Property-Based Testing", arXiv 2510.09907) shows LLM agents can discover and write properties across the Python ecosystem. A "Property-Generated Solver" framework uses PBT to validate high-level program invariants rather than specific input-output examples.

**What bug class it prevents:**  
**Behavioral drift** — implementation that passes all example-based tests but violates the underlying invariant. PBT explores the input space automatically, catching edge cases that unit tests miss. When the property is derived from the spec, the test becomes the spec.

**Limitations:**  
- PBT catches violations *after* implementation — it is test-time, not plan-time.
- Writing good properties requires domain knowledge. LLMs can write trivially-true properties (vacuous specs).
- Does not prevent planner-time symbol invention.

**Sources:**  
- https://arxiv.org/html/2510.09907v1  
- https://kiro.dev/blog/property-based-testing/

---

### 1.16 JSON Schema Output Enforcement

**What it is:**  
Modern LLM providers (OpenAI's Structured Output Mode, Anthropic's tool-use mode) support constrained generation against a JSON Schema. The model is forced — not just asked — to produce output matching the schema. MCP tool definitions expose a JSON Schema for each tool's input parameters. When an agent calls a tool, the schema is validated before execution. ScaleMCP (2025) proposes "Dynamic Auto-Synchronizing" MCP tools where the schema is derived from the implementation, preventing the tool description from drifting from what the tool actually accepts.

**What bug class it prevents:**  
**Agent output shape drift** — an agent producing `{"status": "done"}` when downstream consumers expect `{"completed": true, "result": {...}}`. Also prevents agents from passing wrong-typed arguments to tools (string where int expected, missing required field).

**Limitations:**  
- JSON Schema validates shape, not semantic content. An agent can hallucinate a function name that fits the string schema perfectly.
- Schema drift is still possible when tool implementations change without updating the schema. ScaleMCP addresses this but requires tooling.

**Computational cost:** Negligible (schema validation is pure parsing).

**Sources:**  
- https://dev.to/dowhatmatters/output-format-enforcement-for-agents-json-schema-or-it-didnt-happen-1pbi  
- https://auto-post.io/blog/automate-schema-for-ai-agents

---

## Section 2: Bidirectional Spec-Code Mechanisms

### Enforcement Strength Taxonomy

| Mechanism | Enforcement Phase | Strength | What It Catches |
|-----------|-----------------|----------|-----------------|
| Protobuf/gRPC IDL codegen | Compile-time | Very strong — compile error | Wrong method names, wrong argument types |
| TypeSpec → OpenAPI → codegen | Build-time CI diff | Strong — build failure | Spec-implementation shape divergence |
| TypeScript `.d.ts` declaration files | Compile-time (tsc) | Strong — type error | Wrong function signatures, wrong return types |
| JSON Schema structured output | Generation-time | Strong — constrained sampling | Wrong output shapes from agents |
| Pyright type stubs | IDE + CI | Strong — type error | Python API surface violations |
| Property-based tests (Hypothesis) | Test-time | Medium — finds violations probabilistically | Behavioral invariant violations |
| Contract tests (golden files) | Test-time | Medium — catches regressions | API surface changes |
| ContextCov AST pattern matching | Commit-time | Medium — pattern violations | Style and architectural constraints |
| Aider repo-map injection | Plan-time (in-context) | Weak — LLM may ignore | Symbol hallucination (soft prevention) |
| Cursor embedding retrieval | Plan-time (in-context) | Weak — probabilistic retrieval | Wrong API usage patterns |
| JSON Schema MCP tool validation | Runtime | Medium — tool call rejection | Wrong tool argument shapes |
| OpenHands event-stream observation | Runtime | Strong — actual execution | All executor-level failures |

### The Compile-Time vs. Test-Time vs. Runtime Tradeoff

**Compile-time** (gRPC, TypeSpec, `.d.ts`): The strongest class. If the plan says "call `createUser(email, password)`" but the compiled type says `createUser(UserInput)`, the executor gets a compile error immediately. Requires typed languages and pre-agreed interfaces. Works only for the API *surface*, not for internal implementation choices.

**Test-time** (PBT, contract tests, golden files): Catches behavioral violations but requires code to be written first. The planner's hallucination becomes a failing test. Feedback loop is minutes, not milliseconds. Property-based tests are more powerful than example-based tests because they explore the input space.

**Runtime** (OpenHands event-stream, API gateway validation): The code runs; the wrong decorator name produces an `AttributeError`; the executor sees the error in its observation. The feedback loop is 10-15 minutes (as described in verify-kit's failure mode). This is the current verify-kit state.

**Plan-time** (repo-map injection, tree-sitter MCP tools): The only mechanism that *prevents* drift rather than detecting it. If the planner's context contains the actual symbol table before writing the plan, the planner can consult it. The weakness: soft prevention (the LLM may still hallucinate even with the symbol table present) vs. hard prevention (compile-time errors that are deterministic).

### The Missing Rung: Plan-Time Hard Enforcement

Current mechanisms have a gap: there is no widely-used mechanism that deterministically prevents a planner from writing `@register_check` in a plan. The closest analogs:

1. **Tool-calling for symbol lookup**: If the planner is forced to call a `get_symbol("register_check")` tool that returns "not found" before it can include that symbol in a plan, the hallucination is surfaced. This requires making symbol lookup a mandatory pre-writing step.

2. **Plan schema validation**: If a plan's API references are extracted and validated against the live symbol index before the plan is committed to disk, non-existent symbols fail validation. This is the equivalent of "compile the plan" rather than "compile the code."

Neither of these is implemented in GSD or any major framework as of mid-2026.

---

## Section 3: Concrete Drift-Prevention Recipes for GSD

### Recipe 1: Pre-Plan Symbol Extraction Tool (Highest Value)

**The pattern:** Before the planner writes any plan that references source code APIs, force it to call a tree-sitter symbol extraction MCP tool. The tool returns the actual exported names, decorators, and function signatures from the relevant modules.

**Implementation sketch for verify-kit:**
```bash
# .planning/tools/symbol-index.sh — run before plan authoring
# Build SQLite index of all Python symbols in the project
python3 -c "
import ast, sqlite3, pathlib
conn = sqlite3.connect('.planning/symbol-index.db')
conn.execute('CREATE TABLE IF NOT EXISTS symbols (module TEXT, name TEXT, kind TEXT, lineno INT)')
for f in pathlib.Path('src').rglob('*.py'):
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            conn.execute('INSERT INTO symbols VALUES (?,?,?,?)',
                (str(f), node.name, type(node).__name__, node.lineno))
        for deco in getattr(node, 'decorator_list', []):
            name = deco.id if isinstance(deco, ast.Name) else (
                deco.attr if isinstance(deco, ast.Attribute) else None)
            if name:
                conn.execute('INSERT INTO symbols VALUES (?,?,?,?)',
                    (str(f), name, 'decorator', node.lineno))
conn.commit()
"
```

Then expose this as a CLAUDE.md instruction or MCP tool that the planner must call: "Before writing any plan step that references a decorator, function, or class, call `query_symbols(name)` to verify it exists."

**Bug class prevented:** Planner inventing `@register_check` when `@register` is the real name.  
**Enforcement phase:** Plan-time (soft — depends on planner compliance).  
**Cost:** Single Python pass over source, milliseconds.

---

### Recipe 2: Plan-Time Static Validation Gate

**The pattern:** After the planner writes PLAN.md but before it's committed, a post-processing step extracts all code references (function names, decorator names, class names, import paths) from the plan and validates them against the symbol index.

**Implementation sketch:**
```python
# .planning/scripts/validate-plan-symbols.py
import re, sqlite3, sys

plan_text = open(sys.argv[1]).read()

# Extract decorator references from plan (e.g., @register_check, @skip_in_ci)
decorators = re.findall(r'@([a-zA-Z_][a-zA-Z0-9_]*)', plan_text)
# Extract function call references (e.g., `register_check(...)`)
functions = re.findall(r'`([a-zA-Z_][a-zA-Z0-9_]+)\(', plan_text)

conn = sqlite3.connect('.planning/symbol-index.db')
missing = []
for name in set(decorators + functions):
    row = conn.execute('SELECT name FROM symbols WHERE name=?', (name,)).fetchone()
    if not row:
        missing.append(name)

if missing:
    print(f"PLAN VALIDATION FAILED: these symbols don't exist in source: {missing}")
    sys.exit(1)
print("Plan symbols validated OK")
```

Add to `just plan-validate` and call it in the GSD workflow between `plan-phase` and `execute-phase`.

**Bug class prevented:** Plan containing nonexistent API names reaches the executor.  
**Enforcement phase:** Between plan-time and execution-time — a new "plan-compile" phase.  
**Cost:** Milliseconds (SQLite lookup).

---

### Recipe 3: Inject Frozen API Surface into Planner Context

**The pattern:** Generate a compact "API surface document" from the actual source — listing all public functions, classes, decorators, and their signatures — and include it as mandatory context in every planning prompt. This is Aider's repo-map pattern applied to GSD.

**Implementation sketch:**
```bash
# .planning/scripts/generate-api-surface.sh
# Run before any plan-phase call
python3 -c "
import ast, pathlib
for f in pathlib.Path('src').rglob('*.py'):
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            args = [a.arg for a in node.args.args]
            decos = [d.id if hasattr(d,'id') else str(d) for d in node.decorator_list]
            deco_str = ' '.join(f'@{d}' for d in decos)
            print(f'{f}:{node.lineno}: {deco_str} def {node.name}({", ".join(args)})')
" > .planning/API-SURFACE.md
```

Include API-SURFACE.md in the planner's system prompt (in CLAUDE.md or the GSD `plan-phase` prompt template):

```markdown
# MANDATORY: Before writing any plan step, verify API names in .planning/API-SURFACE.md
# Do NOT invent function names, decorator names, or class names that do not appear in this file.
```

**Bug class prevented:** Planner writing plans with invented API names.  
**Enforcement phase:** Plan-time (soft prevention via context injection).  
**Cost:** Single AST pass, < 1 second.

---

### Recipe 4: Contract Tests as the Spec (Test-Time Hard Enforcement)

**The pattern:** For each internal module boundary, write a contract test that verifies the module's public API surface matches what the spec says. Place contract tests in the plan that *produces* the module (as per the "contracts live with producers" principle already in verify-kit's memory).

**Example:**
```python
# tests/contracts/test_checks_api.py — lives in the plan that produces checks.py
import inspect
from verify_kit import checks

def test_register_decorator_exists():
    """Contract: checks module must export a @register decorator."""
    assert hasattr(checks, 'register')
    assert callable(checks.register)

def test_register_signature():
    """Contract: @register must accept (name: str) -> Callable."""
    sig = inspect.signature(checks.register)
    assert list(sig.parameters.keys()) == ['name']
```

These tests fail immediately if the implementation drifts from the spec. They also serve as authoritative documentation that the reviewer (Codex) can read to understand what the API actually is.

**Bug class prevented:** Executor implementing the wrong API without detection until integration.  
**Enforcement phase:** Test-time (run as part of `just verify`).  
**Cost:** Normal test execution cost.

---

### Recipe 5: MCP Tool Schema as the Live API Contract

**The pattern:** Expose verify-kit's internal APIs as MCP tools with JSON Schema definitions. The schema is derived from Pydantic models or Python type annotations — it is not hand-written. When the planner needs to call an API, it calls the MCP tool rather than generating raw code. Tool call validation catches wrong names immediately (tool not found) and wrong argument shapes (schema validation failure).

This requires verify-kit's APIs to be MCP-compatible, which may be out of scope for v0.1, but is a natural evolution path.

**Bug class prevented:** Wrong tool names at planning time (tool not found → immediate error), wrong argument types at call time (schema validation).  
**Enforcement phase:** Plan-time (tool lookup) and execution-time (schema validation).

---

### Recipe 6: REVIEW-CHECKLIST as Pre-Plan Agent Context

**The pattern:** The verify-kit project already has `.planning/REVIEW-CHECKLIST.md` accumulating known-bad patterns. Extend this to include a mandatory pre-plan check:

```markdown
## Pre-Plan Symbol Verification (REQUIRED)

Before writing any PLAN.md that references source code APIs:

1. Run: `bash .planning/scripts/generate-api-surface.sh`
2. Read `.planning/API-SURFACE.md`
3. For every decorator, function, or class name mentioned in the plan, confirm it appears in API-SURFACE.md
4. If a name does not appear: either use the correct name from API-SURFACE.md, or flag it as a "new symbol to create" with an explicit note.
```

This transforms the checklist from a post-plan review tool into a pre-plan grounding protocol.

---

## Section 4: Open Problems

### 4.1 Dynamic Symbols Are Invisible to Static Analysis

Tree-sitter, SCIP, and AST-based tools all work at parse time. Python decorators registered via `registry = {}; registry[name] = fn` or `@app.route('/path')` patterns are not statically extractable as plain symbol names. Django's URL routing, Flask's app decorators, plugin registries, and metaclass-generated methods are all invisible to static analyzers. A planner can hallucinate a `@register_check` decorator that doesn't exist in the AST but would be added to a registry at import time — and no static tool will catch it.

**Current state:** No solution. Runtime introspection (importing the module and calling `dir()`) is the only ground truth, but this requires the code to be importable, which requires dependencies to be installed, which requires a working environment.

### 4.2 Cross-Agent Context Partitioning

In the verify-kit GSD workflow, the planner and reviewer never share a context window. The reviewer (Codex) reads only the plan, not the source. No current framework has a clean solution to: "reviewer reads plan AND source AND verifies every symbol in the plan against the source." LangGraph can put both in the same state, but getting the reviewer to actually perform the cross-reference is a prompting problem, not an architecture problem.

**Current state:** Partially addressed by Recipe 1 (force planner to pre-verify) and Recipe 2 (post-plan validation gate). No framework automatically enforces reviewer-verifies-plan-against-source.

### 4.3 Plan Language Is Not Machine-Checkable

PLAN.md is natural language prose. Even if we extract symbol names from it with regex, we get false positives (symbol mentioned in a prohibition: "do NOT use `@register_check`") and false negatives (symbol mentioned in a way the regex doesn't capture). Plans don't have a formal grammar.

**Potential solution:** Structured plan format (YAML or JSON with explicit `api_references: [...]` fields). The planner is forced to enumerate the APIs it plans to use in a machine-readable list that is validated before execution. This is a workflow design change, not a tooling change.

**Current state:** No standard. GSD uses Markdown prose. The REVIEW-CHECKLIST is the closest thing to a semi-formal constraint.

### 4.4 Semantic Drift Survives All Static Checks

Two symbols can share a name but mean different things across module versions, refactoring, or design changes. `@register` in v1 accepts `(name: str)` but in v2 accepts `(name: str, priority: int = 0)`. The symbol name is correct but the calling convention is wrong. No repo-map, SCIP index, or AST tool catches this without reading the actual signature — and signature extraction requires parsing to the parameter level, which Aider's repo-map does do, but the planner must be shown the signature and must read it correctly.

**Current state:** Partially mitigated by Recipe 3 (inject full signatures into planner context). Fully prevented only by compile-time type checking (which requires typed language + generated stubs).

### 4.5 The Reviewer's Blind Spot Is Structural

Research (arXiv 2601.04170) shows semantic drift occurs in nearly half of multi-agent LLM workflows by 600 interactions. Even with shared context, agents exhibit **asymmetric drift** — they are more likely to drift from goals that conflict with their training values. A reviewer that has been shown the correct API surface may still "agree" with a plan containing `@register_check` because its training patterns associate the -check suffix with registration patterns.

**Current state:** No mechanical solution. The ContextCov "LLM-as-judge" approach for semantic violations acknowledges this. The only defense is deterministic static checks (Recipes 1-2) which don't rely on LLM judgment.

### 4.6 Drift Compounds in Long Sessions

Aider's repo-map and Cursor's embedding retrieval both operate per-query. As sessions grow, context windows fill and older context (including the correct symbol names) is dropped. LangGraph's compilation step validates the graph structure but not the content of prompts inside nodes. AutoGen group chat propagates drift to all agents as soon as one agent states it.

**Current state:** No framework has a principled solution to long-session symbol drift. Rate-limited full-context refresh (rebuild the API surface doc, re-inject into all agent contexts) is a manual mitigation not automated by any tool.

---

## Key Takeaway for verify-kit

The verify-kit failure mode (planner invents `@register_check`) lives in a gap that no widely-adopted framework closes at plan-time with hard enforcement. The closest the field gets is Aider's repo-map (soft prevention via context injection) and tree-sitter MCP tools (on-demand symbol lookup). The highest-leverage investment for verify-kit is:

1. **Recipe 2 (Plan Validation Gate)** — adds a "plan-compile" step that rejects plans with nonexistent symbols. Deterministic, fast, adds to `just verify`. This is the only mechanism in this catalog that provides hard enforcement at plan-time without requiring a type-checked language.

2. **Recipe 3 (API Surface Document)** — costs one shell command, reduces planner hallucination via context grounding. Soft but cheap.

3. **Recipe 4 (Contract Tests as Spec)** — already aligned with verify-kit's "contracts live with producers" principle. Converts the test suite into an authoritative specification that both the reviewer and executor can read.

---

## Sources

- [Aider repo-map mechanism](https://aider.chat/2023/10/22/repomap.html)
- [Aider Repository Mapping System (DeepWiki)](https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system)
- [Aider repository map overview](https://aider.chat/docs/repomap.html)
- [SCIP: A Better Code Indexing Format Than LSIF](https://sourcegraph.com/blog/announcing-scip)
- [Cody AI-Assisted Coding: Context Retrieval and Evaluation](https://arxiv.org/html/2408.05344v1)
- [Navigating OpenAPI, TypeSpec, and API-Drift](https://netapinotes.com/navigating-openapi-typespec-and-api-drift-in-the-post-openapi-era/)
- [OpenAPI + NestJS: type-safe controllers from the contract](https://evilmartians.com/chronicles/openapi-nestjs-type-safe-controllers-from-the-contract)
- [TypeSpec for OpenAPI (Speakeasy)](https://www.speakeasy.com/openapi/frameworks/typespec)
- [MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352)
- [MetaGPT at ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/6507b115562bb0a305f1958ccc87355a-Paper-Conference.pdf)
- [LangGraph AI Framework 2025](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-ai-framework-2025-complete-architecture-guide-multi-agent-orchestration-analysis)
- [How Cursor Indexes Codebases Fast](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast)
- [How Cursor Actually Indexes Your Codebase (Towards Data Science)](https://towardsdatascience.com/how-cursor-actually-indexes-your-codebase/)
- [Cursor Semantic Search: 12.5% Better Accuracy](https://www.digitalapplied.com/blog/cursor-semantic-search-coding-ai-guide)
- [ContextCov: Executable Constraints from Agent Instruction Files](https://arxiv.org/html/2603.00822v1)
- [Kiro: Agentic IDE for Spec-Driven Development](https://kiro.dev/blog/introducing-kiro/)
- [AWS Kiro: The Agentic IDE That Makes Specs the Unit of Work](https://dev.to/jubinsoni/aws-kiro-the-agentic-ide-that-makes-specs-the-unit-of-work-3eko)
- [Spec-Driven Development: When Architecture Becomes Executable (InfoQ)](https://www.infoq.com/articles/spec-driven-development/)
- [Spec-Driven Development (Thoughtworks)](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [Agentic Property-Based Testing](https://arxiv.org/html/2510.09907v1)
- [Property-Based Testing and Kiro](https://kiro.dev/blog/property-based-testing/)
- [OpenHands: Open Platform for AI Software Developers](https://arxiv.org/abs/2407.16741)
- [OpenHands Software Agent SDK](https://arxiv.org/html/2511.03690v1)
- [CrewAI Memory Systems Deep Dive](https://sparkco.ai/blog/deep-dive-into-crewai-memory-systems)
- [AutoGen Group Chat](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/group-chat.html)
- [AutoGen Multi-Agent Conversation Framework](https://arxiv.org/pdf/2308.08155)
- [Tree-sitter Code Index: Cut AI Context Usage by 50x](https://dev.to/uwe_c_39d9ab7d16ff8dfe67e/how-i-cut-ai-context-usage-by-50x-with-a-tree-sitter-code-index-plm)
- [CodeGraph: Stop Your AI Agent From Grepping 50 Times](https://dev.to/arshtechpro/codegraph-stop-your-ai-agent-from-grepping-the-same-files-50-times-3bgm)
- [codedb: Zig code intelligence MCP server](https://github.com/justrach/codedb)
- [JSON Schema Output Enforcement for Agents](https://dev.to/dowhatmatters/output-format-enforcement-for-agents-json-schema-or-it-didnt-happen-1pbi)
- [MCP Automated Schema for AI Agents](https://auto-post.io/blog/automate-schema-for-ai-agents)
- [Agent Drift: Behavioral Degradation in Multi-Agent LLM Systems](https://arxiv.org/pdf/2601.04170)
- [Augment Code: Spec-Driven AI Code Generation](https://www.augmentcode.com/guides/spec-driven-ai-code-generation-with-multi-agent-systems)
- [Agent Experience Best Practices (marmelab)](https://marmelab.com/blog/2026/01/21/agent-experience.html)
- [FastAPI gRPC Stubs and ML Contracts](https://johal.in/fastapi-grpcio-tools-stub-code-generation-protos-ml-contracts-2025-13/)
