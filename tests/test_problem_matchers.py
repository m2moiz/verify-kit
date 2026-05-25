# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""
Validate that the custom VS Code problem-matcher regexes in
`template/.vscode/tasks.json.jinja2` actually parse real Ruff / Pyright /
Biome output captured in `tests/fixtures/`.

Each test:
1. Loads the regex straight from the rendered `.vscode/tasks.json` so a drift
   between matcher definition and test is impossible.
2. Compiles the regex via `re.compile` (regex syntax sanity).
3. Matches a captured fixture line and asserts the named/numbered groups
   extract file/line/column/message correctly.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


FIXTURES = Path(__file__).parent / "fixtures"


def _load_matchers(scratch: Path) -> dict[str, dict]:
    text = (scratch / ".vscode" / "tasks.json").read_text()
    stripped = re.sub(r"//.*", "", text)
    d = json.loads(stripped)
    return {m["name"]: m for m in d["problemMatchers"]}


@pytest.fixture
def matchers(tmp_path: Path) -> dict[str, dict]:
    scratch = render_scratch_project(tmp_path)
    return _load_matchers(scratch)


def test_ruff_matcher_parses_fixture(matchers: dict[str, dict]) -> None:
    m = matchers["verify-kit-ruff"]
    pat = re.compile(m["pattern"]["regexp"])
    line = (FIXTURES / "ruff_sample.txt").read_text().strip()
    match = pat.match(line)
    assert match is not None, f"Ruff regex did not match: {line!r}"
    # groups: 1=file 2=line 3=column 4=code 5=message
    assert match.group(1) == "src/foo.py"
    assert match.group(2) == "12"
    assert match.group(3) == "5"
    assert match.group(4) == "F401"
    assert match.group(5) == "'os' imported but unused"


def test_pyright_matcher_parses_fixture(matchers: dict[str, dict]) -> None:
    m = matchers["verify-kit-pyright"]
    pat = re.compile(m["pattern"]["regexp"])
    line = (FIXTURES / "pyright_sample.txt").read_text().rstrip("\n")
    match = pat.match(line)
    assert match is not None, f"Pyright regex did not match: {line!r}"
    # groups: 1=file 2=line 3=column 4=severity 5=message 6=code
    assert match.group(1) == "/abs/path/src/foo.py"
    assert match.group(2) == "42"
    assert match.group(3) == "9"
    assert match.group(4) == "error"
    assert '"x" is unbound' in match.group(5)
    assert match.group(6) == "reportUnboundVariable"


def test_biome_matcher_parses_fixture(matchers: dict[str, dict]) -> None:
    m = matchers["verify-kit-biome"]
    pat = re.compile(m["pattern"]["regexp"])
    line = (FIXTURES / "biome_sample.txt").read_text().strip()
    match = pat.match(line)
    assert match is not None, f"Biome regex did not match: {line!r}"
    # groups: 1=severity 2=file 3=line 4=column 5=message
    assert match.group(1) == "error"
    assert match.group(2) == "src/foo.ts"
    assert match.group(3) == "8"
    assert match.group(4) == "3"
    assert match.group(5) == "Unused variable"
