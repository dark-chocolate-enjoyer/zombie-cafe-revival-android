# Build register

Every APK that matters, newest JP build last. Files live in `Desktop/ZCafeStuff/` (JP:
`Japanese APK Restoration/Versions/`, EN: `English APK Restoration/APKs/`). Hashes are SHA-256.
Add a row for every new build; mark *device-tested* only after it ran on the A54.

## Japanese 1.7.0 builds

| # | Date | Built from | What changed | SHA-256 | A54 |
|---|---|---|---|---|---|
| 0 | 2016 | — | **Original** (APKPure copy of Google Play JP 1.7.0). Never edit. | `015d265d0c1a6e68aaff50e3e01ee792a41d6192ce7823476581e4d573508942` | — |
| 1 | 2026-07-24 | 0 | Toxin exchange: furniture rows 182–185 → cash-for-Toxin packs; lib 8 bytes at `0x113b88` (Type-10 purchase → `addToxin`); re-signed with repo key | `3b2dcbf38d83744c990e5f349552a4234487c4b9c9cdd9e56b82b7b02f9d41d2` | BlueStacks only |
| 2 | 2026-07-26 | 1 | **Debug** prices $20–$1,000. Never distribute. | `be92bfc687c9188cbaef7ef39768bc9fa5bf8b4ac735bb3a0f3ca794f916e57f` | — |
| 3 | 2026-07-26 | 1 | + Toxin shop icons (furniture atlas sprites 110–113) | `0040ef37b3039399e480c9f5846be62efc57be3796a287981f10c2213fdf265a` | — |
| 4 | 2026-09-25 | 3 | Android 14: manifest targetSdk 16→24 (1 byte); 9 `getDeviceId`/`getSimSerialNumber` → constant in dex. Scripts: `jp/english/v4_compat/` | `3b4a1fc42b033610fe29e32c9353c61530ea32761da4e080e507ea5f359f3fb9` | ✅ owner played; no map crashes |
| 5 | 2026-09-25 | 4 | **Full English**: 5 data files, help/error HTML, 3 sprite sheets (99 sprites), dex (10 strings), native lib (761 strings, 84 pointers moved, no code), arsc (app name "Zombie Cafe JP"). No stat/price changes. Built by `jp/english/build.py` | `1f95c7f9cc68031d331eede29f66a6efa4678753056c86fa12c833a91e3030b5` | ✅ boots; screens checked by Claude |
| 5d | 2026-10-09 | 5 | **Debug, never distribute.** Crash-hunt build: manifest `debuggable=true` + `lib/armeabi/wrap.sh` (bionic malloc debug). Built by `jp/stability/make_debug_apk.py`. Crashes when a saved raid is resumed (raid bug, `jp/stability/README.md`). An earlier same-day variant (`b0dd22b1…`, `backtrace` option) crashed at startup; not kept | `81aac57221fdee4d95df81aeb12e622179bb7b82764f0c8522c50cc73b7f8718` | ✅ runs; 25 map trips OK |
| 5e | 2026-10-09 | 5 | **Debug, never distribute.** As 5d with `free_track=16384`, plus the **raid fix** (`jp/stability/lib_fixes.py`: 1 byte at `0x17302a`, owner-approved for debug builds) | `f7ab607226d26c6535db045881e82ef09d3705a7911556419b1b65690848c817` | ✅ resumed raid OK (fix works); 37 map trips, no crash, no reports |
| 5f | 2026-10-09 | 5 | **Debug, never distribute.** GWP-ASan build (`make_debug_apk.py --mode gwp`, `wrap_gwpasan.sh`: 1-in-24 sampling, 26,000 slots, launched under another name so libc honours the variables) + raid fix | `79d55663802f2009352f0b9ae593efa07187e776fa9e2ea05a643414caf7c8ab` | ✅ caught a read overflow in `String::operator+=` (launch 3 of 4) |
| 5g | 2026-10-09 | 5 | **Debug, never distribute.** As 5f + **toString fix** (`lib_fixes.py`: 20-byte helper over unused `String::Test()` + `bl` at `0x2918de`; `jp/stability/STRING_BUG.md`) | `0a362d6a9f671bd052823d701eded12b21ebda06172fe7de94605b348b1a359d` | ⚠️ map crash still happens (launch 2, quick Map press) |
| 5h | 2026-10-09 | 5 | **Debug, never distribute.** No memory checker; raid + toString fixes; `classes.dex` rebuilt with every Java → native call behind one lock (`lock_natives.py`: 51 wrappers, 95 call sites; `make_debug_apk.py --mode lock`) | `3b69510fec55351d714b4a8688de455892834a3a6a5efc455b6850b8dd33ba08` | ⚠️ crashed anyway (launch 2, Scudo in `Cafe::~Cafe`) → not a Java-thread race |
| **6** | 2026-10-09 | 5 | **Public v0.1, published 2026-10-10** (github.com/dark-chocolate-enjoyer/zombie-cafe-revival-jp/releases/tag/v0.1). **Crash fix + offline.** v5 + `lib_fixes.py` (28 bytes: raid-resume list typo, `StringBuffer::toString` terminator, **`javaGetDeviceInfoForURL` terminator = the cafe → map crash**) + `offline_patch.py` (classes.dex: game believes it has no internet, sends no server requests). Built by `jp/english/build.py`; differs from v5 only in the lib (28 B) and `URLManager.a(Context)`. Not debuggable. `jp/stability/DEVICEINFO_BUG.md` | `8a9a77163bc571b77899e254103ccb373155ec29fe76899e7d1bf254b78a1e07` | ✅ 20/20 automated cafe → map rounds, no crash (control without the device-info fix: 10/20 crashed); owner left it open in the background 24+ h, no crash (L-22; not a map-trip test); owner hand play-test pending |
| 6c | 2026-10-09 | 6 | **Test only, not archived.** v6 with the 4 device-info bytes reverted (control) | `ae9a24e4…` | 10/20 crashed |

All JP builds after 0 are signed with the repo `debug.keystore` (alias `alias_name`), so each
installs over the previous one and keeps the save. Uninstall a Capcom-signed JP install first.

## English Revival releases (paused project; reference)

| Release | Date | SHA-256 | Notes |
|---|---|---|---|
| `android14-compat-test-v0.1` | 2026-06-09 | `5add41bba4d40100d7df474a6373fc0a17c3dd0408f68f1c6b723a42e8aa343c` | targetSdk 24, TEXTREL patch, device-ID fix |
| `v1.0v-balance-change` | 2026-06-22 | `bb489e470412c23d9b00db1bd9fbbbbce31a7901196bca8c27dc876bbddefc90` | food + character v1.0 balance |
| v1.1.0 "Balance-Update" | 2026-07-01 | `27b4af0867e1315d6b10824b5d186c57dad675d1447a742f1788b3f82f2c1f4a` | pre-release, before the music fix |
| `v1.1.0` | 2026-07-03 | `d51273188c1c62df16869f535b344c8f414847f68032ddd41e40f54d66954cc4` | Stage O characters, $2,000/Toxin, music fix |

Older EN test builds and crash-fix experiments: `English APK Restoration/INDEX.md`.

## Phone test checklist (each new JP build)

1. Install over the previous build (`adb install -r --user 0 …`); app opens past the logos.
2. Café loads; cook and serve for a few minutes.
3. Store → Toxin packs: buy each tier; cash goes down, Toxin goes up.
4. Force-close and reopen: Toxin and café state persist.
5. Map round trips ×5 (the EN crash trigger).
6. Spot-check anything the build changed (text, balance values) and note the result in `CHANGELOG.md`.
