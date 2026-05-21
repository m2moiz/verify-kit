#!/usr/bin/env python3
"""Obsidian Flavored Markdown audit — code-block aware.

Walks every `.md` file in the vault and checks:
  - Wikilinks `[[Note]]` and `[[Note#Heading]]` resolve to real notes/headings
  - Embeds `![[Note]]` resolve
  - Callout types `> [!type]` are valid Obsidian types
  - Frontmatter YAML parses cleanly and has conventional keys

Skips:
  - Fenced code blocks (so bash `[[ -f X ]]` doesn't get flagged as a wikilink)
  - Block-ID anchors `[[Note#^id]]` — assumed well-formed (validating these
    requires a separate pass over `^id` markers in the target file)
  - Table-escaped pipes `\\|` in wikilinks

Usage:
  python3 audit-obsidian.py              # auto-detects vault as the parent
                                          # of the directory this script lives in
  python3 audit-obsidian.py /path/to/vault  # explicit vault path

Exit code: 0 if no issues, 1 if any issues found.

Lives at: research/scripts/audit-obsidian.py
"""

from __future__ import annotations
import re, sys, yaml
from pathlib import Path
from collections import defaultdict

# Auto-detect the vault root. This script lives at <vault>/scripts/audit-obsidian.py,
# so the vault root is one directory up from the script's location.
# A CLI argument overrides this.
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_VAULT = SCRIPT_DIR.parent
VAULT = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_VAULT

if not VAULT.is_dir():
    print(f"ERROR: Vault path does not exist or is not a directory: {VAULT}", file=sys.stderr)
    sys.exit(2)

KNOWN_CALLOUTS = {
    "note", "abstract", "summary", "tldr",
    "info", "todo", "tip", "hint", "important",
    "success", "check", "done",
    "question", "help", "faq",
    "warning", "caution", "attention",
    "failure", "fail", "missing",
    "danger", "error",
    "bug", "example", "quote", "cite",
}

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|[^\]]+)?\]\]")
EMBED = re.compile(r"!\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|[^\]]+)?\]\]")
CALLOUT = re.compile(r"^\s*>\s*\[!([a-zA-Z]+)\]", re.M)
HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.M)
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)

def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks (```...```) and inline code (`...`) so we
    don't mistake bash `[[ -f X ]]` test syntax for Obsidian wikilinks."""
    # Fenced first
    text = re.sub(r"```.*?\n.*?```", "", text, flags=re.S)
    # Indented code (4+ spaces at line start, simple heuristic)
    text = re.sub(r"^(?: {4}|\t).*$", "", text, flags=re.M)
    # Inline `code`
    text = re.sub(r"`[^`\n]+`", "", text)
    return text

def slugify_heading(h: str) -> str:
    return h.strip().lower()

def collect_files():
    files = sorted(VAULT.rglob("*.md"))
    notes: dict[str, Path] = {}
    headings_by_note: dict[str, set[str]] = {}
    for f in files:
        basename = f.stem
        relpath = str(f.relative_to(VAULT).with_suffix(""))
        notes[basename] = f
        notes[relpath] = f
        body = f.read_text()
        headings_by_note[str(f.relative_to(VAULT))] = {
            slugify_heading(m.group(2)) for m in HEADING.finditer(body)
        }
    return files, notes, headings_by_note

def audit_file(f: Path, notes, headings_by_note):
    issues = []
    raw = f.read_text()
    text = strip_code_blocks(raw)
    rel = str(f.relative_to(VAULT))

    m = FRONTMATTER.match(raw)
    if not m:
        issues.append(("frontmatter", "MISSING — no `---` frontmatter block"))
    else:
        try:
            fm = yaml.safe_load(m.group(1))
            if not isinstance(fm, dict):
                issues.append(("frontmatter", "Frontmatter does not parse to a mapping"))
            else:
                missing = [k for k in ("title", "tags", "created") if k not in fm]
                if missing:
                    issues.append(("frontmatter", f"Soft: missing conventional keys: {missing}"))
        except yaml.YAMLError as e:
            issues.append(("frontmatter", f"YAML parse error: {e}"))

    for callout_type in CALLOUT.findall(text):
        if callout_type.lower() not in KNOWN_CALLOUTS:
            issues.append(("callout", f"Unknown callout type: [!{callout_type}]"))

    own_headings = headings_by_note.get(rel, set())
    for match in WIKILINK.finditer(text):
        # Strip trailing backslash from target — Obsidian table-escape syntax
        # `[[tools/copier\|Copier]]` is valid Obsidian inside a markdown table.
        target = match.group(1).strip().rstrip("\\")
        anchor = (match.group(2) or "").strip().rstrip("\\")

        if not target:
            if anchor and slugify_heading(anchor) not in own_headings:
                issues.append(("wikilink", f"Same-note heading not found: #{anchor}"))
            continue

        if target not in notes:
            issues.append(("wikilink", f"Unresolved wikilink target: [[{target}]]"))
            continue

        if anchor:
            # Block-id anchors (#^id) reference inline block markers, not headings.
            # Validating them requires a separate pass over `^id` markers in the
            # target file. Skip for now — assume well-formed.
            if anchor.startswith("^"):
                continue
            target_rel = str(notes[target].relative_to(VAULT))
            if slugify_heading(anchor) not in headings_by_note.get(target_rel, set()):
                issues.append(("wikilink", f"Heading not found in [[{target}#{anchor}]]"))

    for match in EMBED.finditer(text):
        target = match.group(1).strip()
        ext = target.split(".")[-1].lower() if "." in target else "md"
        if ext == "md" and target not in notes:
            issues.append(("embed", f"Unresolved embed target: ![[{target}]]"))

    return issues

def main():
    files, notes, headings_by_note = collect_files()
    print(f"# Obsidian vault audit (code-block aware)\n\nFiles scanned: {len(files)}\n")

    total = 0
    files_with_issues = 0
    by_type = defaultdict(int)
    unique_unresolved = defaultdict(int)

    for f in files:
        issues = audit_file(f, notes, headings_by_note)
        if issues:
            files_with_issues += 1
            print(f"\n## {f.relative_to(VAULT)}")
            for cat, msg in issues:
                print(f"  - [{cat}] {msg}")
                total += 1
                by_type[cat] += 1
                if "Unresolved wikilink" in msg:
                    target = msg.split("[[")[1].rstrip("]")
                    unique_unresolved[target] += 1

    print(f"\n---\n\n# Summary\n")
    print(f"Files with issues: {files_with_issues}/{len(files)}")
    print(f"Total issues: {total}")
    for cat, n in sorted(by_type.items()):
        print(f"  - {cat}: {n}")

    if unique_unresolved:
        print(f"\n## Unique unresolved wikilink targets (sorted by frequency)\n")
        for target, n in sorted(unique_unresolved.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {n:3d}× [[{target}]]")

    # Exit non-zero if any issues — useful for CI / git hooks / one-liners.
    return 0 if total == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
