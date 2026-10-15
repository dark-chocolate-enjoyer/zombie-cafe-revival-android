#!/usr/bin/env python3
"""Annotated Thumb disassembly of one function in an Android ARM .so.
usage: dis.py LIB 'Class::method' [max_insns]   or   dis.py LIB 0xADDR [max_insns]
Annotates: bl/blx targets (symbols / PLT imports), PC-relative literals, GOT slots -> symbol,
float literals, rodata strings."""
import bisect
import re
import struct
import subprocess
import sys

import capstone

lib = sys.argv[1]
data = open(lib, 'rb').read()


def run(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


# segments vaddr->offset
segs = []
for line in run('readelf', '-l', '-W', lib).splitlines():
    p = line.split()
    if p and p[0] == 'LOAD':
        segs.append((int(p[2], 16), int(p[1], 16), int(p[4], 16)))


def off(va):
    for v, o, sz in segs:
        if v <= va < v + sz:
            return va - v + o
    return None


def u32(va):
    o = off(va)
    return struct.unpack_from('<I', data, o)[0] if o is not None else None


secs = {}
for line in run('readelf', '-S', '-W', lib).splitlines():
    m = re.match(r'\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)', line)
    if m:
        secs[m.group(1)] = (int(m.group(2), 16), int(m.group(4), 16))


def in_sec(va, name):
    s = secs.get(name)
    return s and s[0] <= va < s[0] + s[1]


# symbols
syms, sizes = {}, {}
for line in run('nm', '-DC', '-S', '--defined-only', lib).splitlines():
    m = re.match(r'([0-9a-f]+) ([0-9a-f]+) (\w) (.*)', line)
    if m:
        a = int(m.group(1), 16)
        syms.setdefault(a & ~1, m.group(4))
        sizes[m.group(4)] = (a, int(m.group(2), 16))
addrs = sorted(syms)

# relocations: GOT slot -> symbol, PLT slot order
got, plt_names = {}, []
for line in run('readelf', '-r', '-W', '-C', lib).splitlines():
    m = re.match(r'([0-9a-f]{8})\s+[0-9a-f]+\s+(R_ARM_\w+)\s*(?:([0-9a-f]+)\s+(.*))?', line)
    if not m:
        continue
    slot, typ, name = int(m.group(1), 16), m.group(2), (m.group(4) or '').strip()
    if typ == 'R_ARM_JUMP_SLOT':
        plt_names.append(name.split(' + ')[0])
    elif typ in ('R_ARM_GLOB_DAT', 'R_ARM_ABS32') and name:
        got[slot] = name.split(' + ')[0]
    elif typ == 'R_ARM_RELATIVE':
        v = u32(slot)
        if v is not None:
            i = bisect.bisect_right(addrs, v & ~1) - 1
            got[slot] = ('&' + syms[addrs[i]] + (f'+{(v & ~1) - addrs[i]:#x}' if (v & ~1) != addrs[i] else '')) \
                if i >= 0 and (v & ~1) - addrs[i] < 0x10000 else f'&{v:#x}'
plt_start = secs['.plt'][0]


def name_of(t):
    if in_sec(t, '.plt'):
        i = (t - plt_start - 20) // 12
        return 'PLT:' + (plt_names[i] if 0 <= i < len(plt_names) else '?')
    i = bisect.bisect_right(addrs, t) - 1
    if i < 0:
        return hex(t)
    return syms[addrs[i]] + (f'+{t - addrs[i]:#x}' if t != addrs[i] else '')


def describe(va):
    if va in got:
        return f'GOT[{got[va]}]'
    if in_sec(va, '.rodata'):
        o = off(va)
        s = data[o:o + 60].split(b'\0')[0]
        if len(s) >= 3 and all(32 <= c < 127 for c in s):
            return f'"{s.decode()}"'
        f = struct.unpack_from('<f', data, o)[0]
        return f'rodata {va:#x} (float {f:g} / int {u32(va)})'
    if va & ~1 in syms:
        return '&' + syms[va & ~1]
    return f'{va:#x}'


target = sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 600
if target.startswith('0x'):
    start, size = int(target, 16) & ~1, 0x400
else:
    cands = [k for k in sizes if k == target or k.startswith(target + '(')]
    if not cands:
        sys.exit('no symbol ' + target)
    start, size = sizes[cands[0]]
    start &= ~1
    print(f'; {cands[0]} @ {start:#x} size {size:#x}')

md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
md.detail = True
md.skipdata = True
regs = {}
gotbase = None
o = off(start)
for n, ins in enumerate(md.disasm(data[o:o + size], start)):
    if n >= limit:
        break
    note = ''
    ops = ins.op_str
    try:
        if ins.mnemonic in ('bl', 'blx', 'b.w') and ops.startswith('#'):
            note = name_of(int(ops[1:], 16))
        elif ins.mnemonic.startswith('ldr') and '[pc' in ops:
            m = re.search(r'#(-?0x[0-9a-f]+|-?\d+)', ops)
            imm = int(m.group(1), 0) if m else 0
            lit = ((ins.address + 4) & ~3) + imm
            v = u32(lit)
            rd = ops.split(',')[0]
            regs[rd] = v
            note = f'lit {v:#x}'
        elif ins.mnemonic.startswith('vldr') and '[pc' in ops:
            m = re.search(r'#(-?0x[0-9a-f]+|-?\d+)', ops)
            imm = int(m.group(1), 0) if m else 0
            lit = ((ins.address + 4) & ~3) + imm
            o2 = off(lit)
            note = f'= {struct.unpack_from("<f", data, o2)[0]:g}' if ops.startswith('s') else \
                f'= {struct.unpack_from("<d", data, o2)[0]:g}'
        elif ins.mnemonic.startswith('add') and ops.endswith(', pc'):
            rd = ops.split(',')[0]
            if regs.get(rd) is not None:
                va = (regs[rd] + ins.address + 4) & 0xffffffff
                regs[rd] = va
                if in_sec(va, '.got'):
                    gotbase = va
                note = describe(va)
        elif ins.mnemonic.startswith('ldr') and re.match(r'\w+, \[(\w+), (\w+)\]$', ops):
            rd, ra, rb = re.match(r'(\w+), \[(\w+), (\w+)\]$', ops).groups()
            if isinstance(regs.get(rb), int) and gotbase:
                va = (gotbase + regs[rb]) & 0xffffffff
                note = describe(va)
            regs[rd] = None
        elif ins.mnemonic.startswith('add') and re.match(r'(\w+), (\w+)(?:, (\w+))?$', ops):
            g = re.match(r'(\w+), (\w+)(?:, (\w+))?$', ops).groups()
            rd, ra, rb = (g[0], g[0], g[1]) if g[2] is None else g
            if isinstance(regs.get(rb), int) and gotbase and (regs.get(ra) == gotbase or regs.get(ra) is None) \
                    and regs[rb] > 0xff000000:
                va = (gotbase + regs[rb]) & 0xffffffff
                note = describe(va)
                regs[rd] = va
            else:
                regs[rd] = None
        elif ins.mnemonic.startswith('mov') and ops.startswith('r'):
            regs[ops.split(',')[0]] = None
    except Exception as e:  # keep going
        note = f'?{e}'
    print(f'{ins.address:08x}  {ins.mnemonic:8} {ops:32} {("; " + note) if note else ""}')
