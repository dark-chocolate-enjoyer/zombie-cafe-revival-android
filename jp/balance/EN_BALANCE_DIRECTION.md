# The owner's English balance direction (vanilla → v1.1.0), and how it maps to JP

Measured 2026-09-26 from data, not from memory. **The owner wants the JP build
taken in the same direction as their English v1.1.0.**

## 1. What can be seen (verified)

| Data | Where | Confidence |
| --- | --- | --- |
| **EN vanilla** (original Capcom values) | git `e6e654fe:src/assets/data/*.bin.mid` (Airyzz's "Adding unpacked APKs", 2023-06-19), decoded with the repo codec | exact |
| **EN v1.1.0** (owner's final) | `src/assets/data/*.bin.mid.json` | exact — verified value-identical to the shipped `ZombieCafe-v1.1.0-Release.apk` |
| Side-by-side tables | `reference/en_food_vanilla_vs_v11.csv`, `reference/en_characters_vanilla_vs_v11.csv` (regenerate: `python3 jp/balance/make_en_reference.py`) | exact |
| Per-stage before/after + rollbacks | `docs/balance/rebalance_*/` (v0.2 food stages, E, F, G–N, Stage O steps 1–9) | historical record |
| Owner-stated philosophy | `docs/balance/v1.0_balance_summary.md` (food), `docs/balance/rebalance_v1_stage_o_character_rebalance/STAGE_O_SUMMARY.md` (characters), `docs/reverse/playable_chef_mechanics.md` | owner-approved |

Airyzz's only data edits before the owner's work: 3 characters appended (2 Maids + Lieutenant
Colonel, EN idx 216–218, ported from JP), 3 Cost tweaks, and the cash→Toxin shop rows. Food untouched.

**Discrepancy to raise with the owner:** `v1.0_balance_summary.md` says Stage I raised the Toxin
exchange 1.5× ($30k/$75k/$375k/$1.5M), but the shipped v1.1.0 APK and current repo still use
Airyzz's $20k/$50k/$250k/$1M. Stage I was applied at one point but did not survive into the release.

## 2. Direction — dishes (164 of 216 changed)

Owner's stated goals: **less grind; fun over perfect smoothing; premium investment (paid
cookbooks, toxin recipes, special-stove chain) should clearly out-earn free food and scale with
cost; hardest boss/raid recipes stay elite; no dish should lose money.**

What the numbers show:
- Ingredient cost **down** on 102 dishes (up on 27); servings **up** on 81 (down 40);
  price-per-serving **never lowered** (up on 58).
- Cook time and XP nudged both ways (18/20) — **XP per minute deliberately held at vanilla**
  (after a Stage K XP rollback): money got better, levelling pace did not.
- Money-losing dishes: vanilla 4 → v1.1 **0**.

| Unlock levels | changed | median profit/min vanilla → v1.1 | median XP/min | median profit margin |
| --- | --- | --- | --- | --- |
| 0–5 | 17/21 | 1.67 → **4.00** | 0.361 → 0.364 | 0.78 → 1.84 |
| 6–10 | 21/29 | 1.17 → **1.86** | 0.156 → 0.156 | 0.74 → 1.44 |
| 11–15 | 40/52 | 1.33 → **2.96** | 0.212 → 0.212 | 1.00 → 1.69 |
| 16–20 | 23/28 | 1.09 → **2.29** | 0.182 → 0.183 | 0.73 → 1.58 |
| 21–30 | 19/25 | 2.00 → **2.25** | 0.175 → 0.175 | 0.60 → 1.10 |
| 31+ | 44/61 | 2.15 → **2.64** | 0.149 → 0.149 | 1.05 → 1.70 |

Net effect (owner's estimate): food economy ~45–55% more rewarding; free progression 20–40%
stronger; premium/stove-chain dishes much stronger. Biggest lifts where vanilla was weakest (early
and mid game).

## 3. Direction — characters (184 of 219 changed)

| Class | changed | What moved |
| --- | --- | --- |
| **Playable chefs** (81) | 80 | TipRating ~×1.8 (range 1–10 → 5–20); TipMultiplier ~×2 (max 5 → 6); Speed ×1.4; CookXP ×1.2; Cost smoothed into a ladder (26 up/12 down, max $5k → $12k cash). Energy/Attack/Regen also rose but are **inert on chefs**. CookSpeed kept near vanilla (chefs are "set": ask before touching). |
| **Toxin workers** (67) | 66 | Cost curve re-spread (32 cheaper, 21 dearer; max 60 → 140 toxin); Speed ×1.33, Attack ×1.33, TipRating ×1.45, Regen ×1.3; Energy re-balanced both ways with a floor (few under 100). Anchors: Maid, Governor (tip king TR25), Godfather, Zombie Man (combat king). |
| **Cash workers** (38) | 38 | Mostly cheaper (14 down / 8 up) and stronger: Speed ×1.55, Attack ×1.6, TipRating ×1.2; priced at **3,000 cash ≈ 1 toxin**. |
| Free / enemy (30) | 0 | untouched |

Rules behind it (owner-confirmed): chef CookSpeed/TipMultiplier are **global** (buff every
cook), so they're the strongest levers; workers are valued on Energy/Attack/Speed, tip is
self-only so valued low; caps Attack 15 / Speed 14 / TipRating 25; value should rise with cost
(no inversions, no strictly dominated purchases); human (cash) and zombie (toxin) skins are the
same character at two price points (cash ≈ TipMult −1).

## 4. How EN maps onto JP (measured)

- **Dishes:** join JP↔EN by `ImageID`, using the **first** EN row with that ID (EN premium variants
  reuse images). 139 of 234 JP dishes have an EN twin; **65 of those are byte-identical to EN
  vanilla** (the owner's EN v1.1 values can be ported almost directly); 74 were repriced by
  Capcom's JP team (port the owner's *ratios/direction*); 95 are JP-only (design them on the same
  curve). Columns `en_*_vanilla` / `en_*_v11` / `jp_equals_en_vanilla` in `snapshots/foods_current.csv`.
- **Characters:** join by art (`Category/CharacterArtString`) + chef flag + currency (188 JP rows
  matched, 58 of them playable chefs). **JP Energy, Speed, AttackStrength and TipRating are exactly
  10× the EN values** for the same character (median of every matched class); TipMultiplier and
  Cost are on the same scale. So EN rules translate as ×10: caps Attack 150 / Speed 140 / TipRating 250,
  chef TipRating target ~200, etc. EN columns in `snapshots/characters_current.csv`.
- **Not portable:** the 1,397 JP gacha/event units have no EN counterpart and can't be obtained
  offline today — the roster/acquisition decision comes before balancing them.
