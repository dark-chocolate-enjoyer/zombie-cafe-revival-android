# JP Zombie Cafe Revival — START HERE

Read the Now block first, then `records/DECISIONS.md` (binding rulings). Rules for AI agents: `AGENTS.md`.
Each fact has one home: rulings in DECISIONS, every build and its hash in `records/VERSIONS.md`, history in
`records/CHANGELOG.md`. This file holds the current state (Now) and how-to reference (§1–§10), and links to
the others instead of repeating them.

## Now (updated 2026-10-15)

- **Released:** JP v0.1 = internal build 6, published 2026-10-10 in its own repo
  `dark-chocolate-enjoyer/zombie-cafe-revival-jp` (D-17, D-18). Build 6 is the current base.
- **Stability:** the cafe → map crash (Scudo "corrupted chunk header") was a one-byte overrun in Capcom's
  `javaGetDeviceInfoForURL`, fixed in build 6 together with the raid and string fixes and offline mode. 20/20
  automated rounds passed; the control without the fix crashed 10/20 (`jp/stability/DEVICEINFO_BUG.md`). The
  owner left it open in the background for 24+ hours with no crash (L-22); a hand play-test with cafe → map trips
  isn't logged yet.
- **In progress (not balance):** portfolio pages `AI_WORKFLOW.md` + `TECHNICAL_WRITEUP.md` (drafts outside the
  repo, not published) and the agent workflow upgrade (AGENTS.md, hooks; L-21, D-21).
- **Next (balance):** the owner is reviewing the dish proposal `jp/balance/proposals/dishes_proposal_v2.xlsx`
  (Desktop: `Review/JP Dishes - Proposal v2 (2026-10-08).xlsx`; generator `balance/propose_dishes.py`; v1
  superseded). Event-dish rows wait on the §8 unlock decision (JP-only event dishes earn ~1.4× classic ones).
  When verdicts come back: turn Approve rows (using the workbook's "New …" values, which the owner may have
  edited) into `jp/balance/overrides/010_dishes.csv`, build, install, play-test. Then: a dish earnings model on
  the real tip/customer formulas (`reverse/TIPS_AND_CUSTOMERS.md`), the characters/chefs/workers proposal,
  furniture, and the §8 decision brief (`records/prompts/2026-09-26_jp-balance-handoff_prompt.md`).
- **Waiting on the owner** (these block most balance work):
  1. Dish proposal v2 verdicts.
  2. Roster: which of the 1,724 characters stay, and how each kept one is obtained offline (store tier /
     quest reward / level unlock / offline draw).
  3. Gacha/roulette: redesign as an offline Toxin draw, or remove.
  4. The 62 dead online quests to retire (`quest_offline_matrix.csv`).

### Roadmap progress (update at each milestone)

| Phase | Done | Remaining |
| --- | --- | --- |
| 1 Foundation + Toxin exchange | ~95% | test exchange tiers 2–4 + save/reload on the A54; `constants` decoded read-only (`reverse/`), `font3` undecoded (never repack either) |
| 2 Offline playability | ~45% | modern-Android fixes ✅ (32-bit-capable phones); server requests stopped (v6 offline mode; 3 ungated HTTP paths left: `jp/stability/offline_patch.py`); retire 62 dead online quests; offline gacha design |
| 3 English | ~95% | gacha/roulette/event art (server-only screens); `assets/EULA` still Japanese; very long bios (9–11 lines) |
| 4 Balance + content | ~10% | roster keep/cut + offline acquisition; dishes, chefs, workers, furniture, quests (D-06, D-07) |
| 5 Stability + release | ~40% | **cafe → map crash fixed in v6** (hand play-test with map trips not logged yet); device test matrix, known-issues list, release build |


## 1. Project in one paragraph

We are restoring the **Japanese Zombie Cafe 1.7.0** (Capcom/Beeline, 2016 — the
final, content-richest version) as an **offline, English, fairly balanced** game
for modern 32-bit-capable Android. The English "Zombie Cafe Revival" (Airyzz
repo, `src/`) was the previous focus but is **paused**: its native heap-corruption
crash (Scudo, map transitions) was never solved, and the JP build turned out to
be more stable on the owner's phone. English-side work is kept only as a
**reference** (especially its balance philosophy).

## 2. Builds and phones

- **Which phones:** ones that support 32-bit apps (D-16).
- **Every build**, what changed, its hash and whether it ran on the A54: `records/VERSIONS.md`. The APKs
  themselves are in the owner's local archive `ZCafeStuff/Japanese APK Restoration/Versions/`, not in the repo.
- Build 6 vs the original: text/images, the Toxin exchange, 3 native bug fixes and offline mode. No stat, price
  or progression value has been rebalanced yet.

## 3. Repo map (JP side)

```
jp/
  START_HERE.md            <- this file (current state)
  english/                 the build pipeline (produces the APK) — see §4
    build.py               ONE command builds the whole APK
    tm/, tm_src/           translation memories (jp -> en) — do not touch for balance
    lib_*.py, arsc_patch.py, smali_patch.py, img_patch.py   (translation layers, done)
    v4_compat/             how the modern-Android shell (Versions/4 = work/base_v4.apk: targetSdk + device-ID fixes) was made
    work/                  (gitignored) base_json = decoded JP ORIGINAL data, base_v4.apk shell
    out/                   (gitignored) build output: json/ (final data), bin/, the APK, reports
  balance/                 <- NEW: where balance work happens
    apply_overrides.py     applies overrides/*.csv during build (validated, see §5)
    overrides/             owner-APPROVED changes only (currently empty)
    export_current.py      regenerates snapshots/ from the latest build (incl. EN vanilla + EN v1.1 columns)
    snapshots/             foods_current.csv, characters_current.csv, furniture_current.csv
    EN_BALANCE_DIRECTION.md  <- the owner's EN vanilla->v1.1 direction, measured; READ before proposing anything
    make_en_reference.py   rebuilds reference/ (EN vanilla from git e6e654fe vs EN v1.1 = src/assets/data)
    reference/             en_food_vanilla_vs_v11.csv, en_characters_vanilla_vs_v11.csv
    propose_dishes.py      dish proposal generator (rules at the top) -> proposals/ + Desktop Review/
    proposals/             report-only proposals awaiting owner verdicts (dishes_proposal_v2 = current; v1 superseded)
  stability/               crash hunt: make_debug_apk.py + wrap.sh (malloc-debug test APK), tools/scan_use_after_delete.py,
                           README.md = findings; logs/ (git-ignored) = phone captures, save backups
  reverse/                 game-code findings: TIPS_AND_CUSTOMERS.md (tip formula, customer rates, offline
                           selling), constants_jp.json (constants.bin.mid decoded), tools/ (disassembly helpers)
  research/                (mostly gitignored) earlier report-only analysis passes 1-4;
                           only the crosswalks + roster CSV that the build/export read are committed
    pass1_inventory_schema/   schemas, balance_porting_strategy.md (READ), JP balance snapshots
    pass2_codecs_quests/      quest decode, font/image audits
    pass3_translation/        crosswalks, owner_decision_brief.md, roster_curation_brief.md
    pass4_systems_curation/   roster_curation_candidates.csv (keep/cut per character),
                              quest_offline_matrix.csv, system_dependency_map.md (server vs local)
records/                   project record (master copy, mirrored to Desktop/ZCafeStuff/Records):
                           CHANGELOG.md, DECISIONS.md, VERSIONS.md, EN_ARCHIVE.md, prompts/, sync_to_desktop.sh
AGENTS.md, CLAUDE.md       rules for AI agents (CLAUDE.md imports AGENTS.md for Claude Code)
.claude/settings.json      Claude Code hooks (scripts in .claude/hooks/): state at session start,
                           changelog check before finishing, Desktop sync at session end
docs/jp-revival/           roadmap.md, toxin-exchange.md (public-facing notes)
tool/file_types/*_jp.go    byte-identical JP codecs (used via work/rmgr binary)
src/, docs/balance/, docs/reverse/   English Revival (paused; reference only)
en_archive/                (gitignored) old EN test builds/zips/logs
```

Outside the repo: a local `Documents\Balancing Zombie Cafe\outputs\` folder holds
the backup original + earlier JP toxin builds (docs reference these paths — don't move).

## 4. Build, install, test

```bash
cd jp/english && python3 build.py            # -> out/ZombieCafe_JP_English.apk (+ out/report.txt, out/balance_applied.csv)
python3 ../balance/export_current.py         # refresh balance/snapshots/*.csv from the build
PYTHONPATH=.pylib python3 img_patch.py       # only if sprite text changes (Pillow lives in .pylib)
```
- Signing: repo `debug.keystore`, alias `alias_name`, pass `zombiecafe` (same key as all JP builds → installs over them, keeps the save).
- Phone: only visible to **Windows adb**: `A=/mnt/c/platform-tools/adb.exe`. Install needs a Windows path:
  `cp out/ZombieCafe_JP_English.apk /mnt/c/Users/<you>/jp_en.apk && $A install -r --user 0 'C:\Users\<you>\jp_en.apk'`
  Launch: `$A shell am start --user 0 -n com.capcom.zombiecafeandroidJP/.ZombieCafeAndroid`.
  Screenshot: `$A exec-out screencap -p > shot.png`. Taps must be long-ish: `$A shell input swipe X Y X Y 150`
  (screen 2340x1080). Always pass `--user 0` (a Secure Folder profile exists).
- pip is PEP-668 locked and venv is unavailable: install Python libs with `python3 -m pip install --target jp/english/.pylib <pkg>` and run with `PYTHONPATH`.
- A build that changes nothing must reproduce v6 byte-for-byte in every file except the signature — use that as a regression check
  (`build.py` applies `jp/stability/lib_fixes.py` and `offline_patch.py`; v5 + those = v6).

## 5. How balance changes MUST be made

1. Never edit `work/base_json`, `out/`, or game binaries by hand.
2. Proposals are **report-only** first (spreadsheets/CSVs for the owner). The owner
   checks every character/chef/dish themselves before anything is implemented —
   an AI cannot play-test progression, so the owner's review is the gate.
3. Only after explicit owner approval: write rows to `jp/balance/overrides/NNN_<stage>.csv`
   (`file,record_index,field,expected_current,new_value,note`). `expected_current`
   must equal the value before the change or the build aborts (catches
   double-applies / stale proposals). Text fields are rejected.
4. `python3 build.py` → check `out/balance_applied.csv` → install on the A54 → owner play-tests.
5. Keep a rollback: deleting an override file and rebuilding restores the previous state.

## 6. Data fields that matter for balance

Full schemas: `jp/research/pass1_inventory_schema/jp_data_schema_report.md`.

- **foodData (234)**: `Price` (ingredient cost), `UnlockLevel`, `CookTimeMinutes`, `Servings`,
  `PricePerServing`, `ExperiencePoints`. Snapshot adds revenue/profit/profit_per_min/xp_per_min.
- **characterData (1,724)**: `CafeLevelRequired`, `Cost`, `PurchaseWithToxin` (1 = toxin; row 148 holds 10 — raw byte, keep),
  `PlayableFlag` (1 = playable chef, = EN `U14`), `Energy`, `Speed`, `AttackStrength`, `TipRating`,
  `CookSpeedBonus`, `TipMultiplier`, `U19` (≈EN RegenBoost, unverified), `U20` (≈EN CookXPBonus, unverified), U9–U12/U21–U23 unknown.
  JP stat scales are much larger than EN (Energy up to 22,200, TipRating up to 100).
- **furnitureData (835)**: `Price`, `PurchaseWithToxin`, `UnlockLevel`, `MoneyPerHour`, `MaximumMoney`,
  `RatingBonus`, `StoveSpeedMult`, `ExperiencePoints`, `BuyMoneyAmount` (Toxin packs rows 182-185),
  JP-only unknowns `UMid`, `UTailFloat1/UTailInt/UTailFloat2` — don't balance around them until understood.
- **quest (1,020)**: `LevelGate`, `GoalAmount`, `RewardXP`, `RewardPacked` (high int16 = Toxin reward).

Roles in `snapshots/characters_current.csv`: playable_chef 78, worker_toxin 1,397,
worker_cash 62, enemy_or_event_chef 106, event_reward_or_customer 76, generic_customer 5.

## 7. What we already know (don't rediscover)

**The owner wants JP balanced in the same direction they took the English game from vanilla to
their v1.1.0** — measured in `balance/EN_BALANCE_DIRECTION.md`. Headlines: dishes = cheaper
ingredients + more servings + never-lower price/serving (profit/min up ~1.2–2.4×, biggest early/mid),
XP/min held flat, no money-losing dishes, premium food clearly beats free; chefs = TipRating ~×1.8
and TipMult ~×2 with a smooth cost ladder; workers = stronger per cost with no dominated buys.
JP↔EN mapping: 65 JP dishes are identical to EN vanilla; **JP Energy/Speed/Attack/TipRating are
exactly 10× EN** (TipMult/Cost same scale), so EN caps and targets translate ×10.

From `research/pass1_inventory_schema/balance_porting_strategy.md` (read it):
- **The gacha catalogue is the whole problem:** 1,397 toxin units, 88% strictly
  dominated (live-service power creep). Gacha/roulette prize tables were
  **server-side** and the Zombie Store needs a server → those units can't be
  obtained offline today. Balancing units nobody can get is wasted work: the
  roster keep/cut decision (pass4 `roster_curation_candidates.csv`: keep 505 /
  cut 241 / uncertain 978) and an offline acquisition design come FIRST.
- Food economy is already close to EN (shared dishes: JP price ≈1.16× EN, XP ≈1.0×); event dishes have joke prices.
- Suggested stage order there: JP-A schema closure → JP-B roster/taxonomy freeze → JP-C chefs → JP-D staff de-creep → JP-E economy → JP-F raids/quests.

Owner-confirmed game mechanics (chef vs worker stats, tips, customers), the chef rule (D-05), the
cash:Toxin character rate (2,000:1 for JP, D-10; EN's old 3,000:1 is superseded) and the Toxin exchange
prices (D-09) live in `records/DECISIONS.md`. Read them there, not from memory or old notes.

English balance reference material (the owner's accepted philosophy, EN numbers):
`docs/balance/v1.0_balance_summary.md` (food), `docs/balance/rebalance_v1_stage_o_character_rebalance/STAGE_O_SUMMARY.md`
(characters), `docs/reverse/playable_chef_mechanics.md`, EN data in `src/assets/data/*.json`. These hold EN
numbers and EN-era rates (e.g. Stage O's 3,000 cash = 1 Toxin); where they differ from DECISIONS, DECISIONS wins.

## 8. Open owner decisions

Moved to the Now block ("Waiting on the owner"), so they're updated in one place.

## 9. Don'ts

- General rules (no commits unless asked, never touch the original APK or `work/base_json`, never repack
  `constants.bin.mid`) are in `AGENTS.md` and DECISIONS (D-08, D-12). Project-specific ones:
- Don't redo translation work; if English text needs a fix, edit `english/tm*/` and rebuild.
- Don't trust EN-derived "caps" blindly — JP scales differ; measure, then propose.

## 10. Gotchas learned the hard way

- JP fonts only carry ASCII for Latin text: no accents or curly quotes (`build.py` converts é→e etc.).
- The character bio box wraps per character at 13–14 cells, so English bios are pre-wrapped with `\n`
  (a `\` marker garbles text there). The shop/furniture box word-wraps normally.
- Zombie/customer personal names are stored in the save when created; ones made before v5 stay Japanese.
- Native-lib text is overwritten in place; longer strings are relocated into freed space and their
  pointers repointed (`english/lib_refs.py` → `lib_patch.py`). Re-run `lib_refs.py` if the base lib changes.
- EN food reuses image IDs for premium variants: join JP↔EN dishes on the **first** EN row per ImageID.
- JP TipRating is capped at 100 in the tip formula (EN is uncapped, /10): never port EN TipRating ×10 above 100.
- Git push from WSL needs the Windows credential manager:
  `git -c credential.helper= -c 'credential.helper=!"/mnt/c/Program Files/Git/mingw64/bin/git-credential-manager.exe"' push …`.
  Never `git fetch --tags --force` (would clobber the corrected local tags).
