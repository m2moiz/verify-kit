## Summary

<!-- 1-3 sentences: what changes, why -->

## Test plan

<!-- How was this verified? `just verify` output? Specific scenarios? -->

## Dual-audience checklist

Every change must answer all six rows. Tick each. If a row is N/A for this PR, write "N/A — <reason>" in the box.

- [ ] **1. Human in terminal sees:** Pretty colorized output via isatty; spinner; failed checks summarized with one-line next-action hint.
- [ ] **2. Human in VS Code sees:** SARIF in Problems panel, JUnit in Testing sidebar — no agent involvement required.
- [ ] **3. Agent calling programmatically gets:** Deterministic JSON with stable schema (introspectable via `describe`), error envelope `{code, message, hint, fix_command, docs_url}`, semantic exit codes.
- [ ] **4. Agent has a fix path:** Failed check returns `fix_command`; `fix_propose` MCP tool returns unified diff with rationale; agent can re-verify without human round-trip.
- [ ] **5. Human can override agent:** Every fix is `--dry-run`-able; destructive MCP tools annotated `destructiveHint: true`; Stop-hook escape hatch (`VERIFY_KIT_SKIP=1`); audit log in `.verify-kit/audit.jsonl`.
- [ ] **6. Both can collaborate mid-flow:** Same `verify-kit trace --last` works for both; state file-backed in `.verify-kit/` so human can `cat` while agent runs.

## Conventional-commit type

<!-- One of: feat / fix / chore / docs / refactor / perf / test (use `feat!:` for breaking) -->

## Breaking changes for consumers

<!-- If this changes any Copier prompt, rendered file path, or generated-project API: describe the migration step for users running `copier update`. Otherwise: "None." -->
