# Zombie Cafe Revival — rules for AI agents

The rulebook for every AI tool working in this repo. Codex and similar tools read this file
directly; Claude Code loads it through `CLAUDE.md`. The owner (Mani) directs the work: agents
investigate, propose, and implement only what the owner approves.

**Current focus (since 2026-09-25): the Japanese 1.7.0 build.** The English Revival (`src/`,
`docs/balance/`, `docs/reverse/`) is paused; summary in `records/EN_ARCHIVE.md`.

## Read first

1. `jp/START_HERE.md`: the **Now** block (current state, next step, what's waiting on the owner),
   then the section your task needs (build/test commands, balance procedure, gotchas).
2. `records/DECISIONS.md`: the owner's rulings. Active entries are binding.

When needed: `records/CHANGELOG.md` (history; the last few entries are usually enough),
`records/VERSIONS.md` (every APK and its hash), `records/EN_ARCHIVE.md` (paused English work), and
topic notes such as `jp/stability/README.md` and `jp/balance/EN_BALANCE_DIRECTION.md`.

## Rules

- **Report first.** Proposals are report-only until the owner approves them (D-07).
- **Balance** changes go ONLY through owner-approved rows in `jp/balance/overrides/*.csv`, validated
  by the build, in the same direction as EN vanilla → v1.1.0 (D-06). Never change a playable chef
  without asking (D-05).
- **Scripted, checked edits.** Never hand-edit binaries; never modify the original APKs or
  `jp/english/work/base_json` (D-08).
- **Build** the JP APK: `cd jp/english && python3 build.py`.
- **Phone:** the Galaxy A54, reachable only via Windows adb (`/mnt/c/platform-tools/adb.exe`),
  always with `--user 0`.
- **Python libs:** `python3 -m pip install --target jp/english/.pylib <pkg>` (system pip is locked).
- **Git:** commit or push only when the owner asks (D-12). No AI attribution lines in commits or PRs
  (D-14). Stage exact paths (`git add <path>`), never `git add -A`.
- **Nothing public unless the owner asks:** no new files in published folders such as `docs/`, and
  nothing posted or uploaded anywhere (D-20).
- **Flag important caveats unprompted:** naming, risks, untested builds or anything hard to undo goes
  to the owner, with a recommendation, before you act (D-19).
- **Compatibility** is described as 32-bit app support, never by Android version (D-16).

## Owner log

When the owner writes `log: …` (a play-test result, something they noticed, a decision), append it
to `records/CHANGELOG.md` as an entry with who = Owner. If it changes a build's status, update
`records/VERSIONS.md` and the Now block in `jp/START_HERE.md`; if it's a ruling, add it to
`records/DECISIONS.md`.

## End of every session that changed something

Keep it short: record, don't narrate.

1. Append one entry to `records/CHANGELOG.md` (date · ID · title — who; Ask / Did / Result / Open,
   ≤8 lines).
2. New or changed owner ruling → `records/DECISIONS.md` (supersede, never delete). Then search the repo for
   the old value (e.g. `grep -rn "3,000"`) and replace any copy with a pointer to the D-number, so no
   other file keeps teaching the old rule.
3. New APK → a row in `records/VERSIONS.md` with its hash.
4. Refresh the Now block in `jp/START_HERE.md` (and its date) at every milestone, not only for
   new APKs.
5. A prompt written to hand work to another session → save it verbatim in
   `records/prompts/YYYY-MM-DD_<topic>.md`.
6. Files for the owner to review → `Desktop/ZCafeStuff/` (reviews → `Japanese APK Restoration/Review/`,
   portfolio → `Portfolio/`) (D-13).
7. Run `records/sync_to_desktop.sh`. (In Claude Code a hook also runs it when the session ends.)
