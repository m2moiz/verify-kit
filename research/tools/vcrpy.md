---
title: vcrpy
aliases: [VCR.py, pytest-recording]
tags: [verify-kit, tools, testing, llm-addon]
created: 2026-05-18
status: ALWAYS-SHIP-when-has_llm
layer: LLM Add-on
phase_introduced: Phase 5
---

# 📼 vcrpy + pytest-recording

> [!abstract] One-line summary
> Record real LLM API calls once, replay deterministically forever — turns expensive LLM tests into free, offline, fast tests.

## What it does

`vcrpy` intercepts HTTP requests and records the response to a "cassette" YAML file. On replay, calls return the recorded response without hitting the network. `pytest-recording` is the pytest plugin wrapper — annotate a test with `@pytest.mark.vcr` and the cassette auto-records on first run, auto-replays on every subsequent run.

## Why we picked it

For LLM testing, vcrpy solves three problems at once:

| Problem | Solution |
|---|---|
| API calls cost money | Replay = free after first record |
| API calls are non-deterministic | Cassette returns identical bytes every time |
| API calls are slow | Replay is ~1ms vs hundreds of ms / seconds |
| API keys can leak in cassettes | `before_record_request` filter scrubs `authorization`, `x-api-key`, etc. |

| Alternative | Why secondary |
|---|---|
| Mock the LLM library directly | Brittle to library updates; doesn't cover wire-level changes |
| `responses` (HTTP mocking) | Manual response definition; vcrpy auto-records first run |
| `litellm` cache | Cache is for production; vcrpy is for tests |

See [[agent-reports/wave-2-llm-hosting]] for the full pattern.

## Usage in verify-kit

```python
import pytest
from openai import OpenAI

@pytest.mark.vcr
def test_summary_quality():
    client = OpenAI()
    result = client.chat.completions.create(...)
    assert "expected substring" in result.choices[0].message.content
```

First run: `pytest` records to `tests/cassettes/test_summary_quality.yaml`. Subsequent runs replay from disk.

Phase 5 ships:
- `pytest-recording` config in `pyproject.toml`'s `[tool.pytest.ini_options]`
- `conftest.py` with `vcr_config()` filtering auth headers via `before_record_request`
- `just refresh-cassettes` recipe to re-record (delete + re-run with `--record-mode=new_episodes`)

## Install

```python
# In generated project deps when has_llm=true
"vcrpy>=6",
"pytest-recording>=0.13",
```

## Gotchas

> [!warning] Don't commit unfiltered cassettes
> First-run recording captures `authorization` headers. Always set `before_record_request` filter BEFORE first run, or the cassette will contain your API keys.

```python
# conftest.py — required pattern
import pytest

@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            ("authorization", "REDACTED"),
            ("x-api-key", "REDACTED"),
            ("openai-organization", "REDACTED"),
        ],
        "filter_query_parameters": ["api_key"],
    }
```

- **Record mode flags** — `none` (default; only replay), `new_episodes` (replay + record new), `all` (always re-record), `once` (record if cassette missing). Use `none` in CI, `new_episodes` locally when adding tests.
- **Binary streaming responses** — vcrpy YAML-serializes everything; streaming LLM responses get reassembled on replay. Works but can produce massive cassette files. For large responses, switch to JSON cassette format.
- **Cassettes ARE source code** — commit them; review them in PRs; treat the diff seriously.

## Key docs

- vcrpy: <https://vcrpy.readthedocs.io/>
- pytest-recording: <https://github.com/kiwicom/pytest-recording>
- Filter recipes: <https://vcrpy.readthedocs.io/en/latest/advanced.html#filter-sensitive-data-from-the-response>

## Related notes

- [[tools/autoevals]] — pairs with vcrpy for deterministic eval runs
- [[tools/litellm]] — LiteLLM's cache is the production equivalent
- [[00-stack-decisions#LLM Add-on]] — default-shipping slot
