# The unterminated-string bug (`StringBuffer::toString`), found 2026-10-09

A bug in Capcom's own C++ string code in `libZombieCafeAndroid.so` (JP 1.7.0; the EN lib shares the
engine, unchecked). Found with GWP-ASan on the Galaxy A54. Fixed in the debug builds
from 5g onwards (`lib_fixes.py`), not yet in the release build.

**Status:** real bug, fixed in debug builds. **Not the cause of the cafe → map crash**: build 5g has the fix
and still crashed on the first cafe exit (run 6, see "Test result").

## 1. How the game stores text

`String` (12 bytes on the stack or inside objects):

| Offset | Type | Meaning |
| --- | --- | --- |
| `+0` | `StringRef*` | shared buffer record: `+0` = `char*` buffer, `+4` = int16 reference count |
| `+4` | int16 | start offset into the buffer (substrings share the parent's buffer) |
| `+6` | int16 | length in bytes |

Most constructors allocate `length + 1` bytes and keep a terminating `0` after the text, e.g.
`String::String(char const*)` (`0x290d04`): `malloc(strlen + 1)`, `memset`, `memcpy(strlen + 1)`.
Some functions rely on that terminator.

## 2. The bug

`StringBuffer` collects pieces in a linked list (`StringBuffer::append`) and keeps the total length at
`+0x18`. `StringBuffer::toString()` (`0x2918c2`) joins them:

```
002918dc  ldr   r0, [r5, #0x18]     ; total length
002918de  blx   malloc              ; malloc(total)          ← no + 1
002918e2  str   r0, [r4]            ; ref->buffer = it
002918e4  ldr   r3, [r5, #0x18]
002918e8  strh  r3, [r6, #6]        ; length = total
...       loop: memcpy(buffer + pos, piece, piece.length)   ; never writes a 0 after the text
```

So every string it returns has **no terminator and no room for one**.

`String::operator+=(String other)` (`0x291590`) assumes the terminator exists:

```
002915a8  r4 = this.len + other.len
002915aa  adds r4, #1
002915ae  blx  malloc               ; new buffer: this.len + other.len + 1 (correct)
002915b8  blx  memset               ; zeroed
002915cc  blx  memcpy               ; this.len bytes of this
002915e2  adds r2, #1
002915e4  blx  memcpy               ; other.len + 1 bytes of other   ← reads 1 byte past an unterminated other
```

It reads one byte past the end of a `toString()` result, and that stray byte becomes the new
string's last byte, so the result is unterminated too. The damage spreads through concatenation.

**Reach:** `StringBuffer::toString()` has **153 call sites** (cafe: `ZombieCafe::endLoadOrders`,
`GameStateCafe::tickEditModes`; raids, event menus, dialogs, character screens…).
`StringUtil::replace(String, String, String)` (`0x292450`) builds its result with it (18 callers),
e.g. every objective/quest text with a placeholder.

**Why it worked in 2016:** Android's old allocators rounded small requests up and often handed out
fresh (zeroed) memory, so the byte after the text was usually `0` by luck. Android 11+'s Scudo returns
recycled blocks, so that byte is often leftover data.

## 3. Evidence (GWP-ASan, build 5f, run 5, launch 3, 2026-10-09 17:38:46)

```
signal 11 (SIGSEGV), code 2 (SEGV_ACCERR), fault addr 0xe14f2000
Cause: [GWP-ASan]: Buffer Overflow, 0 bytes right of a 16-byte allocation at 0xe14f1ff0
  #00 libc.so (__memcpy_base_a55+484)
  #01 libZombieCafeAndroid.so (String::operator+=(String)+84)          ; the second memcpy, 0x2915e4
  #02 libZombieCafeAndroid.so (String::operator+(String)+26)
  #03 libZombieCafeAndroid.so (ObjectiveDialog::ObjectiveDialog(ConfirmDialog*, ObjectiveCompleteDialog*, BuyToxinDialog*)+4290)
  #04 libZombieCafeAndroid.so (GameStateCafe::init()+4394)
r0 c527edf0 (destination)   r1 e14f2000 (source, = the guard page)
```

`r1` (memcpy's source) sat on the guard page, so it was a **read** past a 16-byte source string. In
`ObjectiveDialog` (`0x1ed65a`–`0x1ed6a6`, recipe objectives, type 4) the text is
`recipeName + "<literal>" + description`, and `description` came from `StringUtil::replace` →
`StringBuffer::toString()`. The allocation stack was cut to 1 frame (GWP-ASan's frame-pointer unwinder
can't walk this lib); the registers settled it.

A read alone can't damage memory. A write would need code that sizes a buffer from `length` but copies
"until the 0 byte" (`strlen`, `strcpy`, `%s`) from such a string. None was found or caught.

## 4. The fix (`lib_fixes.py`, debug builds 5g+)

No spare bytes in `toString()`, so a helper goes into `String::Test() const` (`0x290ec2`, 66 bytes):
no callers anywhere, and its address appears only in `.dynsym` (checked 2026-10-09).

```
helper @ 0x290ec2  (20 bytes: 10b5041c013013f65aed002801d00021015510bd)
  push  {r4, lr}
  adds  r4, r0, #0        ; len
  adds  r0, #1
  blx   malloc            ; malloc(len + 1)
  cmp   r0, #0
  beq   done
  movs  r1, #0
  strb  r1, [r0, r4]      ; buffer[len] = 0
done:
  pop   {r4, pc}

call site @ 0x2918de: blx malloc (13f650e8) -> bl 0x290ec2 (fff7f0fa)
```

Register-safe: the helper saves `r4` and returns `r0` like `malloc`; `r1`–`r3` were already clobbered
by `malloc`. Stack stays 8-byte aligned. Verified: exactly 24 bytes of the lib differ from v5, all in
the three fix ranges (raid fix + these two), and the patched code disassembles as above.

## 5. Test result (build 5g, run 6, 2026-10-09)

Launch 1: 11 cafe → map trips in 68 s, no crash (closed by the owner). Launch 2: owner pressed Map right after the
cafe loaded → **Scudo "corrupted chunk header" at 17:48:23.494**, in `CafeWall::~CafeWall` ←
`Cafe::~Cafe` ← `GameStateCafe::uninit`, ~1.1 s after the cafe loaded. So the map crash survives this
fix. Next lead (owner's timing observation): see README finding 11, the network-callback race.
