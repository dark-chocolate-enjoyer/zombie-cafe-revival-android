# The cafe → map crash: root cause found and fixed (2026-10-09)

**Status: solved in v6.** The crash `Scudo ERROR: corrupted chunk header` (Android 11+, whose Scudo allocator checks block headers) (seen on cafe → map
trips since the JP project started, and the same message that stopped the EN Revival) is caused by a
one-byte write past the end of a heap block in Capcom's `javaGetDeviceInfoForURL`. Fixed in
`lib_fixes.py` (4 bytes); in the release build from v6.

## 1. The bug

`javaGetDeviceInfoForURL` (`libZombieCafeAndroid.so` `0x29924c`) asks Java for a device-info text and copies
it into a C buffer:

```
0029926e  bl    GetArrayLength          ; len = length of the Java byte[]   (80 on the A54)
00299272  adds  r5, r0, #0              ; r5 = len
00299274  blx   malloc                  ; buf = malloc(len)                 ← no room for a terminator
...       bl    GetByteArrayRegion      ; copy len bytes into buf
00299288  movs  r3, #0
0029928a  strb  r3, [r4, r5]            ; buf[len] = 0                      ← 1 byte PAST the end
```

The text comes from `CC_Android.fromNative_GetDeviceInfoForURL()`:
`&brand=…&mani=…&dev=…&model=…&prod=…` (and more), built from fixed device properties, so it has the
same length every time on a given phone: **80 bytes on the Galaxy A54**.

It runs on every save upload (`CCServer::SaveMyGameState` ← `ZombieCafe::saveGameState`, at cafe load and
cafe exit) and on daily-activity analytics (`MALTAHoover::sendDailyActivity`), even with no internet.

## 2. Why it corrupts the heap on the A54 (and not on 2016 phones)

Android 11+ uses the Scudo allocator. Each block has a header (label) in front of the data, and blocks of
similar size share regions of fixed-size slots. Scudo's size table on this phone (read from its libc at
`0x227d0`) goes `0x20, 0x30, 0x40, 0x50, 0x60…`, and on Android the header area is **16 bytes**: every
victim address in every crash is 16-byte aligned (`…f30`, `…4f0`, `…850`, `…2b0`, `…b30`…).

So `malloc(80)` takes 16 (header) + 80 (data) = **96 bytes, exactly one 96-byte slot, with nothing spare**.
`buf[80] = 0` lands on the **first byte of the next slot**, which is the next block's header. Scudo detects
that later, when the next block is freed, and aborts the game.

The victims are therefore whatever lives in the neighbouring 96-byte slot (objects of 65–80 bytes):
`CafeWall` (72 B), `EatTask` (68 B), `MoveTask`, `CharacterCommandBar` arrays, 65–80-character text
buffers… and the abort happens when those are freed, mostly during the cafe teardown right after the save.

Older allocators (dlmalloc/jemalloc) rounded such a block up with spare bytes, so the stray zero landed
in padding. On another phone the text length differs: the bug only bites when 16 + length fills a slot
exactly (lengths 16, 32, 48, 80, 96… up the table), which is why it can look device-dependent.

## 3. Evidence

| Step | Result |
| --- | --- |
| GWP-ASan (5f/5g, automated runs A and B) | `Cause: [GWP-ASan]: Buffer Overflow, 0 bytes right of a 80-byte allocation`, frame #0 `javaGetDeviceInfoForURL+62` (the `strb` at `0x29928a`); registers `r4` = block start, `r5` = `0x50` |
| Automated loop, run A (5g, online) | 15/40 Scudo crashes |
| Automated loop, run B (5g + offline, no server traffic) | 17/39 Scudo crashes → server requests are not the cause |
| **v6** (v5 + raid, toString, **device-info** fixes + offline) | **0/20** |
| **Control** = v6 with only the 4 device-info bytes put back (`0bf684eb`) | **10/20** |
| Victim addresses in the control run | all exact multiples of 96 bytes apart (one 96-byte-slot region); the v5 crash at 16:01 hit one of the same addresses (`0xe7b764f0`) |

v6 vs control differ in 4 bytes only, so the fix is causal (10/20 vs 0/20, Fisher p ≈ 0.0004).

## 4. The fix (`lib_fixes.py`, entry "device-info terminator: call")

`0x299274`: `blx malloc` (`0bf684eb`) → `bl 0x290ec2` (`f7f725fe`), the helper added for the toString fix
(`STRING_BUG.md`): `malloc(len + 1)` and `buf[len] = 0`. The game's own `buf[len] = 0` then stays inside
the block. `r5` (len) is untouched; the helper preserves `r4`.

## 5. Open questions

- The EN Revival lib (`src/lib/armeabi/libZombieCafeAndroid.so`) has **no** `javaGetDeviceInfoForURL`
  (older engine). Whether the EN crash has a similar Java → native text off-by-one elsewhere is unchecked.
  The quick scan written for it (scratch) is broken: it did not even find the known JP case.
- The other two fixes (raid list typo, toString terminator) are real bugs but were not the crash.
- Owner play-test of v6 by hand still to do (the automated test only does launch → Play → Map).
