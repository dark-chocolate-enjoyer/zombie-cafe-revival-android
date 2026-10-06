# Zombie Cafe Revival — project guide for Claude

**Current focus (since 2026-09-25): the Japanese 1.7.0 build.** Read `jp/START_HERE.md`
before doing anything; it has the status, repo map, build/install/test commands,
balance workflow and rules. The English Revival (`src/`, `docs/balance/`,
`docs/reverse/`) is paused and serves as reference only.

Essentials:
- Build the JP APK: `cd jp/english && python3 build.py`. Balance changes go ONLY through
  owner-approved rows in `jp/balance/overrides/*.csv` (validated by the build).
- Balance direction: take JP the way the owner took EN from vanilla to v1.1.0 — see
  `jp/balance/EN_BALANCE_DIRECTION.md` (measured; JP char stats = 10x EN).
- Balance work is report-only until the owner approves it. The owner reviews every
  character/chef/dish in spreadsheets and play-tests on their Galaxy A54.
- Never change a playable chef (`PlayableFlag=1`) without asking first.
- The phone is reachable only via Windows adb: `/mnt/c/platform-tools/adb.exe`, always `--user 0`.
- Don't commit/push unless asked. Don't modify original APKs or `jp/english/work/base_json`.
- Python libs: `python3 -m pip install --target jp/english/.pylib <pkg>` (system pip is locked).
