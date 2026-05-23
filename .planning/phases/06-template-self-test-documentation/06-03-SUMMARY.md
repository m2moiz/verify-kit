---
phase: 06-template-self-test-documentation
plan: "06-03"
plan_name: summarize-input-defenses
subsystem: backend-llm-defenses
tags: [security, llm, prompt-injection, fastapi, pydantic]
dependency_graph:
  requires: ["06-02"]
  provides: ["_CONTROL_CHARS", "_INJECTION_MARKERS", "SummarizeRequest._strip_and_check"]
  affects: ["06-04", "06-06"]
tech_stack:
  added: ["pydantic.field_validator", "re (stdlib)"]
  patterns: ["module-level compiled regex constants", "Pydantic field_validator(@classmethod) for sanitize-then-deny"]
key_files:
  created:
    - tests/test_phase06_summarize_defenses_polarity.py
  modified:
    - template/{% if has_backend %}app{% endif %}/api.py.jinja2
decisions:
  - "Patch app.api.call_llm (consumer-side binding) not harness.llm.call_llm"
  - "Strip control chars BEFORE injection-marker check (prevents \\x00-smuggling)"
  - "Field(max_length=5000) over manual length-check (Pydantic-native, single source of truth)"
  - "Rely on FastAPI Pydantic-typed parameter for Content-Type enforcement (no middleware)"
metrics:
  duration: ~12 min
  completed: 2026-05-23
closes_beads: [verify-kit-yr7]
---

# Phase 6 Plan 03: Summarize Input Defenses Summary

Layered starter-grade input defenses landed on `/summarize` (verify-kit-yr7): length cap + control-char strip + 3-marker injection denylist + Pydantic Content-Type enforcement, with a 9-case polarity test forcing every defense + the Phase 5 contract.

## What Landed

### `_INJECTION_MARKERS` (exact regex list as committed)

These three regexes are the producer contract for downstream plans (06-06 README documents them verbatim; 06-04 deliberately does NOT reuse them for `/echo`):

```python
_INJECTION_MARKERS = [
    re.compile(r"(?i)\b(ignore|disregard|forget)\s+(all\s+)?previous\s+(instructions|prompts)"),
    re.compile(r"<\|im_(start|end)\|>"),
    re.compile(r"(?i)###\s*system\b"),
]
```

### `_CONTROL_CHARS` (shared with 06-04 by pattern, not by import)

```python
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
```

### `SummarizeRequest` (extended; Phase 5 routing preserved)

```python
class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to summarize in one sentence.")

    @field_validator("text")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = _CONTROL_CHARS.sub("", v)
        for marker in _INJECTION_MARKERS:
            if marker.search(v):
                raise ValueError("input contains a disallowed pattern")
        return v
```

Order matters: control chars are stripped FIRST so an attacker cannot smuggle `### system` past the denylist by inserting `\x00` into the marker (mitigates T-06-09).

### OWASP LLM01 caveat (sentence for 06-06 README)

The api.py module comment block carries the caveat for downstream README cross-reference:

> These are layered checks that run at Pydantic validation time, BEFORE the LLM call. **NOT bulletproof: per OWASP LLM01, prompt injection cannot be fully prevented by input filtering alone; consumers MUST add output filtering + classifier prefilter + system-prompt sandwiching for production use.**

06-06 must reference this caveat verbatim in the README LLM section.

## Defenses (4 layers)

| # | Layer | Where | Threat |
|---|-------|-------|--------|
| 1 | Length cap (5000) | `Field(max_length=5000)` | T-06-08 (wallet DoS) |
| 2 | Control-char strip | `_CONTROL_CHARS.sub("", v)` in validator | T-06-09 (zero-width smuggling) |
| 3 | Injection denylist | `_INJECTION_MARKERS` in validator | T-06-07 (basic prompt injection) |
| 4 | Content-Type | FastAPI Pydantic default | (non-JSON → 422) |

## Polarity Test Coverage (9 cases)

| Test | Asserts |
|------|---------|
| `test_rendered_api_has_all_four_defenses` | All defense markers + Phase 5 contract grep |
| `test_has_llm_false_has_no_defenses` | has_llm=false polarity — no leakage |
| `test_summarize_happy_path` | 200 + `{summary, cost_usd, latency_ms}` shape |
| `test_summarize_length_cap` | 5001 chars → 422, LLM never invoked |
| `test_summarize_control_chars_stripped` | `Hi\x00\x07there` → 200, LLM sees `Hithere` |
| `test_summarize_injection_marker_ignore_previous` | 422 + LLM not invoked |
| `test_summarize_injection_marker_chatml` | 422 + LLM not invoked |
| `test_summarize_injection_marker_system_header` | 422 + LLM not invoked |
| `test_summarize_content_type_non_json` | text/plain → 422 + LLM not invoked |

## Verify Outputs

```
tests/test_phase06_summarize_defenses_polarity.py — 9 passed in 45.38s
tests/test_phase05_polarity.py + tests/test_phase06_auth_polarity.py — 80 passed in 8m03s (no regression)
```

## Deviations from Plan

None. The plan's cycle-1 fix (patch `app.api.call_llm` not `harness.llm.call_llm`) was followed verbatim and the test passed on the first run.

Minor: the executor used `tests/_helpers.render_scratch_project` for the Task 1 verify step (Python-API form) instead of running `copier copy` as a subprocess as the plan's `<verify>` block originally drafted — the original required additional `--data project_name=...` flags. The semantic verification (grep for all defense markers + polarity check) is identical and the existing test infrastructure was the canonical channel per REVIEW-CHECKLIST §1.

## Bead Closure

- `verify-kit-yr7` → closed at plan end with reason: `/summarize input defenses landed in 06-03; length cap + control-char strip + Content-Type + injection-marker denylist`.

## Commits

- `6d1fee5` — feat(api): add input defenses to /summarize endpoint
- `774a808` — test(api): summarize input-defense polarity (9 cases)

## Downstream

- **06-04 (echo hardening):** reuses the same `_CONTROL_CHARS` *pattern* (different module). Does NOT reuse `_INJECTION_MARKERS` — `/echo` is not an LLM endpoint and denylist would generate false positives on legitimate user input.
- **06-06 (README):** documents the four defenses + the OWASP LLM01 caveat sentence verbatim. Producer-side names (`_CONTROL_CHARS`, `_INJECTION_MARKERS`, `SummarizeRequest`) MUST appear in README as committed.

## Self-Check: PASSED

- `template/{% if has_backend %}app{% endif %}/api.py.jinja2` — modified, verified.
- `tests/test_phase06_summarize_defenses_polarity.py` — created, 9 cases pass.
- Commits `6d1fee5` and `774a808` exist in `git log`.
