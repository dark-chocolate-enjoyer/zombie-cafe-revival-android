# Textrel patch — throwaway test build for the Galaxy A54

**What this is.** A throwaway, signed APK in which the single text relocation in
`libZombieCafeAndroid.so` has been removed via the **robust Strategy A** patch from
[`textrel_patch_plan.md`](textrel_patch_plan.md). The goal is to test on the A54
(Android 14) whether removing `DT_TEXTREL` lets the native library load past
`System.loadLibrary`.

**Constraints honoured**
- `src/lib/armeabi/libZombieCafeAndroid.so` was **not** modified — sha256 still
  `24c6509a978c7de96935b263363bda6ad6b5ea41b9ba819755ae8ad16d2cb45d` (verified before and
  after the build).
- No gameplay data touched; nothing committed.
- The patch was applied to a **scratch copy** (`/tmp/textrel/patched.so`) first.
- The patched `.so` was placed **only** into `build/lib/armeabi/` (which is git-ignored)
  for this test APK.
- Not installed from WSL — install/test is to be done from Windows CMD with `adb`.

---

## 1. Library identities (sha256)

| Artifact | sha256 | Notes |
|---|---|---|
| **Original source** `src/lib/armeabi/libZombieCafeAndroid.so` | `24c6509a978c7de96935b263363bda6ad6b5ea41b9ba819755ae8ad16d2cb45d` | **unchanged** (pristine) |
| **Patched scratch** `/tmp/textrel/patched.so` | `d7b7e6c42da4a80ab99d071d4794c0daec5e62074525ae90f8ca08833e39ef08` | robust Strategy A applied |
| **Lib inside final APK** `lib/armeabi/libZombieCafeAndroid.so` | `d7b7e6c42da4a80ab99d071d4794c0daec5e62074525ae90f8ca08833e39ef08` | byte-identical to scratch ✔ |

Both files are **1,947,420 bytes** (size unchanged — all edits are equal-length
in-place overwrites).

---

## 2. Byte edits applied (robust Strategy A)

Applied by a verify-before-write script (`/tmp/textrel/patch_textrel.py`) that asserts
the expected *old* bytes at each offset before writing. Script output:

```
  Edit 1  : thunk -> bx lr
    @ 0x0005ddc0: 04008fe2 -> 1eff2fe1
  Edit 2a : .rel.dyn[0] <- entry[3977] (relative, off 0x1daf6c)
    @ 0x00055490: ccdd050017000000 -> 6caf1d0017000000
  Edit 2b : .rel.dyn[3977] -> R_ARM_NONE (off 0x5ddcc)
    @ 0x0005d0d8: 6caf1d0017000000 -> ccdd050000000000
  Edit 3a : DT_TEXTREL slot -> DT_RELCOUNT=3977
    @ 0x001d4a70: 1600000000000000 -> faffff6f890f0000
  Edit 3b : old DT_RELCOUNT slot -> DT_NULL
    @ 0x001d4a78: faffff6f8a0f0000 -> 0000000000000000
patched OK
```

| # | File offset | Old bytes | New bytes | Effect |
|---|---|---|---|---|
| 1 | `0x0005ddc0` | `04 00 8f e2` (`add r0,pc,#4`) | `1e ff 2f e1` (`bx lr`) | neuter the `__on_dlclose`/`__cxa_finalize` finalizer thunk |
| 2a | `0x00055490` | `cc dd 05 00 17 00 00 00` (off `0x5ddcc`, RELATIVE) | `6c af 1d 00 17 00 00 00` (off `0x1daf6c`, RELATIVE) | swap the last relative entry into `.rel.dyn[0]` |
| 2b | `0x0005d0d8` | `6c af 1d 00 17 00 00 00` (off `0x1daf6c`, RELATIVE) | `cc dd 05 00 00 00 00 00` (off `0x5ddcc`, **R_ARM_NONE**) | move the text reloc to the type-checked tail, retyped to a no-op |
| 3a | `0x001d4a70` | `16 00 00 00 00 00 00 00` (`DT_TEXTREL` 0) | `fa ff ff 6f 89 0f 00 00` (`DT_RELCOUNT` 3977) | strip `DT_TEXTREL`; move `RELCOUNT` up, decremented |
| 3b | `0x001d4a78` | `fa ff ff 6f 8a 0f 00 00` (`DT_RELCOUNT` 3978) | `00 00 00 00 00 00 00 00` (`DT_NULL`) | new dynamic-array terminator |

**`cmp -l` confirms exactly 23 differing bytes, all inside the 5 intended regions:**

```
byte 0x55490 ..0x55492   (Edit 2a, 3 bytes)
byte 0x5d0d8 ..0x5d0da, 0x5d0dc   (Edit 2b, 4 bytes)
byte 0x5ddc0 ..0x5ddc3   (Edit 1, 4 bytes)
byte 0x1d4a70..0x1d4a75  (Edit 3a, 6 bytes)
byte 0x1d4a78..0x1d4a7d  (Edit 3b, 6 bytes)
total differing bytes: 23
```

---

## 3. Static verification of the patched `.so`

**[1] `DT_TEXTREL` removed** — `readelf -d /tmp/textrel/patched.so | grep -i textrel`
produced **no output** (exit 1). ✔

**[2] Dynamic counters** — `readelf -d | grep -iE 'RELSZ|RELCOUNT|NULL'`:
```
 0x00000002 (PLTRELSZ)   1208 (bytes)
 0x00000012 (RELSZ)      32080 (bytes)   <- unchanged (retype, not delete)
 0x6ffffffa (RELCOUNT)   3977            <- was 3978
 0x00000000 (NULL)       0x0             <- terminator intact
```

**[3] The `0x5ddcc` relocation is now a no-op** — `readelf -r | grep -i ddcc`:
```
0005ddcc  00000000 R_ARM_NONE
```
and the new first `.rel.dyn` entry is the swapped-in relative reloc:
```
001daf6c  00000017 R_ARM_RELATIVE
```

**[4] Zero *applied* text-segment relocations** (type-aware classifier):
```
text-segment reloc ENTRIES (by offset)        : 1
  of which R_ARM_NONE (no-op, not applied)    : 1
  of which APPLIED (would write to text)      : 0   <-- target
```
> Note: the offset-only classifier from the plan reports **1** because the benign
> `R_ARM_NONE` entry still *carries* offset `0x5ddcc`. `R_ARM_NONE` is never applied by
> the linker, so the meaningful count — relocations that would **write** to the
> read-only text segment — is **0** (the original had exactly **1**). This is expected
> for the robust swap variant, which intentionally leaves a no-op placeholder rather
> than physically deleting an entry (which would shift the whole file).

**[5] File size unchanged** — both `src` and patched are `1947420` bytes. ✔

**[6] Source `.so` still pristine** — sha256 `24c6509a…` before and after the entire
build. ✔

---

## 4. Build pipeline

```bash
# 5. regenerate build/ from src/ (copies the PRISTINE source lib in)
go run ./tool/build_tool -i src/ -o build/

# 6. overwrite ONLY build/ with the patched scratch lib
cp /tmp/textrel/patched.so ./build/lib/armeabi/libZombieCafeAndroid.so   # -> d7b7e6c4…

# 7. extension lib as usual
cp src/lib/cpp/build/libZombieCafeExtension.so ./build/lib/armeabi/libZombieCafeExtension.so

# 8. strip numeric quotes so apktool reads ints
perl -pi -e "s/: '([0-9]+)'/: \1/g" build/apktool.yml      # -> minSdkVersion: 8, targetSdkVersion: 24

# 9. build + sign
rm -f ./build/out/out-unsigned.apk ./build/out/zombie-cafe-target24-textrelpatch-signed.apk
mkdir -p ./build/out
apktool b ./build -o ./build/out/out-unsigned.apk
apksigner sign \
  --ks debug.keystore --ks-pass pass:zombiecafe --key-pass pass:zombiecafe \
  --ks-key-alias alias_name \
  --out ./build/out/zombie-cafe-target24-textrelpatch-signed.apk \
  ./build/out/out-unsigned.apk
apksigner verify --verbose ./build/out/zombie-cafe-target24-textrelpatch-signed.apk

# 10. export to Windows desktop
cp ./build/out/zombie-cafe-target24-textrelpatch-signed.apk \
   /mnt/c/Users/New/Desktop/zombie-cafe-target24-textrelpatch-signed.apk
```

**Order matters:** `build_tool` (step 5) copies the *unpatched* source lib into `build/`,
so the patched lib is dropped in *afterwards* (step 6). Verified: the `build/` lib was
`24c6509a…` immediately after step 5, then `d7b7e6c4…` after step 6.

The patched lib survives apktool packaging unchanged — the lib **extracted back out of the
final signed APK** hashes to `d7b7e6c4…` and has **no `DT_TEXTREL`** (`RELCOUNT 3977`).

---

## 5. Final APK

| | |
|---|---|
| Build output | `build/out/zombie-cafe-target24-textrelpatch-signed.apk` |
| Exported to | `/mnt/c/Users/New/Desktop/zombie-cafe-target24-textrelpatch-signed.apk` |
| Windows path | `C:\Users\New\Desktop\zombie-cafe-target24-textrelpatch-signed.apk` |
| Size | 38,798,242 bytes |
| APK sha256 | `3ea9b066b0bc05755a5c745cc1b8d2e19abdc5d78e6e11a8dcab8e56f58f24aa` (build output and desktop copy match) |
| `package` | `com.capcom.zombiecafeandroid` versionCode `19` (`ZombieCafeAndroid 1.1.2.0a`) |
| `minSdkVersion` | `8` |
| `targetSdkVersion` | `24` |

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

## 6. How to install & test (from Windows CMD — not run here)

```bat
adb uninstall com.capcom.zombiecafeandroid
adb install "C:\Users\New\Desktop\zombie-cafe-target24-textrelpatch-signed.apk"
adb logcat -c & adb logcat | findstr /I "ZombieCafe UnsatisfiedLinkError text relocations dlopen"
```

**What success looks like:** the app launches past `System.loadLibrary` with **no**
`"has text relocations"` `UnsatisfiedLinkError`. That confirms the TEXTREL patch is the
correct and sufficient fix for the load failure on the A54.

**If it still crashes:** capture the new logcat. A *different* error (missing symbol,
GLESv1, server) means TEXTREL was necessary but not the only blocker; a SIGSEGV at load
would point at a patch-mechanics issue (see `textrel_patch_plan.md` §10 failure modes).

---

## 7. Repo state

```
$ git status --short
 M src/apktool.yml
?? docs/compat/

$ git diff --stat
 src/apktool.yml | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

- `src/apktool.yml` — pre-existing `targetSdkVersion 14→24` change (not from this task).
- `docs/compat/` — untracked docs (this report joins them).
- `build/` is **git-ignored**, so the patched lib placed there does not appear in git
  status and cannot leak into a commit.
- The scratch copy and patch script live under `/tmp/textrel/` (outside the repo).

### Files created/modified by this task
- Created: `docs/compat/textrel_patch_test_build.md` (this report).
- Created (outside repo, throwaway): `/tmp/textrel/patched.so`,
  `/tmp/textrel/patch_textrel.py`.
- Regenerated (git-ignored): `build/` tree, including the patched
  `build/lib/armeabi/libZombieCafeAndroid.so` and
  `build/out/zombie-cafe-target24-textrelpatch-signed.apk`.
- Exported: `/mnt/c/Users/New/Desktop/zombie-cafe-target24-textrelpatch-signed.apk`.
- **Not** modified: `src/lib/armeabi/libZombieCafeAndroid.so` (sha256 `24c6509a…`).
