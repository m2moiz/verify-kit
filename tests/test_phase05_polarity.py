# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""Phase 5 LLM-add-on polarity tests.

Locks the entire Phase 5 contract under a parametrized matrix over the
``has_backend`` × ``has_llm`` × ``llm_backend`` axes. Forcing-functions
every Phase 5 review HIGH (#1-#8) and the Pitfalls that were caught
during plan-review-convergence (Pitfalls 1, 3, 4, 5, 6, 8).

Lives at the repo top-level (NOT under ``tests/backend`` or
``tests/llm``) per REVIEW-CHECKLIST §7 — those subdirectories are paths
the harness pytest-invokes, and a polarity test that itself renders
scratch projects could recurse.

All scratch renders go through ``render_scratch_project`` (Python API,
not raw ``subprocess.run`` with copier) per REVIEW-CHECKLIST §1. Any
subprocess that targets a scratch project passes ``env=_CLEAN_ENV``
per REVIEW-CHECKLIST §8.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from tests._helpers import _CLEAN_ENV, render_scratch_project  # noqa: F401

# ── Base data shared across renders ───────────────────────────────────────────

_BASE: dict[str, object] = {
    "project_name": "PolarityP5",
    "project_description": "phase 5 polarity test",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "has_claude_code": True,  # needed so SKILL.md is rendered for assertions
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_devcontainer": False,
    "has_db": False,
    "has_logfire": False,
    "has_fastapi_mcp": False,
}


def _render(tmp_path: Path, *, has_backend: bool, has_llm: bool,
            llm_backend: str = "none") -> Path:
    return render_scratch_project(
        tmp_path,
        **{
            **_BASE,
            "has_backend": has_backend,
            "has_llm": has_llm,
            "llm_backend": llm_backend,
        },  # type: ignore[arg-type]
    )


# Effective cells: 2 (has_backend) × 1 (has_llm=False) + 2 × 3 (has_llm=True)
# = 2 + 6 = 8 effective renders. We parametrize the LLM-true cells over the
# llm_backend axis and pass a single dummy value for the LLM-false cells.
_CELLS_LLM_TRUE: list[tuple[bool, str]] = [
    (True, "langfuse-cloud"),
    (True, "langfuse-self-host"),
    (True, "none"),
    (False, "langfuse-cloud"),
    (False, "langfuse-self-host"),
    (False, "none"),
]

_CELLS_LLM_FALSE: list[bool] = [True, False]  # has_backend axis only


# ── Forcing-function tests ────────────────────────────────────────────────────


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_llm_artifacts_polarity(tmp_path: Path, has_backend: bool,
                                llm_backend: str) -> None:
    """has_llm=true renders ship harness/llm.py + eval/ + tests/llm/ + nightly-eval.yml."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    assert (scratch / "harness" / "llm.py").exists()
    assert (scratch / "eval").is_dir()
    assert (scratch / "tests" / "llm").is_dir()
    assert (scratch / ".github" / "workflows" / "nightly-eval.yml").exists()


@pytest.mark.parametrize("has_backend", _CELLS_LLM_FALSE)
def test_llm_artifacts_absent_when_no_llm(tmp_path: Path,
                                          has_backend: bool) -> None:
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=False)
    assert not (scratch / "harness" / "llm.py").exists()
    assert not (scratch / "eval").exists()
    assert not (scratch / "tests" / "llm").exists()
    assert not (scratch / ".github" / "workflows" / "nightly-eval.yml").exists()


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_docker_compose_langfuse_only_in_self_host_cell(
    tmp_path: Path, has_backend: bool, llm_backend: str
) -> None:
    """docker-compose.langfuse.yml renders ONLY for langfuse-self-host."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    compose = scratch / "docker-compose.langfuse.yml"
    if llm_backend == "langfuse-self-host":
        assert compose.exists()
    else:
        assert not compose.exists()


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_summarize_endpoint_polarity_llm_true(
    tmp_path: Path, has_backend: bool, llm_backend: str
) -> None:
    """/summarize present ONLY when has_backend=true AND has_llm=true."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    api = scratch / "app" / "api.py"
    if has_backend:
        text = api.read_text()
        assert "/summarize" in text
        assert "/healthz" in text and "/echo" in text  # Phase 4 not regressed
    else:
        assert not api.exists()
        # ensure no orphan app/ tree
        assert not (scratch / "app").exists()


@pytest.mark.parametrize("has_backend", _CELLS_LLM_FALSE)
def test_summarize_absent_when_no_llm(tmp_path: Path,
                                      has_backend: bool) -> None:
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=False)
    if has_backend:
        api = scratch / "app" / "api.py"
        text = api.read_text()
        assert "/summarize" not in text
        assert "from harness.llm" not in text


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_no_empty_segment_leaks(tmp_path: Path, has_backend: bool,
                                llm_backend: str) -> None:
    """No empty path segments / .jinja2-only filenames anywhere in the tree."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    bad: list[str] = []
    for node in scratch.rglob("*"):
        name = node.name
        if name == "" or name == ".jinja2":
            bad.append(str(node.relative_to(scratch)))
        if "{%" in name:
            bad.append(str(node.relative_to(scratch)))
    assert not bad, f"empty-segment leaks: {bad}"


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_pyproject_has_no_tokenx(tmp_path: Path, has_backend: bool,
                                 llm_backend: str) -> None:
    """D-22: tokenx-core dropped — no bare 'tokenx' nor 'tokenx-core' in deps."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    text = (scratch / "pyproject.toml").read_text()
    # Reject both shapes: "tokenx" and "tokenx-core" inside dependency strings
    assert not re.search(r'"tokenx(-core)?"[<>=,~!]', text), (
        "D-22: tokenx / tokenx-core must not appear in has_llm pyproject"
    )
    assert "tokenx" not in text.lower(), "tokenx referenced anywhere"


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_pyproject_uses_optional_dependencies_not_dependency_groups(
    tmp_path: Path, has_backend: bool, llm_backend: str
) -> None:
    """HIGH #3: dev deps live under [project.optional-dependencies], NOT [dependency-groups]."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    text = (scratch / "pyproject.toml").read_text()
    assert "[project.optional-dependencies]" in text
    assert "[dependency-groups]" not in text


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_no_result_data_anywhere(tmp_path: Path, has_backend: bool,
                                 llm_backend: str) -> None:
    """Pitfall 4: 'result.data' substring absent from every .py file."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    offenders: list[str] = []
    for py in scratch.rglob("*.py"):
        if "result.data" in py.read_text():
            offenders.append(str(py.relative_to(scratch)))
    assert not offenders, f"result.data found in: {offenders}"


def test_summarize_uses_call_llm_not_pydantic_ai_directly(
    tmp_path: Path,
) -> None:
    """HIGH #2: /summarize routes via call_llm; does NOT import pydantic_ai.Agent."""
    scratch = _render(tmp_path, has_backend=True, has_llm=True,
                      llm_backend="langfuse-cloud")
    api = (scratch / "app" / "api.py").read_text()
    assert "from harness.llm import" in api
    assert "call_llm(" in api
    assert "pydantic_ai.Agent" not in api
    assert "from pydantic_ai import" not in api


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_eval_results_path_consistency(tmp_path: Path, has_backend: bool,
                                       llm_backend: str) -> None:
    """HIGH #5: justfile + nightly-eval.yml + SKILL.md ALL reference .verify/eval-results.json."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    canonical = ".verify/eval-results.json"
    justfile = (scratch / "justfile").read_text()
    assert canonical in justfile, "justfile missing canonical eval-results path"
    nightly = (scratch / ".github" / "workflows" / "nightly-eval.yml").read_text()
    assert canonical in nightly, "nightly-eval.yml missing canonical eval-results path"
    skill = scratch / ".claude" / "skills" / "verify-kit-eval" / "SKILL.md"
    assert canonical in skill.read_text(), "SKILL.md missing canonical eval-results path"


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_promptfoo_config_has_prompts_section(
    tmp_path: Path, has_backend: bool, llm_backend: str
) -> None:
    """HIGH #4: promptfoo.config.yaml has prompts: entry referencing producer file."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    config_path = scratch / "eval" / "promptfoo.config.yaml"
    parsed = yaml.safe_load(config_path.read_text())
    assert isinstance(parsed, dict)
    assert "prompts" in parsed
    prompts = parsed["prompts"]
    assert isinstance(prompts, list) and len(prompts) >= 1
    # The producer file must exist
    assert (scratch / "eval" / "prompts" / "summarize.txt").exists()
    # Reference must point at the producer file
    assert any("summarize.txt" in str(p) for p in prompts)


def test_fix_propose_skill_uses_noarg_form(tmp_path: Path) -> None:
    """HIGH #6: SKILL.md uses no-arg fix_propose() — no invented JSON-string args."""
    scratch = _render(tmp_path, has_backend=True, has_llm=True,
                      llm_backend="langfuse-cloud")
    skill = scratch / ".claude" / "skills" / "verify-kit-eval" / "SKILL.md"
    text = skill.read_text()
    assert "fix_propose" in text
    # Reject patterns: fix_propose '{   or   fix_propose({
    assert not re.search(r"fix_propose\s*['\"\(]\s*\{", text)


@pytest.mark.parametrize("has_backend,llm_backend", _CELLS_LLM_TRUE)
def test_env_destination_per_cell_llm_true(
    tmp_path: Path, has_backend: bool, llm_backend: str
) -> None:
    """HIGH #1: exactly one .env.example per (has_llm, has_backend) cell."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=True,
                      llm_backend=llm_backend)
    root_env = scratch / ".env.example"
    app_env = scratch / "app" / ".env.example"
    if has_backend:
        # (T,T): root .env.example carries the auth-token slot (Plan 06-02);
        # app/.env.example may still exist as the legacy backend env file.
        assert root_env.exists()
        root_text = root_env.read_text()
        assert "VERIFYKIT_AUTH_TOKEN=" in root_text
        # LLM env block present in whichever rendered env file carries it;
        # both files are rendered under (T,T), so check at least one.
        candidates = [root_text]
        if app_env.exists():
            candidates.append(app_env.read_text())
        assert any("LANGFUSE" in t or "ANTHROPIC_API_KEY" in t for t in candidates)
    else:
        # (T,F): env lives at root, app/ absent
        assert root_env.exists()
        assert not app_env.exists()
        text = root_env.read_text()
        assert "LANGFUSE" in text or "ANTHROPIC_API_KEY" in text


@pytest.mark.parametrize("has_backend", _CELLS_LLM_FALSE)
def test_env_destination_per_cell_llm_false(tmp_path: Path,
                                            has_backend: bool) -> None:
    """has_llm=false: no LLM env block in any rendered .env.example."""
    scratch = _render(tmp_path, has_backend=has_backend, has_llm=False)
    root_env = scratch / ".env.example"
    app_env = scratch / "app" / ".env.example"
    # has_llm=false contract:
    # - has_backend=true: root .env.example exists (Plan 06-02 auth-token slot);
    #   app/.env.example may exist as legacy file. Neither contains LLM keys.
    # - has_backend=false: no .env.example anywhere (root file gated has_backend,
    #   LLM-only root file gated has_llm).
    if has_backend:
        assert root_env.exists()
        root_text = root_env.read_text()
        assert "VERIFYKIT_AUTH_TOKEN=" in root_text
        assert "LANGFUSE" not in root_text
        assert "ANTHROPIC_API_KEY" not in root_text
        if app_env.exists():
            app_text = app_env.read_text()
            assert "LANGFUSE" not in app_text
            assert "ANTHROPIC_API_KEY" not in app_text
    else:
        assert not root_env.exists()
        assert not app_env.exists()


def test_golden_jsonl_rows_parse(tmp_path: Path) -> None:
    """Spot check on eval/datasets/golden.jsonl — each row is valid JSON."""
    scratch = _render(tmp_path, has_backend=True, has_llm=True,
                      llm_backend="langfuse-cloud")
    golden = scratch / "eval" / "datasets" / "golden.jsonl"
    assert golden.exists()
    rows = [json.loads(ln) for ln in golden.read_text().splitlines() if ln.strip()]
    assert len(rows) >= 1
