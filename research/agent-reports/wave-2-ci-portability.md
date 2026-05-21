---
title: CI-Portable Harness + Modern Testing Practices
aliases: [Wave 2 - CI, GitHub Actions vs Dagger, Modern Test Pyramid]
tags: [research, wave-2, ci, testing, github-actions, just]
wave: 2
source_agent: ci-modern-testing
created: 2026-05-17
---

# Portable Verification Harness & Modern AI Test Practices (2024–2026)

> [!abstract] Headline
> **GitHub Actions only, with `act` for local. "CI portability" is non-goal.** ~68% of OSS lives on GitHub; the thin-wrapper pattern (10 lines of YAML calling `just verify`) gives 95% of true portability anyway. Modern test stack converges on tiered AI eval: mocked unit + VCR integration + nightly live golden suite.

## 1. CI Portability — Actual Landscape

| Tool | What | Adoption | Fit | Tradeoff |
|---|---|---|---|---|
| **GitHub Actions** | YAML workflows tied to GitHub | ~68% of GitHub-hosted OSS in 2025; 11.5B public minutes/yr | Excellent if you accept lock-in | Vendor-coupled; YAML is worst part of every project |
| **[`act`](https://github.com/nektos/act)** | Run GH Actions workflows locally in Docker | Popular (~50k stars) | Good — handles ~90% of workflows | Skips macOS/Windows runners, services, `actions/cache`, OIDC; debugger not portability layer |
| **[Dagger.io](https://dagger.io/)** | Pipelines as code (Go/Python/TS) running in containers on any CI | Growing fast post-Earthly collapse | Excellent for "write once, run anywhere" | Learning curve; pulls into Dagger runtime; overkill for solo |
| **Earthly** | Container-native build DSL | **Discontinued July 2025** — repo maintenance mode | Avoid for new work | Company pivoted to "Earthly Lunar" AI guardrails |
| **GitLab CI / CircleCI / Jenkins** | Alternative providers | Combined < GH Actions in OSS; bigger in enterprise | N/A for solo OSS | Not where OSS contributors live |
| **[Devcontainers](https://containers.dev/)** | Reproducible dev environment spec | Supported by VS Code, JetBrains, Zed, Codespaces | Excellent as environment layer | Doesn't solve CI orchestration; only "where deps live" |

### Reality check on multi-CI portability

GitHub Actions runs ~68% of OSS projects on GitHub. For a solo developer's template, **building a Dagger or Earthly abstraction layer "in case I switch CI" is premature optimization** — realistic switching cost is rewriting one YAML file, not rebuilding pipelines.

The high-leverage portability pattern that *actually* matters is the **"thin CI wrapper" pattern**: all logic in command runner (`make verify`, `just verify`), `.github/workflows/ci.yml` is ~10 lines that call it. 95% of true portability with 5% of complexity.

## 2. The Modern Test Pyramid in 2025–2026

Pyramid not dead but **Trophy ([Kent C. Dodds, 2018](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications))** decisively won mindshare for API-centric and frontend-heavy apps. 2025 consensus from sources like [QAlified](https://qalified.com/blog/test-pyramid-for-engineering-teams/), [ankurm.com](https://ankurm.com/test-pyramid-vs-test-trophy/):

- **Pyramid** still right for domain-heavy code with complex business logic (compilers, ML, finance)
- **Trophy** wins for API/web apps where most bugs live at seams
- **Hybrid is what teams actually do**: many unit tests for tricky logic, many integration tests for flows, handful of E2E for critical paths, static analysis as wide base of trophy

### Modern primitives worth including

- **Property-based testing** ([Hypothesis](https://hypothesis.readthedocs.io/), [fast-check](https://fast-check.dev/)): Used by ~5% of Python devs (2023 survey), 6th-most-popular Python test framework. [2025 OOPSLA paper](https://cseweb.ucsd.edu/~mcoblenz/assets/pdf/OOPSLA_2025_PBT.pdf) shows improves test design even when bugs aren't found. Bake in `tests/properties/` slot with one example
- **Snapshot/golden testing**: Now standard for UI (React/Vitest), API responses, prompt outputs. Codify `tests/golden/` directory
- **Mutation testing** ([Stryker](https://stryker-mutator.io/), [mutmut](https://mutmut.readthedocs.io/), [Cosmic Ray](https://github.com/sixty-north/cosmic-ray)): Still niche. Stryker variants imported in ~500 repos total. Marginal for harness — too slow for CI, valuable as one-off audit. Add `just mutation-test` target but don't run by default
- **Contract testing** ([Pact](https://pact.io/)): Critical for microservice teams; overkill for solo

## 3. AI-Heavy App Testing (the real meat)

Synthesizing [PromptLayer](https://blog.promptlayer.com/llm-eval-framework/), [Datadog](https://www.datadoghq.com/blog/llm-evaluation-framework-best-practices/), [Confident AI](https://www.confident-ai.com/docs/llm-evaluation/core-concepts/test-cases-goldens-datasets), [Maxim](https://www.getmaxim.ai/articles/building-a-golden-dataset-for-ai-evaluation-a-step-by-step-guide/), and [arXiv 2507.21504](https://arxiv.org/html/2507.21504v1):

### Three-tier convention

1. **Unit-level (mocked)** — every PR. LLM client stubbed; assert on prompt structure, tool selection, retry logic, parser behavior. Fast (<1s), deterministic, no API spend.
2. **Integration with VCR cassettes** — every PR. Record-replay (`pytest-recording`, [VCR.py](https://vcrpy.readthedocs.io/), `nock`) plays back real API responses. Catches schema drift in tool outputs. Refresh weekly.
3. **Live eval suite (golden dataset)** — **nightly or on-demand**, NOT per-PR. Hits real APIs. Scored against expected outputs. The regression net.

### Golden datasets — the 2025 spec

- **Start small: 25–50 examples** ([Confident AI](https://www.confident-ai.com/docs/llm-evaluation/core-concepts/test-cases-goldens-datasets)). Each has `input`, `expected_output`, custom fields
- **Silver → Gold promotion**: synthetic = silver; SME-reviewed = gold
- **Version in git** alongside code. Pipeline configs and metrics thresholds are code
- **Coverage targets**: representative inputs + edge cases + known failure modes
- **Refresh quarterly** or when prompts/models change materially

### Non-determinism handling

- **Pin seed/temperature=0** for deterministic-mode tests where provider supports
- **Stochastic acceptance**: for inherently random outputs, run N trials and assert aggregate metrics ("85% of runs pass rubric") rather than single-shot equality
- **Flake budget**: teams reason about LLM tests with fail-rate threshold (e.g. "≤5% flakes acceptable"). When test exceeds budget, tighten prompt, raise temperature 0, or move from blocking to advisory
- **Cost guardrail**: cap live eval at $X per nightly run; print spend in report

## 4. Pre-commit vs CI: the Duplication Question

From [Sebastian Witowski](https://switowski.com/blog/pre-commit-vs-ci/), [Craig Motlin](https://motlin.medium.com/pre-commit-or-ci-cd-5779d3a0e566), and [Gatlen Culp's 2025 guide](https://gatlenculp.medium.com/effortless-code-quality-the-ultimate-pre-commit-hooks-guide-for-2025-57ca501d9835):

**Duplication is correct and intentional.** Pre-commit hooks can be skipped (`-n`); CI is the gate. The split that works:

| Layer | Pre-commit | CI | Both |
|---|---|---|---|
| Fast formatter (ruff, prettier) | yes | yes (re-check) | yes |
| Linter (ruff, eslint) | yes | yes | yes |
| Secret scan (gitleaks) | yes | yes | yes |
| Type check (pyright, tsc) | optional (slow) | yes | sometimes |
| Unit tests | no (too slow) | yes | no |
| Integration tests | no | yes | no |
| LLM live eval | no | nightly only | no |

**Rule of thumb**: anything >3 seconds belongs in CI only or `pre-push` hook, not `pre-commit`. Hook speed is #1 reason developers disable them.

## 5. Is `make` Back? Command-Runner Verdict

From [Applied Go](https://appliedgo.net/spotlight/just-make-a-task/), [LWN's Just review](https://lwn.net/Articles/1047715/), [mylinux.work](https://mylinux.work/guides/taskfile-vs-just-vs-make/), [Atomic Object](https://spin.atomicobject.com/just-task-runner/):

- **Make**: installed everywhere; tab-sensitive; awkward for non-build tasks. "Is back" sentiment real because of *ubiquity*, not ergonomics
- **[Just](https://github.com/casey/just)**: Rust binary, clean syntax, `just --list` discoverability, recipes can be any language. **Currently winning indie/OSS mindshare**. Now packaged in most distros
- **[Task](https://taskfile.dev/)**: Go binary, YAML syntax, checksum-based dependency tracking (better than make's timestamps). Wins for complex build graphs
- **[mise](https://mise.jdx.dev/)** tasks: tool-version manager + task runner; ascendant in polyglot projects

**2026 verdict for harness**: `just` is right default. Universally available, no tab traps, list-discoverable, can shell out to anything. Provide fallback `Makefile` shim with same target names for environments without `just`. Skip Task unless project has complex build DAG.

## 6. Devcontainers + Codespaces

Per [Ivan Lee's 2025 take](https://ivanlee.me/devcontainers-in-2025-a-personal-take/), [Mitchell Rysavy](https://www.mitchellrysavy.com/blog/2025/02/26/devcontainers.html), and [devcontainers spec](https://containers.dev/):

- **Spec adoption broad**: VS Code, JetBrains, Zed, Codespaces, GitPod, multiple CDEs
- **Codespaces uptake real but uneven**: enterprises and bootcamps love it; solo OSS devs use occasionally
- **For portable harness**: include `.devcontainer/devcontainer.json` as **optional** layer. Don't make mandatory. Most contributors run locally; devcontainer is "free insurance" for cloud envs and Windows users

## 7. Smoke Tests as First-Class Artifact

From [Datadog](https://www.datadoghq.com/blog/smoke-testing-synthetic-monitoring/), [New Relic](https://newrelic.com/blog/apm/smoke-testing-with-synthetic-monitors), [Harness](https://www.harness.io/harness-devops-academy/integrating-smoke-testing-into-your-ci-cd-pipeline-what-devops-needs-to-know):

Pattern now codified:

- **5–10 most critical user flows**, no more
- **Runs in <30 seconds**, against real (deployed) target
- **Single geographic region**, no exhaustive permutations
- **Go/no-go gate** — fail loud, fail fast, trigger rollback
- Tools: [Datadog Synthetics](https://docs.datadoghq.com/synthetics/), [Checkly](https://www.checklyhq.com/), [Playwright](https://playwright.dev/) as scheduled CI job, hand-rolled `curl` + assertions

For indie harness, **`just smoke` → shell script of curl calls + few Playwright steps** is right baseline.

## 8. The Convergent "Verify Everything" Command

No formal RFC, but convergent indie convention:

```
just verify   # lint + typecheck + unit + integration + smoke (against local) + secret-scan
just verify --quick   # skip slow tiers
just verify --full    # also run live LLM evals
```

CI calls `just verify`. Pre-commit calls `just verify --quick`. Deploy pipeline calls `just smoke` against just-deployed target. User types `just verify` and trusts result.

## Recommendation A — CI Strategy

**Pick GitHub Actions only, with `act` for local development. Treat "CI portability" as non-goal.**

Reasoning:
1. ~68% of OSS lives on GitHub; harness's target audience overwhelmingly ships there
2. Thin-wrapper pattern (`just verify` called by 10 lines of YAML) gives 95% of true portability — if you ever move CI, rewrite YAML in an hour
3. Dagger excellent technology but runtime dependency adding learning cost and abstraction debt without paying off for solo
4. Earthly is dead — its discontinuation cautionary tale about betting on opinionated meta-CI tools
5. Devcontainer + `just` is actual portability story: anyone, on any OS, can run same checks same way locally

Harness ships: `.github/workflows/{ci,nightly-eval,deploy-smoke}.yml` (thin), `justfile` (thick), `.devcontainer/devcontainer.json` (optional), `.pre-commit-config.yaml` (fast checks only).

## Recommendation B — Modern Test Stack

Harness ships these layers, all callable via `just`:

1. **Static** (`just lint`): ruff/eslint + pyright/tsc + gitleaks. Pre-commit + CI
2. **Unit** (`just test-unit`): pytest/vitest with LLM clients mocked. Fast (<10s), deterministic. Include `tests/properties/` slot with one Hypothesis/fast-check example
3. **Integration** (`just test-int`): VCR/nock cassettes for HTTP and LLM APIs. Cassettes versioned in git; refreshed weekly via `just refresh-cassettes`
4. **Golden** (`just test-golden`): snapshot tests for prompt outputs, API responses, UI components. Refresh via `just update-golden`
5. **E2E** (`just test-e2e`): Playwright, 3–5 critical user journeys only. CI but not pre-commit
6. **Smoke** (`just smoke [url]`): <30s post-deploy go/no-go. 5 curl/Playwright checks against deployed target
7. **AI eval** (`just eval`): nightly only. Golden dataset of 25–50 examples. Reports scores vs baseline, fails CI if regression beyond threshold. Cost cap enforced
8. **Mutation** (`just mutation`): on-demand quality audit, never in CI. Stryker/mutmut
9. **`just verify`** as top-level umbrella running 1–5 + 6-against-local. Aliased as `make verify` via Makefile shim

Defaults: temperature=0 + seed pinning for LLM unit tests; flake-budget config for stochastic tests (`pytest-flakefinder` or N-of-M assertions); `EVAL_BUDGET_USD` env var eval runner respects.

This stack reflects 2025–2026 industry consensus: pyramid for unit/integration base, trophy-style emphasis on integration, golden/snapshot as first-class peer, smoke as deploy gate, live AI evals quarantined to nightly so per-PR feedback stays fast and cheap.

## Sources

- [Dagger Earthly migration](https://dagger.io/blog/earthly-to-dagger-migration)
- [Just Make a Task (Applied Go)](https://appliedgo.net/spotlight/just-make-a-task/)
- [Just: a command runner (LWN)](https://lwn.net/Articles/1047715/)
- [Why the Test Pyramid Still Matters in 2025 (QAlified)](https://qalified.com/blog/test-pyramid-for-engineering-teams/)
- [Test Pyramid vs Test Trophy (ankurm.com)](https://ankurm.com/test-pyramid-vs-test-trophy/)
- [LLM Eval Framework (PromptLayer)](https://blog.promptlayer.com/llm-eval-framework/)
- [Building a Golden Dataset (Maxim)](https://www.getmaxim.ai/articles/building-a-golden-dataset-for-ai-evaluation-a-step-by-step-guide/)
- [LLM Evaluation Framework Best Practices (Datadog)](https://www.datadoghq.com/blog/llm-evaluation-framework-best-practices/)
- [nektos/act](https://github.com/nektos/act)
- [Pre-commit vs CI (Witowski)](https://switowski.com/blog/pre-commit-vs-ci/)
- [Pre-Commit Hooks Guide 2025 (Gatlen Culp)](https://gatlenculp.medium.com/effortless-code-quality-the-ultimate-pre-commit-hooks-guide-for-2025-57ca501d9835)
- [CI/CD Costs 2026 (LeanOps)](https://leanopstech.com/blog/ci-cd-pipeline-costs-github-actions-circleci-gitlab-2026/)
- [Devcontainers in 2025 (Ivan Lee)](https://ivanlee.me/devcontainers-in-2025-a-personal-take/)
- [Empirical Evaluation of PBT in Python (OOPSLA 2025)](https://cseweb.ucsd.edu/~mcoblenz/assets/pdf/OOPSLA_2025_PBT.pdf)
- [Stryker Mutator](https://stryker-mutator.io/)
- [Smoke Testing in CI/CD (Harness)](https://www.harness.io/harness-devops-academy/integrating-smoke-testing-into-your-ci-cd-pipeline-what-devops-needs-to-know)
- [Evaluation of LLM Agents Survey (arXiv 2507.21504)](https://arxiv.org/html/2507.21504v1)

## Related notes

- [[wave-2-polyglot-orchestration]] · [[wave-2-scaffolding-tools]] · [[wave-1-llm-eval-frameworks]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- [[tools/just]]
