# Zombie Cafe Revival — v1.0.0 Balance Change

## Overview

*Zombie Cafe* was a charming free-to-play café sim — and like most of its era, it was balanced to be grindy. Many recipes were traps, premium dishes were often worse than free ones, and late-game progression crawled.

**v1.0.0 — Balance Change** is the first full balance-focused version of Zombie Cafe Revival. It keeps the original game's personality while making recipes, chefs, staff, and premium content feel more rewarding.

<!-- Screenshot placeholder: cookbook before/after -->

## What changed?

- This version rebalances food profits, XP pacing, playable chefs, infectable zombies/staff, and toxin exchange.
- DLC and premium cookbooks now give stronger, more worthwhile recipes.
- The release includes the existing Android/BlueStacks compatibility repair.

## Releases

Latest release: [v1.0.0 — Balance Change](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.0v-balance-change)

Older compatibility test: [v0.1.0 — Android 16 32-bit Compatibility Test](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/android14-compat-test-v0.1)

## Premium and DLC dishes now feel worth buying

In the original game, many paid cookbook and special-stove recipes earned *less* than free food at the same level. In v1.0.0, premium and stove-chain recipes were redesigned so that investment scales: the **Pirate, Vampire, Mafia, Medieval, Super Hero, Politician, and Day of the Dead** cookbooks now carry real progression value, and the special stove chain rewards committing to it.

<!-- Screenshot placeholder: premium cookbook page -->

## Boss and raid recipes are elite rewards

Not everything was smoothed out on purpose. Some of the best recipes in the game remain locked behind the hardest boss and raid cafes — beating them should still feel like winning something special. Raid rewards kept their provisional values in v1.0 and will get a dedicated pass later.

<!-- Screenshot placeholder: boss cafe / raid map -->

## Better progression pacing

Food profit is stronger so more dishes are worth cooking, but XP was rebuilt around vanilla XP-per-minute pacing. That keeps the game more rewarding without racing too quickly through cafe levels.

## How the rebalance was made

1. **Extract** — the game's binary data files were decoded into human-readable JSON using custom Go tooling from the revival project.
2. **Measure** — every dish was scored on total earnings, profit, profit per minute, XP per minute, cook time, unlock level, and how it's acquired (free, paid cookbook, special stove, raid).
3. **Stage** — changes were proposed in reviewable stages (cleanup passes, a clean-number pass, a premium/stove-chain redesign, a free-progression pass), each with explicit accept/hold decisions per dish.
4. **Validate** — every stage was applied by script with preflight checks, value-safety limits, anchor verification, and full before/after audits — over a thousand automated checks for the free pass alone.
5. **Build & verify** — the data was re-packed into the game's binary format, rebuilt into a signed APK, and the packed data inside the APK was decoded again to prove it matches the source byte-for-byte.

Claude and ChatGPT were used as planning and review tools; the balance itself was driven by extracted data, tables, staged proposals, manual decisions, and validation checks.

## Current status

The **v1.0.0 — Balance Change** APK is built, signed, repaired with the known BlueStacks-compatible native library, and verified against the current balanced data.

## Download

Download: [v1.0.0 Balance Change APK](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.0v-balance-change)

The APK is provided as a GitHub Release asset for the **v1.0.0 — Balance Change** release.

```text
File:    ZombieCafe-v1.0.0-Balance-Change.apk
SHA-256: bb489e470412c23d9b00db1bd9fbbbbce31a7901196bca8c27dc876bbddefc90
```

Android sideloading is required. Tested in BlueStacks. Requires 32-bit ARM support. Many newer 64-bit-only devices may not run the game.

## Future work

- Fix the map/cafe transition text corruption/crash bug.
- Final raid reward pass.
- Review of unknown/promo recipes.

## Disclaimer

This is an unofficial fan-made balance mod/revival project. It is not affiliated with, endorsed by, or approved by Capcom or Beeline Interactive. Zombie Cafe and all original game assets belong to their respective rights holders.
