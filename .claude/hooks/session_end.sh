#!/usr/bin/env bash
# SessionEnd hook: mirror the records to the owner's Windows Desktop (D-11), so the Desktop copy is
# never older than the last session. Skipped on machines without that Desktop folder.
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
[ -d /mnt/c/Users/New/Desktop/ZCafeStuff ] || exit 0
"$ROOT/records/sync_to_desktop.sh" >/dev/null 2>&1 || true
