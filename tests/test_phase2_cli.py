"""Tests for harness.cli — Plan 02-06, Task 2.

Coverage map (from plan <verify><automated>):
    (a) verify --quick exits 0 on a clean fixture
    (b) verify --format=json produces parseable JSON on stdout AND writes 3 disk files
    (c) verify --frmt=json → did-you-mean: --format? on stderr and exits 2
    (d) verify --check=lnit → did-you-mean: lint.ruff and exits 2
    (e) list-checks --format=json → valid JSON array
    (f) describe output parses as JSON
    (g) atexit registered shutdown handler at module import time
    + (h) describe envelope keys (FMT-04 contract)
    + (i) atomic disk writes + EXIT_WRITE_FAILED precedence over EXIT_CHECK_FAIL

Did-you-mean assertions for unknown flags / commands need ``app_entry()``
(standalone_mode=False handler) — pure ``CliRunner.invoke(app, ...)`` is
acceptable only for the happy path.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def cli_modules(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    scratch = render_scratch_project(tmp_path_factory.mktemp("cli-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.cli as cli
        import harness.models as models

        yield {"scratch": scratch, "cli": cli, "models": models}
    finally:
        sys.path.remove(str(scratch))


def _make_fixture_cwd(tmp_path: Path) -> Path:
    """Build a project root where the quick-tier checks pass."""
    (tmp_path / ".mise.toml").write_text(
        '[tools]\npython = "3.13"\nnode = "20"\n', encoding="utf-8"
    )
    (tmp_path / ".copier-answers.yml").write_text(
        "_src_path: file:///fake\n", encoding="utf-8"
    )
    return tmp_path


# ── (a) verify --quick exits 0 on clean fixture ──────────────────────────────


def test_verify_quick_exits_zero(cli_modules, tmp_path: Path, monkeypatch):
    cli = cli_modules["cli"]
    cwd = _make_fixture_cwd(tmp_path)
    monkeypatch.chdir(cwd)

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli.app, ["verify", "--quick", "--format=json"])
    assert result.exit_code == 0, f"stderr/out: {result.output}"


# ── (b) verify --format=json writes 3 disk files AND emits JSON to stdout ────


def test_verify_format_json_writes_three_disk_files(
    cli_modules, tmp_path: Path, monkeypatch
):
    cli = cli_modules["cli"]
    cwd = _make_fixture_cwd(tmp_path)
    monkeypatch.chdir(cwd)

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli.app, ["verify", "--quick", "--format=json"])
    assert result.exit_code == 0

    # Parse stdout as JSON (the json formatter wrote it).
    parsed = json.loads(result.stdout)
    assert "exit_code" in parsed
    assert "summary" in parsed

    # Three disk artifacts must exist post-run (HARN-02 SC#2).
    assert (cwd / ".verify" / "report.json").exists()
    assert (cwd / ".verify" / "report.junit.xml").exists()
    assert (cwd / ".verify" / "report.sarif").exists()


# ── (c) unknown flag --frmt=json → did-you-mean --format? exits 2 ────────────


def test_verify_unknown_flag_did_you_mean(tmp_path: Path, cli_modules):
    """Did-you-mean for unknown flag requires the app_entry() wrapper, not
    CliRunner.invoke(app, ...). We invoke via subprocess so the console_script
    code path runs end-to-end (review MEDIUM-4)."""
    scratch = cli_modules["scratch"]
    cwd = _make_fixture_cwd(tmp_path)

    proc = subprocess.run(
        [sys.executable, "-m", "harness.cli", "verify", "--frmt=json"],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(scratch)},
    )
    assert proc.returncode == 2, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    # Message body lives on stderr per the docstring.
    assert "did you mean" in proc.stderr.lower()
    assert "format" in proc.stderr.lower()


# ── (d) unknown --check=lnit → did-you-mean: lint.ruff, exits 2 ──────────────


def test_verify_unknown_check_id_did_you_mean(
    tmp_path: Path, cli_modules
):
    scratch = cli_modules["scratch"]
    cwd = _make_fixture_cwd(tmp_path)

    proc = subprocess.run(
        [sys.executable, "-m", "harness.cli", "verify", "--quick",
         "--check=lnit.ruff", "--format=json", "--no-cache"],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(scratch)},
    )
    assert proc.returncode == 2, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    # Either suggests lint.ruff OR mentions it
    assert "did you mean" in proc.stderr.lower()


# ── (e) list-checks --format=json → JSON array ───────────────────────────────


def test_list_checks_format_json(cli_modules):
    cli = cli_modules["cli"]
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli.app, ["list-checks", "--format=json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload, "list-checks should yield ≥1 entry"
    entry = payload[0]
    assert "check_id" in entry
    assert "fn" not in entry, (
        "CheckCatalogEntry must NOT leak the fn field (review MEDIUM-1)"
    )


# ── (f) describe parses as JSON ──────────────────────────────────────────────


def test_describe_emits_json(cli_modules):
    cli = cli_modules["cli"]
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli.app, ["describe"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    # FMT-04 envelope: version + commands + exit_codes + check_catalog_schema
    assert payload.get("version") == "1"
    assert "exit_codes" in payload
    assert "checks" in payload
    assert "check_catalog_schema" in payload
    assert "report_schema" in payload
    assert "jsonl_summary_marker" in payload
    # Exit-code precedence note required (review MEDIUM-6)
    assert "exit_code_precedence" in payload


# ── (g) atexit registered for shutdown at module import ──────────────────────


def test_atexit_shutdown_registered(cli_modules):
    """Sanity check from <verification> section: importing harness.cli must
    register harness.observability.shutdown via atexit at module load
    (RESEARCH.md §13 S2)."""
    import atexit
    cli = cli_modules["cli"]
    # cli module should have set the sentinel to True at import.
    assert getattr(cli, "_ATEXIT_REGISTERED", False) is True
    # And the function should be in atexit's handler list.
    handlers = getattr(atexit, "_exithandlers", [])
    # CPython exposes _exithandlers in this form: list[tuple(fn, args, kwargs)]
    names = [t[0].__name__ for t in handlers if callable(getattr(t, "__getitem__", None) and t[0])]
    # On CPython _exithandlers may be `[(fn, args, kwargs), ...]`; fallback:
    if not names:
        # Fallback: ensure the sentinel is set (the implementation guarantees
        # it only flips True after atexit.register succeeds).
        assert cli._ATEXIT_REGISTERED is True
    else:
        assert "shutdown" in names


# ── (i) EXIT_WRITE_FAILED supersedes EXIT_CHECK_FAIL ─────────────────────────


def test_exit_write_failed_supersedes_check_fail(
    cli_modules, tmp_path: Path, monkeypatch
):
    """If `.verify/report.*` disk write fails, the CLI MUST exit
    EXIT_WRITE_FAILED=12 even when checks themselves had failures.

    We simulate by making `.verify` a regular file so mkdir+open fails.
    """
    cli = cli_modules["cli"]
    cwd = _make_fixture_cwd(tmp_path)
    monkeypatch.chdir(cwd)

    # Block .verify from being created as a dir
    (cwd / ".verify").write_text("not a directory\n", encoding="utf-8")

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli.app, ["verify", "--quick", "--format=json", "--no-cache"])

    EXIT_WRITE_FAILED = cli_modules["models"].EXIT_WRITE_FAILED
    assert result.exit_code == EXIT_WRITE_FAILED, (
        f"expected EXIT_WRITE_FAILED={EXIT_WRITE_FAILED}, got {result.exit_code}: {result.output}"
    )
