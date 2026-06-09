# `getDeviceId` SecurityException fix — Galaxy A54 (Android 14)

## What this fixes

With the [textrel patch](textrel_patch_test_build.md) applied, the app now loads its
native library successfully and launches further — but then crashes during `onStart`:

```
java.lang.SecurityException: getDeviceId: The uid 10485 does not meet the requirements
                              to access device identifiers.
  at android.telephony.TelephonyManager.getDeviceId(TelephonyManager.java:2825)
  at com.capcom.zombiecafeandroid.DeviceType.getDeviceID(Unknown Source:18)
  at com.capcom.zombiecafeandroid.ZombieCafeAndroid.onStart(Unknown Source:189)
```

This patch removes the restricted device-identifier calls from
`DeviceType.getDeviceID()` so the game starts on modern Android, while keeping a
**stable, per-device** identifier for the rest of the app.

**Constraints honoured**
- No gameplay data modified.
- `src/lib/armeabi/libZombieCafeAndroid.so` **not** modified — sha256 still
  `24c6509a978c7de96935b263363bda6ad6b5ea41b9ba819755ae8ad16d2cb45d`.
- The textrel-patched native lib process is **exactly the same** as the prior build
  (scratch `d7b7e6c4…` copied only into `build/lib/armeabi/`).
- Nothing committed.

---

## 1. File and method changed

- **File:** `src/smali/com/capcom/zombiecafeandroid/DeviceType.smali`
- **Method:** `.method public static getDeviceID()V`

Two restricted `android.telephony.TelephonyManager` calls inside that method were
replaced with a constant fake IMEI string.

---

## 2. Why modern Android crashes on `getDeviceId`

`TelephonyManager.getDeviceId()` (and `getSimSerialNumber()`, `getImei()`,
`getSubscriberId()`, …) return **non-resettable hardware identifiers**. Starting with
**Android 10 (API 29)**, Google restricted these:

- They now require the **privileged** `READ_PRIVILEGED_PHONE_STATE` permission, which is
  only grantable to system/carrier apps — a normal app **cannot** hold it.
- A normal app calling them throws **`java.lang.SecurityException: … does not meet the
  requirements to access device identifiers`** — even if it declared
  `READ_PHONE_STATE`. (Before API 29, `READ_PHONE_STATE` was enough; the game targets an
  era where it "just worked".)

This game was built for Android 4.x (`getDeviceId()` was the normal way to get a stable
device ID then). On the A54 (Android 14 / API 34) the call is hard-blocked, so
`getDeviceID()` throws inside `onStart`, killing the app right after the native library
finally loads.

Note the failure only became reachable **because** the earlier blockers were fixed:
install gate (target 24) → native text relocation (lib patch) → **now** the telephony
identifier call. Each fix peels back to the next runtime gate.

---

## 3. Before / after

`getDeviceID()` returns `void`; its real job is to populate two static fields on
`ZombieCafeAndroid`:
- `mAndroidID` — the `Settings.Secure.ANDROID_ID` string, and
- `mDeviceId` — a `UUID` built from the hashes of `(deviceId, simSerial, androidId)`.

The patch swaps **only** the two restricted hardware-identifier reads for the constant
`"000000000000000"` (a conventional 15-digit "all zeros" IMEI placeholder). Everything
downstream is untouched, so `mDeviceId` is still a real UUID and remains **stable and
unique per device** via the un-restricted `ANDROID_ID`.

### Edit 1 — `getDeviceId()` → constant
```diff
-    invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;
-
-    move-result-object v3
+    const-string v3, "000000000000000"
```

### Edit 2 — `getSimSerialNumber()` → constant
```diff
-    invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getSimSerialNumber()Ljava/lang/String;
-
-    move-result-object v0
+    const-string v0, "000000000000000"
```

**Why both:** `getSimSerialNumber()` (line 723, the very next identifier read) is
restricted on API 29+ in exactly the same way. Fixing only `getDeviceId()` would have
moved the same `SecurityException` down two lines. Both are now constants.

**What is intentionally left intact:**
- `getSystemService("phone")` + `check-cast … TelephonyManager` — these do **not**
  require any permission and never throw; leaving them keeps the diff minimal. (The
  `TelephonyManager` reference simply goes unused; the register `v0` is later reused for
  the fake string, which is valid smali.)
- `Settings.Secure.getString(ANDROID_ID)` — **not** a restricted API; provides the
  real per-device entropy.
- The `UUID` construction, logging, and the `9774d56d682e549c` android_id sanity check.

Register usage stays consistent (`.locals 10` unchanged): `v3`/`v0` receive the constant
exactly where the old `move-result-object` wrote them, so the subsequent
`StringBuilder.append`/`hashCode` chain is unaffected. The unsigned APK assembled with no
smali/dex errors, and `"000000000000000"` is present in the compiled `classes.dex`.

### Resulting behaviour
| Field | Before | After |
|---|---|---|
| `mAndroidID` | `ANDROID_ID` | `ANDROID_ID` (unchanged) |
| device-id component of UUID | real IMEI | constant `000000000000000` |
| sim-serial component of UUID | real SIM serial | constant `000000000000000` |
| `mDeviceId` | UUID(android_id, imei, simserial) | UUID(android_id, const, const) — still stable & per-device |
| `onStart` | throws `SecurityException` | proceeds |

---

## 4. Scope note — other `getDeviceId()` call sites

`getDeviceId()` also appears in bundled third-party SDKs and one internal class, none of
which are in the current crash stack:

```
src/smali/com/capcom/zombiecafeandroid/g.smali
src/smali/com/paypal/android/b/b.smali
src/smali/com/paypal/android/MEP/b/a.smali
src/smali/com/chartboost/sdk/CBAPIRequest.smali   (x2)
src/smali/com/tapjoy/TapjoyConnectCore.smali
src/smali/org/acra/ErrorReporter.smali
src/smali/com/fiksu/asotracking/b.smali
```

These are **out of scope** for this fix (ads/analytics/payment/crash-reporter SDKs that
aren't exercised at `onStart`). If a later test reaches one of them, the same
`const-string` substitution applies. Only `DeviceType.getDeviceID()` was changed here.

---

## 5. Build commands used

```bash
# patched src/smali/com/capcom/zombiecafeandroid/DeviceType.smali (Edits 1 & 2 above)

# 1. regenerate build/ from src/ (copies the patched smali in)
go run ./tool/build_tool -i src/ -o build/

# 2. drop in the SAME textrel-patched native lib as before (scratch copy; src/ untouched)
cp /tmp/textrel/patched.so ./build/lib/armeabi/libZombieCafeAndroid.so     # d7b7e6c4…, no DT_TEXTREL

# 3. extension lib as usual
cp src/lib/cpp/build/libZombieCafeExtension.so ./build/lib/armeabi/libZombieCafeExtension.so

# 4. strip numeric quotes so apktool reads ints  (minSdk 8, targetSdk 24)
perl -pi -e "s/: '([0-9]+)'/: \1/g" build/apktool.yml

# 5. build unsigned
rm -f ./build/out/out-unsigned.apk ./build/out/zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk
mkdir -p ./build/out
apktool b ./build -o ./build/out/out-unsigned.apk

# 6. sign (debug keystore, v1+v2+v3)
apksigner sign \
  --ks debug.keystore --ks-pass pass:zombiecafe --key-pass pass:zombiecafe \
  --ks-key-alias alias_name \
  --out ./build/out/zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk \
  ./build/out/out-unsigned.apk

# 7. verify
apksigner verify --verbose ./build/out/zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk

# 8. export to Windows desktop
cp ./build/out/zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk \
   /mnt/c/Users/New/Desktop/zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk
```

---

## 6. APK output

| | |
|---|---|
| Build output | `build/out/zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk` |
| Exported to | `/mnt/c/Users/New/Desktop/zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk` |
| Windows path | `C:\Users\New\Desktop\zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk` |
| Size | 38,798,242 bytes |
| APK sha256 | `5add41bba4d40100d7df474a6373fc0a17c3dd0408f68f1c6b723a42e8aa343c` (build output == desktop copy) |
| `minSdkVersion` / `targetSdkVersion` | `8` / `24` |
| In-APK native lib | `libZombieCafeAndroid.so` sha256 `d7b7e6c4…`, **no `DT_TEXTREL`** (textrel patch intact) |
| `classes.dex` | contains the `000000000000000` constant ✔ |

### Signature verification output
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

---

## 7. Install & test (from Windows CMD — not run here)

```bat
adb uninstall com.capcom.zombiecafeandroid
adb install "C:\Users\New\Desktop\zombie-cafe-target24-textrelpatch-deviceidfix-signed.apk"
adb logcat -c & adb logcat | findstr /I "ZombieCafe SecurityException getDeviceId onStart"
```

**Success:** `onStart` completes with no `SecurityException` and the game advances past
the launch sequence. **If it still crashes:** capture the new stack — a different
`SecurityException`/identifier call (e.g. from `g.smali` or an SDK in §4) or a new
runtime gate (server, GLES) would be the next blocker.

---

## 8. Repo state

```
$ git status --short
 M src/apktool.yml
 M src/smali/com/capcom/zombiecafeandroid/DeviceType.smali
?? docs/compat/

$ git diff --stat
 src/apktool.yml                                         | 2 +-
 src/smali/com/capcom/zombiecafeandroid/DeviceType.smali | 8 ++------
 2 files changed, 3 insertions(+), 7 deletions(-)
```

- `src/apktool.yml` — pre-existing `targetSdkVersion 14→24` change (earlier task).
- `src/smali/.../DeviceType.smali` — **this task** (the device-id fix).
- `docs/compat/` — untracked docs (this report joins them).
- `build/` is git-ignored; the textrel-patched lib placed there and the output APK do
  not appear in git and cannot leak into a commit.
- `src/lib/armeabi/libZombieCafeAndroid.so` unchanged (sha256 `24c6509a…`).
- Nothing committed.
