#!/usr/bin/env bash
# Copies demo/ into a new folder ready for `git init` + push. Pushes nothing.
set -euo pipefail
dest="${1:-../safecode-demo}"
[ -e "$dest" ] && { echo "$dest already exists"; exit 1; }
mkdir -p "$dest"
cp -r demo/. "$dest"/
rm -rf "$dest/backup" "$dest/.pytest_cache"
echo "Created $dest. Next: cd $dest && git init -b main && git add -A && git commit -m 'demo app' (see SETUP.md)"
