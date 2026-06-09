# Native text-relocation investigation — `libZombieCafeAndroid.so`

**Context.** On a Samsung Galaxy A54 (Android 14, SDK 34) the rebuilt
`targetSdkVersion 24` APK **installs successfully** but **crashes immediately** during
`System.loadLibrary`:

```
java.lang.UnsatisfiedLinkError: dlopen failed:
  "/data/app/.../lib/arm/libZombieCafeAndroid.so" has text relocations
        at com.capcom.zombiecafeandroid.ZombieCafeAndroid.<clinit>
```

This report inspects the library to characterise the text relocation, judge how hard it
is to remove, and recommend the next smallest experiment.

> **Scope guardrails honoured:** no gameplay data touched, the APK was not rebuilt, the
> `.so` was **not** patched, and nothing was committed. Only read-only ELF inspection
> was performed; the one new artifact is the relocation dump
> `libZombieCafeAndroid_relocations.txt`.

---

## TL;DR

- The library is a **32-bit ARMv5TE** shared object built with an **ancient NDK
  (GCC 4.4.3)**.
- It carries a `DT_TEXTREL` dynamic tag. Android's linker rejects libraries with text
  relocations once `targetSdkVersion ≥ 23` — which is exactly the target we raised to
  (24) to clear the install gate. **The install fix is what surfaced this crash.**
- The text relocation is **a single, isolated site** — exactly **one** relocation
  (`R_ARM_RELATIVE` at `0x5ddcc`) lands in executable memory. The other **4,160**
  relocations all target the normal writable data segment and are *not* text
  relocations. The binary is otherwise fully position-independent.
- That one site is a stock **GCC init/CRT thunk** that embeds a relocatable pointer
  literal inline in `.text`.
- Because it is one isolated, compiler-generated site, **binary-patching it is
  bounded** (though still delicate). Rewriting the whole native library is impractical;
  running on **Android ≤ 5.1** sidesteps the problem entirely with zero changes.

---

## 1. Exact source path in the repo

Authoritative source artifact (checked into `src/`):

```
src/lib/armeabi/libZombieCafeAndroid.so
```

- Size: **1,947,420 bytes**
- `sha256`: `24c6509a978c7de96935b263363bda6ad6b5ea41b9ba819755ae8ad16d2cb45d`

A second, **byte-identical** copy exists at `build/lib/armeabi/libZombieCafeAndroid.so`
(same sha256). That copy is a **generated build output** — the build tool copies the
`src/` tree into `build/`. The source of truth is the `src/` path.

> Note: this is the *game-engine* native library and has **no source in the repo** (it
> is a stripped prebuilt). It is **not** the same as `libZombieCafeExtension.so`, which
> *is* built from source under `src/lib/cpp/` (`Memory.cpp`, `ZombieCafeExtension.cpp`).
> The crash is in `libZombieCafeAndroid.so`, the prebuilt engine library.

---

## 2. Architecture (`file` / `readelf -h`)

```
$ file src/lib/armeabi/libZombieCafeAndroid.so
ELF 32-bit LSB shared object, ARM, EABI5 version 1 (SYSV), dynamically linked, stripped
```

```
$ readelf -h src/lib/armeabi/libZombieCafeAndroid.so
  Class:                             ELF32
  Data:                              2's complement, little endian
  Type:                              DYN (Shared object file)
  Machine:                           ARM
  Flags:                             0x5000002, Version5 EABI, <unknown>
  Entry point address:               0x5ddc0
```

ARM build attributes and compiler identity:

```
$ readelf -A ...        →  Tag_CPU_name: "5TE"   Tag_CPU_arch: v5TE   Tag_THUMB_ISA_use: Thumb-1
$ readelf -p .comment   →  GCC: (GNU) 4.4.3   (repeated for every TU)
```

**Summary:** 32-bit ARM, ARMv5TE / Thumb-1, EABI5, stripped, built with **GCC 4.4.3**
(Android NDK ~r4/r5 era, circa 2010). This is consistent with the rest of the
compat work: the app is a very old 32-bit-only title. The A54 still provides 32-bit
translation (`armeabi-v7a,armeabi`), so ABI is *not* the blocker on this device — the
text relocation is.

---

## 3. Does it have TEXTREL flags?

**Yes.** The dynamic section contains a `DT_TEXTREL` entry:

```
$ readelf -d src/lib/armeabi/libZombieCafeAndroid.so | grep -i textrel
 0x00000016 (TEXTREL)                    0x0
```

Notes on how to read this:

- `DT_TEXTREL` (tag `0x16`) being **present at all** is the signal. Its value (`0x0`)
  is irrelevant — the tag is a boolean marker that says "this object has at least one
  relocation against a non-writable (text) segment." Old toolchains emit `DT_TEXTREL`
  rather than setting the `DF_TEXTREL` bit inside `DT_FLAGS`.
- There is **no `DT_FLAGS` entry** in this library, so there is no `DF_TEXTREL` bit to
  inspect; the standalone `DT_TEXTREL` tag is the authoritative indicator here.
- The Android dynamic linker keys off this exact tag. For `targetSdkVersion ≥ 23` it
  refuses to load the library (`"has text relocations"`); for `< 23` it only logs a
  warning. We are at target 24 → fatal.

---

## 4. Dynamic-section entries related to TEXTREL

Full `readelf -d` (relevant rows):

```
 Tag        Type            Name/Value
 0x00000016 (TEXTREL)       0x0          ← the text-relocation marker
 0x00000011 (REL)           0x55490      ← .rel.dyn base
 0x00000012 (RELSZ)         32080 (bytes)   → 32080 / 8 = 4010 entries
 0x00000013 (RELENT)        8 (bytes)
 0x6ffffffa (RELCOUNT)      3978         ← count of leading R_ARM_RELATIVE relocs
 0x00000017 (JMPREL)        0x5d1e0      ← .rel.plt base
 0x00000002 (PLTRELSZ)      1208 (bytes)    → 1208 / 8 = 151 entries
 0x00000014 (PLTREL)        REL
 0x00000003 (PLTGOT)        0x1d5aa8
 0x00000010 (SYMBOLIC)      0x0          ← symbolic binding (relevant to why RELATIVE relocs dominate)
```

There is **no `DT_FLAGS` / `DT_FLAGS_1`** entry and **no `GNU_RELRO`** segment. The
relocation tables are classic REL (8-byte) form, split into `.rel.dyn` (general) and
`.rel.plt` (PLT/jump slots).

---

## 5. Relocation sections and relocation types (`readelf -r`)

Two relocation sections (saved in full to `libZombieCafeAndroid_relocations.txt`):

| Section    | Type | Entries |
|------------|------|---------|
| `.rel.dyn` | REL  | 4010    |
| `.rel.plt` | REL  | 151     |
| **Total**  |      | **4161** |

Relocation-type histogram across both sections:

| Type              | Count | Targets |
|-------------------|-------|---------|
| `R_ARM_RELATIVE`  | 3978  | base-relative pointers (mostly `.got` / `.data.rel.ro` / `.init_array` / `.data`) |
| `R_ARM_JUMP_SLOT` | 151   | `.got.plt` (PLT, writable) |
| `R_ARM_ABS32`     | 28    | absolute symbol pointers in writable data |
| `R_ARM_GLOB_DAT`  | 4     | GOT entries for global symbols |

The `R_ARM_RELATIVE` count (3978) matches `DT_RELCOUNT`, confirming the table is the
normal "relative relocs first" layout.

---

## 6. Are the text relocations few/concentrated or widespread?

**Extremely concentrated — there is exactly ONE text relocation.**

A "text relocation" is a relocation whose *target offset* falls inside a non-writable
loadable segment. From the program headers, the read-execute segment is:

```
LOAD  Offset 0x000000  VirtAddr 0x00000000  FileSiz 0x1d227c  Flg R E   ← code/rodata, NOT writable
LOAD  Offset 0x1d227c  VirtAddr 0x001d327c  FileSiz 0x07cf4   Flg RW    ← data, writable
```

Classifying every relocation by whether its offset is `< 0x1d227c` (inside the R E
segment):

```
Total relocation entries parsed: 4161
  In read-execute (text) LOAD segment: 1          ← the only text relocation
    ...of which in .text (code):       1
    ...of which in .rodata:            0
  In read-write (data) LOAD segment:  4160         ← normal, not text relocations
  Text-seg reloc offset range: 0x5ddcc .. 0x5ddcc
```

So **4,160 of 4,161 relocations are perfectly normal** writable-data relocations (the
library is otherwise fully position-independent — note the compiler even routed its
relocatable read-only pointers into `.data.rel.ro`, a *writable* RELRO-style section,
which avoids text relocs). **Exactly one** relocation writes into code:

```
$ grep -n . docs/compat/libZombieCafeAndroid_relocations.txt   # the sole in-text entry:
0005ddcc  00000017 R_ARM_RELATIVE
```

### What that one site is

The bytes at `0x5ddc0` (the entry-point address, start of `.text`) decode to a stock
GCC init/CRT thunk:

```
0x5ddc0:  e28f0004   add r0, pc, #4      ; r0 = 0x5ddcc (address of the literal below)
0x5ddc4:  e5900000   ldr r0, [r0]        ; r0 = *(0x5ddcc)
0x5ddc8:  eafffe8e   b   0x5d808         ; branch into .plt (call an imported function)
0x5ddcc:  0x001daf70 .word               ; ← inline relocatable literal = start of .bss
                                         ;    this word needs base added at load time
```

`0x1daf70` is the start of `.bss`. The compiler placed a **relocatable data pointer
inline in the executable section** instead of in the GOT, so the loader must write into
a code page to fix it up — that single write is the entire text-relocation problem. It
is a compiler/CRT artifact (the kind of optional `__gmon_start__` / clone-table /
constructor-registration glue old GCC emits at the head of `.text`), **not** pervasive
hand-written non-PIC code.

**Verdict:** one isolated, compiler-generated site. This is the best possible case for
a prebuilt library — and it materially changes the difficulty math below.

---

## 7. What it would theoretically take to remove/patch the text relocation

To make `dlopen` succeed at `targetSdkVersion ≥ 23`, two things must both be true:
**(a)** the loader must no longer need to write into a non-writable segment, and
**(b)** the `DT_TEXTREL` tag must be gone (the linker rejects on the tag's presence).
You cannot keep `DT_TEXTREL` and "just allow it" — the OS hard-fails regardless of the
value.

Concrete routes, easiest-to-source-hardest:

1. **Recompile from source (clean fix).** Rebuild with a modern NDK that keeps
   relocatable pointers out of `.text` (modern compilers route them through the GOT, so
   no `DT_TEXTREL` is emitted). *Blocked: there is no source for this engine library in
   the repo.*

2. **Binary-patch the single site (bounded surgery).** Because there is exactly one
   text relocation:
   - **Option 2a — GOT-indirect the literal.** Move the `0x1daf70` pointer into a GOT
     slot in the writable segment, rewrite the `add/ldr` pair to load it from there, and
     drop the in-text `R_ARM_RELATIVE` entry plus the `DT_TEXTREL` tag. Clean but
     fiddly: the writable segment is far from this code, so the load can't be a single
     short PC-relative form — it needs an extra indirection. Requires careful
     ARM/Thumb encoding.
   - **Option 2b — neuter the thunk.** If this head-of-`.text` thunk is the optional
     CRT glue it appears to be (calls a weak/no-op import via the PLT), replace it with
     a `bx lr` (or NOP-out the relocated load), delete the one `R_ARM_RELATIVE` entry,
     and remove `DT_TEXTREL`. Smallest possible patch (one instruction + two metadata
     edits) **but** must be verified safe — we'd need to confirm the thunk's target and
     that nothing depends on `*(0x5ddcc)` being relocated. Risk: silent breakage if the
     thunk is load-bearing.
   - Either way the relocation table size, `DT_REL*` counts, `DT_RELCOUNT`, and segment
     permissions must stay self-consistent so the linker doesn't choke on the edited
     metadata.

3. **What you cannot do:** you can't simply delete the `R_ARM_RELATIVE` entry and leave
   the inline literal — the stored value would be an unrelocated `.bss` offset and would
   be wrong under ASLR. You also can't bake in a fixed load base (shared objects are
   loaded at a randomized address). And you can't make only the page writable while
   keeping `DT_TEXTREL` — the OS rejects on the tag.

---

## 8. Difficulty comparison of the three paths

| Path | Difficulty | Why | Helps the A54? |
|------|-----------|-----|----------------|
| **Patch the text relocation** (binary surgery on the one site) | **Medium, but bounded** | Only **one** site to fix; the rest of the lib is already PIC. Requires ELF/ARM-encoding care and load-testing, with real risk if the thunk is load-bearing (2b) or the indirection is mis-encoded (2a). Verifiable on a scratch copy. | **Yes** — the A54 has 32-bit support, so a TEXTREL-free 32-bit lib should load. |
| **Rewrite / replace the native library** | **Very high / impractical** | `libZombieCafeAndroid.so` is the entire ~1.9 MB stripped game engine (GLESv1+GLESv2 renderer, JNI entry points the Java/smali layer calls by exact name). Re-implementing its ABI from scratch is a full reverse-engineering project, not a compat tweak. | Yes if completed, but the effort is disproportionate. |
| **Use an older Android ≤ 5.1 (API ≤ 22) environment** | **Lowest / trivial** | API ≤ 22 does **not** enforce the install SDK floor (so the *original* target-14 APK installs) **and** only *warns* on text relocations (so the lib loads as-is). Zero binary changes. This is also why BlueStacks already works — it runs an older, permissive image. | **No** — it does not make the A54 itself work; it's a validation/playable-fallback environment. |

**Reading the table:** patching is the only path that both (a) is realistic in effort
and (b) actually targets modern devices like the A54. Replacing the library is
disproportionate. The Android-≤5.1 route is essentially free but only proves the rest of
the app is healthy and gives a playable fallback — it doesn't advance the modern-device
goal.

---

## 9. Recommended next smallest experiment

**Run the existing signed APK on an Android ≤ 5.1 (API ≤ 22) emulator/device and confirm
the game reaches its main loop — with no changes to the `.so`.**

Rationale (why this is the right *smallest* next step, before any patching):

- It is **zero-risk and zero-modification** (honours "don't patch the library yet"). It
  uses an environment where the text relocation is tolerated, so it isolates the single
  remaining question: *is the text relocation the **only** modern blocker, or are there
  deeper load-time problems (missing symbols, GLESv1 availability, server/JNI issues)?*
- If the game **loads and runs** on API ≤ 22, then `DT_TEXTREL` is confirmed as the sole
  thing standing between us and the A54, and investing in the bounded one-site binary
  patch (path 1 / Option 2) is justified.
- If the game **also fails** on API ≤ 22, then patching the text relocation would be
  wasted effort and we've learned that cheaply, before touching the binary.

Practical form: `emulator @api22` (or an existing BlueStacks instance), then
`adb install` the **original unmodified** APK (target 14 installs fine there) — or the
target-24 build, since ≤ 5.1 ignores both the SDK floor and the TEXTREL.

**Only if that passes**, the *follow-up* smallest experiment is to prototype the
single-site TEXTREL patch on a **throwaway copy** of the `.so` (Option 2b first, since
it's the smallest edit), `dlopen`-test it in isolation, and verify `readelf -d` no
longer lists `DT_TEXTREL` before considering a rebuilt APK. That work stays out of scope
for *this* report (no patching yet).

---

## Appendix — commands used

```bash
file    src/lib/armeabi/libZombieCafeAndroid.so
readelf -h  src/lib/armeabi/libZombieCafeAndroid.so
readelf -A  src/lib/armeabi/libZombieCafeAndroid.so
readelf -p .comment src/lib/armeabi/libZombieCafeAndroid.so
readelf -d  src/lib/armeabi/libZombieCafeAndroid.so | grep -i textrel
readelf -S  src/lib/armeabi/libZombieCafeAndroid.so      # section headers
readelf -l  src/lib/armeabi/libZombieCafeAndroid.so      # program headers / segments
readelf -r  src/lib/armeabi/libZombieCafeAndroid.so > docs/compat/libZombieCafeAndroid_relocations.txt
objdump -d --start-address=0x5ddc0 --stop-address=0x5de00 src/lib/armeabi/libZombieCafeAndroid.so
# scanelf was NOT available in this environment; equivalent data obtained via readelf -d/-r.
```

Raw relocation dump: [`libZombieCafeAndroid_relocations.txt`](libZombieCafeAndroid_relocations.txt)
