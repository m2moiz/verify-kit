# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""Copier Jinja extension that exposes an `env_detect` filter.

Detects presence of agent-tool config directories in the user's home so
Copier prompts can default booleans to `true` when the tool is already
installed. Pure stdlib — no extra dependencies."""
from __future__ import annotations

import os
from pathlib import Path

from jinja2.ext import Extension

AGENT_PATHS: dict[str, list[str]] = {
    "claude_code": ["~/.claude"],
    "cursor": ["~/.cursor"],
    "windsurf": ["~/.windsurf", "~/.codeium/windsurf"],
    # ~/.gitconfig removed — virtually every dev has this file, false-positive signal.
    # Only use ~/.config/github-copilot/ which is Copilot-specific.
    "copilot": ["~/.config/github-copilot"],
    "zed": ["~/.config/zed", "~/Library/Application Support/Zed"],
    "continue": ["~/.continue"],
}


def env_detect(tool: str) -> bool:
    """Return True if the given agent-tool config path exists under $HOME.

    Unknown tool names return False cleanly (no KeyError, no filesystem noise).
    """
    for raw in AGENT_PATHS.get(tool, []):
        if Path(os.path.expanduser(raw)).exists():
            return True
    return False


class EnvDetectExtension(Extension):
    """Jinja2 extension that registers the `env_detect` filter."""

    def __init__(self, environment: object) -> None:
        super().__init__(environment)  # type: ignore[call-arg]
        environment.filters["env_detect"] = env_detect  # type: ignore[attr-defined]
