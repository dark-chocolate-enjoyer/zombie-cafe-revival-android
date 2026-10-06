# Handoff prompt — JP balance rework (paste into a new Claude Code chat opened in the repo)

> Kept as a record of how this project hands work to an AI session: the owner pasted this
> on 2026-09-26 to start the JP balance phase. Some files it lists (`jp/research/`,
> `docs/balance/rebalance_*`, `docs/reverse/`) are local working notes, not in the public repo.

---

We're continuing the Japanese Zombie Cafe 1.7.0 restoration. The English
translation and Android 14 compatibility are finished and verified on my phone
(build v5). The next phase is the **dish / character / playable-chef balance
rework**.

Start by reading, in this order (don't read anything else yet):
1. `jp/START_HERE.md` (status, repo map, build/test commands, balance rules)
2. `jp/balance/EN_BALANCE_DIRECTION.md` — **the direction I want.** I already rebalanced the English game from vanilla
   to my v1.1.0 (dishes: cheaper ingredients, more servings, higher profit/min especially early-mid game, XP pace held,
   premium food clearly worth it; chefs: much higher TipRating/TipMultiplier on a smooth cost ladder; workers: stronger
   per cost, nothing dominated). Take the JP build the same way. That doc also shows how EN maps onto JP
   (65 JP dishes are identical to EN vanilla; JP character stats are exactly 10x EN).
3. `jp/research/pass1_inventory_schema/balance_porting_strategy.md`
4. `jp/research/pass4_systems_curation/README.md` and the headers of `roster_curation_candidates.csv`
5. `jp/balance/snapshots/*.csv` (current JP values with English names, plus EN-vanilla and my EN-v1.1 columns; regenerate with
   `cd jp/english && python3 build.py && python3 ../balance/export_current.py` if missing)
6. For the English balance philosophy I already approved: `docs/balance/rebalance_v1_stage_o_character_rebalance/STAGE_O_SUMMARY.md`,
   `docs/balance/v1.0_balance_summary.md`, `docs/reverse/playable_chef_mechanics.md`

How I want to work:
- You can't play the game, so you can't judge progression feel. I review **every character, playable chef and dish**
  in Excel spreadsheets before anything is implemented. Everything you produce is **report-only** until I approve it.
- Deliverables are `.xlsx` workbooks I can sort, filter and annotate: one row per item, current values,
  the English-game equivalent where one exists, derived metrics, your proposed values with a one-line reason,
  and an empty "Owner verdict" column. Keep proposals conservative and explain the curve you're aiming for.
- Nothing gets applied until I say so. Approved changes go only into `jp/balance/overrides/*.csv`, then build,
  install on my A54 and I play-test.
- Never change a playable chef without asking me first.
- Keep token use lean: prefer scripts over reading huge files; don't re-derive what `jp/START_HERE.md` already says.

First task: don't propose new numbers yet. Build me:
1. A **review workbook** (foods, playable chefs, workers, furniture economy) of the current JP values,
   side by side with EN vanilla and my EN v1.1 values for shared items, what my EN direction would imply for each
   (as a suggestion column, not applied), and flags for obvious outliers or dominated units.
2. A short **decision brief** for the open questions that block balancing (roster keep/cut and how each kept
   character is obtained offline, gacha redesign vs removal, Toxin exchange rate — note my EN docs say $30k/$75k/$375k/$1.5M
   but the shipped v1.1 still has $20k/$50k/$250k/$1M — and dead online quests),
   with your recommendation for each.
Then stop and wait for my review.

---
