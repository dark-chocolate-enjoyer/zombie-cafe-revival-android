# v1.0 Native Library Repair Notes

Short technical note on the launch-crash repair that produced the released v1.0 Balance Candidate APK.

## Symptom

The first v1.0 build installed cleanly but crashed immediately on first launch, then black-screened on subsequent launches.

## Cause

Logcat capture showed a fatal exception at startup:

```text
java.lang.UnsatisfiedLinkError: dlopen failed: failed to link libZombieCafeAndroid.so
    at com.capcom.zombiecafeandroid.ZombieCafeAndroid.<clinit>
```

The game's main native library failed to **link**, killing the process in the Activity class initializer — before any food data was read or game initialization ran. The stock `libZombieCafeAndroid.so` uses text relocations that the BlueStacks Android runtime refuses to link; a compatibility-patched copy of the library is required for emulator builds, and the first v1.0 build had packed the unpatched one.

The packed food data inside the crashing APK was decoded and verified correct (all 216 dishes matched the balanced source). **The crash was not caused by the food data or the balance work.**

## Fix

- The v1.0 food data and all other build output were preserved unchanged.
- Only the generated build-copy native library was replaced with the known-good, BlueStacks-compatible patched library (taken from a previously verified working build — native libraries only, no other files).
- The APK was reassembled and signed; signature verification passes (v1/v2/v3 schemes).
- The repaired APK was verified to launch in BlueStacks, and its packed food data was decoded again and confirmed identical to the balanced source.

## Scope of the repair

To be explicit:

- **No gameplay data was changed.** This was purely a build/runtime packaging repair.
- The repository source tree (`src/lib/` included) was **not** modified for the repair; only the generated build output was touched.

## Released APK

```text
File:    zombie_cafe_v1_0_balance_candidate_signed_repaired.apk
SHA-256: f630f3ddfeee823c485c478a8281d5278e2db09a69f265bc87b4986649e9a96c
```
