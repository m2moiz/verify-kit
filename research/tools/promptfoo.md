---
title: Promptfoo
aliases: [promptfoo]
tags: [verify-kit, tools, llm-eval, llm-addon, opt-in]
created: 2026-05-18
status: OPT-IN
layer: LLM Add-on
phase_introduced: Phase 5
---

# 🧪 Promptfoo

> [!abstract] One-line summary
> Declarative YAML-driven LLM evaluation framework — runs scorers against golden datasets in CI.

## What it does

Promptfoo runs a YAML-defined eval matrix: a set of prompts × a set of providers × a set of scorers (factuality, regex, JS function, LLM-as-judge, etc.). Outputs structured pass/fail reports. Pairs well with cost caps for nightly CI runs.

## Why we picked it (as opt-in)

The default LLM add-on path uses `autoevals` (pytest-native scorers, no extra binary). Promptfoo is offered as an opt-in via Copier prompt `--promptfoo` when:

- You want a declarative YAML config divorced from Python test files
- You want CI-friendly cost capping with `EVAL_BUDGET_USD`
- You want a web UI for comparing prompt variants

| Alternative | Why opt-in rather than default |
|---|---|
| `autoevals` (default) | Already pytest-native; no Node binary required for default install |
| `deepeval` | Pytest-native + Confident AI dashboard; also opt-in |

## Usage in verify-kit (when opted in)

```yaml
# eval/promptfoo.yaml
prompts:
  - "Summarize: {{text}}"
providers:
  - openai:gpt-4o-mini
  - anthropic:claude-haiku-4-5
tests:
  - vars:
      text: "..."
    assert:
      - type: factuality
        value: "..."
      - type: cost
        threshold: 0.001
```

Phase 5 wires:
- `just eval` recipe running `promptfoo eval -c eval/promptfoo.yaml`
- `nightly-eval.yml` GitHub Action with `EVAL_BUDGET_USD` cap

## Install

```bash
# Node binary
npm install -g promptfoo

# Or pnpm dlx (preferred in verify-kit)
pnpm dlx promptfoo eval -c eval/promptfoo.yaml
```

## Gotchas

- **Node binary** — only opt-in when project already has Node or `pnpm dlx` is acceptable
- **Provider keys** — needs `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. in env; respect the `--env-path .env` flag for project-local secrets
- **Cost caps are enforced before eval runs** — exceeding `EVAL_BUDGET_USD` makes the run refuse to start (not stop mid-run)

## Key docs

- Getting started: <https://www.promptfoo.dev/docs/getting-started/>
- YAML config reference: <https://www.promptfoo.dev/docs/configuration/guide/>
- Assertions catalog: <https://www.promptfoo.dev/docs/configuration/expected-outputs/>

## Related notes

- [[00-stack-decisions#LLM Add-on]] — opt-in slot
- [[tools/langfuse]] — observability backend (traces complement evals)
- [[tools/autoevals]] — the default-shipping pytest-native alternative
- [[agent-reports/wave-1-llm-eval-frameworks]] — comparison wave
