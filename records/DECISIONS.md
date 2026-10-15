# Decisions register

The owner's rulings and confirmed facts. **Active entries are binding for every AI session.**
New ruling → add the next ID; changed ruling → add a new entry and mark the old one
`SUPERSEDED by D-xx` (never delete). Each entry: date, ruling, why (one line), source.

## Active

| ID | Date | Ruling | Why / source |
|---|---|---|---|
| D-01 | 2026-09-25 | **Focus is the JP 1.7.0 build.** The EN Revival is paused and used only as reference. | EN heap crash unsolved after 2 months (L-05); JP more stable on the A54 |
| D-02 | 2026-09-25 | Test device = owner's **Galaxy A54, Android 14**. BlueStacks (Android 9) can't validate memory bugs or Android 14 fixes. | L-05, L-08 |
| D-03 | 2026-09-25 | Translation: **copy the EN game's text verbatim** wherever the same item/character/line exists; write natural English only for JP-only content. Capcom collab characters use official Western names. | Owner, L-09 |
| D-04 | 2026-07-14 | Keep HQ quests; keep Capcom collab content faithful; gacha redesign is designed-for but not implemented until approved. | Working decisions in JP research pass 4 |
| D-05 | 2026-06-30 | **Playable chefs are "set": never change one without asking first.** "Cook speed" requests mean workers, not chefs. | Owner, after a wrong chef edit in EN Stage U |
| D-06 | 2026-09-26 | **Balance the JP build in the same direction as EN vanilla → v1.1.0** (`jp/balance/EN_BALANCE_DIRECTION.md`). | Owner |
| D-07 | 2026-09-26 | Balance process: report-only `.xlsx` → owner reviews every item → approved rows only in `jp/balance/overrides/*.csv` → build → A54 play-test. | Owner: an AI can't judge progression feel |
| D-08 | 2026-06 | Edits are scripted with "expected current value" checks and a rollback; never hand-edit binaries; never modify original APKs; never repack `constants.bin.mid`. | Lessons from EN stages (e.g. Stage F double-apply scare) |
| D-09 | 2026-10-08 | **Toxin exchange = $2,000 per Toxin** ($20k/$50k/$250k/$1M for 10/30/175/750). | EN v1.1 deliberately reverted v1.0's ×1.5; owner confirmed for JP |
| D-10 | 2026-10-08 | **Cash vs Toxin character pricing = 2,000 cash : 1 Toxin** (same as the exchange). | Owner. Supersedes D-S1 |
| D-11 | 2026-10-08 | Records: master copy in repo `records/` (+ `jp/START_HERE.md`), mirrored to `Desktop/ZCafeStuff/Records/`; key prompts kept verbatim, other requests as one line per changelog entry. | Owner |
| D-12 | 2026-10-06 | Commit/push only when the owner asks. Release commits are dated on release day; other late commits on the commit day. | Owner, L-11 |
| D-13 | 2026-10-06 | Files written for the owner to read are also copied to `Desktop/ZCafeStuff/` (reviews → `Japanese APK Restoration/Review/`, portfolio → `Portfolio/`). | Owner prefers reading on Windows |
| D-14 | 2026-10-08 | **No AI attribution in git**: no `Co-Authored-By: Claude` trailers or "Generated with Claude Code" lines in commits/PRs. The 16 commits that had one were rewritten and force-pushed (old history kept locally in `refs/backup/before-claude-line-removal/`). | Owner: GitHub showed "claude" as a project contributor |
| D-15 | 2026-10-09 | **Release builds from v6 include the stability fixes and offline mode**: `jp/stability/lib_fixes.py` (native bug fixes, checked byte patches) and `offline_patch.py` (no server requests), applied by `jp/english/build.py`. Debug/test builds (`make_debug_apk.py`) are never distributed. | Owner: "make v6 apply ALL these fixes" after the crash hunt |
| D-16 | 2026-10-10 | **Describe compatibility as 32-bit app support, not by Android version.** The game is Capcom's 32-bit ARM code: it runs on phones whose CPU and Android build support 32-bit apps (A54 yes; Pixel 7+ no). Android versions only set which compatibility fixes are needed. Don't call builds "Android 14 builds". | Owner. `jp/research/device-compatibility.md (local only, gitignored)` |
| D-17 | 2026-10-10 | **Public JP versions are numbered separately from internal builds.** Internal build 6 = public **v0.1** (tag `v0.1` in the separate repo `zombie-cafe-revival-jp`, see D-18), not "beta", no "coming soon" text. Internal build numbers stay in `VERSIONS.md`. | Owner: the public doesn't know what "6" means |
| D-18 | 2026-10-10 | **JP releases live in their own repo, `dark-chocolate-enjoyer/zombie-cafe-revival-jp`** (README + releases only; code stays in this repo). This repo's README only says "For the JP version, check out Zombie Cafe JP". | Owner: one Releases page per game, no mixed EN/JP list |
| D-19 | 2026-10-09 | **Flag important caveats unprompted**: naming, risks, untested builds or anything hard to undo is raised with a recommendation before acting, even when not asked. | Owner, on learning unfinished EN builds had been tagged v1.0/v1.1 without a warning: "Why wouldn't they tell me this?" (was in Claude's private memory until 2026-10-15) |
| D-20 | 2026-10-10 | **Nothing public unless the owner asks**: no new files in published folders such as `docs/`; stage exact paths, never `git add -A`. | Owner, after finding pages placed in `docs/jp-revival/`: "dont put anything on github unless instructed" (was in Claude's private memory until 2026-10-15) |
| D-21 | 2026-10-15 | **Agent workflow**: `AGENTS.md` is the one rulebook for every AI tool (Claude Code loads it via `CLAUDE.md`); Claude's private memory holds no project rules. Claude Code hooks (`.claude/settings.json`) add the current state at session start, send the agent back if files changed without a changelog entry, and sync the records at session end. Owner findings are recorded when the owner writes `log: …`. `jp/START_HERE.md` keeps the current state in one dated Now block and links to other records instead of repeating them. | Owner approved the workflow review (L-21) |

## Confirmed game mechanics (owner-verified in EN; re-check in JP when it matters)

- Playable chef (`PlayableFlag`/EN `U14` = 1) cooks and serves but **cannot raid**; its Energy, Regen and Attack are dead stats.
- The chef's **CookSpeedBonus and TipMultiplier apply to every cook** (up to ~12 at once) — the strongest levers in the game. Chef TipRating has no engine cap.
- Workers (non-chef, cost > 0) cook, serve and raid; value = Energy/Attack/Speed. Their TipRating and CookSpeed are self-only, so tip is valued low.
- Human (cash) and zombie (toxin) versions of a character are two price points of one character (cash version ≈ TipMultiplier −1).
- JP Energy/Speed/Attack/TipRating are exactly 10× EN; TipMultiplier and Cost share EN's scale.
- **Tips (read from JP game code, 2026-10-09; `jp/reverse/TIPS_AND_CUSTOMERS.md`)**: per serving, tip = price × 0.2 × min(server's TipRating + equipment, 100)/100 × **current chef's** TipMultiplier. JP TipRating is **capped at 100**; EN uses TipRating/10 uncapped, so JP 100 = EN 10 and EN values above 10 have no JP equivalent. Ingredient cost plays no part in tips.
- **Customers (code)**: live arrivals ~2.7/min at rating 0 up to ~12.4/min at full rating (hard ceiling; one serving each). App closed: time counts at 0.25×, staff serve 2/min each → ~0.7/min with 2 staff, max ~2.3/min.
- Selling speed (owner, 2026-10-08): a 5★ café sells ~10 servings/min mid-game (300 servings ≈ 30 min), 20–50/min late game. With the app closed, the background "café still running" script sells ~10–20× slower (model: 15×).

## Superseded

| ID | Date | Was | Superseded by |
|---|---|---|---|
| D-S1 | 2026-06-30 | Cash characters valued at 3,000 cash : 1 Toxin (raised from 2,000 because cash units were too strong) | D-10 |
| D-S2 | 2026-06-22 | Toxin exchange ×1.5: $30k/$75k/$375k/$1.5M (EN v1.0 Stage I) | D-09 |
