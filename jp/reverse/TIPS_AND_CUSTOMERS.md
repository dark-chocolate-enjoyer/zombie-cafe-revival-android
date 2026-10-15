# How tips, customers and selling work (read from the JP 1.7.0 game code)

Source: `jp/english/work/base_lib.so` (JP 1.7.0 native library; it still has its C++ function
names) and `constants.bin.mid`, decoded 2026-10-09 by emulating the game's own loader
(`tools/zemu_constants.py` → `constants_jp.json`, 590 constants, every byte of the file accounted for).
Addresses are for the JP library. EN comparison from `src/lib/armeabi/libZombieCafeAndroid.so`.

## 1. The tip on each sold serving

When a customer finishes eating (`GameStateCafe::onEatTaskComplete`, 0x1114e8):

```
tip value  = min(waiter's TipRating + equipment "charisma" bonus, 100)       set when the plate is served
tip        = sell price × 0.2 × tip value / 100                             fraction rounded up at random
tip        = tip × chef's TipMultiplier                                     (whole number)
cash      += sell price + tip
```

- **The waiter's TipRating** (the game calls it "Charisma") is captured when the dish is put on the table
  (`ServeTask::tick` → `Food::Food(..., tipValue)`, 0x215ce0). Whoever served that table counts:
  a worker or your playable chef. Equipment adds to it (`Character::getAdditionCharisma`).
- **It is capped at 100.** A tip value of 100 is a 20% tip before the multiplier. Anything above 100 is wasted.
- **TipMultiplier is your current chef's** (the chef object at ZombieCafe+0x590; swapping chef replaces it),
  so it multiplies every tip in the café, whoever served.
- **Tips scale with the sell price ($/serving)**, not with profit. Ingredient cost doesn't matter at all.
- Rounding: the fractional tip becomes +1 at random with probability equal to the fraction (an unknown
  table/chair byte can lower that chance slightly; ignorable).
- Per serving, on average: **customer pays = price × (1 + 0.002 × min(TipRating,100) × TipMultiplier)**.
  Examples: TipRating 50, multiplier 2 → +20%. TipRating 100, multiplier 6 → +120% (customer pays 2.2× price).

**English game for comparison:** `tip = price × 0.2 × TipRating / 10 × TipMultiplier`, **no cap**.
JP TipRating 100 = EN TipRating 10. EN TipRating 20 (a 40% tip) or 25 (50%) has **no JP equivalent**:
ported at 10× (200/250) it would be capped at 100. The JP data itself never goes above 100 for chefs.

## 2. How fast customers come (live play)

`GameStateCafe::resetCustomerTimer` / `spawnCustomer`:

- A passer-by appears every `18,000 − 13,500 × rating` ms (±1 s): every 18 s at rating 0, every 4.5 s at
  rating 1.0 (full stars).
- Each comes in with chance `(211 + 27 × rating) / 256`: 82% → 93%.
- Rating = base + bonuses (furniture/objectives), **capped at 1.0** (`ZombieCafe::getModifiedRating`).
- **Arrivals: ~2.7/min at rating 0, ~5.4/min at 0.6, ~12.4/min at full rating — the ceiling.**
  One customer buys and eats one serving (eat time 30 s; leaves after 60 s if not served).
  So a full-star café sells at most ~12 servings/min; a 300-serving pot takes ~25 min.

## 3. While the app is closed (the background "café still running" script)

`GameStateCafe::advanceTime` → `advanceTimeSection` (a small queueing model):

- Away time counts at **0.25×** (`GameStateCafe_TIME_SCALE_FACTOR`).
- Staff can serve **2 customers/min each** (`AVERAGE_SERVING_TIME` 30 s); counted staff = your chef + every
  character set to work. Arrivals beyond that capacity are lost.
- Seats limit it slightly (cafe-full probability ≈ 27% at full rating).
- Sales = random servings from your counters (stops when food runs out).
- Tip = sales × 0.2 × **average** tip value (chef + working staff, each capped at 100) / 100 × chef TipMultiplier.

Servings sold per real minute with the app closed, full rating (live: ~12.4/min):

| staff working (incl. chef) | 1 | 2 | 3 | 4 | 6 | 7+ |
|---|---|---|---|---|---|---|
| servings/min | 0.36 | 0.73 | 1.1 | 1.5 | 2.2 | 2.3 (max) |
| slower than live | ×34 | ×17 | ×11 | ×8 | ×6 | ×5 |

## 4. What this means for dish balance

- A dish's real earning rate is limited by **customers**, not just the stove: at most ~12 servings/min live
  and ~0.4–2.3/min while away. Profit per cook-minute ignores this.
- Per customer, a dish earns **price × (1 + tip%)**, so **$/serving is the stat that matters** once the stove
  isn't the bottleneck, and tips amplify it. Two dishes with equal profit: the higher-price one wins.
- **Fewer servings sell out sooner.** Overnight at 2 staff (~0.7/min ≈ 44/hour), a 1,200-serving pot
  takes ~27 hours to sell; a 300-serving pot ~7 hours.
- For characters: in JP, TipRating above 100 does nothing; TipMultiplier (chef) is the uncapped tip lever.

## Constants used (from `constants_jp.json`)

| constant | value |
|---|---|
| GameStateCafe_MIN / MAX_CUSTOMER_INTERVAL | 4,500 / 18,000 ms |
| GameStateCafe_MIN / MAX_CUSTOMER_VISIT_CHANCE_FP8 | 211 / 238 (÷256) |
| GameStateCafe_CUSTOMER_INTERVAL_VARIANCE | 1,000 ms |
| GameStateCafe_TIME_SCALE_FACTOR | 0.25 |
| GameStateCafe_AVERAGE_SERVING_TIME | 30,000 ms |
| GameStateCafe_TABLE_SERVER_MODIFIER | 0.12 |
| EatTask_EAT_TIME / WAIT_FOR_FOOD_TIME | 30,000 / 60,000 ms |
| GameStateCafe_RATING_INCREMENT / DECREMENT | +0.005 per customer served / −0.006 on the not-served path |
| ServeTask_SERVE_TIME | 350 |

Tools (`tools/`): `zdis.py` annotated disassembly of a named function, `zxref.py` callers of a function,
`zlit.py` code that uses a named global, `zemu_constants.py` decodes `constants.bin.mid` (read-only:
**still never repack it**).
