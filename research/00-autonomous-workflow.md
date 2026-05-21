---
title: Autonomous Multi-Agent Workflow (Claude + Codex)
aliases: [Autonomous, Overnight, Claude+Codex, Multi-Agent]
tags: [verify-kit, autonomous, multi-agent, synthesis]
created: 2026-05-17
status: ready-to-use
---

# 🤖 Autonomous Multi-Agent Workflow

> [!abstract] The pattern that ships
> **Isolated worktrees per agent + deterministic verifier as trust anchor + LLM judge as scope-creep guard + human at PR review.** This is what Spotify Honk, Cursor 2.0, Anthropic's research system, and Factory.ai all converged on independently. The solo-dev version is two worktrees, a `VERIFY.sh`, a judge prompt, and a Ralph loop with budget caps.

## The architecture

```
                     ┌───────────────────────────────────────────┐
                     │              STATE.md (append-only)        │
                     │   read by: Claude    written by: loop      │
                     └───────────────────────────────────────────┘
                              ▲                          │
              writes STATE    │                          │ reads
                              │                          ▼
   ┌──────────────────┐   PLAN.md     ┌──────────────────────────┐
   │   CLAUDE (-p)    │──────────────▶│       PLAN.md             │
   │   ARCHITECT      │   writes      │   read by: Codex          │
   │   plans next     │               └──────────────────────────┘
   │   atomic task    │                          │
   │   never edits    │                          ▼
   │   source         │               ┌──────────────────────────┐
   └──────────────────┘               │  CODEX exec --cd worktree│
        ▲                              │  IMPLEMENTER             │
        │ STATUS=DONE                  │  picks next [ ] task,    │
        │ ends loop                    │  edits, runs VERIFY.sh,  │
        │                              │  commits on green        │
        │                              └──────────────────────────┘
        │                                          │
        │    appends         ┌───────────────────────────────┐
        └────────────────────│ PHASE-EXEC-NOTES.md +         │
                             │ CODEX-LAST.md + git commits   │
                             └───────────────────────────────┘
                                         │
                              loop back to Claude → Verify

Transitions:
  Claude.Stop hook → checks PLAN.md exists → launches codex exec
  codex exit 0     → loop continues
  codex exit 2     → loop continues, Claude sees partial in STATE.md
  codex exit 1     → loop breaks, human triage
  STATUS=DONE      → loop breaks, success

Failure modes:
  • Codex hangs                   → wrap in `timeout 30m codex exec ...`
  • Both commit to same branch    → prevented by worktree on `codex/work`
  • Budget blown                  → token-counting jq filter exits 1
```

## The shared contract (`.agents/` directory)

| File | Written by | Read by | Purpose |
|---|---|---|---|
| `AGENTS.md` | You | Every agent | House rules read at start of every loop |
| `SPEC.md` | You (before bed) | Both | The goal for this run |
| `PLAN.md` | Claude (architect) | Codex | Current atomic task |
| `TASKS.md` | Both | Both | Checkbox checklist as message bus |
| `VERIFY.sh` | You | Both | Deterministic gate (`just verify`) |
| `JUDGE_PROMPT.md` | You | Verifier | LLM judge instructions |
| `STATE.md` | Loop | Claude | Append-only progress |
| `PHASE-EXEC-NOTES.md` | Codex | Claude | What shipped, what blocked |
| `events.ndjson` | Loop | Both | Audit log |

> [!important] Filesystem is the message bus
> NEVER let agents talk peer-to-peer. Every handoff goes through a file commit. Git history IS your event log; reflog is your audit trail.

## Decomposition (Aider Architect/Editor pattern)

- **Claude Code = Architect.** Reads `SPEC.md`, updates `PLAN.md` and `TASKS.md`. Never edits source. (30–50% cheaper than running strong model end-to-end.)
- **Codex CLI = Implementer.** Reads `PLAN.md` + `TASKS.md`, edits source in its worktree, runs `VERIFY.sh`, commits on green.
- **Verifier loop** (also Claude Code, separate cheap-model invocation, headless): on every commit, runs `VERIFY.sh`; if green, runs LLM judge against `SPEC.md`; if judge says PASS, opens a PR; if FAIL, appends reason to `TASKS.md` as new task.

## Headless invocations

### Claude headless
```bash
claude -p "Read .agents/STATE.md. Goal: $GOAL. Write next atomic task to PLAN.md. If goal met, write DONE to .agents/STATUS." \
  --output-format stream-json \
  --dangerously-skip-permissions
```

### Codex headless (the safe-but-autonomous flags)
```bash
codex exec \
  --cd "$WT" \                            # work in worktree
  --sandbox workspace-write \             # process-level isolation
  --ask-for-approval never \              # autonomous
  --skip-git-repo-check \
  --json \                                # NDJSON event stream
  --output-last-message "$OUT" \          # final message to file (handoff goldmine)
  --output-schema schema/exec-result.json \  # force JSON Schema conformance
  "$PROMPT"
```

> [!warning] NEVER use `--dangerously-bypass-approvals-and-sandbox` (`--yolo`) outside a container
> That + no budget cap + auto-push to main = the **$50k Claude Code recursion incident from July 2025**. 1.67B tokens. Don't.

## The shortest overnight loop (copy-paste)

```bash
#!/usr/bin/env bash
# scripts/overnight.sh
set -euo pipefail
GOAL="${1:?usage: ./overnight.sh \"goal text\"}"
MAX_ITERS=20
MAX_USD=15
REPO="$(git rev-parse --show-toplevel)"
WT="$REPO/.worktrees/codex"
git worktree add -B codex/work "$WT" main 2>/dev/null || true
mkdir -p "$REPO/.agents"
ITER=0

while (( ITER < MAX_ITERS )); do
  ITER=$((ITER+1))
  echo "=== iteration $ITER/$MAX_ITERS ==="

  # 1. Claude plans into PLAN.md
  claude -p "Read .agents/STATE.md. Goal: $GOAL.
Write the next atomic task to PLAN.md. If goal is met, write DONE to .agents/STATUS." \
    --output-format stream-json --dangerously-skip-permissions \
    | tee -a .agents/claude.log >/dev/null

  [[ -f .agents/STATUS && "$(cat .agents/STATUS)" == "DONE" ]] && break

  # 2. Codex executes PLAN.md in the worktree
  timeout 30m codex exec --cd "$WT" --sandbox workspace-write --ask-for-approval never \
    --json -o "$REPO/.agents/CODEX-LAST.md" \
    "Read $REPO/PLAN.md. Execute task-by-task with atomic git commits on branch codex/work.
When done, append a dated section to $REPO/.agents/PHASE-EXEC-NOTES.md describing what shipped,
what failed, and what you'd hand back. Exit 0 on success, 2 on partial, 1 on failure." \
    2>>.agents/codex.log
  CODEX_RC=$?

  # 3. Update shared STATE.md for Claude's next iteration
  {
    echo "## $(date -Iseconds) codex rc=$CODEX_RC iter=$ITER"
    cat .agents/CODEX-LAST.md
  } >> .agents/STATE.md

  git -C "$WT" push origin codex/work || true
  (( CODEX_RC == 1 )) && { echo "Codex hard-failed"; break; }
done

# Notification
osascript -e "display notification \"overnight loop done after $ITER iters\" with title \"verify-kit\"" || true
```

Run: `nohup ./overnight.sh "make tests pass without changing public API" >/tmp/overnight.log 2>&1 &`

## GSD-native autonomous flow (already installed)

GSD v1.42.3 has built-in autonomous + cross-AI features:

```bash
# One-time setup (DONE on 2026-05-17)
gsd-sdk query config-set workflow.plan_review_convergence true
gsd-sdk query config-set review.default_reviewers '["codex"]'
npx get-shit-done-cc@latest --codex --global  # GSD skills for Codex CLI

# Per-phase workflow
/gsd:plan-review-convergence 1 --codex --max-cycles 3   # plan + Codex review until APPROVED
/gsd:autonomous --from 1 --to 2                          # execute phases in subagents
/gsd:verify-work                                         # UAT
/gsd:ship                                                # PR
```

## Stop-hook for cross-AI plan review

`.claude/hooks/codex-review.sh` — Codex adversarially reviews Claude's latest PLAN.md on every Stop:

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
# Guard against infinite loop — REQUIRED
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

# Cap iterations per session
STATE_DIR="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/state"
mkdir -p "$STATE_DIR"
COUNTER="$STATE_DIR/codex-review-count"
COUNT=$(cat "$COUNTER" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 5 ]; then
  osascript -e 'display notification "Codex review cap hit — human needed" with title "GSD"' || true
  exit 0
fi
echo $((COUNT + 1)) > "$COUNTER"

# Find latest PLAN.md
PLAN=$(ls -t .planning/phases/*/[0-9]*-PLAN.md 2>/dev/null | head -1)
[ -z "$PLAN" ] && exit 0

# Run Codex in isolated worktree
WORKTREE="/tmp/codex-review-$$"
git worktree add -q "$WORKTREE" HEAD 2>/dev/null || exit 0
trap 'git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true' EXIT

REVIEW=$(cd "$WORKTREE" && timeout 600 codex exec -m gpt-5.3-codex -s read-only \
  "Adversarially review $PLAN against .planning/PROJECT.md and .planning/REQUIREMENTS.md.
   List HIGH-severity concerns only. End reply with exactly one line:
   VERDICT: APPROVED   or   VERDICT: REVISE" 2>&1 || echo "VERDICT: APPROVED")

if echo "$REVIEW" | grep -q "VERDICT: REVISE"; then
  REASON=$(echo "$REVIEW" | sed -n '/VERDICT:/!p' | tail -50)
  jq -n --arg r "Codex review found HIGH concerns:\n\n$REASON" \
        '{decision:"block", reason:$r}'
  exit 0
fi

rm -f "$COUNTER"   # APPROVED — reset counter
exit 0
```

Register in `.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/codex-review.sh",
        "timeout": 900
      }]
    }]
  }
}
```

## Anti-patterns to avoid by name

> [!danger] Three anti-patterns from research wave 5
> 1. **Peer-to-peer agent messaging.** Infinite loops + cost explosions live here. Force every handoff through a file commit. Filesystem is the bus.
> 2. **One agent doing both architect AND implementer roles.** Loses Architect/Editor cost+quality win; judge has nothing independent to compare against.
> 3. **`--dangerously-skip-permissions` + no budget cap + auto-push to main.** The $50k recursion incident vector. Always cap iterations, always cap USD, always push to a feature branch.

## Honest assessment for fully autonomous overnight

**Realistic with 2026 tooling:**
- Plan + Codex review convergence for 2–3 phases (high confidence)
- Execute a single well-spec'd phase with Stop-hook gate (medium-high confidence)
- Ralph-loop a tightly-scoped slice with clear DONE criteria + comprehensive tests (medium confidence)

**Still needs the human:**
- `SPEC.md` quality before bed (highest leverage move)
- Grey-area accept/reject decisions GSD pauses for
- Anything touching secrets, infra, destructive git ops
- Multi-phase architectural decisions
- Morning PR review (NEVER auto-merge to main)

**Failure recovery at 3am:**
- `MAX_ITERS=20`, `MAX_USD=15` hard caps in `overnight.sh`
- `timeout 6h` wrapper on whole session
- Run in worktree → if broken, `git worktree remove` loses compute not code
- `osascript` notification + `gh issue create` on cap-hit
- Eval gate before merge: `just verify` must exit 0

## Tools installed for this workflow

- ✅ **claude-squad** (`cs`) at `/Users/moiz/.local/bin/cs` — tmux + worktree per agent
- ✅ **codex** v0.130 at `/opt/homebrew/bin/codex`
- ✅ **claude** v2.1.143
- ✅ **GSD for Codex** — `npx get-shit-done-cc@latest --codex --global` installed
- ✅ **just**, **mise**, **fswatch**, **jq**, **tmux**, **gh**, **uv** all present
- ✅ GSD config: `workflow.plan_review_convergence=true`, `review.default_reviewers=["codex"]`

## Related notes

- [[wave-5-multi-agent-case-studies]] — Spotify Honk, Cursor 2.0, Aider, Ralph loop case studies
- [[wave-5-coordination-primitives]] — git worktrees, jj, beads, message buses
- [[wave-5-claude-codex-mechanics]] — full `codex exec` flag reference, dux, oh-my-hermes, relay
- [[wave-5-gsd-autonomous]] — GSD autonomous + cross-AI features
- [[tools/claude-squad]] — multi-agent worktree+tmux orchestrator
- [[00-architecture-overview]] — verify-kit architecture
