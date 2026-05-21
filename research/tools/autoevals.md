---
title: autoevals
aliases: [autoevals, braintrust-autoevals]
tags: [verify-kit, tools, llm-eval, llm-addon]
created: 2026-05-18
status: ALWAYS-SHIP-when-has_llm
layer: LLM Add-on
phase_introduced: Phase 5
---

# 🧪 autoevals

> [!abstract] One-line summary
> Pytest-native LLM scorers — factuality, relevance, JSON match, embedding similarity — without needing a Braintrust account.

## What it does

Provides a library of off-the-shelf eval scorers (factuality, relevance, semantic similarity, regex, JSON-shape) that return numeric scores. Each scorer is a Python function — drops into pytest assertions naturally. From Braintrust's OSS catalog; no SaaS dependency.

## Why we picked it

The default-shipping scorer library when `has_llm=true`. Chosen over:

| Alternative | Why rejected as default |
|---|---|
| `promptfoo` | Node binary + YAML config; opt-in only ([[tools/promptfoo]]) |
| `deepeval` | Pytest-native too, but Confident AI dashboard couples; opt-in |
| Roll-your-own | "You'll write a worse autoevals over six months" |

See [[agent-reports/wave-1-llm-eval-frameworks]].

## Usage in verify-kit

```python
# Generated project tests when has_llm=true
from autoevals import Factuality, NumericDiff

def test_summary_is_factual():
    scorer = Factuality()
    result = scorer(
        input="...",
        output=my_llm_summary("..."),
        expected="The original text says X about Y."
    )
    assert result.score > 0.8
```

Pairs with `vcrpy` for deterministic test runs (see [[tools/vcrpy]]).

## Install

```python
# In generated project deps when has_llm=true
"autoevals>=0.0.40",
```

## Gotchas

- **Scorers that call LLMs cost money** — pair every LLM-using scorer with `vcrpy` cassettes; budget per-call via `tokencost`
- **Threshold tuning** — start with `> 0.5` for soft asserts, tighten with eval data; don't expect 1.0 for natural-language matches
- **Multiple scorers per case** — combine `Factuality()` with cheap deterministic ones (`NumericDiff`, JSON regex) to catch obvious failures without spending tokens

## Key docs

- README: <https://github.com/braintrustdata/autoevals>
- Scorer catalog: see source `autoevals/__init__.py`

## Related notes

- [[00-stack-decisions#LLM Add-on]] — default-shipping slot
- [[tools/vcrpy]] — partner for deterministic eval runs
- [[tools/promptfoo]] — declarative alternative (opt-in)
- [[agent-reports/wave-1-llm-eval-frameworks]] — wave that picked this
