![Zombie Cafe Revival banner](src/assets/images/banner.png)

# Zombie Cafe Revival

Android maintenance, balancing, and localization work for *Zombie Cafe*, maintained by [dark-chocolate-enjoyer](https://github.com/dark-chocolate-enjoyer).

[Download v1.1.0](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.1.0) | [Project documentation](https://dark-chocolate-enjoyer.github.io/zombie-cafe-revival-android/) | [Implementation notes](https://dark-chocolate-enjoyer.github.io/zombie-cafe-revival-android/engineering.html)

## Project scope

This repository contains a playable Android revival with revised progression, repaired audio behaviour, and compatibility fixes for newer Android environments. It also contains the ongoing restoration of the final Japanese release, including English localization and replacements for services that disappeared when the original servers closed.

The work is based on inspection of the game's native ARM code, Smali application layer, packed binary data, and assets. Reproducible tools and technical notes are kept beside the game source instead of treating the APK as an opaque final artifact.

## Current release

**v1.1.0 - Balance + Music Fix** includes:

- corrected cafe music rotation and state recovery after maps, raids, and cafe reloads;
- a complete character rebalance across cooking, combat, energy, regeneration, cost, and tips;
- the v1.0 food economy and progression rework;
- the Android/BlueStacks native-library compatibility repair.

Download the signed APK and read the player-facing changes on the [v1.1.0 release page](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.1.0).

## Engineering work

### Music playback repair

The original audio path could leave stale playback state behind after a track ended or the game changed scenes. The repair updates the native state transitions, restores cafe track rotation, assigns raid-specific themes, and recovers missing OGG assets from the later Japanese build. The exact control-flow changes and relevant C++ snippets are documented in the [implementation notes](https://dark-chocolate-enjoyer.github.io/zombie-cafe-revival-android/engineering.html#music).

### Japanese version restoration

The Japanese 1.7.0 build uses different packed layouts for food, furniture, quests, and strings. Dedicated readers and guarded writers were developed to decode those formats and verify byte-identical round trips before edited data is repacked.

The retired premium-currency purchase route has also been replaced with a local cash-to-Toxin exchange. The patch was derived by comparing the working English implementation with the Japanese ARM binary, identifying the purchase branch and the registers carrying the selected cash cost and Toxin reward, then transplanting the equivalent arithmetic while preserving the Japanese function's surrounding control flow. See the [cash-to-Toxin analysis](https://dark-chocolate-enjoyer.github.io/zombie-cafe-revival-android/engineering.html#toxin).

### Balance and data tooling

Custom Go and Python tools unpack game data into reviewable structures, validate proposed changes, and serialize it back into the formats expected by the client. Food and character changes are evaluated against progression, profit, experience, combat, unlock, and premium-value data rather than edited as isolated numbers.

## Repository map

| Path | Contents |
| --- | --- |
| `src/` | Decoded Android application, native libraries, assets, Smali, and game data |
| `tool/` | Binary codecs, resource tooling, localization helpers, and patch scripts |
| `docs/` | Compatibility investigations, balance records, release notes, and implementation reports |

## Building

The build requires Go, CMake, an Android NDK toolchain, apktool, and an APK signing tool. The project tooling converts the editable resource tree back into the game's binary formats before apktool rebuilds the application.

```bash
go run ./tool/build_tool/ -i src/ -o build/
cp src/lib/cpp/build/libZombieCafeExtension.so build/lib/armeabi/
apktool b build -o build/out/ZombieCafe.apk
apksigner sign --ks debug.keystore build/out/ZombieCafe.apk
```

Compatibility builds must include the repaired `libZombieCafeAndroid.so`; background and investigation notes are collected under `docs/compat/`.

## Project history

The initial reverse-engineering and Android build foundation came from [Airyzz's Zombie Cafe Revival](https://github.com/Airyzz/zombie-cafe-revival). This repository is the independently maintained continuation containing the balance releases, Android compatibility work, music repair, Japanese-version restoration, localization tooling, and current documentation described above.
