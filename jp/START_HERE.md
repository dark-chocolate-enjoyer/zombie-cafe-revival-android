# JP Zombie Cafe Revival — START HERE

Last updated 2026-09-26. Read this file first; it is the single entry point for
any new session. Everything below is current unless marked otherwise.

## 1. Project in one paragraph

We are restoring the **Japanese Zombie Cafe 1.7.0** (Capcom/Beeline, 2016 — the
final, content-richest version) as an **offline, English, fairly balanced** game
for modern 32-bit-capable Android. The English "Zombie Cafe Revival" (Airyzz
repo, `src/`) was the previous focus but is **paused**: its native heap-corruption
crash (Scudo, map transitions) was never solved, and the JP build turned out to
be more stable on the owner's phone. English-side work is kept only as a
**reference** (especially its balance philosophy).

## 2. Current state (all verified on the owner's Galaxy A54, Android 14)

| Version (owner's local build archive `ZCafeStuff/Japanese APK Restoration/Versions/`, not in the repo) | What |
| --- | --- |
| `0 - ...ORIGINAL (untouched, do not edit).apk` | preserved JP 1.7.0, sha256 `015d265d…8942` |
| `3 - ...toxin-icons` | cash→Toxin shop exchange (4 packs) + Toxin icons |
| `4 - ...Android14-32bit` | + targetSdk 24 + 9 device-ID fixes (installs/boots on Android 14) |
| **`5 - ...ENGLISH_Android14 LATEST`** | **+ full English translation. This is the current base.** |

v5 changes vs original are **text/images + the Toxin exchange only**: no stat,
price or progression value has been rebalanced yet. The full change list is in
`ZCafeStuff/Japanese APK Restoration/Docs/2 - What Was Changed vs Original JP APK.md`;
the roadmap/checklist is `Docs/1 - JP Restoration Checklist.md`.

## 3. Repo map (JP side)

```
jp/
  START_HERE.md            <- this file
  HANDOFF_PROMPT_balance.md  prompt used to start the balance-rework session
  english/                 the build pipeline (produces the APK) — see §4
    build.py               ONE command builds the whole APK
    tm/, tm_src/           translation memories (jp -> en) — do not touch for balance
    lib_*.py, arsc_patch.py, smali_patch.py, img_patch.py   (translation layers, done)
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
  research/                (mostly gitignored) earlier report-only analysis passes 1-4;
                           only the crosswalks + roster CSV that the build/export read are committed
    pass1_inventory_schema/   schemas, balance_porting_strategy.md (READ), JP balance snapshots
    pass2_codecs_quests/      quest decode, font/image audits
    pass3_translation/        crosswalks, owner_decision_brief.md, roster_curation_brief.md
    pass4_systems_curation/   roster_curation_candidates.csv (keep/cut per character),
                              quest_offline_matrix.csv, system_dependency_map.md (server vs local)
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
- A build that changes nothing must reproduce v5 byte-for-byte in every file except the signature — use that as a regression check.

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

Owner-confirmed mechanics from the English game (verify they hold in the JP engine):
- **Playable chef** (`PlayableFlag=1`) cooks and serves but **cannot raid**; its Energy, Regen and Attack are **dead stats**.
  Its `CookSpeedBonus` and `TipMultiplier` apply **globally to every cook** (up to ~12 at once), so they're the most powerful stats in the game.
  `TipRating` has no engine cap (EN policy scaled toward ~25).
- **Owned/infectable workers** (non-chef, Cost>0) cook, serve AND raid; Energy/Attack/Speed are their real value.
  Their TipRating/CookSpeed apply only to themselves, so tip is valued low. EN pricing rule: **3,000 cash ≈ 1 Toxin**.
- Human variant = cheaper **cash** skin, zombie variant = premium **toxin** skin of the same character (not duplicates).
- **Never change a playable chef without asking the owner first.** "Cook speed" requests mean workers, not chefs.
- Toxin exchange: JP build currently uses Airyzz's original $20k/$50k/$250k/$1M for 10/30/175/750 Toxin;
  EN v1.1 settled on $30k/$75k/$375k/$1.5M (`docs/balance/rebalance_v1_stage_i_toxin_exchange/`).

English balance reference material (the owner's accepted philosophy, EN numbers):
`docs/balance/v1.0_balance_summary.md` (food), `docs/balance/rebalance_v1_stage_o_character_rebalance/STAGE_O_SUMMARY.md`
(characters), `docs/reverse/playable_chef_mechanics.md`, EN data in `src/assets/data/*.json`.

## 8. Open owner decisions (block most balance work)

1. Roster: which of the 1,724 characters stay, and how each kept one is obtained offline (store tier / quest reward / level unlock / offline draw).
2. Gacha/roulette: redesign as an offline Toxin draw, or remove.
3. The 62 dead online quests to retire (`quest_offline_matrix.csv`).
4. Toxin exchange rate for the JP build.

## 9. Don'ts

- Don't repack `constants.bin.mid` (undecoded). Don't touch the original APK or `work/base_json`.
- Don't commit or push without the owner asking.
- Don't redo translation work; if English text needs a fix, edit `english/tm*/` and rebuild.
- Don't trust EN-derived "caps" blindly — JP scales differ; measure, then propose.
