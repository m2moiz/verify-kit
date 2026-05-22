---
title: "Cost double-tokenization — re-tokenize vs read the provider's billed usage"
aliases: [cost-double-tokenization, litellm-completion-cost, tokencost-vs-litellm]
tags: [verify-kit, learnings, atomic, llm, observability, code-review]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Cost double-tokenization — re-tokenize vs read provider usage

> [!abstract] Pattern
> When you have a `response` object from `litellm.completion(...)`, it already contains the provider's reported `usage.prompt_tokens` + `usage.completion_tokens`. If you also call `tokencost.calculate_prompt_cost(string, model)` on the raw prompt string, you'll **re-tokenize the prompt with tokencost's own tokenizer**, which can differ from the provider's. The cost you report drifts from the actual billed cost. Use `litellm.completion_cost(completion_response=response)` instead — it reads the provider's billed usage block.

## The incident this came from

`/gsd:code-review 5` finding **WR-04** (warning, not critical, but a real behavior bug):

> The call_via_litellm function calls `tokencost.calculate_*_cost(string, model)` which re-tokenizes, ignoring the provider-reported usage block — `verify_kit.cost_usd` drifts from actual billed cost. Should use `litellm.completion_cost(completion_response=response)`.

### Before (buggy)

```python
# template/harness/{% if has_llm %}llm.py{% endif %}.jinja2 — pre-WR-04 fix
cost_usd = 0.0
try:
    from tokencost import (
        calculate_completion_cost,
        calculate_prompt_cost,
    )
    prompt_cost = calculate_prompt_cost(prompt, requested_model)
    completion_cost = calculate_completion_cost(content, requested_model)
    cost_usd = float(prompt_cost) + float(completion_cost)
except Exception:
    cost_usd = 0.0
```

The two `calculate_*_cost(string, model)` calls tokenize `prompt` and `content` (raw text) using tokencost's tokenizer. The provider may have used a different tokenizer for billing (esp. Anthropic vs OpenAI tokenizer differences, system message overhead, message-formatting overhead). Result: `verify_kit.cost_usd` shows a number that's close to but not equal to what the provider actually charged.

### After (correct)

```python
# template/harness/{% if has_llm %}llm.py{% endif %}.jinja2 — post-WR-04 fix
cost_usd = 0.0
try:
    from litellm import completion_cost as _litellm_completion_cost
    cost_usd = float(_litellm_completion_cost(completion_response=response) or 0.0)
except Exception:
    cost_usd = 0.0
```

`litellm.completion_cost(completion_response=response)` reads `response.usage.prompt_tokens` + `response.usage.completion_tokens` — the **billed** token counts from the provider's response — and multiplies by the per-model pricing. That's what the provider actually charged you.

> [!quote] Evidence
> Before/after: `template/harness/{% if has_llm %}llm.py{% endif %}.jinja2:235-248`
> Code review report: `.planning/phases/05-llm-add-on/05-REVIEW.md` WR-04 section
> Fix commit: [`b406bd0`](#) — "fix(phase-5): address 5 code-review warnings from /gsd:code-review 5"

## Why it matters

This bug undermines threat **T-05-05** in the same phase's SECURITY.md:

> T-05-05: Repudiation — LLM call cost reporting → **mitigate** via `verify_kit.cost_usd` + `verify_kit.routing_path` span attributes

The `secure-phase` audit verified the attribute *exists* on the span. It cannot verify the *value* is accurate. So a phase that closed all 19 threats SECURED was actually shipping a cost-reporting bug that directly violated one of the threats it claimed to have mitigated.

This is the kind of bug:
- **convergence loop**: cannot catch (reviewing plans, not runtime code).
- **polarity matrix**: cannot catch (testing template renders, not the inside of `call_via_litellm`'s response handling).
- **secure-phase**: cannot catch (verifies attribute exists, not that value is right).
- **code-review**: **catches it** (reads the runtime code with a fresh eye).

> [!important] Implication
> All four gates are needed. Code-review is not redundant with secure-phase. [[each-gate-catches-different-classes-of-bug]].

## What to do about it

> [!tip] Apply
> - **When you have a response object from an LLM SDK, use that SDK's cost helper.** litellm's `completion_cost(completion_response=…)` reads the billed usage block. Provider SDKs have similar helpers (`response.usage.input_tokens` for Anthropic, etc.).
> - **`tokencost.calculate_*_cost(string, model)` is for pre-flight estimation only** — when you have a prompt but haven't called the LLM yet (e.g., the nightly-eval workflow's budget pre-flight). Once you have a response, don't re-tokenize.
> - **Verify behavior at the boundary, not just shape.** Threat T-05-05's mitigation should have asserted not just that `cost_usd` is set, but that it equals `response.usage.prompt_tokens × price + response.usage.completion_tokens × price` (or whatever provider formula). A real assertion at the source rather than presence at the sink.

## The `tokencost` library is still useful

Don't remove it. `tokencost` has two value-adds for verify-kit:
1. **Pre-flight estimation** in the nightly-eval workflow — counts tokens BEFORE making the LLM call so the EVAL_BUDGET_USD pre-flight gate can refuse runaway runs.
2. **Coverage of providers litellm doesn't price.** As of 2026-05-22, litellm prices 400+ models but not all; tokencost has independent coverage.

The fix is to use `tokencost` for pre-flight (no response object yet) and `litellm.completion_cost(completion_response=…)` for post-flight (have response, want billed cost).

## Related patterns

- [[each-gate-catches-different-classes-of-bug]] — why code-review catches what secure-phase can't.
- [[session-2026-05-22-phase-5-llm-and-verification]] §❌ Mistakes #7

## Open questions

- Should `verify_kit.cost_estimate_usd` (from tokencost pre-flight) be a *separate* span attribute from `verify_kit.cost_usd` (from litellm.completion_cost)? That'd let drift between estimate and actual be measurable. Worth considering for a future enhancement.
