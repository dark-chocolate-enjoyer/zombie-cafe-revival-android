#!/usr/bin/env python3
"""Find functions referencing a data symbol via GOT slot or GOT-relative offset.
usage: zlit.py LIB 'Sym::name' [...]"""
import bisect, re, struct, subprocess, sys
lib = sys.argv[1]
data = open(lib, 'rb').read()
GOTBASE = 0x4d0c94  # JP base_lib.so: value of "add rX, pc" GOT base; change for other libs
syms, byname = {}, {}
for line in subprocess.run(['nm', '-DC', '-S', '--defined-only', lib], capture_output=True, text=True).stdout.splitlines():
    m = re.match(r'([0-9a-f]+) ([0-9a-f]+) (\w) (.*)', line)
    if m:
        a = int(m.group(1), 16)
        byname[m.group(4)] = a
        if m.group(3) in 'TtWw':
            syms.setdefault(a & ~1, m.group(4))
addrs = sorted(syms)
# GOT slots: RELATIVE value or GLOB_DAT symbol
def off(va):
    return va - 0x1000 if va >= 0x4c93a0 else va
slots = {}
for line in subprocess.run(['readelf', '-r', '-W', lib], capture_output=True, text=True).stdout.splitlines():
    m = re.match(r'([0-9a-f]{8})\s+[0-9a-f]+\s+(R_ARM_\w+)\s*(?:([0-9a-f]+)\s+)?', line)
    if m and m.group(2) in ('R_ARM_RELATIVE', 'R_ARM_GLOB_DAT', 'R_ARM_ABS32'):
        slot = int(m.group(1), 16)
        val = struct.unpack_from('<I', data, off(slot))[0] if m.group(2) == 'R_ARM_RELATIVE' else int(m.group(3), 16)
        slots.setdefault(val, []).append(slot)
text_start, text_end = 0xa5358, 0xa5358 + 0x23a3d4  # JP base_lib.so .text (readelf -S); change for other libs
words = {}
for p in range(text_start & ~3, text_end, 4):
    words.setdefault(struct.unpack_from('<I', data, p)[0], []).append(p)
for name in sys.argv[2:]:
    a = byname[name]
    keys = [((s - GOTBASE) & 0xffffffff, f'GOT slot {s:#x}') for s in slots.get(a, [])] + [((a - GOTBASE) & 0xffffffff, 'GOTOFF')]
    print(f'== {name} @ {a:#x}')
    seen = set()
    for k, how in keys:
        for p in words.get(k, []):
            i = bisect.bisect_right(addrs, p) - 1
            fn = syms[addrs[i]]
            if (fn, how) not in seen:
                seen.add((fn, how))
                print(f'   {fn}  (pool {p:#x}, {how})')
