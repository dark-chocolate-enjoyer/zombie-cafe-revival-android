# Binary patch plan — remove the single text relocation from `libZombieCafeAndroid.so`

**Status: PLAN ONLY. Nothing was modified.** The `.so` was not patched, the APK was
not rebuilt, no gameplay data was touched, and nothing was committed. This document is
the result of read-only inspection (`readelf`, `xxd`, manual ARM decode — the local
`objdump` has no ARM backend) plus a precise, byte-level patch recipe to be executed
**later, on a throwaway copy**.

Prerequisites established earlier:
- [`android_target_sdk_24_test.md`](android_target_sdk_24_test.md) — A54 (Android 14)
  installs the target-24 APK, then crashes in `System.loadLibrary`.
- [`native_text_relocation_investigation.md`](native_text_relocation_investigation.md)
  — `DT_TEXTREL` present; exactly **one** text relocation: `R_ARM_RELATIVE` @ `0x5ddcc`.
- [`libZombieCafeAndroid_relocations.txt`](libZombieCafeAndroid_relocations.txt) — raw
  relocation dump.

Target library (source of truth): `src/lib/armeabi/libZombieCafeAndroid.so`
(1,947,420 bytes, sha256 `24c6509a978c7de96935b263363bda6ad6b5ea41b9ba819755ae8ad16d2cb45d`).

---

## TL;DR of the plan

The one text relocation exists only to fix up an inline pointer literal used by a
**non-essential CRT finalizer** (`__cxa_finalize(__dso_handle)` at library unload). The
safest fix is to **neuter that finalizer and neutralize its relocation**, then **strip
`DT_TEXTREL`** — all as in-place byte overwrites that keep the file the exact same size
(no section/segment moves). Four small edits, fully reversible because we only ever
touch a scratch copy.

---

## 1. What function/thunk is at `0x5ddc0`?

It is the **shared-object CRT finalizer emitted by the NDK `crtbegin_so` object** —
conventionally named `__on_dlclose` (the `crtbegin_so` analogue of GCC's
`__do_global_dtors_aux`). Decoded (ARM, not Thumb — the address is even and
`.fini_array` stores `0x5ddc0`):

```
0x5ddc0:  e28f0004   add r0, pc, #4      ; r0 = &literal (0x5ddcc)
0x5ddc4:  e5900000   ldr r0, [r0]        ; r0 = *(0x5ddcc)  = relocated __dso_handle
0x5ddc8:  eafffe8e   b   0x5d808         ; tail-call -> PLT[#29]
0x5ddcc:  .word 0x001daf70               ; inline literal = &__dso_handle (start of .bss)
```

Three independent pieces of evidence confirm the identity:

- **It is a registered finalizer.** `.fini_array` (file off `0x1d2364`) contains
  `ffffffff | 0x0005ddc0 | 0x00000000` — i.e. `.fini_array[1] = 0x5ddc0`. The dynamic
  linker calls it on unload via `DT_FINI_ARRAY`.
- **Its tail-call target is `__cxa_finalize`** (see §2–§3).
- **Its argument is `__dso_handle`.** The inline literal `0x1daf70` is the exact start
  of `.bss`, where `crtbegin_so` places `__dso_handle`.

`e_entry` also points at `0x5ddc0`, but that is meaningless for a `DYN` shared object
(the kernel/linker ignores `e_entry` for `.so`s) — it is `0x5ddc0` simply because
`crtbegin_so` is linked first, so its code lands at the start of `.text`.

---

## 2. What is the branch target at `0x5d808`?

`0x5d808` is inside `.plt` (`0x5d698 … 0x5ddc0`). The ARM PLT here has a 20-byte PLT0
header (`0x5d698 … 0x5d6ac`) followed by 12-byte stubs. Therefore:

```
(0x5d808 − 0x5d6ac) / 12 = 0x15c / 12 = 29   → PLT entry #29 (0-indexed), exact boundary
```

Decoding the stub at `0x5d808` (bytes `01 c6 8f e2 | 78 ca 8c e2 | 18 f3 bc e5`):

```
0x5d808:  e28fc601   add ip, pc, #0x00100000   ; ip = 0x5d810 + 0x100000 = 0x15d810
0x5d80c:  e28cca78   add ip, ip, #0x00078000   ; ip = 0x1d5810
0x5d810:  e5bcf318   ldr pc, [ip, #0x318]!     ; ip = 0x1d5b28 ; jump via *GOT[0x1d5b28]
```

So `0x5d808` is **PLT entry #29**, which jumps through `.got.plt` slot **`0x1d5b28`**.

(`PLTGOT`/`.got.plt` base = `0x1d5aa8`; `(0x1d5b28 − 0x1d5aa8)/4 = 32`; slots 0–2 are
reserved, so GOT slot 32 ⇒ PLT/JMPREL index 29 — consistent.)

---

## 3. Which import does `0x5d808` resolve to?

The GOT slot `0x1d5b28` is fixed up by the matching `.rel.plt` JUMP_SLOT relocation:

```
001d5b28  00058816 R_ARM_JUMP_SLOT   00000000   __cxa_finalize
```

**It resolves to `__cxa_finalize`** (dynsym #1416, `FUNC GLOBAL UND`, imported from
`libc`). The thunk is therefore exactly `__cxa_finalize(__dso_handle)`.

---

## 4. Optional CRT glue, or load-bearing?

**Optional CRT glue — safe to neuter in this app's usage.** Rationale:

- `__cxa_finalize(__dso_handle)` runs the C++ static/global destructors and
  `__cxa_atexit`-registered handlers **belonging to this DSO**, and only **at library
  unload (`dlclose`)** (it is in `.fini_array`, not `.init_array`).
- The engine library is loaded once via `System.loadLibrary` and stays mapped for the
  **entire process lifetime**. Android terminates the app by **killing the process**;
  the kernel reclaims all memory and fds. Per-DSO unload finalization is effectively
  never exercised, and is not how this title persists state.
- Save/persistence in this revival is handled by explicit **Go-side** save code
  (`save_game_state.go` et al.), not by C++ static destructors firing at unload.
- Even at genuine process exit, libc's own `exit()` path calls `__cxa_finalize(nullptr)`
  independently, so global cleanup is not solely dependent on this thunk.

**Residual caveat (the one thing to confirm before trusting the neuter):** if any C++
static object in the engine performs a *required* side effect in its destructor (flush a
file, release an OS/global resource that the process-kill path wouldn't) **and** the
library is actually `dlclose`d during normal play, neutering would skip it. For a game
that never unloads its own engine, this is very low risk — but it is the assumption the
"neuter" strategy rests on, so it is called out explicitly here and again in §10.

---

## 5. Which patch strategy is safer?

Two viable strategies (matching §7 Option 2a/2b of the investigation):

| | **A. Neuter the finalizer + nullify its reloc** | **B. GOT-indirect the literal** |
|---|---|---|
| Idea | Make the finalizer return immediately; turn its text relocation into a no-op | Keep the finalizer working, but load `__dso_handle` from a relocated GOT slot instead of an inline text literal |
| Bytes changed | ~**4 small edits**, file size unchanged | More: re-encode the load + add/relocate a GOT slot |
| New relocations | none (one reloc retyped to `R_ARM_NONE`) | must add/repurpose a writable-segment reloc |
| Encoding risk | minimal (single `bx lr`) | high — `.got` is ~`0x178000` bytes away, unreachable by a short PC-relative form; needs a literal-pool pointer + extra indirection |
| Behaviour change | per-DSO unload destructors skipped (benign here) | none (fully preserved) |
| Table/layout disturbance | none (in-place) | likely needs a spare GOT slot / table edit |

**Recommendation: Strategy A.** It is smaller, needs no new relocation, no GOT
juggling, and no risky long-distance re-encoding; its only cost (skipping unload-time
static destructors) is benign for a load-once, run-until-killed game (§4). Strategy B's
sole advantage — preserving finalization we don't rely on — does not justify its extra
fragility. **B is documented as the fallback** if §4's caveat is ever shown to matter.

---

## 6. Exact bytes to change (Strategy A, recommended "robust" variant)

All edits are **in-place overwrites**; the file length stays **1,947,420 bytes**. Note
for ARM `.so`s, file offset == vaddr in the R-E segment, and file offset == vaddr −
`0x1000` in the RW segment.

> **Verify-before-write:** every edit lists the expected *old* bytes. A patch script
> must assert the old bytes match before overwriting (guards against drift).

### Edit 1 — Neuter the finalizer (code), so the dead literal is never dereferenced
| Field | Value |
|---|---|
| File offset | `0x0005ddc0` (vaddr `0x5ddc0`) |
| Old (4 bytes) | `04 00 8f e2`  (`add r0, pc, #4`) |
| New (4 bytes) | `1e ff 2f e1`  (`bx lr` — ARM `e12fff1e`) |

The finalizer now returns immediately. The following `ldr/b` (`0x5ddc4`, `0x5ddc8`) and
the literal (`0x5ddcc`) become dead. *(Optional tidiness: NOP-fill `0x5ddc4`/`0x5ddc8`
with `00 f0 20 e3` each; not required since `bx lr` returns first.)*

### Edit 2a — Move the text reloc out of the relative block (swap entry[0] ⇄ entry[3977])
The text relocation is `.rel.dyn[0]`. Swap it with the **last** relative entry
(`.rel.dyn[3977]`) so the leading block stays purely relative.

| Field | Value |
|---|---|
| File offset | `0x00055490` (`.rel.dyn[0]`) |
| Old (8 bytes) | `cc dd 05 00 17 00 00 00`  (off `0x5ddcc`, `R_ARM_RELATIVE`) |
| New (8 bytes) | `6c af 1d 00 17 00 00 00`  (off `0x1daf6c`, `R_ARM_RELATIVE` — copied from entry[3977]) |

`0x1daf6c` is the last word of `.data` (writable) — applying a relative reloc there is
correct, and relative relocs are order-independent, so relocating it from index 0 is
fine.

### Edit 2b — Retype the moved text reloc to `R_ARM_NONE` (no-op) at entry[3977]
| Field | Value |
|---|---|
| File offset | `0x0005d0d8` (`.rel.dyn[3977]`) |
| Old (8 bytes) | `6c af 1d 00 17 00 00 00`  (off `0x1daf6c`, `R_ARM_RELATIVE`) |
| New (8 bytes) | `cc dd 05 00 00 00 00 00`  (off `0x5ddcc`, **`R_ARM_NONE`**, sym 0) |

Now index 3977 sits **after** the relative block, in the type-checked tail of `.rel.dyn`,
where every loader sees `R_ARM_NONE` and skips it. **No relocation targets `0x5ddcc`
any more.** `DT_RELSZ` is unchanged (we retyped, not removed — see §7).

### Edit 3 — Strip `DT_TEXTREL` by shifting the `.dynamic` tail up one entry
The tail is `… RELSZ, RELENT, [TEXTREL], [RELCOUNT], [NULL]`. Overwrite `TEXTREL` with
`RELCOUNT` (decremented), then `RELCOUNT`'s old slot with `NULL`:

| File offset | Old (8 bytes) | New (8 bytes) | Meaning |
|---|---|---|---|
| `0x001d4a70` | `16 00 00 00  00 00 00 00`  (`DT_TEXTREL` 0) | `fa ff ff 6f  89 0f 00 00`  (`DT_RELCOUNT` = **3977**) | TEXTREL removed; RELCOUNT moves up & decremented |
| `0x001d4a78` | `fa ff ff 6f  8a 0f 00 00`  (`DT_RELCOUNT` 3978) | `00 00 00 00  00 00 00 00`  (`DT_NULL`) | new array terminator |
| `0x001d4a80` | `00 00 00 00  00 00 00 00`  (`DT_NULL`) | `00 00 00 00  00 00 00 00`  (unchanged) | trailing NULL (idempotent) |

The dynamic array stays the same physical size and remains `DT_NULL`-terminated, now
with **28 meaningful entries** (TEXTREL gone) and `RELCOUNT = 3977`.

### Minimal variant (bionic-only, smaller)
If the patched `.so` will *only* ever be loaded by Android's bionic linker (which
type-checks each classic `DT_REL` entry and does **not** use `DT_RELCOUNT` as a
type-skipping fast path), Edits 2a/2b collapse into a single in-place retype:

- `0x00055490`: `cc dd 05 00 17 00 00 00` → `cc dd 05 00 00 00 00 00` (entry[0] →
  `R_ARM_NONE`), plus Edit 3's `RELCOUNT` decrement.

This is fewer bytes but **fragile** under any loader that honours `DT_RELCOUNT`'s
"first N are all relative" contract (e.g. glibc / `qemu-user` testing), because index 0
would still be inside the relative fast-path range. **Use the robust variant by
default.**

---

## 7. Exact ELF metadata changes

| Item | Before | After | How |
|---|---|---|---|
| Reloc entry `@0x5ddcc` (`.rel.dyn[0]`) | `R_ARM_RELATIVE`, off `0x5ddcc` | relocated away; the surviving copy is `R_ARM_NONE` at `.rel.dyn[3977]` | Edits 2a + 2b |
| `DT_TEXTREL` (tag `0x16`) | present, value `0x0` | **removed** | Edit 3 (tail shift) |
| `DT_RELSZ` (tag `0x12`) | `32080` (`0x7d50`, 4010 entries) | **unchanged** | we retype, not delete — physical table size must stay so nothing after `.rel.dyn` shifts |
| `DT_RELCOUNT` (tag `0x6ffffffa`) | `3978` | `3977` | Edit 3 (decrement, moved up one slot) |
| `DT_NULL` terminator | last entry | preserved (array still NULL-terminated) | Edit 3 |
| All other dyn tags (`REL`, `RELENT`, `JMPREL`, `PLTGOT`, `SYM*`, `STR*`, `INIT/FINI_ARRAY*`, `NEEDED`, `SONAME`, `SYMBOLIC`) | — | **unchanged** | — |
| `.rel.plt` / JUMP_SLOTs / GOT / PLT | — | **unchanged** | `__cxa_finalize`'s PLT entry is left intact; we simply stop calling it |
| Program headers / section headers / segment perms / file size | — | **unchanged** | all edits are equal-length in-place overwrites |

Key invariant: **`DT_RELSZ` stays `0x7d50`.** Physically removing an entry would force
every byte after `.rel.dyn` to shift, cascading into `.rel.plt`, `.plt`, `.text`,
program-header offsets, etc. Retyping the spare entry to `R_ARM_NONE` is the canonical
way to "delete" a relocation without moving anything.

---

## 8. Tools/scripts to patch a throwaway copy

**Always operate on a scratch copy — never `src/`:**

```bash
mkdir -p /tmp/textrel
cp src/lib/armeabi/libZombieCafeAndroid.so /tmp/textrel/patched.so
sha256sum /tmp/textrel/patched.so   # must equal 24c6509a…
```

Recommended: a small **Python `r+b`** script that asserts old bytes, then writes — it is
self-documenting and refuses to run on a drifted file:

```python
# patch_textrel.py  (run against the SCRATCH copy only)
EDITS = [  # (file_offset, expected_old_bytes, new_bytes)
  (0x0005ddc0, bytes.fromhex("04008fe2"),            bytes.fromhex("1eff2fe1")),  # bx lr
  (0x00055490, bytes.fromhex("ccdd05001700 0000".replace(" ","")),
                                                     bytes.fromhex("6caf1d0017000000")),  # swap in entry[3977]
  (0x0005d0d8, bytes.fromhex("6caf1d0017000000"),    bytes.fromhex("ccdd050000000000")),  # -> R_ARM_NONE
  (0x001d4a70, bytes.fromhex("1600000000000000"),    bytes.fromhex("faffff6f890f0000")),  # TEXTREL -> RELCOUNT(3977)
  (0x001d4a78, bytes.fromhex("faffff6f8a0f0000"),    bytes.fromhex("0000000000000000")),  # RELCOUNT -> NULL
]
import sys
p = sys.argv[1]
with open(p, "r+b") as f:
    for off, old, new in EDITS:
        assert len(old) == len(new), (hex(off), "length mismatch")
        f.seek(off); cur = f.read(len(old))
        assert cur == old, f"drift @ {off:#x}: got {cur.hex()} expected {old.hex()}"
        f.seek(off); f.write(new)
print("patched OK")
```

Alternatives:
- **`dd`** per edit (`dd of=patched.so bs=1 seek=$((0x5ddc0)) conv=notrunc` fed by a
  `printf '\x1e\xff\x2f\xe1'`). Works but no old-byte assertion — easy to get wrong.
- **`xxd -r`** patch lines, or a hex editor (`hexedit`, `ImHex`) for manual edits.
- **`lief`** (Python ELF lib) can edit dynamic entries/relocations at a higher level,
  but it *rewrites the whole file/layout*, which is riskier for a stripped engine `.so`
  than surgical equal-length overwrites — only consider it if a full rebuild of the
  relocation tables is ever wanted.
- **`patchelf`** has **no** option to drop `DT_TEXTREL` or retype a single relocation,
  so it cannot do this job alone. **`scanelf -qT`** (pax-utils) is useful for
  *checking* TEXTREL but not patching; it was not available in this environment.

---

## 9. Verification before rebuilding the APK

Run entirely on the scratch copy; do **not** touch `src/` or build an APK yet.

**A. Static ELF checks (the gate):**
```bash
readelf -d  /tmp/textrel/patched.so | grep -i textrel        # EXPECT: no output (DT_TEXTREL gone)
readelf -d  /tmp/textrel/patched.so | grep -iE 'RELSZ|RELCOUNT|NULL'
                                                             # EXPECT: RELSZ 32080, RELCOUNT 3977, NULL terminator
readelf -r  /tmp/textrel/patched.so | grep -i ddcc           # EXPECT: the 0x5ddcc entry is R_ARM_NONE (or absent)
readelf -h  /tmp/textrel/patched.so                          # EXPECT: identical header
readelf -l  /tmp/textrel/patched.so                          # EXPECT: identical segments/perms
```

**B. "Zero text relocations" check** (re-run the §6 classifier from the investigation):
```bash
readelf -r /tmp/textrel/patched.so > /tmp/textrel/relocs.txt
awk '/^[0-9a-fA-F]{8} /{o=strtonum("0x"$1); if(o<0x1d227c)n++} END{print "text-segment relocs:", n+0}' \
    /tmp/textrel/relocs.txt        # EXPECT: 0
```

**C. Byte-diff sanity** (nothing moved, only intended bytes changed):
```bash
cmp -l src/lib/armeabi/libZombieCafeAndroid.so /tmp/textrel/patched.so
# EXPECT: differing bytes ONLY within 0x5ddc0–0x5ddc3, 0x55490–0x55497,
#         0x5d0d8–0x5d0df, 0x1d4a70–0x1d4a7f ; file sizes equal
ls -l /tmp/textrel/patched.so      # EXPECT: 1947420 bytes (unchanged)
```

**D. Functional load test (decisive, but after this plan):** because the lib `NEEDED`s
`libGLESv1_CM/libGLESv2/liblog/...` (Android-only), it can't be `dlopen`'d on desktop.
The cheapest real check is on Android:
- push the scratch `.so` to a writable path on the A54 (or an emulator) and `dlopen` it
  from a tiny harness, watching `logcat` for the **absence** of `has text relocations`;
  **or**
- proceed to a throwaway test APK (next task, out of scope here) and launch on the A54,
  confirming it clears `System.loadLibrary` and reaches the game's main loop.

Static checks A–C are the gate; D is the proof.

---

## 10. Possible failure modes

1. **The finalizer was load-bearing.** A C++ static destructor with a required side
   effect is skipped because we neutered `__on_dlclose` (§4 caveat). *Likelihood: low*
   (load-once engine, saves are Go-side). *Mitigation:* if observed, switch to Strategy
   B (preserve finalization via GOT indirection).
2. **`DT_TEXTREL` removed while a text reloc still applies.** If any relocation still
   targets the now-read-only text segment, the linker maps text read-only and the write
   faults → **SIGSEGV at load (worse than today's clean error)**. *Mitigation:* §9 step
   B must report **0** text-segment relocs before trusting the patch.
3. **`DT_RELCOUNT` fast-path mismatch.** Using the *minimal* variant under a
   `RELCOUNT`-honouring loader (glibc/qemu-user) would re-apply index 0 as relative and
   corrupt a code byte. *Mitigation:* use the **robust swap** variant (default).
4. **`.dynamic` tail mis-edited.** Dropping the `DT_NULL` terminator or clobbering
   another tag breaks dynamic parsing → load failure/UB. *Mitigation:* §9 step A must
   show a valid `DT_NULL`-terminated array with all expected tags.
5. **Wrong endianness / drift in hand-edits.** *Mitigation:* the §8 script asserts every
   *old* byte before writing; `cmp -l` confirms only the four regions changed.
6. **Hidden references to the thunk.** Something other than `.fini_array[1]`/`e_entry`
   calls `0x5ddc0`. *Likelihood: negligible* (it's CRT glue). *Mitigation:* a scan for
   branches into `0x5ddc0` can be added once an ARM disassembler is available.
7. **App self-integrity check.** If the game hashes its own `.so`, the byte change would
   trip it. *Likelihood: low for this title.* *Mitigation:* on-device smoke test.
8. **Unrelated modern-loader gates.** 16 KB-page devices (Android 15+) and any missing
   GLESv1 path are **separate** issues this patch does not address; don't attribute a
   later failure to the TEXTREL patch without re-reading logcat. *Mitigation:* the §9
   on-device test reads `logcat` for the specific next error.

---

## 11. Rollback plan

- **`src/` is never touched.** All work is on a scratch copy
  (`/tmp/textrel/patched.so`). Rollback = delete the scratch file; `src/` stays at
  sha256 `24c6509a…`, and `git status` shows it unmodified.
- **No commits, no APK rebuild** in this task, so there is nothing to revert in VCS. If a
  later experiment ever copies a patched lib into `build/` or `src/`, restore with
  `git checkout -- src/lib/armeabi/libZombieCafeAndroid.so` (or recopy from the recorded
  sha256 original).
- **Reproducible & reversible patch.** The four edits are equal-length overwrites; keep
  the `cmp -l` output (or a `bsdiff`) so the patch can be re-applied or exactly inverted
  byte-for-byte.
- **Device-level fallback.** If a patched test APK misbehaves on the A54, uninstall it
  and reinstall the known-good unpatched target-24 APK, or fall back to the
  Android ≤ 5.1 / BlueStacks path (which needs no native change at all).

---

## Appendix — read-only commands used for this plan

```bash
# region & PLT/thunk decode (objdump here has no ARM backend, so bytes were decoded by hand)
objdump -i                                                   # confirmed: x86 only, no 'arm'
xxd -s 0x5d698 -l 20  src/lib/armeabi/libZombieCafeAndroid.so   # PLT0 header
xxd -s 0x5d800 -l 24  src/lib/armeabi/libZombieCafeAndroid.so   # PLT entry #29 @0x5d808
xxd -s 0x5ddc0 -l 16  src/lib/armeabi/libZombieCafeAndroid.so   # the finalizer thunk
xxd -s 0x1d2364 -l 12 src/lib/armeabi/libZombieCafeAndroid.so   # .fini_array  (-> 0x5ddc0)
xxd -s 0x55490 -l 8   src/lib/armeabi/libZombieCafeAndroid.so   # .rel.dyn[0]   (text reloc)
xxd -s 0x5d0d0 -l 32  src/lib/armeabi/libZombieCafeAndroid.so   # .rel.dyn[3976..3979] boundary
xxd -s 0x1d49a0 -l 232 src/lib/armeabi/libZombieCafeAndroid.so  # full .dynamic
readelf -d  src/lib/armeabi/libZombieCafeAndroid.so
readelf -r  src/lib/armeabi/libZombieCafeAndroid.so
readelf --dyn-syms src/lib/armeabi/libZombieCafeAndroid.so
grep -n 001d5b28 docs/compat/libZombieCafeAndroid_relocations.txt   # -> __cxa_finalize
```
