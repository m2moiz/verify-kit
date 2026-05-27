#!/bin/sh
# check_preset_pii.sh — D-W13 PII guard for preset files.
#
# Called by the pre-commit hook (via .pre-commit-config.yaml) on any staged
# presets/*.yml file. Also runnable standalone:
#   bash scripts/check_preset_pii.sh presets/personal.local.yml
#
# Exit codes:
#   0 — no PII detected
#   1 — PII pattern found in at least one file
#
# Pitfall §9 (verify-kit 07-RESEARCH.md): three-layer PII protection.
#   Layer 1: .gitignore excludes presets/*.local.yml
#   Layer 2: THIS SCRIPT greps staged preset files
#   Layer 3: CI preset-schema-check.yml asserts _schema_version (drift detection)
#
# ── Maintainer-name regex (configurable) ──────────────────────────────────────
# Uncomment and edit the line below to block commits containing the maintainer's
# real name. Forks should substitute their own name(s).
#   MAINTAINER_NAME_REGEX="(Your Real Name|YourHandle)"
MAINTAINER_NAME_REGEX=""

# ── Email allowlist ────────────────────────────────────────────────────────────
# These domains are safe placeholder values committed intentionally.
ALLOWED_EMAIL_DOMAINS="example\\.com|example\\.org"

# ── Script body ───────────────────────────────────────────────────────────────
set -eu

# If no arguments provided, scan all non-local preset files.
if [ $# -eq 0 ]; then
    set -- presets/*.yml 2>/dev/null || true
fi

FOUND_PII=0

for FILE in "$@"; do
    [ -f "$FILE" ] || continue

    LINE_NUM=0
    while IFS= read -r LINE; do
        LINE_NUM=$((LINE_NUM + 1))

        # ── Email pattern check ───────────────────────────────────────────────
        # Match standard email format. The grep -o extracts matched portions so
        # we can check the domain against the allowlist before flagging.
        EMAILS=$(printf '%s' "$LINE" | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' || true)
        if [ -n "$EMAILS" ]; then
            while IFS= read -r EMAIL; do
                DOMAIN=$(printf '%s' "$EMAIL" | sed 's/.*@//')
                # Check if domain is in the allowlist
                if ! printf '%s' "$DOMAIN" | grep -qE "^($ALLOWED_EMAIL_DOMAINS)$"; then
                    printf 'PII detected in %s:%d: %s\n' "$FILE" "$LINE_NUM" "$EMAIL" >&2
                    FOUND_PII=1
                fi
            done <<EOF
$EMAILS
EOF
        fi

        # ── Maintainer-name regex check ───────────────────────────────────────
        if [ -n "$MAINTAINER_NAME_REGEX" ]; then
            if printf '%s' "$LINE" | grep -qE "$MAINTAINER_NAME_REGEX"; then
                MATCH=$(printf '%s' "$LINE" | grep -oE "$MAINTAINER_NAME_REGEX" | head -1)
                printf 'PII detected in %s:%d: %s\n' "$FILE" "$LINE_NUM" "$MATCH" >&2
                FOUND_PII=1
            fi
        fi
    done < "$FILE"
done

if [ "$FOUND_PII" -eq 1 ]; then
    printf '\nIf this is intentional, commit with --no-verify (documented in presets/README.md).\n' >&2
    exit 1
fi

exit 0
