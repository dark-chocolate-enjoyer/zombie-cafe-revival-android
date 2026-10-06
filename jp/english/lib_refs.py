#!/usr/bin/env python3
"""Find every Japanese string in the JP native lib and every code/data
reference into it, so strings can be overwritten in place safely.

Writes work/lib_strings.json: [{off, size, jp, refs_start, refs_inside}]
  refs_inside = references that land strictly inside a string (a shared tail);
  those bytes must keep their original content.
"""
import json, re, struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
lib = open(os.path.join(HERE, 'work', 'base_lib.so'), 'rb').read()

TEXT = (0xa5358, 0xa5358 + 0x23a3d4)
RODATA = (0x31eab8, 0x31eab8 + 0x1a92f4)
REL_DYN = (0x8e2ec, 0x15f78)
# RW segment: vaddr 0x4c93a0 <- file 0x4c83a0
def v2f(v):
    return v - 0x1000 if v >= 0x4c93a0 else v

JP = re.compile(r'[぀-ヿ一-鿿！-～　-〿]')

# --- 1. strings in .rodata ---------------------------------------------
strings = []
for m in re.finditer(rb'[^\x00]+\x00', lib[RODATA[0]:RODATA[1]]):
    s = m.group()[:-1]
    try:
        t = s.decode('utf-8')
    except UnicodeDecodeError:
        continue
    if JP.search(t):
        strings.append({'off': RODATA[0] + m.start(), 'size': len(s), 'jp': t})

# --- 2. references --------------------------------------------------------
targets = {}

lit_uses = {}

def add(t, src):
    targets.setdefault(t, []).append(src)
    if src[0] == 'pcrel':
        lit_uses.setdefault(src[1], set()).add(src[2])

# data pointers via R_ARM_RELATIVE
for i in range(REL_DYN[1] // 8):
    r_off, r_info = struct.unpack_from('<II', lib, REL_DYN[0] + i * 8)
    if r_info & 0xff == 23:
        add(struct.unpack_from('<I', lib, v2f(r_off))[0], ('rel', v2f(r_off), 0))

# Thumb-1 PIC: ldr rd,[pc,#imm] ... add rd,pc
for a in range(TEXT[0], TEXT[1] - 1, 2):
    h = struct.unpack_from('<H', lib, a)[0]
    if h & 0xfff8 == 0x4478:
        rd = h & 7
        for back in range(2, 40, 2):
            b = a - back
            hb = struct.unpack_from('<H', lib, b)[0]
            if hb & 0xff00 == 0x4800 | (rd << 8):
                lit = ((b + 4) & ~3) + (hb & 0xff) * 4
                if TEXT[0] <= lit < TEXT[1] + 0x2000:
                    w = struct.unpack_from('<I', lib, lit)[0]
                    add((w + a + 4) & 0xffffffff, ('pcrel', lit, a + 4))
                break

# ARM: ldr rd,[pc,#imm12] ... add rd,pc,rd
for a in range(TEXT[0] & ~3, TEXT[1] - 3, 4):
    w = struct.unpack_from('<I', lib, a)[0]
    if w & 0x0fff0ff0 == 0x008f0000 and (w >> 28) == 0xe:
        rd, rm = (w >> 12) & 15, w & 15
        for back in range(4, 80, 4):
            wb = struct.unpack_from('<I', lib, a - back)[0]
            if wb & 0xffff0000 == 0xe59f0000 and (wb >> 12) & 15 == rm:
                lit = a - back + 8 + (wb & 0xfff)
                v = struct.unpack_from('<I', lib, lit)[0]
                add((v + a + 8) & 0xffffffff, ('pcrel', lit, a + 8))
                break

starts = inside = 0
for s in strings:
    s['refs_start'] = targets.get(s['off'], [])
    s['refs_inside'] = sorted({t - s['off'] for t in targets if s['off'] < t < s['off'] + s['size']})
    starts += bool(s['refs_start'])
    inside += bool(s['refs_inside'])
json.dump(strings, open(os.path.join(HERE, 'work', 'lib_strings.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({str(k): sorted(v) for k, v in lit_uses.items()}, open(os.path.join(HERE, 'work', 'lib_lit_uses.json'), 'w'))
print(f'{len(strings)} JP strings; {starts} have a start reference; {inside} have references inside them')
for s in strings:
    if s['refs_inside']:
        print(hex(s['off']), s['jp'], s['refs_inside'])
unref = [s for s in strings if not s['refs_start']]
print('unreferenced:', len(unref))
for s in unref[:40]:
    print('  ', hex(s['off']), s['jp'][:40])
