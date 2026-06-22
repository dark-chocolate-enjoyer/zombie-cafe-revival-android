![Zombie Cafe Revival banner](/src/assets/images/banner.png)

# Zombie Cafe Revival — 1.0v Balance Change

> This is an unofficial fan-made balance mod/revival project. It is not affiliated with, endorsed by, or approved by Capcom or Beeline Interactive. Zombie Cafe and all original game assets belong to their respective rights holders.

A reverse-engineered revival of *Zombie Cafe* (Android) with a full balance-focused update. **1.0v Balance Change** makes the game feel fresher, less grindy, and more rewarding while keeping the original Zombie Cafe feel.

This work builds on the original [Zombie Cafe Revival](https://airyz.xyz/p/zombie-cafe-revival/) reverse-engineering effort, which restored the game's build pipeline and runtime.

## What 1.0v changes

- **Food economy rebalanced** — prices, servings, and profits were adjusted so more recipes are worth cooking.
- **XP pacing corrected** — food XP now stays close to vanilla XP-per-minute pacing instead of making progression too fast.
- **Premium and DLC recipes improved** — paid cookbooks and special stove-chain recipes now feel more worthwhile.
- **Playable chefs rebalanced** — late-game chefs have stronger identities and more interesting roles.
- **Infectable zombies/staff rebalanced** — Maids are useful safe workers, Governor is the top tip specialist, Godfather is the best all-rounder, and Zombie Man is an elite combat monster.
- **Toxin exchange adjusted** — cash-to-toxin exchange prices were raised to match the stronger economy.
- **Android/BlueStacks compatibility repair included** — the release APK uses the known working native-library repair.

For the full public notes, see the [1.0v Balance Change release notes](docs/release-notes/v1.0v-balance-change.md).

## Download

Download: [1.0v Balance Change APK](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.0v-balance-change)

The APK is provided as a GitHub Release asset for the **1.0v Balance Change** release. If the asset is not visible yet, it still needs to be attached to the GitHub Release.

```text
File:    zombie_cafe_v1_0_k2_balance_candidate_signed_repaired.apk
SHA-256: bb489e470412c23d9b00db1bd9fbbbbce31a7901196bca8c27dc876bbddefc90
```

The APK is not committed to this repository — download it from the Releases page and verify the checksum.

## Installation

- This is a sideloaded Android APK; you'll need to allow installation from unknown sources.
- Tested in **BlueStacks**.
- Real-device support may vary, especially on modern Android versions and ARM64-only devices (the game ships 32-bit `armeabi` native libraries).

## How it was made

The balance rework was managed through extracted game data, spreadsheets/tables of every dish's economy, staged change proposals, manual accept/hold decisions per dish, and scripted validation checks (value-range safety, anchor dishes, before/after verification) at every step. Claude and ChatGPT were used as planning and review tools throughout; the actual changes were driven by the data, the staged proposals, and manual decisions.

High-level pipeline:

1. Decode the game's binary data files into human-readable JSON (custom Go tools).
2. Analyze the food economy (profit, profit/minute, XP/minute, unlock pacing, ownership: free vs. premium vs. raid).
3. Propose balance changes in reviewable stages, validate, and apply only verified rows.
4. Re-pack the data, rebuild the APK with the project build tools, sign, and verify the result in-emulator.

See [docs/balance/native_repair_notes.md](docs/balance/native_repair_notes.md) for how a native-library packaging issue in the first v1.0 build was diagnosed and repaired.

## Building from source

### Requirements
 - cmake
 - make
 - go
 - apktool
 - apksigner / jarsigner

### LibZombieCafeExtension
LibZombieCafeExtension is an extra library that applies runtime patches to the game's `libZombieCafeAndroid.so`:

```bash
cd src/lib/cpp
mkdir build
cd build
cmake ../ -DCMAKE_TOOLCHAIN_FILE=$NDK_HOME/build/cmake/android.toolchain.cmake -DANDROID_ABI=armeabi-v7a -DANDROID_PLATFORM=android-8
make
```

### Building the APK
Custom tools convert the human-readable file structure into the game's expected binary formats:

```bash
go run ./tool/build_tool/ -i src/ -o build/

cp src/lib/cpp/build/libZombieCafeExtension.so ./build/lib/armeabi/libZombieCafeExtension.so

apktool b ./build -o ./build/out/out.apk

apksigner sign --ks debug.keystore --ks-key-alias alias_name ./build/out/out.apk
```

Note for emulator (BlueStacks) builds: the stock `libZombieCafeAndroid.so` uses text relocations that fail to link on some Android runtimes; a compatibility-patched copy of the library must be packed instead (see [native repair notes](docs/balance/native_repair_notes.md)).

## Known future work

- Map/cafe transition text corruption/crash bug.
- Raid reward final pass.
- Unknown/promo recipe pass.

## License & disclaimer

This is an unofficial fan-made balance mod/revival project. It is not affiliated with, endorsed by, or approved by Capcom or Beeline Interactive. Zombie Cafe and all original game assets belong to their respective rights holders. No original game assets are distributed in this repository.
