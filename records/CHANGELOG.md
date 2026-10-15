# Project changelog

One entry per milestone, oldest first; append new entries at the bottom.
Format: **date · ID · title — who**, then *Ask* (the owner's request in one line), *Did*,
*Result* (versions, hashes, verification), *Open*. Rules and rulings live in `DECISIONS.md`;
the current state lives in `jp/START_HERE.md`; APK hashes in `VERSIONS.md`.
Who: Airyzz (upstream author), Owner (Mani), Claude Code / Claude Fable (Anthropic), Codex, ChatGPT.

---

**2023-06-19 → 2024-11-22 · L-01 · Upstream revival — Airyzz**
Did: decoded the EN (and JP) APKs, wrote the Go build/pack tooling, toxin-buy patch, server
replacement, audio restore; released Zombie Cafe Revival 1.0.1. Vanilla Capcom data = git `e6e654fe`.

**2026-06-05 → 06-09 · L-02 · Modern Android compatibility (EN) — Owner + Claude Code (ChatGPT reviewing)**
Ask: make the EN APK install and run on a Galaxy A54 (Android 14).
Did: targetSdk 14→24; TEXTREL removal patch in the native lib; `getDeviceId` → constant.
Result: release `android14-compat-test-v0.1` (`60658e3f`). Docs: `docs/compat/`.

**2026-06-09 → 06-22 · L-03 · EN v1.0 balance (food + characters) — Owner + Claude Code / Claude Fable (ChatGPT reviewing)**
Ask: less grind; premium food worth buying; fairer characters.
Did: food v0.2 stages → Stage F premium (41 dishes) + Stage E free (115) + clean numbers; characters
Stage H (chefs) + J (workers); XP pacing K/K2; Toxin exchange ×1.5 (Stage I). Every stage report-only
first, applied with pre-checks and rollbacks (`docs/balance/rebalance_*`).
Result: release `v1.0v-balance-change` (APK `bb489e47`), 2026-06-22.

**2026-06-24 → 07-03 · L-04 · EN v1.1: characters + music fix — Owner + Claude Code / Claude Fable / Codex**
Did: Stage L–N review workbooks; Stage O character rebalance (steps 1–9: chefs, workers, energy/regen,
cost curve); Toxin exchange reverted to $2,000/Toxin (D-09); music silence fixed (StartMusic guard,
82-byte native patch + smali state machine).
Result: release `v1.1.0` (APK `d5127318`), 2026-07-03. Summary: `docs/balance/rebalance_v1_stage_o_character_rebalance/STAGE_O_SUMMARY.md`.

**2026-07-04 → 09-11 · L-05 · EN heap-corruption crash hunt — Claude Code / Claude Fable / "ASTRA" / Codex**
Ask: fix the A54 crash on café exit / map transitions (Scudo "corrupted chunk header").
Did: ~20 static and runtime reports, 4 trial patches (ScudoPathFix, MoveTaskOwnerFix, ASTRA arms).
Result: **not solved**; corruptor narrowed to a ≤32-byte object overflowing into 48-byte allocations.
Led to D-01 (pivot to JP). Summary: `records/EN_ARCHIVE.md`.

**2026-07-10 → 07-14 · L-06 · JP research passes 1–4 (report-only) — Claude Fable**
Ask: audit the JP 1.7.0 APK for an English, offline, balanced revival (`prompts/2026-07-10_*`).
Did: schemas; byte-identical Go codecs for 9 JP data files; quest decode; translation drafts
(UI 740/741, quests 56/56, furniture names, food); roster keep/cut and offline-quest matrices; proved
gacha prize tables are server-side.
Result: `jp/research/pass1…pass4`.

**2026-07-24 → 07-26 · L-07 · JP Toxin exchange port — ChatGPT (Jul 24 build; icon build's author unrecorded), audited by Claude Code**
Did: furniture rows 182–185 → cash-for-Toxin packs; 8-byte native patch (Type-10 purchase → addToxin);
Toxin shop icons. Result: JP `Versions/1–3` (see `VERSIONS.md`); tier 1 confirmed in BlueStacks.

**2026-09-25 · L-08 · Pivot to JP; Android 14 build — Claude Code (Opus 5.5)**
Ask: give up on EN memory issues; make the JP APK run on 32-bit-capable Android like EN; report what
was changed vs the original; organise Desktop/ZCafeStuff.
Did: targetSdk 16→24 (1 byte); 9 device-ID reads → constant (JP lib needed no TEXTREL fix);
Desktop split into English/Japanese folders.
Result: JP v4 (`3b4a1fc4`), installs and boots on the A54.

**2026-09-25 · L-09 · JP full English build — Claude Code (Opus 5.5)**
Ask: finish the English translation; copy EN-game text verbatim wherever possible (D-03).
Did: all data text (≈1,470 names, ≈2,450 bios, 410 furniture descriptions), 761 native-lib strings
(in place, 84 relocated), Java dialogs, app name "Zombie Cafe JP", help/error HTML, 99 sprites
(EN art copied where it exists). Pipeline: `jp/english/build.py`.
Result: JP v5 (`1f95c7f9`), verified on the A54. Open: gacha/roulette/event art (server-only screens).

**2026-09-26 · L-10 · Handoff prep for the balance phase — Claude Code (Opus 5.5)**
Ask: organise the repo so a fresh chat can do the balance rework; measure the EN direction.
Did: JP work consolidated under `jp/`; balance overrides hook (`jp/balance/apply_overrides.py`) +
snapshots; EN vanilla vs v1.1 measured (`jp/balance/EN_BALANCE_DIRECTION.md`): JP character stats are
exactly 10× EN; 65 JP dishes equal EN vanilla. Handoff prompt: `prompts/2026-09-26_*`.

**2026-10-06 · L-11 · Git history backfilled; tags fixed; portfolio audits — Claude Code**
Did: Jun–Sep work committed to `main` (`237bfbb4`, release commits dated on release day); tags
`v1.0v-balance-change`/`v1.1.0` repointed to verified sources; audits in `Desktop/ZCafeStuff/Portfolio/`.

**2026-10-08 · L-12 · Record keeping set up — Claude Code (Opus 5.5)**
Ask: a minimal, traceable record of changes, decisions and key prompts for AIs and humans.
Did: `records/` (this file, `DECISIONS.md`, `VERSIONS.md`, `EN_ARCHIVE.md`, `prompts/`), Desktop mirror
(`records/sync_to_desktop.sh`), Claude memory folded into records and trimmed (backup in
`en_archive/claude_memory_backup_2026-10-08/`). Decisions D-09, D-10 recorded.

**2026-10-08 · L-13 · Dish balance proposal v1 — Claude Code (Opus 5.5)**
Ask: "Make a CSV of the proposed changes you want to make to the dishes … so I can manually review all the changes."
Did: `jp/balance/propose_dishes.py` → `proposals/dishes_proposal_v1.{csv,xlsx}` (+ Desktop `Review/`). Rules from
EN vanilla→v1.1: 65 EN-identical dishes get the owner's EN v1.1 numbers; others lifted to the EN v1.1 median margin
for their cook length (cost cut ≤60% → servings ≤+20% → $/serving +1), capped at $6.5/min; quick-cash dishes held;
cook time/XP/unlock unchanged; flavour numbers kept. 126 of 234 dishes change. Nothing applied.
Open: owner verdicts; event-dish offline unlock (§8) decides whether they get the premium lift.

**2026-10-08 · L-14 · Dish proposal v2: matches the owner's EN pattern; buff colour-coding — Claude Code (Opus 5.5)**
Ask: colour-code buffs/nerfs (green shades by size); do the JP-only dishes follow the EN v1.1 buff pattern?
Did: back-test showed v1's single margin target missed the owner's EN changes on 40/173 dishes. v2 treats each dish
like the middle of its 5 most similar free EN dishes (same % cost/servings change, same $/serving bump; LOO error
20% vs 41% for no change). Guards: never lower profit or $/serving; $16+/serving dishes held (no EN equivalent);
loose matches flagged. Workbook: 9-shade green/red shading on every changed number (cost … profit, $/min, margin,
XP/min) and per dish, live as the owner edits; Summary compares groups + chart.
Result: 148 of 234 change. Buffs follow EN in every group, but JP-only (mostly event) dishes already earned 2.2×
classic dishes per minute; after v2 the gap is 1.4×. Open: event-dish offline unlock (§8) decides those rows.

**2026-10-08 · L-15 · "claude" removed from GitHub contributors — Claude Code (Opus 5.5)**
Ask: "one of the contributors on my project is now claude … can you remove that?"
Cause: the 16 commits made by Claude Code on 2026-10-06 (L-11, incl. the backdated v1.0/v1.1 release commits) ended
with Claude Code's default `Co-Authored-By: Claude` line, which GitHub counts as a contributor.
Did: rewrote only those message lines (files, authors, dates identical; verified), force-pushed `main` (now `237bfbb4`)
and tags `v1.0v-balance-change`/`v1.1.0`; releases still attached. Old refs: `refs/backup/before-claude-line-removal/`.
Rule D-14 + CLAUDE.md: no AI attribution lines in commits/PRs. Also recorded the owner's selling-speed numbers.

**2026-10-09 · L-16 · Tip formula and customer rates read from the game code — Claude Code (Opus 5.5)**
Ask: "find a calculation of how tipRating is calculated to determine the tip bonus for each sold dish … look at the .so files".
Did: disassembled the JP lib (it keeps its C++ names); decoded `constants.bin.mid` by emulating `Constants::load`
(Unicorn; all 11,269 bytes, 590 constants). Write-up `jp/reverse/TIPS_AND_CUSTOMERS.md`, tools in `jp/reverse/tools/`.
Result: tip = price × 0.2 × min(TipRating,100)/100 × chef TipMultiplier (EN: TipRating/10, uncapped); live arrivals
max ~12.4/min; app-closed selling 0.25× time and 2 servings/min per staff (~5–34× slower). Rules in DECISIONS.
Open: build the dish earnings model on these formulas; JP TipRating cap affects the character balance port.

**2026-10-09 · L-17 · JP has the EN heap crash; malloc-debug build finds a raid use-after-free — Claude Code (Opus 5.5)**
Ask: capture logcat while the owner loops cafe → map → cafe until it crashes; then "Build the debug version".
Did: v5 crashed on the 13th trip, Scudo "corrupted chunk header" in `Cafe::~Cafe` (= EN crash; one crash predates v5).
Built 5d (`jp/stability/`: debuggable + `wrap.sh` malloc debug). Owner: 25 trips clean; first raid entry crashed
reading freed memory. Disassembly: `GameStateRaid::init` walks a list it just deleted (copy-paste typo, 1-byte fix
`0x17302a`). Whole-lib scan: the only such case. Save backed up via run-as (`jp/stability/logs/`, git-ignored).
Result: 5d `81aac572…` on the A54. The buggy block runs only when a saved raid is resumed; the v5 crash run's raid was
newly generated, so it is NOT the map-crash cause (first called "prime suspect", corrected same day). Open: run 3
(`free_track=16384`) for the map crash; raid fix needs owner OK.
Later: owner approved the fix for debug builds → 5e (fix + `free_track=16384`): resumed raid OK, 37 trips clean, 0 reports.
Also found: the 16:01 crash was on the FIRST cafe exit after launch (no raid). Map-crash cause still open; malloc debug
masks it (likely a long-lived culprit: guards are only checked when a block is freed).
Then GWP-ASan (5f; needed `exec -a` because libc skips GWP_ASAN_* vars in `app_process*`): launch 3 of 4 caught
"Buffer Overflow, 0 bytes right of a 16-byte allocation", a READ in `String::operator+=(String)` from `ObjectiveDialog`
during cafe load. Root: `StringBuffer::toString()` mallocs exactly the text length, no terminator (153 call sites).
5g = fix for that (owner-approved): still crashed (Scudo) ~1 s after the cafe loaded on a quick Map press, so not the
map-crash cause. Owner noticed quick Map presses crash. Found: failed server requests run the game's native callback
(`CCServer::Android_ServerCallback`) on Java background threads, unsynchronised with the game thread. Docs:
`jp/stability/STRING_BUG.md`, README findings 9-11.
5h = every Java → native call behind one Java lock (verified working: Android logged a network callback waiting on the
game thread's frame). Still crashed (launch 2: 12 trips + 2 raids, Scudo in `Cafe::~Cafe` `delete[]`). The native lib
creates no threads of its own, so game code ran one thread at a time → not a threading race; single-thread corruption.
Watchpoint plan: verified the PC reaches the phone over Wi-Fi (192.168.0.219) and that a debugger can run in the game's
sandbox; not continued this session (debugger files removed from the phone). Open: v6 = v5 + both fixes; dead-server
request elimination test; automated GWP-ASan loop.

**2026-10-09 · L-18 · Cafe → map crash solved: Capcom off-by-one in `javaGetDeviceInfoForURL`; v6 — Claude Code (Opus 5.5)**
Ask: run the dead-server elimination and an automated GWP-ASan loop, then "make v6 apply ALL these fixes".
Did: `tools/auto_loop.py` (adb: launch → Play → Map, classify). A (online) 15/40 crashed, B (offline) 17/39: network ruled out.
GWP-ASan caught `buf = malloc(len); buf[len] = 0` in `javaGetDeviceInfoForURL` (80-byte text + 16-byte Scudo header = one 96-byte slot
exactly → the zero hits the next block's header). Fixed (4 bytes). v6 = v5 + 3 lib fixes + offline, via `build.py`.
Result: v6 `8a9a7716…` 0/20 crashes; control (v6 minus that fix) 10/20; victims all 96-byte multiples apart. Docs: `jp/stability/DEVICEINFO_BUG.md`.
Open: owner hand play-test of v6; EN lib has no such function (EN crash cause unchecked); 3 ungated HTTP paths remain.
Release prep: internal build 6 = public **v0.1** (owner: no "beta", no version history implied): asset `ZombieCafe-JP-English-v0.1.apk` (same hash),
notes `release-assets/release-notes-v0.1.md` (local only, gitignored). Published from a new repo `zombie-cafe-revival-jp`
(tag `v0.1`; local folder `repos/zombie-cafe-revival-jp/`, README copied from the EN one); this README now only points there (D-18).

**2026-10-10 · L-19 · Device compatibility documented: 32-bit support, not Android version — Claude Code (Opus 5.5)**
Ask: "stop calling it android 14 … its because its a phone which supports 32 bit games … figure out exactly why".
Did: read from the A54 (`abilist32 = armeabi-v7a,armeabi`, `zygote64_32`, Cortex-A78 + A55, `app_process32`) and the lib
(ELF32 ARMv5TE/Thumb-1, `armeabi` only, links 32-bit system libs, no TEXTREL); checked Pixel 7+ 64-bit-only policy and
AArch32-less Arm cores. Wrote `jp/research/device-compatibility.md (local only, gitignored)`; reworded release notes, START_HERE, stability docs; D-16.

**2026-10-10 · L-20 · JP v0.1 published — Owner (Claude Code prepared)**
Ask: release the JP game in its own repo; main README only points there; owner publishes it himself.
Did: new repo `dark-chocolate-enjoyer/zombie-cafe-revival-jp` (README from the EN one, banner); release `v0.1`
"Zombie Cafe JP (English) v0.1" (not pre-release, latest) with `ZombieCafe-JP-English-v0.1.apk`; main README commit `1e5b79b8`.
Fixed: WSL git had no user.email (commits stamped `itzsweetz@Manis-Computer.localdomain`, unlinked on GitHub; 24 older main-repo
commits keep it); now the GitHub noreply address, JP commit amended (`0eb14f8`).
Result: GitHub asset sha256 = `8a9a7716…` = build 6, verified via the GitHub API.

**2026-10-10 → 10-15 · L-21 · Portfolio pages drafted; agent workflow upgraded — Owner + Claude Code (Opus 5.5)**
Ask: a page showing how the AI agents were directed and checked, split into "AI workflow" + a technical write-up; then
"critique this workflow … how would you improve upon this?" and show it as a diagram.
Did: drafts `AI_WORKFLOW.md` + `TECHNICAL_WRITEUP.md` (outside the repo, with a GitHub-style preview on the Desktop; Mermaid diagram);
old Pages files staged for deletion (`docs/index.html`, `docs/engineering.html`, …). Workflow: new `AGENTS.md` (shared rulebook;
Claude-memory rules moved in as D-19, D-20); `CLAUDE.md` imports it; hooks in `.claude/settings.json` + `.claude/hooks/` (session-start
state, changelog check before finishing, Desktop sync at session end), pipe-tested; START_HERE gets a dated Now block, §7 duplicate of
DECISIONS removed (it still said 3,000 cash : 1 Toxin, superseded by D-10); D-21.
Open → answered 10-15: offline-line addition dropped; 24-hour claim dropped from the page (L-22); owner commits and pushes the pages,
records, JP code and hooks himself from prepared commands.

**2026-10-15 · L-22 · Owner log: v0.1 left open in the background 24+ hours — Owner**
Log: build 6 (public v0.1) stayed open in the background on the A54 for over 24 hours, some time between 10-10 and 10-14;
no crash, nothing went wrong. Not a test of the cafe → map crash: in the background the game stops its loop (`onPause` →
`GLSurfaceView.onPause()`, checked in the EN smali), so no map trips ran. Hand play-test with map trips still open (VERSIONS row 6).

**2026-10-15 · L-23 · Stale 3,000 : 1 cash rate traced and removed — Claude Code (Opus 5.5)**
Ask: newer sessions kept using 3,000 cash = 1 Toxin; why, and fix it.
Did: cause: D-10 (2,000 : 1, 10-08) superseded D-S1 in DECISIONS, but copies of the old rate stayed in START_HERE §7 (committed
10-06, never revisited), `jp/balance/EN_BALANCE_DIRECTION.md` (read-first for balance work) and the local `STAGE_O_SUMMARY.md`
that START_HERE points to. The checklist only said "update DECISIONS". Now: §7 points to DECISIONS (L-21); the EN docs are
labelled EN-only with D-10; AGENTS.md checklist step 2 says to grep for the old value when a ruling changes.

**2026-10-15 · L-24 · DECISIONS always loaded; portfolio pages tightened — Owner + Claude Code (Opus 5.5)**
Ask: import DECISIONS in CLAUDE.md; plainer page style (no "In 30 seconds", no bold-lead bullets); compact the technical write-up;
identify the games by game version, not Android version.
Did: `CLAUDE.md` now imports `@AGENTS.md` and `@records/DECISIONS.md` (diagram + table updated). AI_WORKFLOW: "Summary", plain lead
line, plain rule bullets. TECHNICAL_WRITEUP 2,813 → 1,881 words; crash attempts as a table; EN = game version 1.1.2.0a, JP = 1.7.0
(both read from the APK manifests). JP crash section rebuilt around the cafe → map crash (Scudo background now sits with
that bug; raid and string bugs moved to "found along the way"). Credits sections dropped (README already credits Airyzz).
Pages copied into the repo root for the owner's push.
