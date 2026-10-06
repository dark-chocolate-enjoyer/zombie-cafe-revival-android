#!/usr/bin/env python3
"""Write English over the Japanese strings in libZombieCafeAndroid.so.

Each string keeps its original start address. English that fits is written in
place (NUL-padded). English that doesn't fit is placed in slack space left by
other shortened strings, and every known reference (R_ARM_RELATIVE data
pointers and PC-relative literal-pool words) is repointed; a truncated copy
stays at the old address so any reference we failed to find still reads
sensible text. Run lib_refs.py first.

Output: work/patched/lib/armeabi/libZombieCafeAndroid.so
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, 'work')

lib = bytearray(open(os.path.join(W, 'base_lib.so'), 'rb').read())
strings = json.load(open(os.path.join(W, 'lib_strings.json'), encoding='utf-8'))
lit_uses = {int(k): v for k, v in json.load(open(os.path.join(W, 'lib_lit_uses.json'))).items()}

tm = {}
for f in sorted(os.listdir(os.path.join(HERE, 'tm'))):
    if f.startswith('lib_') and f.endswith('.tsv'):
        for line in open(os.path.join(HERE, 'tm', f), encoding='utf-8'):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            idx, _, en = line.partition('\t')
            tm[int(idx)] = en.replace('\\n', '\n')

problems = []
plan = []  # (string, encoded english)
for i, s in enumerate(strings):
    if i not in tm:
        problems.append(f'untranslated lib string {i}: {s["jp"]!r}')
        continue
    en = tm[i]
    if any(ord(c) > 126 and c != '\n' for c in en):
        problems.append(f'non-ASCII in lib string {i}: {en!r}')
    for spec in ('%d', '%s', '%%'):
        if s['jp'].count(spec) != en.count(spec):
            problems.append(f'format mismatch in lib string {i}: {s["jp"]!r} -> {en!r}')
    plan.append((i, s, en.encode('utf-8')))
if problems:
    print('\n'.join(problems))
    sys.exit(1)


def relocatable(s):
    if not s['refs_start']:
        return False
    for kind, loc, base in s['refs_start']:
        if kind == 'pcrel' and lit_uses.get(loc) != [base]:
            return False
    return True


# pass 1: in-place writes, collect slack
gaps, relocate = [], []
for i, s, en in plan:
    off, size = s['off'], s['size']
    if len(en) <= size:
        lib[off:off + size + 1] = en + b'\0' * (size + 1 - len(en))
        if size - len(en) >= 8:
            gaps.append([off + len(en) + 1, size - len(en)])
    else:
        relocate.append((i, s, en))

# pass 2: relocate strings that don't fit
moved = truncated = 0
gaps.sort(key=lambda g: g[1])
for i, s, en in relocate:
    off, size = s['off'], s['size']
    fallback = en[:size]
    lib[off:off + size + 1] = fallback + b'\0' * (size + 1 - len(fallback))
    if not relocatable(s):
        truncated += 1
        print(f'  truncated in place (refs not fully known) #{i}: {fallback!r}')
        continue
    need = len(en) + 1
    g = next((g for g in gaps if g[1] >= need), None)
    if g is None:
        truncated += 1
        print(f'  no slack left, truncated #{i}: {fallback!r}')
        continue
    new = g[0]
    lib[new:new + need] = en + b'\0'
    g[0] += need
    g[1] -= need
    gaps.sort(key=lambda g: g[1])
    for kind, loc, base in s['refs_start']:
        if kind == 'rel':
            struct.pack_into('<I', lib, loc, new)
        else:
            struct.pack_into('<I', lib, loc, (new - base) & 0xffffffff)
    moved += 1

out = os.path.join(W, 'patched', 'lib', 'armeabi', 'libZombieCafeAndroid.so')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'wb').write(lib)
print(f'lib strings: {len(plan)} translated, {len(plan) - len(relocate)} in place, {moved} relocated, {truncated} truncated')
print(f'slack remaining: {sum(g[1] for g in gaps)} bytes')
