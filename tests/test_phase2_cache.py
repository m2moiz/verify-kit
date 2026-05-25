# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.cache (Plan 02-03, Task 1).

Covers SQLite WAL-mode cache, key composition, eviction, and the
CacheCorruptError contract that CLI maps to EXIT_CACHE_CORRUPT=10.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def cache_module(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("cache-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.cache as cache
        import harness.models as models

        yield cache, models
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _make_result(models, status="pass", check_id="lint.ruff"):
    return models.CheckResult(
        check_id=check_id, status=status, message="ok", duration_ms=12
    )


def test_make_cache_key_deterministic(cache_module) -> None:
    cache, _ = cache_module
    k1 = cache.make_cache_key(
        "lint.ruff", {"src/foo.py": "abc", "pyproject.toml": "def"},
        "ruff 0.6.9", ["--select=E"],
    )
    k2 = cache.make_cache_key(
        "lint.ruff", {"pyproject.toml": "def", "src/foo.py": "abc"},
        "ruff 0.6.9", ["--select=E"],
    )
    assert k1 == k2
    assert len(k1) == 64  # sha256 hexdigest


def test_make_cache_key_changes_on_input_change(cache_module) -> None:
    cache, _ = cache_module
    base = cache.make_cache_key("lint.ruff", {"a.py": "h1"}, "ruff 0.6.9", [])
    diff_hash = cache.make_cache_key("lint.ruff", {"a.py": "h2"}, "ruff 0.6.9", [])
    diff_ver = cache.make_cache_key("lint.ruff", {"a.py": "h1"}, "ruff 0.7.0", [])
    diff_args = cache.make_cache_key("lint.ruff", {"a.py": "h1"}, "ruff 0.6.9", ["--fix"])
    diff_check = cache.make_cache_key("format.ruff", {"a.py": "h1"}, "ruff 0.6.9", [])
    assert base != diff_hash
    assert base != diff_ver
    assert base != diff_args
    assert base != diff_check


def test_get_miss_returns_none(cache_module, tmp_path: Path) -> None:
    cache, _ = cache_module
    store = cache.CacheStore(tmp_path / "cache.db")
    assert store.get("lint.ruff", "nokey") is None


def test_put_then_get_roundtrip(cache_module, tmp_path: Path) -> None:
    cache, models = cache_module
    store = cache.CacheStore(tmp_path / "cache.db")
    result = _make_result(models)
    store.put("lint.ruff", "k1", result)
    got = store.get("lint.ruff", "k1")
    assert got is not None
    assert got.status == "pass"
    assert got.check_id == "lint.ruff"
    assert got.cached is True  # set on retrieval


def test_get_caches_fail_status(cache_module, tmp_path: Path) -> None:
    """Decision 2.3: cache pass + fail + skip uniformly."""
    cache, models = cache_module
    store = cache.CacheStore(tmp_path / "cache.db")
    result = _make_result(models, status="fail")
    store.put("lint.ruff", "k1", result)
    got = store.get("lint.ruff", "k1")
    assert got is not None
    assert got.status == "fail"
    assert got.cached is True


def test_wal_mode_active(cache_module, tmp_path: Path) -> None:
    cache, _ = cache_module
    store = cache.CacheStore(tmp_path / "cache.db")
    # Trigger a connection
    store.put("lint.ruff", "k1", _make_result(_models_for(cache_module)))
    # Open a fresh connection to inspect the pragma
    conn = sqlite3.connect(str(tmp_path / "cache.db"))
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()
        assert mode[0].lower() == "wal"
    finally:
        conn.close()


def _models_for(cache_module):
    _, models = cache_module
    return models


def test_parent_dir_auto_created(cache_module, tmp_path: Path) -> None:
    cache, models = cache_module
    db_path = tmp_path / "nested" / "subdir" / "cache.db"
    store = cache.CacheStore(db_path)
    store.put("lint.ruff", "k", _make_result(models))
    assert db_path.exists()


def test_corrupt_db_raises_cache_corrupt_error(cache_module, tmp_path: Path) -> None:
    cache, models = cache_module
    db_path = tmp_path / "cache.db"
    # Write garbage that won't parse as SQLite
    db_path.write_bytes(b"this is not a sqlite db" * 100)
    with pytest.raises(cache.CacheCorruptError):
        store = cache.CacheStore(db_path)
        store.put("lint.ruff", "k", _make_result(models))


def test_evict_if_needed_drops_oldest(cache_module, tmp_path: Path) -> None:
    cache, models = cache_module
    store = cache.CacheStore(tmp_path / "cache.db")
    # Insert several entries with large payloads to push over a small cap
    for i in range(20):
        r = models.CheckResult(
            check_id="lint.ruff",
            status="pass",
            message="x" * 200,  # ~200 bytes payload
            duration_ms=i,
        )
        store.put("lint.ruff", f"key-{i}", r)
    evicted = store.evict_if_needed(max_bytes=500)
    assert evicted > 0


def test_evict_if_needed_no_op_under_cap(cache_module, tmp_path: Path) -> None:
    cache, models = cache_module
    store = cache.CacheStore(tmp_path / "cache.db")
    store.put("lint.ruff", "k", _make_result(models))
    evicted = store.evict_if_needed(max_bytes=10_000_000)
    assert evicted == 0


def test_clear_removes_all(cache_module, tmp_path: Path) -> None:
    cache, models = cache_module
    store = cache.CacheStore(tmp_path / "cache.db")
    store.put("lint.ruff", "k", _make_result(models))
    store.clear()
    assert store.get("lint.ruff", "k") is None


def test_exports(cache_module) -> None:
    cache, _ = cache_module
    assert "CacheStore" in cache.__all__
    assert "make_cache_key" in cache.__all__
    assert "hash_inputs" in cache.__all__
    assert "get_tool_version" in cache.__all__
    assert "CacheCorruptError" in cache.__all__


def test_get_tool_version_no_tool(cache_module) -> None:
    cache, _ = cache_module
    assert cache.get_tool_version(None) == "no-tool"


def test_hash_inputs_returns_dict(cache_module, tmp_path: Path) -> None:
    cache, _ = cache_module
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    result = cache.hash_inputs(["*.txt"], cwd=tmp_path)
    assert set(result.keys()) == {"a.txt", "b.txt"}
    # sha256 hex digest length
    assert all(len(h) == 64 for h in result.values())
