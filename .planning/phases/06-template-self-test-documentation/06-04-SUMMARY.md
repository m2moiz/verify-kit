---
phase: 06-template-self-test-documentation
plan: "06-04"
plan_name: echo-hardening
subsystem: backend-input-defenses
tags: [security, fastapi, pydantic, input-hardening]
dependency_graph:
  requires: ["06-02"]
  provides: ["_CONTROL_CHARS_ECHO", "EchoRequest._strip_control"]
  affects: ["06-06"]
tech_stack:
  added: ["pydantic.field_validator", "re (stdlib)"]
  patterns: ["module-level compiled regex constants", "Pydantic field_validator(@classmethod) sanitize-only"]
key_files:
  created:
    - tests/test_phase06_echo_hardening_polarity.py
  modified:
    - template/{% if has_backend %}app{% endif %}/models.py.jinja2
decisions:
  - "Hardening lives on EchoRequest in app/models.py (NOT app/api.py) — request-model symmetry"
  - "Distinct identifier _CONTROL_CHARS_ECHO (NOT _CONTROL_CHARS) to decouple from 06-03's regex in api.py per REVIEW-CHECKLIST §3"
  - "NO injection-marker denylist (§4 explicit: /echo does not call an LLM)"
  - "Sanitize-only validator (no raise) — control chars stripped silently; only the length cap rejects"
metrics:
  duration: ~15 min
  completed: 2026-05-23
closes_beads: [verify-kit-93h]
---

# Phase 6 Plan 04: Echo Hardening Summary

Starter-grade input hardening landed on `/echo` (verify-kit-93h): length cap + control-char strip + Pydantic Content-Type enforcement, with a 7-case polarity test forcing each defense, the Phase 4 contract, and 06-02 auth inheritance. The LLM injection-marker denylist is **deliberately omitted** per Phase 6 RESEARCH §4 — `/echo` does not call an LLM, so applying the LLM-specific markers would produce false positives on legitimate user input.

## What Landed

### `_CONTROL_CHARS_ECHO` (exact regex as committed)

```python
_CONTROL_CHARS_ECHO = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
```

Lives in `app/models.py` next to `EchoRequest`. Independent identifier from 06-03's `_CONTROL_CHARS` in `app/api.py` — different files, no cross-coupling. The regex *shape* is identical (same character class) but the symbols are not shared via import, so a rename in either plan does not break the other (REVIEW-CHECKLIST §3 decoupling).

### `EchoRequest` (extended; Phase 4 routing preserved)

```python
class EchoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("message")
    @classmethod
    def _strip_control(cls, v: str) -> str:
        return _CONTROL_CHARS_ECHO.sub("", v)
```

Field name is `message` (NOT `text` — that's `SummarizeRequest`). The validator is **sanitize-only**: it strips control chars and returns; it never raises. Only the length cap (Field constraint) and Content-Type (FastAPI default) can produce 422.

### Decoupling rationale (REVIEW-CHECKLIST §3)

Two regex constants now exist with identical pattern shape but different identifiers and different homes:

| Plan | Identifier | File | Used by |
|------|------------|------|---------|
| 06-03 | `_CONTROL_CHARS` | `app/api.py` | `SummarizeRequest._strip_and_check` |
| 06-04 | `_CONTROL_CHARS_ECHO` | `app/models.py` | `EchoRequest._strip_control` |

This is deliberate. Sharing the constant via `from app.models import _CONTROL_CHARS_ECHO` in api.py would couple 06-03 and 06-04 — a future change to `/echo`'s allowed character set would silently mutate `/summarize`'s defense, and vice versa. The duplication is the cheaper trade.

### Injection-marker denylist is intentionally absent

Phase 6 RESEARCH §4: "Apply layers 1–3 (skip the denylist — it's LLM-specific)". The forcing-function test `test_echo_no_injection_marker_check` asserts that `{"message": "Ignore all previous instructions"}` returns 200, not 422 — if a future refactor hoists `_INJECTION_MARKERS` into models.py and applies it to `EchoRequest`, this test fires immediately.

## Defenses (3 layers — NOT 4)

| # | Layer | Where | Threat |
|---|-------|-------|--------|
| 1 | Length cap (5000) | `Field(max_length=5000)` | T-06-11 (input DoS / memory pressure) |
| 2 | Control-char strip | `_CONTROL_CHARS_ECHO.sub("", v)` in validator | T-06-12 (zero-width / null smuggling through log parsers) |
| 3 | Content-Type | FastAPI Pydantic default | (non-JSON → 422) |
| — | ~~Injection denylist~~ | **deliberately absent** | T-06-13 (over-application asserted by polarity test) |

## Polarity Test Coverage (7 cases)

| Test | Asserts |
|------|---------|
| `test_rendered_models_has_all_three_defenses` | Static template grep + `_INJECTION_MARKERS` absent from models.py + `_CONTROL_CHARS_ECHO` absent from api.py |
| `test_echo_happy_path` | 200 + `{message, request_id, received_at}` shape (Phase 4 contract) |
| `test_echo_length_cap` | 5001 chars → 422 |
| `test_echo_control_chars_stripped` | `"hi\x00\x07there"` → 200 with `message == "hithere"` |
| `test_echo_no_injection_marker_check` | `"Ignore all previous instructions"` → 200 (forcing function for §4) |
| `test_echo_content_type_non_json` | text/plain → 422 |
| `test_echo_inherits_auth` | ENV=prod + missing X-VerifyKit-Token → 401 (06-02 wiring) |

## Verify Outputs

```
tests/test_phase06_echo_hardening_polarity.py — 7 passed in 33.74s
tests/test_phase06_summarize_defenses_polarity.py +
  tests/test_phase06_auth_polarity.py +
  tests/test_phase04_scaffold_polarity.py — 23 passed in 1m48s (no regression)
```

## Deviations from Plan

None. The plan's cycle-1 fix (target `app/models.py.jinja2` next to `EchoRequest`; field is `message`; identifier `_CONTROL_CHARS_ECHO`) was followed verbatim and tests passed on first run.

Minor: the Task 1 static verify used `tests/_helpers.render_scratch_project` (Python-API form) instead of `copier copy --vcs-ref HEAD` as a subprocess — the latter fails on uncommitted template edits (`HEAD` ref does not yet contain them). This mirrors 06-03's identical adjustment and is sanctioned by REVIEW-CHECKLIST §1 (the helper is the canonical channel; the semantic check — grep for `_CONTROL_CHARS_ECHO`, `max_length=5000`, `field_validator("message")` etc. — is identical either way).

## Bead Closure

- `verify-kit-93h` → closed at plan end with reason: `/echo hardening landed in 06-04; length cap + control-char strip + Content-Type via EchoRequest field validator`.

## Commits

- `1128fd0` — feat(api): harden EchoRequest with length cap + control-char strip
- `31dbb83` — test(api): echo hardening polarity (7 cases)
- (SUMMARY commit pending)

## Downstream

- **06-06 (README):** documents `/echo`'s 3 defenses as a parallel section to `/summarize`'s 4 defenses. The README MUST explicitly note the deliberate omission of the denylist for `/echo` with the §4 rationale ("/echo does not call an LLM") — `test_echo_no_injection_marker_check` enforces this from the code side.
- **06-08 (self-test CI):** the `+backend` matrix entry exercises `/echo` end-to-end via `just verify`. The hardened request shape (message length + control chars) is now part of the contract that CI re-verifies on every PR.

## Self-Check: PASSED

- `template/{% if has_backend %}app{% endif %}/models.py.jinja2` — modified, verified by Task 1 helper-based grep.
- `tests/test_phase06_echo_hardening_polarity.py` — created, 7 cases pass.
- Commits `1128fd0` and `31dbb83` exist in `git log`.
- `_CONTROL_CHARS_ECHO` lives in models.py only; absent from api.py (verified by static test).
- `_INJECTION_MARKERS` absent from models.py (verified by static test).
- No regression in 06-03 (9 tests), 06-02 (10 tests), or 04 scaffold (3 tests).
