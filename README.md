![Zombie Cafe Revival banner](/src/assets/images/banner.png)

# Zombie Cafe Revival — v1.0.0 Balance Change

> This is an unofficial fan-made balance mod/revival project. It is not affiliated with, endorsed by, or approved by Capcom or Beeline Interactive. Zombie Cafe and all original game assets belong to their respective rights holders.

A reverse-engineered revival of *Zombie Cafe* (Android) with a full balance-focused update. **v1.0.0 — Balance Change** makes the game feel fresher, less grindy, and more rewarding while keeping the original Zombie Cafe feel.

This work builds on the original [Zombie Cafe Revival](https://airyz.xyz/p/zombie-cafe-revival/) reverse-engineering effort, which restored the game's build pipeline and runtime.

## What v1.0.0 changes

- This version rebalances food profits, XP pacing, playable chefs, infectable zombies/staff, and toxin exchange.
- DLC and premium cookbooks now give stronger, more worthwhile recipes.
- **Android/BlueStacks compatibility repair included** — the release APK uses the known working native-library repair.

For the full public notes, see the [v1.0.0 Balance Change release notes](docs/release-notes/v1.0v-balance-change.md).

## Releases

Latest release: [v1.0.0 — Balance Change](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.0v-balance-change)

Older compatibility test: [v0.1.0 — Android 16 32-bit Compatibility Test](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/android14-compat-test-v0.1)

## Download

Download: [v1.0.0 Balance Change APK](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/download/v1.0v-balance-change/ZombieCafe-v1.0.0-Balance-Change.apk)

The APK is provided as a GitHub Release asset for the **v1.0.0 — Balance Change** release.

```text
File:    ZombieCafe-v1.0.0-Balance-Change.apk
SHA-256: bb489e470412c23d9b00db1bd9fbbbbce31a7901196bca8c27dc876bbddefc90
```

The APK is not committed to this repository — download it from the Releases page and verify the checksum.

## Installation

- This is a sideloaded Android APK; you'll need to allow installation from unknown sources.
- Tested in **BlueStacks**.
- Requires 32-bit ARM support. Many newer 64-bit-only devices may not run the game.

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
