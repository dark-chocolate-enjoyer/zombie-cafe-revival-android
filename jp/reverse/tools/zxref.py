#!/usr/bin/env python3
"""Find Thumb BL/BLX callers of a function. usage: zxref.py LIB 'Class::method' (or 0xADDR)"""
import bisect, re, struct, subprocess, sys
lib, tgt = sys.argv[1], sys.argv[2]
data = open(lib, 'rb').read()
syms = {}
for line in subprocess.run(['nm', '-DC', '-S', '--defined-only', lib], capture_output=True, text=True).stdout.splitlines():
    m = re.match(r'([0-9a-f]+) ([0-9a-f]+) (\w) (.*)', line)
    if m:
        syms.setdefault(int(m.group(1), 16) & ~1, m.group(4))
addrs = sorted(syms)
if tgt.startswith('0x'):
    targets = {int(tgt, 16) & ~1}
else:
    targets = {a for a, n in syms.items() if n == tgt or n.startswith(tgt + '(')}
print('targets:', [hex(t) for t in targets])
text_start, text_end = 0xa5358, 0xa5358 + 0x23a3d4  # JP base_lib.so .text (readelf -S); change for other libs
hw = struct.unpack_from(f'<{(text_end - text_start) // 2}H', data, text_start)
for i in range(len(hw) - 1):
    h1, h2 = hw[i], hw[i + 1]
    if (h1 & 0xF800) != 0xF000 or (h2 & 0xC000) != 0xC000:
        continue
    s = (h1 >> 10) & 1
    j1, j2 = (h2 >> 13) & 1, (h2 >> 11) & 1
    i1, i2 = 1 - (j1 ^ s), 1 - (j2 ^ s)
    imm = (s << 24) | (i1 << 23) | (i2 << 22) | ((h1 & 0x3FF) << 12) | ((h2 & 0x7FF) << 1)
    if s:
        imm -= 1 << 25
    pc = text_start + 2 * i
    t = pc + 4 + imm
    if (h2 & 0x1000) == 0:  # BLX -> ARM target, align
        t &= ~3
    if t in targets:
        k = bisect.bisect_right(addrs, pc) - 1
        print(f'{pc:08x}  in {syms[addrs[k]]}+{pc - addrs[k]:#x}')
