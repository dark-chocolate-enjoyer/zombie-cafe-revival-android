#!/usr/bin/env bash
# One-way mirror of the project record to the owner's Windows Desktop.
# The repo is the master copy (D-11): never edit the Desktop copies — they are
# overwritten on every run. Run at the end of every session that changed a record.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DESK="/mnt/c/Users/New/Desktop/ZCafeStuff"
OUT="$DESK/Records"

rm -rf "$OUT"
mkdir -p "$OUT/prompts"
cp "$REPO"/records/{CHANGELOG,DECISIONS,VERSIONS,EN_ARCHIVE}.md "$OUT/"
cp "$REPO"/records/prompts/*.md "$OUT/prompts/"
cp "$REPO/jp/START_HERE.md" "$OUT/START_HERE (JP status).md"
cp "$REPO/jp/balance/EN_BALANCE_DIRECTION.md" "$OUT/EN_BALANCE_DIRECTION.md"
printf 'Read-only mirror of zombie-cafe-revival/records (synced %s).\nEdit the repo copies, then run records/sync_to_desktop.sh.\n' \
  "$(date '+%Y-%m-%d %H:%M')" > "$OUT/_MIRROR - do not edit.txt"
# the build register also sits next to the APKs it describes
cp "$REPO/records/VERSIONS.md" "$DESK/Japanese APK Restoration/Versions/VERSIONS.md"
echo "synced records -> $OUT"
