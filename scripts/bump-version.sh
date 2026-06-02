#!/usr/bin/env bash
set -euo pipefail

COMPONENT="${1:-}"
if [[ ! "$COMPONENT" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: $0 major|minor|patch" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
VERSION_FILE="$ROOT/VERSION"
CHANGELOG_FILE="$ROOT/CHANGELOG.md"

CURRENT="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$COMPONENT" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
TODAY="$(date +%Y-%m-%d)"

echo "$NEW_VERSION" > "$VERSION_FILE"

ENTRY="## [$NEW_VERSION] - $TODAY\n\n### Note\n- Bump $COMPONENT version\n"
TMPFILE="$(mktemp)"
printf "%s\n" "$ENTRY" > "$TMPFILE"
cat "$CHANGELOG_FILE" >> "$TMPFILE"
mv "$TMPFILE" "$CHANGELOG_FILE"

git -C "$ROOT" add VERSION CHANGELOG.md
git -C "$ROOT" commit -m "chore: bump version to v$NEW_VERSION"
git -C "$ROOT" tag "v$NEW_VERSION"

echo "Bumped to v$NEW_VERSION"
