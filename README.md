![Zombie Cafe Revival banner](src/assets/images/banner.png)

# Zombie Cafe Revival

Android maintenance, balancing, and bug-fixing for the old Capcom game *Zombie Cafe*.

[Download v1.1.0](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.1.0) | [Project documentation](https://dark-chocolate-enjoyer.github.io/zombie-cafe-revival-android/) | [Implementation notes](https://dark-chocolate-enjoyer.github.io/zombie-cafe-revival-android/engineering.html)

## Project

This project is continuing from Airyzz's work to revive an old mobile game developed by Capcom called *Zombie Cafe*.

The latest version v1.1 supports repaired audio behaviour, a compatbility fix to allow the game to run on newer androids, and a complete balance overhaul with almost every dish and character rebalanced to support a less grindy, more interesting progression of the game.

It also contains the ongoing restoration of the final Japanese release - which has much more content compared to the latest English version - including a full translation from Japanese to English, and my option balance changes applied. 

The work is based on inspection of the game's native ARM code, Smali application layer, packed binary data, and assets. 

## Current release

**v1.1.0 (beta) - Balance + Music Fix** includes:

- Corrected cafe music rotation and state recovery after maps, raids, and cafe reloads
- A complete character rebalance across cooking, combat, energy, regeneration, cost, and tips
- Food economy and progression rework from v1.0 with some changes 
- the Android native-library compatibility repair.

Download: [v1.1.0 release page](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android/releases/tag/v1.1.0).

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
