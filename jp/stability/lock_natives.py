#!/usr/bin/env python3
"""Serialise every Java -> native call in the game behind ONE Java lock (crash-hunt test, 2026-10-09).

  python3 lock_natives.py SMALI_DIR

SMALI_DIR = an `apktool d -r` decode of the APK. For every `native` method declared in
com/capcom/zombiecafeandroidJP, a public static wrapper `zcLocked_<name>` is added to the declaring
class: it takes the lock (the class object of the new empty class ZCNativeLock), calls the native and
releases the lock, also on exceptions (the same shape javac emits for `synchronized`). Every call site
is redirected to its wrapper with the same register list, so nothing else in the method changes.
Java monitors are re-entrant, so native -> Java -> native nesting on one thread is fine.

Not wrapped: TrueTypeFont.<clinit> -> initTrueTypeFont (a class-initialisation lock plus this lock
could deadlock). The app's own `synchronized` code (URLManager.a(), l.a(), TrueTypeFont.getInstance/
finalize) calls no natives, so it can't form a lock cycle with this one.

Why: native game code is entered from the game (GL) thread, the UI thread (touches, dialogs,
pause/resume) and background threads (network callbacks, MouseTask) with no synchronisation
(README finding 11). If the cafe -> map crash is such a race, this build should stop it.
"""
import os, re, sys

PKG = 'com/capcom/zombiecafeandroidJP'
LOCK = f'L{PKG}/ZCNativeLock;'
SKIP_SITES = {('TrueTypeFont', '<clinit>()V')}

INVOKE = re.compile(r'^(\s*)invoke-(static|virtual|direct)(/range)? \{([^}]*)\}, (L[^;]+;)->([A-Za-z0-9_$]+)(\([^)]*\)\S+)\s*$')


def params(desc):
    """Split a method descriptor's parameter list -> [(type, words)]."""
    inner = desc[1:desc.index(')')]
    out, i = [], 0
    while i < len(inner):
        j = i
        while inner[j] == '[':
            j += 1
        j = inner.index(';', j) + 1 if inner[j] == 'L' else j + 1
        t = inner[i:j]
        out.append((t, 2 if t in ('J', 'D') else 1))
        i = j
    return out


def wrapper(cls, name, desc, static, private):
    ret = desc[desc.index(')') + 1:]
    ps = params(desc) if static else [(cls, 1)] + params(desc)
    words = sum(w for _, w in ps)
    regs = '{}' if words == 0 else f'{{p0 .. p{words - 1}}}'
    op = 'invoke-static' if static else ('invoke-direct' if private else 'invoke-virtual')
    if words:
        op += '/range'
    wdesc = '(' + ''.join(t for t, _ in ps) + ')' + ret
    move, retop = {'V': ('', 'return-void'), 'J': ('move-result-wide v1', 'return-wide v1'),
                   'D': ('move-result-wide v1', 'return-wide v1')}.get(
        ret, ('move-result-object v1', 'return-object v1') if ret[0] in 'L[' else ('move-result v1', 'return v1'))
    body = [f'.method public static zcLocked_{name}{wdesc}',
            '    .locals 4',
            f'    const-class v0, {LOCK}',
            '    monitor-enter v0',
            '    :try_start_0',
            f'    {op} {regs}, {cls}->{name}{desc}']
    if move:
        body.append(f'    {move}')
    body += ['    monitor-exit v0',
             '    :try_end_0',
             '    .catchall {:try_start_0 .. :try_end_0} :catchall_0',
             f'    {retop}',
             '    :catchall_0',
             '    move-exception v3',
             '    :try_start_1',
             '    monitor-exit v0',
             '    :try_end_1',
             '    .catchall {:try_start_1 .. :try_end_1} :catchall_0',
             '    throw v3',
             '.end method', '']
    return '\n'.join(body), wdesc


def main():
    root = os.path.join(sys.argv[1], 'smali', PKG)
    files = sorted(f for f in os.listdir(root) if f.endswith('.smali'))
    natives = {}                                    # (cls, name, desc) -> (static, private)
    for f in files:
        cls = f'L{PKG}/{f[:-6]};'
        for line in open(os.path.join(root, f)):
            m = re.match(r'^\.method (.*)\bnative ([A-Za-z0-9_$]+)(\(.*)$', line.strip())
            if m:
                mods = m.group(1).split()
                natives[(cls, m.group(2), m.group(3))] = ('static' in mods, 'private' in mods)
    wrappers, sites = {}, 0
    every = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(sys.argv[1], 'smali'))
                   for f in fs if f.endswith('.smali'))     # call sites may sit outside the package too
    for path in every:
        f = os.path.basename(path)
        out, meth, changed = [], None, False
        for line in open(path):
            if line.startswith('.method'):
                meth = line.split()[-1]
            m = INVOKE.match(line.rstrip('\n'))
            key = m and (m.group(5), m.group(6), m.group(7))
            if m and key in natives and not (path.startswith(root) and (f[:-6], meth) in SKIP_SITES):
                static, private = natives[key]
                if key not in wrappers:
                    wrappers[key] = wrapper(*key, static, private)
                rng = '/range' if m.group(3) else ''
                line = f'{m.group(1)}invoke-static{rng} {{{m.group(4)}}}, {key[0]}->zcLocked_{key[1]}{wrappers[key][1]}\n'
                sites += 1
                changed = True
            out.append(line)
        if changed:
            open(path, 'w').write(''.join(out))
    for (cls, name, desc), (text, _) in sorted(wrappers.items()):
        path = os.path.join(root, cls[len(f'L{PKG}/'):-1] + '.smali')
        with open(path, 'a') as fh:
            fh.write('\n# --- added by jp/stability/lock_natives.py ---\n' + text)
    with open(os.path.join(root, 'ZCNativeLock.smali'), 'w') as fh:
        fh.write(f'.class public final {LOCK}\n.super Ljava/lang/Object;\n.source "ZCNativeLock.java"\n\n'
                 '# Its class object is the one lock every Java -> native call takes (lock_natives.py).\n')
    print(f'{len(natives)} natives declared, {len(wrappers)} wrapped, {sites} call sites redirected')


if __name__ == '__main__':
    main()
