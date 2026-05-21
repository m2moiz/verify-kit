---
title: Vault Scripts
aliases: [scripts, vault tooling]
tags: [verify-kit, vault, tooling, meta]
created: 2026-05-18
---

# 🛠️ Vault Scripts

> [!abstract] What's in here
> Utility scripts for maintaining the `research/` Obsidian vault. These are about the vault's *health*, not the verify-kit project's code. Keep them small and dependency-light.

## Scripts

### `audit-obsidian.py`

Validates every markdown file in the vault against the Obsidian Flavored Markdown spec.

**What it checks:**
- Wikilinks (`[[Note]]`, `[[Note#Heading]]`) resolve to real notes and real headings
- Embeds (`![[Note]]`, `![[image.png]]`) resolve
- Callout types (`> [!type]`) are valid Obsidian types (`note`, `warning`, `info`, etc.)
- Frontmatter YAML parses cleanly
- Code blocks are skipped (bash `[[ -f X ]]` test syntax won't be flagged as a wikilink)
- Markdown table-escaped pipes `\|` in wikilinks are handled correctly
- Block-ID anchors `#^id` are recognized as valid

**Usage:**

```bash
# From anywhere — the script finds the vault relative to its own location
python3 research/scripts/audit-obsidian.py

# Or from inside research/scripts/
cd research/scripts && python3 audit-obsidian.py

# Override the vault path
python3 research/scripts/audit-obsidian.py /path/to/some/other/vault
```

**Exit codes:**
- `0` — no issues found
- `1` — one or more issues
- `2` — vault path doesn't exist (usage error)

**When to run:**
- After writing or editing notes in `research/` — especially after a large batch
- Before committing new docs
- When refactoring (e.g. renaming a note that's linked from many places)
- Optionally as a pre-commit hook on `research/**/*.md` changes

**Output format:**

```text
# Obsidian vault audit (code-block aware)

Files scanned: 41

## path/to/note-with-issues.md
  - [wikilink] Unresolved wikilink target: [[some-missing-note]]
  - [callout] Unknown callout type: [!madeup]

---

# Summary

Files with issues: 1/41
Total issues: 2
  - wikilink: 1
  - callout: 1
```

**Dependencies:**
- Python 3.9+
- `pyyaml` (for frontmatter parsing) — usually present in any Python environment that touched verify-kit; install via `uv pip install pyyaml` if missing

**What it deliberately does NOT do:**
- It doesn't lint markdown style (line length, heading hierarchy, etc.) — use a dedicated markdown linter for that
- It doesn't validate external `[link](https://...)` URLs — those would need a network roundtrip
- It doesn't rename targets when notes move — Obsidian itself handles that during edits
- It doesn't enforce a frontmatter schema beyond a soft check for `title`, `tags`, `created`

## Adding a new script

If you write another vault-maintenance script, drop it here and add a section above. Keep dependencies minimal (stdlib + pyyaml is the bar) so the scripts work in any Python environment that has the vault.
