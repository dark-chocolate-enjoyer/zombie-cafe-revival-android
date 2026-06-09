# Android modern-device compatibility — targetSdkVersion 24 test

Status: built, signed, exported. **Installed successfully on a physical Android 14
device (Samsung Galaxy A54) — install gate cleared.** App then **crashes on launch**
inside `System.loadLibrary` due to a native **text relocation** in
`libZombieCafeAndroid.so`. The blocker has moved from the install-time SDK gate to a
runtime native-loader rejection. See the deep-dive:
[`native_text_relocation_investigation.md`](native_text_relocation_investigation.md).

## Goal
Determine whether the rebuilt Zombie Cafe APK fails to install on modern Android
(14/15) purely because of its very old `targetSdkVersion`, and test the smallest
possible SDK-only patch (raise target to 24, leave min untouched).

This work is **SDK-compatibility only**. No gameplay data, balance values, native
C++, smali, images, offsets, or server code were touched.

## Hypothesis being tested
- The APK targets `targetSdkVersion 14` (Android 4.0-era).
- Android 14 refuses to install apps that target below SDK 23.
- Android 15 refuses to install apps that target below SDK 24.
- BlueStacks installs fine because it runs an older, more permissive Android image.
- Smallest test: raise `targetSdkVersion` to 24 only. Keep `minSdkVersion` at 8.

## Source of truth for SDK values
- **`src/apktool.yml`** → `sdkInfo:` block is authoritative.
- The build tool (`tool/build_tool/copylist/copy_files.go`, entry `"apktool.yml"`)
  copies `src/apktool.yml` **verbatim** into `build/apktool.yml`.
- The `perl` step then strips quotes around numeric values in `build/apktool.yml`
  (`: '8'` → `: 8`) so apktool reads them as integers.
- **No `AndroidManifest.xml` contains a `<uses-sdk>` element** (checked src, build,
  and src/original). apktool injects the SDK values from `apktool.yml`'s `sdkInfo`
  into the compiled manifest at build time.

### Why apktool.yml was enough (and the manifest was not changed)
Because none of the manifests declare `<uses-sdk>`, the only place SDK metadata
exists is `apktool.yml`'s `sdkInfo`. Editing the manifest would have been redundant
(and, with apktool, a manifest `<uses-sdk>` can even conflict with `sdkInfo`). So the
minimal correct change is a one-line edit to `src/apktool.yml`.

## Files changed
| File | Change |
|------|--------|
| `src/apktool.yml` | `targetSdkVersion: '14'` → `'24'` (one line; `minSdkVersion` left at `'8'`) |

`build/apktool.yml` also reflects the new value, but that file is **generated** from
`src/apktool.yml` by the build tool + perl step and is not the source of truth.

## Exact SDK values before / after
| | minSdkVersion | targetSdkVersion |
|---|---|---|
| Before | 8 | 14 |
| After  | 8 | 24 |

Confirmed in the final APK via `aapt dump badging`:
```
sdkVersion:'8'
targetSdkVersion:'24'
```

## Why target 24 specifically
- It is the **lowest** value that clears the Android 15 install floor (target ≥ 24),
  which also clears the Android 14 floor (target ≥ 23). This keeps the change minimal
  and isolates the SDK variable.
- `minSdkVersion` stays at 8 so we do not exclude old devices or change runtime
  behavior — we only lift the install gate.
- Targeting higher (26+, 28+, 30+) would pull in additional runtime enforcement
  (runtime permissions, scoped storage, non-SDK interface restrictions, etc.) that
  could mask whether SDK level alone was the blocker. 24 is the cleanest first probe.

## Build commands used
```bash
# 1. Generate build/ from src/ (copies apktool.yml verbatim, serializes assets)
go run ./tool/build_tool -i src/ -o build/

# 2. Drop the prebuilt native extension lib into place
cp src/lib/cpp/build/libZombieCafeExtension.so ./build/lib/armeabi/libZombieCafeExtension.so

# 3. Strip quotes around numeric apktool.yml values (apktool needs ints)
perl -pi -e "s/: '([0-9]+)'/: \1/g" build/apktool.yml

# 4. Clean previous outputs
rm -f ./build/out/out-unsigned.apk ./build/out/zombie-cafe-target24-signed.apk
mkdir -p ./build/out

# 5. Build unsigned APK
apktool b ./build -o ./build/out/out-unsigned.apk

# 6. Sign with debug keystore (v1+v2+v3)
apksigner sign \
  --ks debug.keystore \
  --ks-pass pass:zombiecafe \
  --key-pass pass:zombiecafe \
  --ks-key-alias alias_name \
  --out ./build/out/zombie-cafe-target24-signed.apk \
  ./build/out/out-unsigned.apk

# 7. Verify signature
apksigner verify --verbose ./build/out/zombie-cafe-target24-signed.apk
```

## APK output paths
- Unsigned: `build/out/out-unsigned.apk`
- Signed:   `build/out/zombie-cafe-target24-signed.apk`
- Exported to Windows Desktop: `/mnt/c/Users/New/Desktop/zombie-cafe-target24-signed.apk`
  (Windows path: `C:\Users\New\Desktop\zombie-cafe-target24-signed.apk`)

## APK signature verification result
```
Verifies
Verified using v1 scheme (JAR signing): true
Verified using v2 scheme (APK Signature Scheme v2): true
Verified using v3 scheme (APK Signature Scheme v3): true
Verified using v3.1 scheme (APK Signature Scheme v3.1): false
Verified using v4 scheme (APK Signature Scheme v4): false
Verified for SourceStamp: false
Number of signers: 1
```
v1 (JAR) signing is present, which is required for the min-SDK-8 install path on
older runtimes; v2/v3 cover modern devices.

## Commands for you to run on your phone (via adb)
Run these from Windows (PowerShell/CMD) where `adb` and your phone are set up. Enable
USB debugging on the phone first.

```bash
# Confirm the phone is connected and authorized
adb devices

# (Recommended) Uninstall any previous copy to avoid signature/downgrade conflicts
adb uninstall com.capcom.zombiecafeandroid

# Install the new target-24 APK
adb install "C:\Users\New\Desktop\zombie-cafe-target24-signed.apk"

# If you want the exact failure reason on a rejected install, use:
adb install -r "C:\Users\New\Desktop\zombie-cafe-target24-signed.apk"
```

Also report your phone's Android version so we can interpret the result:
```bash
adb shell getprop ro.build.version.release   # e.g. 14 or 15
adb shell getprop ro.build.version.sdk       # e.g. 34 or 35
```

## Expected install errors and what they mean
| Result | Meaning |
|--------|---------|
| **Success** | Target SDK was the (or a) blocker. The SDK-only patch worked. |
| `INSTALL_FAILED_DEPRECATED_SDK_VERSION` / "App not compatible / built for an older version of Android" | The OS is still rejecting the target SDK. Means 24 was not high enough for that OS, **or** the message persists at parse time — re-check actual target with `aapt dump badging`. |
| `INSTALL_PARSE_FAILED_NO_CERTIFICATES` / `INSTALL_PARSE_FAILED_NO_CERTIFICATES` | Signature/v1 issue, not SDK. Unlikely here (v1 verified). |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` / signature mismatch | A previous build with a different key is installed. Uninstall first. |
| `INSTALL_FAILED_NO_MATCHING_ABIS` | Native lib ABI mismatch — phone has no `armeabi`/`armeabi-v7a` translation. This is the next suspected blocker (see below). |
| Installs, then **crashes on launch** | Install gate cleared; the remaining problem is runtime (native lib / 64-bit / server), not the install SDK gate. |

## Next suspected blocker if SDK is no longer the issue
1. **ABI / 32-bit native libs.** The app ships `lib/armeabi/libZombieCafeAndroid.so`
   and `libZombieCafeExtension.so` — 32-bit ARM only. Many modern phones are 64-bit
   and, from Android 13+, some devices ship without 32-bit translation. Symptom:
   `INSTALL_FAILED_NO_MATCHING_ABIS`, or it installs but crashes immediately with a
   linker error. Fix path would require building arm64-v8a native libs (out of scope
   for this SDK test, and native C++ is off-limits here).
2. **Runtime behavior at higher target.** Not relevant at 24, but if we later raise
   target further, cleartext HTTP, runtime permissions, and scoped storage become
   enforced.
3. **Server reachability.** Online services may need the revival server running; that
   is a post-install gameplay concern, not an install gate.

The cleanest signal: if `adb install` **succeeds**, the SDK hypothesis is confirmed.
If it fails with an ABI error, the blocker has moved to native 32/64-bit support.

## Physical device test result — Samsung Galaxy A54 (Android 14)

**Outcome: install SUCCEEDED, launch CRASHED (native text relocation).** The
`targetSdkVersion 14 → 24` SDK hypothesis is **confirmed** — the install gate was the
SDK floor, and raising the target to 24 cleared it. A new, separate runtime blocker is
now exposed.

### Device facts
| Property | Value |
|----------|-------|
| `ro.build.version.release` | 14 |
| `ro.build.version.sdk` | 34 |
| `ro.product.cpu.abi` | `arm64-v8a` |
| `ro.product.cpu.abilist` | `arm64-v8a,armeabi-v7a,armeabi` |

The phone **does** carry 32-bit ARM support (`armeabi-v7a,armeabi` in the abilist), so
the earlier "next suspected blocker" #1 (`INSTALL_FAILED_NO_MATCHING_ABIS` / missing
32-bit translation) **did not** occur here. The 32-bit `lib/armeabi/` library was
accepted and extracted to `lib/arm/` on the device.

### Install result
```
adb install C:\Users\New\Desktop\zombie-cafe-target24-signed.apk
Success
```

### Launch result — immediate crash in System.loadLibrary
```
java.lang.UnsatisfiedLinkError: dlopen failed:
  "/data/app/.../lib/arm/libZombieCafeAndroid.so" has text relocations
        at com.capcom.zombiecafeandroid.ZombieCafeAndroid.<clinit>
```

### Interpretation
This matches the bottom row of the "Expected install errors" table ("Installs, then
**crashes on launch**"): the install SDK gate is cleared, and the remaining problem is
runtime native loading — **not** the install SDK gate and **not** ABI translation.

Root cause, in one line: `libZombieCafeAndroid.so` carries a `DT_TEXTREL` dynamic tag
(a load-time relocation that writes into a non-writable code page). Android's dynamic
linker **rejects** any library with text relocations once the app's
`targetSdkVersion ≥ 23` (Android 6.0 "Text Relocations No Longer Supported"). Below
target 23 it was only a warning.

**The tension this exposes:** on Android 14 there is *no* single target value that both
installs and tolerates the text relocation —
- target `< 23` → text relocation tolerated, but the **install** is blocked by the SDK floor;
- target `≥ 23/24` → **installs**, but the linker now treats the text relocation as fatal.

Raising the target to 24 (to clear the install floor) is precisely what crossed the
linker's text-relocation enforcement threshold. So fixing install necessarily surfaced
this load-time failure on a modern device.

Full native analysis, exact relocation counts, patch options, and the recommended next
experiment are in
[`native_text_relocation_investigation.md`](native_text_relocation_investigation.md).
A raw relocation dump is saved alongside it as `libZombieCafeAndroid_relocations.txt`.
