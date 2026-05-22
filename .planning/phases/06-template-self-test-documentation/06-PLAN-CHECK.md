# Phase 6 Plan Check

**Reviewed:** 2026-05-22
**Reviewer:** gsd-plan-checker (Opus 4.7, 1M)
**Verdict:** PASS WITH WARNINGS — proceed to convergence
**Plans reviewed:** 06-01 through 06-10 + 06-WAVES.md (10 plans, 6 waves)
**Files read:** 06-CONTEXT.md, 06-WAVES.md, 06-RESEARCH.md (excerpts), 06-01..06-10 PLAN.md, ROADMAP.md (Phase 6), REQUIREMENTS.md (DOC-01..05), REVIEW-CHECKLIST.md, copier.yml (prompt names)

---

## Success criteria coverage (11 rows)

| # | Criterion | Plan(s) | Verifiable check present? | Verdict |
|---|-----------|---------|--------------------------|---------|
| 1 | `.github/workflows/template-selftest.yml` runs `copier copy` per matrix; fails PR on `just verify` ≠ 0 | 06-08 T1 | yes — YAML structural assertion + 5-combo matrix + `fail-fast: false` + `just verify` as last step (nonzero → job fail → workflow fail → PR fail by GHA default) | PASS (implicit fail-mode; see Cross-cutting I) |
| 2 | README quickstart-first, philosophy, add-on inventory, `copier update`, troubleshooting, dual-audience checklist; <30s to "verified" | 06-06 T1+T2+T3 | partial — quickstart, philosophy, add-on table, Mermaid, dual-audience, footer ALL asserted. **`copier update` walkthrough + troubleshooting section NOT in must_haves or task action list** | WARN — see HIGH #1 below |
| 3 | CHANGELOG SemVer + "Breaking changes for consumers" callout; CONTRIBUTING smoke-test loop + "add a check in 10 lines" | 06-05 T3 + 06-07 T1 | yes — CHANGELOG stub greps for "Breaking changes for consumers" + SemVer; CONTRIBUTING greps for smoke-test loop + `@register` snippet + commit contract | PASS |
| 4 | Architecture diagram (Mermaid or PNG) matching `research/00-architecture-overview.md` | 06-06 T2 | yes — Mermaid `flowchart TD` block with classDef shipped/deferred + all 5 slots asserted | PASS |
| 5 | Self-test workflow runs in `act` <10 min full matrix | 06-08 T3 | partial — act helper script ships; `--matrix combo:base` only (not full matrix). SUMMARY records operator's runtime as SC5 evidence | WARN — see HIGH #2 below |
| 6 | verify-kit-3u2: route auth scaffold (X-VerifyKit-Token) | 06-02 T1+T2+T3 | yes — APIKeyHeader + global Depends + secrets.compare_digest + `/healthz` exclusion + dev fallback + 4-cell polarity test; closes_beads frontmatter set | PASS |
| 7 | verify-kit-yr7: /summarize input-length cap + injection defenses | 06-03 T1+T2 | yes — Field(max_length=5000) + control-char strip + 3 injection markers + Content-Type via Pydantic + 8-case test | PASS |
| 8 | verify-kit-93h: /echo hardening | 06-04 T1+T2 | yes — Field(max_length=5000) + `_CONTROL_CHARS_ECHO` (distinct constant) + explicit no-denylist + forcing-function test for "no denylist on /echo" | PASS |
| 9 | verify-kit-1v6: Phase 5 README LLM human-read pass | 06-09 T1+T2 | yes — checkpoint:human-verify + Phase 5 polarity test regression guard + bd close in completion_checklist | PASS |
| 10 | Phase 4 secure-phase + validate-phase ceremonies | 06-10 T1+T2+T3 | yes — checkpoint-driven ceremony invocation + short-circuit path + new-beads-NOT-rolled-in policy + STATE.md flip with grep verify | PASS |
| 11 | OSS boilerplate (LICENSE, SECURITY.md, CoC, ISSUE_TEMPLATE/*, PR template) | 06-01 T1+T2 + 06-07 T2 | yes — all 6 files specified with content checks, attribution preserved, GHSA URL routed, PR template six rows verbatim | PASS |

**Coverage summary:** 9 PASS / 2 WARN / 0 BLOCKER on success-criterion axis.

---

## Cross-cutting findings (A–J)

### A. Cross-plan contract drift (REVIEW-CHECKLIST §3)
**Verdict: PASS.** WAVES.md §"Cross-wave contracts" enumerates every producer→consumer pair with the exact contract token. Spot-checks:
- 06-02 produces `from app.auth import require_auth` + env `VERIFYKIT_AUTH_TOKEN` + header `X-VerifyKit-Token`. 06-03, 06-04, 06-08 reference these exact symbols. ✓
- 06-03 produces `_INJECTION_MARKERS` and `SummarizeRequest` with Field(max_length=5000). 06-04 explicitly DOES NOT reuse `_INJECTION_MARKERS` (forcing-function test `test_echo_no_injection_marker_check` guards). ✓
- 06-03 vs 06-04 regex constant naming: deliberately decoupled (`_CONTROL_CHARS` vs `_CONTROL_CHARS_ECHO`) to avoid block coupling. ✓
- 06-05 produces conventional-commit contract; 06-07 quotes it verbatim. ✓
- 06-06 footer references files from 06-01 + 06-05 + 06-07 (sibling). ✓
- Copier prompt names (`has_backend`, `has_llm`, `has_logfire`, `has_fastapi_mcp`) verified to match `copier.yml` lines 151–167. ✓

### B. cwd leaks (REVIEW-CHECKLIST §1)
**Verdict: PASS.**
- 06-02 verify-step subprocess uses absolute `src='/Users/moiz/Documents/code/verify-kit'` — note this hard-codes operator path (see WARN #5).
- 06-06 record-cast.sh uses `HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` — absolute-resolved. ✓
- 06-08 act-validate script uses `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"` + `cd "$ROOT"`. ✓
- 06-08 workflow shell uses `$GITHUB_WORKSPACE` + `/tmp/scratch-${{ matrix.combo }}`. ✓
- 06-03 polarity test uses `tests/_helpers.py::_CLEAN_ENV` pattern (REVIEW-CHECKLIST §8). ✓

### C. Dead-code-via-narrative-ordering (REVIEW-CHECKLIST §2)
**Verdict: PASS.** Reviewed all `<action>` blocks. No statements positioned after a `return` line. Field-validators in 06-03 and 06-04 are explicit: clean `v` first, then `return v` at end (06-03 T1 action lines 119–127). ✓

### D. Wave dependencies satisfied
**Verdict: PASS.**
- W1 (06-01, 06-05, 06-10): all `depends_on: []`. ✓
- W2 (06-02): `depends_on: ["06-01"]` — but 06-02 frontmatter does not actually require any 06-01 artifact. **Minor over-declaration of dep — harmless** (forces sequential, no false coupling). NOTE: actually 06-02 ONLY needs Phase 4's landed `app/` code; 06-01 dep is artificially serializing W1→W2. WAVES.md is consistent.
- W3 (06-03, 06-04): both `depends_on: ["06-02"]`; share `api.py.jinja2` across disjoint Jinja blocks. WAVES.md §"parallel-with-care" note flags this and explicitly allows sequential execution as fallback. ✓
- W4 (06-06, 06-07): 06-06 `depends_on: ["06-01","06-02","06-03","06-04","06-05"]`; 06-07 `depends_on: ["06-05"]`. Both W4-eligible. ✓
- W5 (06-08): `depends_on: ["06-02","06-03","06-04"]`. ✓
- W6 (06-09): `depends_on: ["06-06"]`. ✓
- No cycles, no forward refs.

### E. Locked-decision honoring (D-01..D-17)
**Verdict: PASS.** Spot-check of every locked decision:
- D-01 5 rows Linux + nightly macOS — 06-08 T1+T2 ✓
- D-02 5 exact combo names base/backend/llm/backend-llm/full — 06-08 T1 verify ✓
- D-04 cron `0 4 * * 0` — 06-08 T2 verify ✓
- D-05 quickstart-first ordering — 06-06 T1 ✓
- D-06 asciinema GIF (NOT JS embed) — 06-06 T4+T5 + `! grep -q "<script"` ✓
- D-07 inline Mermaid — 06-06 T2 ✓
- D-08 IDE Problems-panel PNG — 06-06 T6 ✓
- D-09 six-row checklist in README — 06-06 T3 verbatim grep ✓
- D-10/D-11/D-12 release-please + Breaking-changes + SemVer — 06-05 + 06-07 ✓
- D-13 (a)(b)(c) CONTRIBUTING — 06-07 T1 ✓
- D-14 PR template checkbox, NO CI grep gate — 06-07 T2; no plan adds a grep gate ✓
- D-15 OSS boilerplate at root — 06-01 ✓
- D-16/D-17 6 hardening plans, one per item — 06-02, 06-03, 06-04, 06-09, 06-10 (audits combined per §10 lightweight-shape) ✓

No locked decision contradicted. No scope reduction language detected ("v1", "static for now", "future enhancement" used only for genuinely-deferred items per Deferred Ideas).

### F. act-local validation (ROADMAP SC5)
**Verdict: WARN.** 06-08 T3 provides `act-validate-selftest.sh` but runs `--matrix combo:base` only, not the full matrix. SC5 reads: "workflow runs end-to-end in `act` locally and finishes in under 10 minutes for the **full matrix**". The plan acknowledges this gap (`§11 Pitfalls: full-matrix in act takes ~30 min on M2 and is overkill`) and documents the choice in SUMMARY, but it does not formally satisfy SC5 verbatim. See HIGH #2.

### G. Beads closure ordering
**Verdict: PASS.** Each bead-closing plan has `closes_beads:` frontmatter AND a `bd close <id> --reason="..."` line in `<completion_checklist>`:
- 06-02 → verify-kit-3u2 ✓
- 06-03 → verify-kit-yr7 ✓
- 06-04 → verify-kit-93h ✓
- 06-09 → verify-kit-1v6 ✓
- WAVES.md "Beads closed at phase completion" table matches frontmatter.

### H. Phase 4 audit short-circuit
**Verdict: PASS.** 06-10 T1+T2 both explicitly cite the short-circuit path: existing 04-SECURITY.md `status: verified, threats_open: 0`; existing 04-VALIDATION.md 435 lines; ceremonies update-in-place per §10. The "new beads NOT rolled into Phase 6" policy is explicit. STATE.md flip in T3 is grep-verified.

### I. DOC-04 acceptance: workflow FAILS PR on `just verify` ≠ 0
**Verdict: PASS with WARN.** 06-08 T1 asserts the YAML structure (matrix + steps + `fail-fast: false`) but does NOT explicitly add a negative-path test that proves a deliberately-broken `just verify` causes job failure. This is implicit by GHA semantics (nonzero exit → step fail → job fail → required check fail → PR block). Conventional for workflow files. Acceptable. **Suggestion (LOW):** add a `# REGRESSION-GUARD:` comment in the workflow header naming that the LAST step's exit code IS the PR gate.

### J. Path-gating: new template files ungated vs per-add-on
**Verdict: PASS.**
- LICENSE, CODE_OF_CONDUCT.md, SECURITY.md, ISSUE_TEMPLATE/*, PR template, README.md, CHANGELOG.md, CONTRIBUTING.md, release-please-config.json, `.release-please-manifest.json`, both workflows — ALL at repo root (06-01 constraints make this explicit: "These files describe the verify-kit project itself; they live at repo root (NOT under `template/`)"). ✓
- The auth scaffold (06-02) IS path-gated via `template/{% if has_backend %}app{% endif %}/auth.py.jinja2`. ✓
- `.env.example` variants (06-02 T3) honor existing 05-01 D-04 two-variant gating (`{% if has_backend and not has_llm %}` vs `{% if has_llm %}`). ✓

No two-guard rule (Phase 4 §3) violations.

---

## HIGH concerns (blocking before convergence OR fixable inline by planner)

### HIGH #1 — README missing `copier update` walkthrough + troubleshooting section
**Plan:** 06-06
**File:** `.planning/phases/06-template-self-test-documentation/06-06-PLAN.md:108-122` (Task 1) and `:166-219` (Task 3)
**Evidence:** ROADMAP SC2 enumerates 6 README contents: (a) philosophy, (b) one-command quickstart, (c) add-on inventory, (d) `copier update` path, (e) troubleshooting, (f) dual-audience checklist. CONTEXT.md "Specific Ideas" line 116 also lists: "... → `copier update` walkthrough → troubleshooting → link to CONTRIBUTING.md". 06-06 Task 1 covers (a)(b)(c)(f); Task 3 covers (f) + Security + footer links. Neither (d) `copier update` walkthrough nor (e) troubleshooting appear in any task action or `must_haves.truths`. The README skeleton lists them in CONTEXT.md but the plan does not enumerate them as deliverables.
**Severity:** HIGH — DOC-01 success criterion #2 is not provably satisfied. A reader would not get the `copier update` migration path.
**Fix:** Either (a) add a Task 3.5 / extend Task 3 action to append `## Updating an existing project` (with `copier update` command + how Breaking-changes-for-consumers section in CHANGELOG informs the update) AND `## Troubleshooting` (3–5 common issues: missing mise, copier update merge conflicts, just-verify exit codes), OR (b) extend Task 1 action's section list to include these two H2s. Add to `must_haves.truths` and Task 3 `<verify>` grep loop.

### HIGH #2 — SC5 act-full-matrix requirement under-delivered
**Plan:** 06-08
**File:** `.planning/phases/06-template-self-test-documentation/06-08-PLAN.md:202-228` (Task 3)
**Evidence:** ROADMAP SC5 verbatim: "template-selftest workflow runs end-to-end in `act` locally and finishes in under 10 minutes for the **full matrix**, gating every PR before merge." Plan ships only `--matrix combo:base` validation with a comment "full-matrix in act takes ~30 min on M2 and is overkill". The plan's SUMMARY captures operator's runtime as SC5 evidence — but the script does not actually run the full matrix.
**Severity:** HIGH — formal SC5 satisfaction is ambiguous. Either the criterion needs renegotiation in CONTEXT.md as a locked decision (which currently it is NOT; no D-XX overrides SC5), or the script must support a `--full` mode that runs all 5 combos.
**Fix options:**
  1. **Preferred:** add a `--full` flag to `act-validate-selftest.sh` that drops the `--matrix combo:base` filter, run it once during operator validation, and record actual runtime in SUMMARY. If <10 min: SC5 satisfied. If >10 min: file a beads issue and update ROADMAP SC5 to reflect reality.
  2. **Alternative:** lock a CONTEXT.md amendment that SC5 is interpreted as "base combo via act locally + full matrix via real GHA runners" — but this is a scope renegotiation, not a planning issue, and should be surfaced to the user before convergence runs.

---

## MEDIUM concerns (should fix before execute; convergence may handle some)

### MED #3 — README footer link to CONTRIBUTING.md ships broken if 06-06 lands before 06-07
**Plan:** 06-06 Task 3 + 06-07
**File:** 06-06-PLAN.md:188-192, 211-214 (verify allows CONTRIBUTING.md to be absent)
**Evidence:** Both are W4. If 06-06 commits before 06-07, the README footer has a dead link until the same wave finishes. Plan explicitly allows it ("Task 3's verify step is allowed to skip this one assertion"). Acceptable for parallel execution within a wave, but downstream PR review would surface the dead link.
**Fix:** Either (a) declare 06-07 a hard dependency of 06-06 (sequential within W4 — small wave-time cost), OR (b) add a Wave-end forcing-function check that after both W4 plans land, the README footer link resolves. Add to 06-PLAN-CHECK or to a wave-completion gate.

### MED #4 — Mermaid `flowchart TD` syntax-validation only by regex (not by mermaid-cli)
**Plan:** 06-06 Task 2
**File:** 06-06-PLAN.md:148-160
**Evidence:** Verify step greps for `flowchart TD` + `classDef shipped` + node names. It does NOT actually render the Mermaid via `mmdc` (mermaid-cli) or `mermaid-py` to catch syntax errors that grep wouldn't (e.g., mismatched `end` blocks, illegal classDef syntax, broken arrow syntax).
**Severity:** MEDIUM — GitHub renders Mermaid server-side; a syntax error shows as "Unable to render diagram" in the README preview, defeating D-07's "single source of truth" intent.
**Fix:** Add to Task 5 (human checkpoint) or as a new auto-verify step: render the Mermaid block via `mmdc -i README.md -o /tmp/arch.svg` (mermaid-cli, npm-install) OR open the README in GitHub preview during Task 5 checkpoint and explicitly confirm the diagram renders.

### MED #5 — 06-02 verify step hard-codes operator absolute path
**Plan:** 06-02 Tasks 1, 2 (verify blocks)
**File:** 06-02-PLAN.md:128, 167 (`src='/Users/moiz/Documents/code/verify-kit'`)
**Evidence:** Verify-step Python uses `src='/Users/moiz/Documents/code/verify-kit'` as the copier source. Identical hard-coding in 06-03 line 141 and 06-04 line 127. This works on the operator's machine but not in CI (where the workflow checks out to `$GITHUB_WORKSPACE`) or for any other contributor.
**Severity:** MEDIUM — these are plan verify-steps the executor runs locally, not CI. They will work for the current operator (who matches the path) but break the principle of reproducibility. Since `just verify` / CI never runs these inline-Python verifications, this is a soft warning, not a CI break.
**Fix:** Replace `src='/Users/moiz/...'` with `src=os.environ.get('VERIFY_KIT_ROOT', os.getcwd())` or use a heuristic `src=str(pathlib.Path.cwd())`. Alternatively, accept the operator-pinning and document it in the SUMMARY.

### MED #6 — 06-02 dev-mode fallback ambiguity when BOTH token set AND env=dev
**Plan:** 06-02 + 06-08
**Evidence:** 06-02 contract: "If VERIFYKIT_AUTH_TOKEN unset AND settings.env == 'dev', request is allowed." 06-08 matrix sets BOTH `VERIFYKIT_AUTH_TOKEN=dev-token-for-tests` AND `ENV=dev`. With token set, env=dev does NOT confer the fallback — requests without the header still return 401. `just verify` inside the scratch project likely doesn't exercise HTTP endpoints (it runs lints/tests/builds), so this is harmless in CI but could surprise downstream agents who read 06-08 SUMMARY and assume "ENV=dev" alone is enough.
**Severity:** MEDIUM — documentation clarity, not functional break.
**Fix:** 06-08 SUMMARY (per the plan's own `<output>` block) should explicitly document: "ENV=dev is set defensively; VERIFYKIT_AUTH_TOKEN takes precedence when set". README (06-06) Security section similarly should clarify token-set-trumps-dev-fallback.

---

## LOW / informational

### LOW #7 — §Open Questions in 06-RESEARCH.md is NOT marked `(RESOLVED)`
**Evidence:** 06-RESEARCH.md line 918: `## Open Questions for the Planner` — no `(RESOLVED)` suffix; questions 1–8 listed with "Recommendation:" replies but no per-question RESOLVED marker. Dimension 11 (Research Resolution) of the plan-check protocol expects either the section heading or each question to carry RESOLVED.
**Severity:** LOW — every question has an inline recommendation that was respected by the plan (Q1→06-10 short-circuit, Q2→docs/casts/, Q3→in-route override, Q4→D-07 locked, Q5→either deliverable accepted in 06-09, Q6→data-file form chosen in 06-08, Q7→0.0.0 manifest in 06-05, Q8→Option A hardcoded in 06-07). Recommendation rather than blocker because plans demonstrably address each item.
**Fix:** Rename section to `## Open Questions for the Planner (RESOLVED)` and append `RESOLVED: <answer>` per question. Cosmetic.

### LOW #8 — 06-02 over-declares `depends_on: ["06-01"]`
**Evidence:** 06-02 frontmatter says `depends_on: ["06-01"]` but 06-02 doesn't reference any 06-01 artifact. WAVES.md groups 06-01 in W1 and 06-02 in W2 — the dep enforces sequential ordering. Harmless but artificially serializes work.
**Fix:** Set `depends_on: []` on 06-02. WAVES.md updates needed (06-02 becomes W1).

### LOW #9 — Asciinema cast cwd-sensitivity inside record-cast.sh recording session
**Evidence:** 06-06 Task 5 checkpoint script instructs recording: `cd /tmp && rm -rf cast-demo && copier copy --trust --defaults gh:m2moiz/verify-kit cast-demo && cd cast-demo && just verify`. The `gh:m2moiz/verify-kit` reference fetches from GitHub at recording time, not the local working-tree (the cast won't reflect uncommitted changes). Acceptable: cast represents post-merge consumer experience.
**Fix:** None needed. Document in 06-06 SUMMARY that the cast intentionally records the gh: form, not the local repo.

### LOW #10 — REVIEW-CHECKLIST §4 forcing-functions strong in 06-07 but absent in 06-02/03/04 main-py edits
**Evidence:** 06-07 explicitly greps `! grep -q "@register_check\|CheckResult(ok="` to catch plan API-surface drift. 06-02 reads main.py / settings.py / api.py via `<read_first>` blocks but does not GREP-ASSERT the negation (e.g., "no leftover Phase 4 patterns inadvertently broken"). The full-file `<read_first>` is the planner's mitigation. Acceptable, but a regression test that runs the full Phase 4 polarity test post-edit (06-02 completion_checklist line 264) covers it.
**Fix:** None — completion checklist already runs `tests/test_phase04_scaffold_polarity.py`.

---

## Recommendation

**PROCEED to `/gsd:plan-review-convergence 6 --codex --max-cycles 3`** with HIGH #1 and HIGH #2 fixed manually first OR fed to the convergence loop as known concerns.

**Manual-fix-first path (recommended):**
1. Patch 06-06 Task 1+3 to add `## Updating an existing project` (with `copier update`) and `## Troubleshooting` sections. Add to `must_haves.truths` and Task 3 verify grep. (~10 min)
2. Decide on HIGH #2 with the user before running convergence: either extend `act-validate-selftest.sh` with `--full` flag, OR amend CONTEXT.md with a new D-XX clarifying SC5 reads "act-local for `base` + GHA-cloud for full matrix". (~5 min decision + 5 min implementation)
3. Then run `/gsd:plan-review-convergence 6 --codex --max-cycles 3` to catch any residual drift.

**Direct-to-convergence path (acceptable):**
- Convergence's Codex reviewer should catch HIGH #1 on first pass (it's a verbatim ROADMAP SC2 gap).
- HIGH #2 is a scope/interpretation issue Codex may flag as ambiguous; user judgment required either way.

**Expected convergence cycles:** 1–2 (most cross-cutting concerns are already addressed by the plan's REVIEW-CHECKLIST §1/§2/§3/§5/§6/§7/§8 self-references and WAVES.md cross-contract register; the structural quality is high). Per `08-plan-convergence-workflow.md`, oscillation diagnostic doesn't apply yet.

**Do NOT proceed to `/gsd:execute-phase 6` until HIGH #1 is fixed and HIGH #2 is decided.**
