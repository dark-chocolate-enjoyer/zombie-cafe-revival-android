#!/usr/bin/env python3
"""Decode constants.bin.mid by emulating Constants::load(DataInputStream*) from the game's .so.
usage: zemu_constants.py LIB constants.bin.mid OUT.json"""
import json
import re
import struct
import subprocess
import sys

sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '..', '..', 'english', '.pylib'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UcError  # noqa: E402
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP  # noqa

lib, cfile, out = sys.argv[1:4]
data = open(lib, 'rb').read()
cdata = open(cfile, 'rb').read()


def run(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


syms, objs = {}, {}
for line in run('nm', '-DC', '-S', '--defined-only', lib).splitlines():
    m = re.match(r'([0-9a-f]+) ([0-9a-f]+) (\w) (.*)', line)
    if m:
        a, sz, t, n = int(m.group(1), 16), int(m.group(2), 16), m.group(3), m.group(4)
        syms[n] = a
        if t in 'BbDdRr':
            objs[a] = (n, sz)

uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
PAGE = 0x1000
uc.mem_map(0, 0x4c8000)
uc.mem_write(0, data[:0x4c7dac])
uc.mem_map(0x4c9000, 0x4a000)
uc.mem_write(0x4c93a0, data[0x4c83a0:0x4c83a0 + 0x115ec])
STUBS, HEAP, STACK, APP, RET = 0x6000000, 0x7000000, 0x8000000, 0x9000000, 0xa000000
for base in (STUBS, HEAP, STACK, APP, RET):
    uc.mem_map(base, 0x400000)
# fake CapcomApp: device size floats = 1.0 so pixel constants come out unscaled
for off in (0x40, 0x44, 0x48, 0x50):
    uc.mem_write(APP + off, struct.pack('<f', 1.0))

# relocations: imported symbols -> stub addresses
stub_names, next_stub = {}, STUBS
for line in run('readelf', '-r', '-W', lib).splitlines():
    m = re.match(r'([0-9a-f]{8})\s+[0-9a-f]+\s+(R_ARM_\w+)\s*(?:([0-9a-f]+)\s+(\S+))?', line)
    if not m:
        continue
    slot, typ = int(m.group(1), 16), m.group(2)
    if typ in ('R_ARM_GLOB_DAT', 'R_ARM_ABS32', 'R_ARM_JUMP_SLOT'):
        val = int(m.group(3), 16) if m.group(3) else 0
        if val == 0:
            stub_names[next_stub] = m.group(4)
            val = next_stub
            next_stub += 8
        if typ == 'R_ARM_ABS32':
            val += struct.unpack('<I', uc.mem_read(slot, 4))[0]
        uc.mem_write(slot, struct.pack('<I', val & 0xffffffff))

pos = [0]
heap = [HEAP + 0x100]
reads = []


def rd(fmt, n):
    v = struct.unpack_from(fmt, cdata, pos[0])[0]
    pos[0] += n
    return v


def ret(u, r0=None, r1=None):
    if r0 is not None:
        u.reg_write(UC_ARM_REG_R0, r0 & 0xffffffff)
    if r1 is not None:
        u.reg_write(UC_ARM_REG_R1, r1 & 0xffffffff)
    u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))


def alloc(n):
    a = heap[0]
    heap[0] += (n + 15) & ~15
    return a


handlers = {
    'DataInputStream::readInt()': lambda u: ret(u, rd('>i', 4)),
    'DataInputStream::readShort()': lambda u: ret(u, rd('>h', 2)),
    'DataInputStream::readByte()': lambda u: ret(u, rd('>b', 1)),
    'DataInputStream::readFloat()': lambda u: ret(u, rd('<I', 4)),  # floats are little-endian
}


def read_long(u):
    v = rd('>q', 8) & 0xffffffffffffffff
    ret(u, v & 0xffffffff, v >> 32)


def read_utf(u):
    n = rd('>H', 2)
    s = cdata[pos[0]:pos[0] + n]
    pos[0] += n
    reads.append(('UTF', s.decode('utf-8', 'replace')))
    ret(u, u.reg_read(UC_ARM_REG_R0))


handlers['DataInputStream::readLong()'] = read_long
handlers['DataInputStream::readUTF()'] = read_utf
handlers['operator new[](unsigned int)'] = lambda u: ret(u, alloc(u.reg_read(UC_ARM_REG_R0)))
handlers['operator new(unsigned int)'] = lambda u: ret(u, alloc(u.reg_read(UC_ARM_REG_R0)))
handlers['CapcomApp::getInstance()'] = lambda u: ret(u, APP)
handlers['String::getBytes() const'] = lambda u: ret(u, alloc(16))
for n in ('String::~String()', 'String::operator=(String)', 'String::operator=(char const*)',
          'L_PrintLog(char const*, char const*)'):
    handlers[n] = lambda u: ret(u, u.reg_read(UC_ARM_REG_R0))

hook_at = {syms[n] & ~1: f for n, f in handlers.items()}
for a, n in stub_names.items():
    hook_at[a] = (lambda u, n=n: ret(u, 0))
hook_at[RET] = None


def on_code(u, addr, size, _):
    a = addr & ~1
    if a == RET:
        u.emu_stop()
        return
    f = hook_at.get(a)
    if f:
        f(u)


bss = sorted(objs)
values = {}


def on_write(u, access, addr, size, value, _):
    o = objs.get(addr)
    if o and o[0].startswith('Constants::'):
        values[o[0][len('Constants::'):]] = (addr, size, value & ((1 << (8 * size)) - 1))


uc.hook_add(UC_HOOK_CODE, on_code)
uc.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=0x4c9000, end=0x513000)
uc.reg_write(UC_ARM_REG_SP, STACK + 0x3f0000)
uc.reg_write(UC_ARM_REG_LR, RET | 1)
uc.reg_write(UC_ARM_REG_R0, HEAP)
start = syms['Constants::load(DataInputStream*)']
try:
    uc.emu_start(start | 1, RET, count=5_000_000)
except UcError as e:
    print('emu error', e, hex(uc.reg_read(UC_ARM_REG_PC)))
print(f'consumed {pos[0]} of {len(cdata)} bytes; {len(values)} constants written')

# interpret values: float if the loader read a float into it is unknown here -> give both views
res = {}
for name, (addr, size, v) in sorted(values.items()):
    item = {'size': size, 'int': v if v < 1 << (8 * size - 1) else v - (1 << (8 * size))}
    if size == 4:
        item['float'] = struct.unpack('<f', struct.pack('<I', v))[0]
        if HEAP <= v < HEAP + 0x400000:
            item['array_ptr'] = True
    res[name] = item
json.dump({'consumed': pos[0], 'size': len(cdata), 'constants': res}, open(out, 'w'), indent=1)
