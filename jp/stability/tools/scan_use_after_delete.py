#!/usr/bin/env python3
"""Static scan of libZombieCafeAndroid.so for 'use after delete' (found in GameStateRaid::init, 2026-10-09).
1. same register: `r0 = rX; bl operator delete/free` followed, before rX is rewritten, by an
   instruction that reads memory through rX or passes rX as r0 to a call.
2. same field: the freed pointer was loaded from `[rB, #off]`; later `[rB, #off]` is loaded again
   (no store to it in between, no NULL test) and used.
Linear per-function scan (ignores branches), so every hit is a CANDIDATE for manual review.
usage: scan_use_after_delete.py LIB [window]"""
import subprocess, sys
import capstone
from capstone import arm

lib = sys.argv[1]
window = int(sys.argv[2]) if len(sys.argv) > 2 else 40
data = open(lib, 'rb').read()


def run(*a):
    return subprocess.run(a, capture_output=True, text=True, check=True).stdout


segs = []
for line in run('readelf', '-l', '-W', lib).splitlines():
    p = line.split()
    if p and p[0] == 'LOAD':
        segs.append((int(p[2], 16), int(p[1], 16), int(p[4], 16)))


def off(va):
    for v, o, sz in segs:
        if v <= va < v + sz:
            return o + va - v


funcs, names = [], {}
for line in run('readelf', '-s', '-W', '-C', lib).splitlines():
    p = line.split(None, 7)
    if len(p) == 8 and p[3] == 'FUNC' and p[6] != 'UND':
        a = int(p[1], 16) & ~1
        names.setdefault(a, p[7])
        if int(p[2]) > 0:          # size-0 symbols (e.g. __cxa_end_cleanup) are names only
            funcs.append((a, int(p[2]), p[7]))
funcs = sorted(set(funcs))
deletes = {a for a, n in names.items() if n.startswith('operator delete') or n == 'free'}
noreturn = {a for a, n in names.items() if n in ('__cxa_end_cleanup', '_Unwind_Resume')}  # EH cleanup ends here

md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
md.detail = True


def is_copy_to_r0(ins):
    """`adds r0, rX, #0` / `mov r0, rX` -> X, else None."""
    ops = ins.operands
    if ins.mnemonic in ('adds', 'mov', 'movs') and len(ops) >= 2 and ops[0].type == arm.ARM_OP_REG \
            and ops[0].reg == arm.ARM_REG_R0 and ops[1].type == arm.ARM_OP_REG:
        if ins.mnemonic == 'adds' and not (len(ops) == 3 and ops[2].type == arm.ARM_OP_IMM and ops[2].imm == 0):
            return None
        return ops[1].reg
    return None


def disasm(a, size):
    """All instructions of a function, skipping literal pools (capstone stops at bad bytes)."""
    o, pos, out = off(a), 0, []
    while pos < size:
        n = 0
        for ins in md.disasm(data[o + pos:o + size], a + pos):
            out.append(ins); n += ins.size
        pos += n + (2 if pos + n < size else 0)
    return out


hits = 0
for a, size, name in funcs:
    if off(a) is None:
        continue
    insns = disasm(a, size)
    at = {ins.address: k for k, ins in enumerate(insns)}
    for i, ins in enumerate(insns):
        if ins.mnemonic != 'bl' or ins.operands[0].imm not in deletes or i == 0:
            continue
        freed, between = None, []
        for back in insns[max(0, i - 3):i][::-1]:
            if back.mnemonic in ('bl', 'blx'):       # r0 is then a return value, not rX
                break
            freed = is_copy_to_r0(back)
            if freed is not None:
                break
            between.append(back)
        if any(freed in b.regs_access()[1] for b in between):   # rX reassigned before the delete
            continue
        if freed is None or freed in (arm.ARM_REG_SP, arm.ARM_REG_R0):
            continue
        j, steps = i + 1, 0
        while j < len(insns) and steps < window:
            ins2, steps = insns[j], steps + 1
            if ins2.mnemonic == 'bx' or (ins2.mnemonic == 'pop' and 'pc' in ins2.op_str):
                break
            if ins2.mnemonic == 'bl' and ins2.operands[0].imm in noreturn:
                break
            if ins2.mnemonic == 'b':                    # unconditional jump: follow it
                tgt = ins2.operands[0].imm
                if tgt not in at:
                    break
                j = at[tgt]
                continue
            regs_read, regs_written = ins2.regs_access()
            use = None
            for op in ins2.operands:
                if op.type == arm.ARM_OP_MEM and op.mem.base == freed:
                    use = 'mem'
            if is_copy_to_r0(ins2) == freed and j + 1 < len(insns) and insns[j + 1].mnemonic in ('bl', 'blx'):
                use = 'call'
            if use:
                hits += 1
                tgt = insns[j + 1].op_str if use == 'call' else ''
                callee = names.get(int(tgt.lstrip('#'), 16), tgt) if tgt.startswith('#0x') else tgt
                print(f'{name}\tdelete@{ins.address:#x}\tuse@{ins2.address:#x}\t{md.reg_name(freed)}\t{use}\t'
                      f'{ins2.mnemonic} {ins2.op_str}\t{callee}')
                break
            if freed in regs_written:
                break
            j += 1
# --- variant 2: `rX = [rB, #off]; delete rX; ... rY = [rB, #off]; use rY` with no store to the field ---
fhits = 0
for a, size, name in funcs:
    if off(a) is None:
        continue
    insns = disasm(a, size)
    at = {ins.address: k for k, ins in enumerate(insns)}
    for i, ins in enumerate(insns):
        if ins.mnemonic != 'bl' or ins.operands[0].imm not in deletes or i == 0:
            continue
        freed = None
        for back in insns[max(0, i - 3):i][::-1]:
            if back.mnemonic in ('bl', 'blx'):
                break
            freed = is_copy_to_r0(back)
            if freed is not None:
                break
        if freed is None:                               # the pointer may also be loaded straight into r0
            freed = arm.ARM_REG_R0
        field = None                                    # where was the freed pointer loaded from?
        for k in range(i - 1, max(-1, i - 8), -1):
            b = insns[k]
            if b.mnemonic in ('bl', 'blx'):
                break
            ops = b.operands
            if b.mnemonic == 'ldr' and len(ops) == 2 and ops[0].reg == freed and ops[1].type == arm.ARM_OP_MEM \
                    and ops[1].mem.index == 0 and ops[1].mem.base not in (arm.ARM_REG_PC, arm.ARM_REG_SP, freed):
                field = (ops[1].mem.base, ops[1].mem.disp)
                if any(field[0] in x.regs_access()[1] for x in insns[k + 1:i]):
                    field = None
                break
        if field is None:
            continue
        base, disp = field
        j, steps, loaded = i + 1, 0, None
        while j < len(insns) and steps < window * 2:
            ins2, steps = insns[j], steps + 1
            if ins2.mnemonic == 'bx' or (ins2.mnemonic == 'pop' and 'pc' in ins2.op_str):
                break
            if ins2.mnemonic == 'bl' and ins2.operands[0].imm in noreturn:
                break
            if ins2.mnemonic == 'b':
                tgt = ins2.operands[0].imm
                if tgt not in at:
                    break
                j = at[tgt]
                continue
            ops = ins2.operands
            mem = [o for o in ops if o.type == arm.ARM_OP_MEM]
            if ins2.mnemonic.startswith('str') and mem and mem[0].mem.base == base and mem[0].mem.disp == disp:
                break                                   # field overwritten (e.g. set to NULL)
            if ins2.mnemonic == 'ldr' and mem and mem[0].mem.base == base and mem[0].mem.disp == disp and mem[0].mem.index == 0:
                loaded = (ops[0].reg, ins2.address)
                # is the reloaded pointer used before being tested? (a `cmp rY, #0` means a NULL check: fine)
                for k in range(j + 1, min(len(insns), j + 6)):
                    u = insns[k]
                    if u.mnemonic in ('cmp', 'cbz', 'cbnz') and u.operands[0].reg == loaded[0]:
                        loaded = None; break
                    if any(o.type == arm.ARM_OP_MEM and o.mem.base == loaded[0] for o in u.operands) or \
                            (is_copy_to_r0(u) == loaded[0] and k + 1 < len(insns) and insns[k + 1].mnemonic in ('bl', 'blx')):
                        fhits += 1
                        print(f'{name}\tdelete@{ins.address:#x}\treload@{loaded[1]:#x}\t[{md.reg_name(base)}, #{disp:#x}]\tfield\t'
                              f'{u.mnemonic} {u.op_str}\t')
                        loaded = None; break
                    if loaded[0] in u.regs_access()[1]:
                        break
                break
            if base in ins2.regs_access()[1]:
                break
            j += 1
print(f'# {hits} same-register candidates, {fhits} field-reload candidates', file=sys.stderr)
