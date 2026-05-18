"""Tests for harness.config (Plan 02-03, Task 2).

Covers the `[tool.verify-kit]` Pydantic schema, did-you-mean on unknown
top-level keys, stray verify-kit.yaml warning, and the multi-form TOML
normalization (nested / flat-dotted / quoted check-id).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def config_module(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("config-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.config as config

        yield config
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _write_pyproject(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "pyproject.toml"
    p.write_text(body)
    return p


def test_missing_file_returns_defaults(config_module, tmp_path: Path) -> None:
    cfg = config_module.load_config(tmp_path / "does-not-exist.toml")
    assert cfg.format.default == "pretty"
    assert cfg.cache.max_size_mb == 100
    assert cfg.cache.enabled is True
    assert cfg.checks.disabled == []
    assert cfg.checks.per_check == {}


def test_empty_tool_verify_kit_returns_defaults(
    config_module, tmp_path: Path
) -> None:
    p = _write_pyproject(tmp_path, "[tool.other]\nfoo = 1\n")
    cfg = config_module.load_config(p)
    assert cfg.cache.max_size_mb == 100


def test_nested_form_parses(config_module, tmp_path: Path) -> None:
    body = """
[tool.verify-kit.cache]
max_size_mb = 200
enabled = false

[tool.verify-kit.format]
default = "json"
"""
    p = _write_pyproject(tmp_path, body)
    cfg = config_module.load_config(p)
    assert cfg.cache.max_size_mb == 200
    assert cfg.cache.enabled is False
    assert cfg.format.default == "json"


def test_flat_dotted_form_parses(config_module, tmp_path: Path) -> None:
    body = """
[tool.verify-kit]
"cache.max_size_mb" = 250
"""
    p = _write_pyproject(tmp_path, body)
    cfg = config_module.load_config(p)
    assert cfg.cache.max_size_mb == 250


def test_typo_raises_did_you_mean(config_module, tmp_path: Path) -> None:
    body = """
[tool.verify-kit.cahce]
max_size_mb = 200
"""
    p = _write_pyproject(tmp_path, body)
    with pytest.raises(ValueError) as exc:
        config_module.load_config(p)
    msg = str(exc.value).lower()
    assert "cahce" in msg
    assert "did you mean" in msg
    assert "cache" in msg


def test_disabled_checks(config_module, tmp_path: Path) -> None:
    body = """
[tool.verify-kit.checks]
disabled = ["lint.biome", "format.ruff"]
"""
    p = _write_pyproject(tmp_path, body)
    cfg = config_module.load_config(p)
    assert "lint.biome" in cfg.checks.disabled
    assert "format.ruff" in cfg.checks.disabled


def test_quoted_dotted_check_id(config_module, tmp_path: Path) -> None:
    body = """
[tool.verify-kit.checks."lint.ruff"]
warn_as_error = false
"""
    p = _write_pyproject(tmp_path, body)
    cfg = config_module.load_config(p)
    assert "lint.ruff" in cfg.checks.per_check
    assert cfg.checks.per_check["lint.ruff"]["warn_as_error"] is False


def test_stray_yaml_logs_warning(
    config_module, tmp_path: Path, monkeypatch
) -> None:
    body = "[tool.verify-kit]\n"
    p = _write_pyproject(tmp_path, body)
    (tmp_path / "verify-kit.yaml").write_text("foo: bar\n")

    captured = []

    def fake_warning(msg, **kwargs):
        captured.append((msg, kwargs))

    monkeypatch.chdir(tmp_path)
    # Monkeypatch the log.warning on the module-bound logger
    monkeypatch.setattr(config_module.log, "warning", fake_warning)

    config_module.load_config(p)

    assert any("verify-kit.yaml" in m or "yaml" in str(kw).lower()
               for m, kw in captured), f"No yaml warning captured: {captured}"


def test_exports(config_module) -> None:
    for name in (
        "HarnessConfig",
        "FormatConfig",
        "CacheConfig",
        "ChecksConfig",
        "load_config",
    ):
        assert name in config_module.__all__


def test_default_pyproject_path_arg(config_module, tmp_path: Path) -> None:
    """Contract: load_config accepts a Path positional/keyword."""
    cfg = config_module.load_config(tmp_path / "nope.toml")
    assert cfg.cache.max_size_mb == 100
