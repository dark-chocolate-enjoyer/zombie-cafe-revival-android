#!/usr/bin/env python3
"""Make a memory-checker test APK from a normal JP build. Debug only: never distribute.

  python3 make_debug_apk.py --mode malloc|gwp|lock [--offline] [in.apk] [out.apk]

  --mode malloc  wrap_mallocdebug.sh: bionic malloc debug  -> ZombieCafe_JP_English_MALLOC_DEBUG.apk
  --mode gwp     wrap_gwpasan.sh: GWP-ASan on Scudo        -> ZombieCafe_JP_English_GWP_ASAN.apk
  --mode lock    no checker; classes.dex rebuilt with every Java -> native call behind one lock
                 (lock_natives.py, via apktool 3.0.1)      -> ZombieCafe_JP_English_NATIVE_LOCK.apk
  --offline      also patch classes.dex so the game believes it has no internet (offline_patch.py);
                 the output name gains _OFFLINE
Default input: jp/english/out/ZombieCafe_JP_English.apk; outputs go to jp/english/out/.
Exactly three changes to the input APK:
  1. AndroidManifest.xml: <application> gains android:debuggable="true" (Android only runs
     wrap.sh for debuggable apps; it also enables `adb shell run-as` for the save files)
  2. lib/armeabi/wrap.sh added (the mode's wrap_*.sh from this folder): starts the game under the checker
  3. lib/armeabi/libZombieCafeAndroid.so: the checked bug fixes in lib_fixes.py
Signed with the repo debug.keystore like every JP build, so it installs over them and keeps the save.
"""
import hashlib, os, struct, subprocess, sys, zipfile

import lib_fixes

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, 'jp', 'english', 'out')
BT = os.path.expanduser('~/Android/Sdk/build-tools/35.0.0')

LIB = 'lib/armeabi/libZombieCafeAndroid.so'
ATTR_DEBUGGABLE = 0x0101000f
TYPE_STRING, TYPE_BOOLEAN = 0x03, 0x12
NO_INDEX = 0xffffffff


def add_debuggable(data):
    """Return the binary manifest with android:debuggable="true" on <application>.

    The new attribute name goes into the string pool right after the strings covered by the
    resource map (where aapt puts attribute names), so every string reference at or after
    that index is shifted by one."""
    d = bytearray(data)
    assert struct.unpack_from('<HH', d, 0) == (0x0003, 8)
    pos = 8
    t, hsz, sz = struct.unpack_from('<HHI', d, pos)
    assert t == 0x0001
    count, styles, flags, start, _ = struct.unpack_from('<IIIII', d, pos + 8)
    assert styles == 0 and flags == 0, 'expects a UTF-16 pool without styles'
    offs = struct.unpack_from(f'<{count}I', d, pos + hsz)
    strings = []
    for o in offs:
        p = pos + start + o
        n = struct.unpack_from('<H', d, p)[0]
        assert n < 0x8000
        strings.append(d[p + 2:p + 2 + 2 * n].decode('utf-16le'))
    pool_end = pos + sz
    t, _, sz = struct.unpack_from('<HHI', d, pool_end)
    assert t == 0x0180
    resmap = list(struct.unpack_from(f'<{(sz - 8) // 4}I', d, pool_end + 8))
    nodes_start = pool_end + sz
    assert 'debuggable' not in strings and ATTR_DEBUGGABLE not in resmap
    ins = len(resmap)
    strings.insert(ins, 'debuggable')
    resmap.append(ATTR_DEBUGGABLE)

    def fix(i):
        return i + 1 if i != NO_INDEX and i >= ins else i

    def fix_at(buf, off):
        struct.pack_into('<I', buf, off, fix(struct.unpack_from('<I', buf, off)[0]))

    nodes = bytearray()
    pos, done = nodes_start, False
    while pos < len(d):
        t, hsz, sz = struct.unpack_from('<HHI', d, pos)
        c = bytearray(d[pos:pos + sz])
        assert 0x0100 <= t <= 0x0104, hex(t)
        fix_at(c, 12)                                   # comment
        if t in (0x0100, 0x0101, 0x0103):               # namespace start/end, element end
            fix_at(c, 16); fix_at(c, 20)
        elif t == 0x0104:                               # CDATA
            fix_at(c, 16)
            if c[23] == TYPE_STRING: fix_at(c, 24)
        else:                                           # element start
            fix_at(c, 16); fix_at(c, 20)
            astart, asize, acount = struct.unpack_from('<HHH', c, 24)
            assert asize == 20
            attrs = []
            for k in range(acount):
                a = 16 + astart + 20 * k
                fix_at(c, a); fix_at(c, a + 4); fix_at(c, a + 8)
                if c[a + 15] == TYPE_STRING: fix_at(c, a + 16)
                attrs.append(a)
            if strings[struct.unpack_from('<I', c, 20)[0]] == 'application':
                assert not done
                last = attrs[-1]
                assert resmap[struct.unpack_from('<I', c, last + 4)[0]] < ATTR_DEBUGGABLE  # stays sorted
                ns = struct.unpack_from('<I', c, last)[0]
                c[last + 20:last + 20] = struct.pack('<IIIHBBI', ns, ins, NO_INDEX, 8, 0, TYPE_BOOLEAN, 0xffffffff)
                struct.pack_into('<I', c, 4, len(c))
                struct.pack_into('<H', c, 28, acount + 1)
                done = True
        nodes += c
        pos += sz
    assert done and pos == len(d)

    body = b''.join(struct.pack('<H', len(s)) + s.encode('utf-16le') + b'\0\0' for s in strings)
    offsets, o = [], 0
    for s in strings:
        offsets.append(o); o += 4 + 2 * len(s)
    body += b'\0' * (-len(body) % 4)
    start = 28 + 4 * len(strings)
    pool = struct.pack('<HHIIIIII', 0x0001, 28, start + len(body), len(strings), 0, 0, start, 0)
    pool += struct.pack(f'<{len(offsets)}I', *offsets) + body
    rmap = struct.pack('<HHI', 0x0180, 8, 8 + 4 * len(resmap)) + struct.pack(f'<{len(resmap)}I', *resmap)
    total = 8 + len(pool) + len(rmap) + len(nodes)
    return struct.pack('<HHI', 0x0003, 8, total) + pool + rmap + bytes(nodes)


def xmltree(apk):
    return subprocess.run([f'{BT}/aapt', 'dump', 'xmltree', apk, 'AndroidManifest.xml'],
                          check=True, capture_output=True, text=True).stdout.splitlines()


MODES = {'malloc': ('wrap_mallocdebug.sh', 'ZombieCafe_JP_English_MALLOC_DEBUG.apk'),
         'gwp': ('wrap_gwpasan.sh', 'ZombieCafe_JP_English_GWP_ASAN.apk'),
         'lock': (None, 'ZombieCafe_JP_English_NATIVE_LOCK.apk')}


def patched_dex(apk, scripts):
    """classes.dex of `apk` decoded with apktool, patched by each script (SMALI_DIR arg), rebuilt."""
    import shutil, tempfile
    tmp = tempfile.mkdtemp(prefix='zc_lock_')
    try:
        dec, built = os.path.join(tmp, 'dec'), os.path.join(tmp, 'built.apk')
        subprocess.run(['apktool', 'd', '-r', '-f', '-o', dec, apk], check=True, capture_output=True)
        for script in scripts:
            subprocess.run([sys.executable, os.path.join(HERE, script), dec], check=True)
        subprocess.run(['apktool', 'b', dec, '-o', built], check=True, capture_output=True)
        return zipfile.ZipFile(built).read('classes.dex')
    finally:
        shutil.rmtree(tmp)


def main():
    args = sys.argv[1:]
    assert len(args) >= 2 and args[0] == '--mode' and args[1] in MODES, __doc__
    args_mode = args[1]
    wrap_name, out_name = MODES[args_mode]
    offline = len(args) > 2 and args[2] == '--offline'
    if offline:
        args = args[:2] + args[3:]
        out_name = out_name.replace('.apk', '_OFFLINE.apk')
    args = args[2:]
    src = args[0] if len(args) > 0 else os.path.join(OUT, 'ZombieCafe_JP_English.apk')
    final = args[1] if len(args) > 1 else os.path.join(OUT, out_name)
    print('input ', hashlib.sha256(open(src, 'rb').read()).hexdigest(), src)
    zin = zipfile.ZipFile(src)
    libdirs = {n.split('/')[1] for n in zin.namelist() if n.startswith('lib/')}
    assert libdirs == {'armeabi'}, libdirs
    wrap = open(os.path.join(HERE, wrap_name), 'rb').read() if wrap_name else None
    assert wrap is None or b'\r' not in wrap
    scripts = (['lock_natives.py'] if args_mode == 'lock' else []) + (['offline_patch.py'] if offline else [])
    dex = patched_dex(src, scripts) if scripts else None
    unsigned, aligned = final + '.unsigned', final + '.aligned'
    with zipfile.ZipFile(unsigned, 'w') as out:
        for info in zin.infolist():
            if info.filename.startswith('META-INF/'):
                continue
            data = zin.read(info.filename)
            if info.filename == 'AndroidManifest.xml':
                data = add_debuggable(data)
            elif info.filename == LIB:
                st = lib_fixes.state(data)
                assert st != 'partial', 'input lib has only some of the fixes'
                data = lib_fixes.apply(data) if st == 'none' else data      # v6+ input already has them
            elif info.filename == 'classes.dex' and dex is not None:
                data = dex
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type, zi.external_attr = info.compress_type, info.external_attr
            out.writestr(zi, data)
        if wrap is not None:
            zi = zipfile.ZipInfo('lib/armeabi/wrap.sh', date_time=(2026, 10, 9, 0, 0, 0))
            zi.compress_type, zi.external_attr = zipfile.ZIP_DEFLATED, 0o100755 << 16
            out.writestr(zi, wrap)
    subprocess.run([f'{BT}/zipalign', '-p', '-f', '4', unsigned, aligned], check=True)
    subprocess.run([f'{BT}/apksigner', 'sign', '--ks', os.path.join(REPO, 'debug.keystore'), '--ks-key-alias', 'alias_name',
                    '--ks-pass', 'pass:zombiecafe', '--out', final, aligned], check=True)
    os.remove(unsigned); os.remove(aligned)
    subprocess.run([f'{BT}/apksigner', 'verify', final], check=True)

    # the manifest must differ by exactly the one added attribute
    before, after = xmltree(src), xmltree(final)
    added = [l for l in after if l not in before]
    assert len(after) == len(before) + 1 and len(added) == 1 and 'android:debuggable(0x0101000f)=(type 0x12)0xffffffff' in added[0], added
    assert [l for l in after if l != added[0]] == before
    names_in, names_out = set(zin.namelist()), set(zipfile.ZipFile(final).namelist())
    assert {n for n in names_out - names_in if not n.startswith('META-INF/')} == ({'lib/armeabi/wrap.sh'} if wrap else set())
    zout = zipfile.ZipFile(final)
    changed = {n for n in names_in if not n.startswith('META-INF/') and zin.read(n) != zout.read(n)}
    assert changed - {LIB} == {'AndroidManifest.xml'} | ({'classes.dex'} if dex else set()), changed
    print('manifest +', added[0].strip())
    if wrap:
        print(f'added    lib/armeabi/wrap.sh ({wrap_name}):')
        for line in wrap.decode().splitlines():
            if line.startswith(('export ', 'LIBC_', 'exec ')):
                print('           ', line)
    if dex:
        print(f'dex      classes.dex rebuilt with {", ".join(scripts)} ({len(dex)} bytes)')
    for name, off, old, new, _ in lib_fixes.FIXES:
        print(f'lib fix  {name}: {off:#x} {old.hex()} -> {new.hex()}')
    print('output', hashlib.sha256(open(final, 'rb').read()).hexdigest(), final)


if __name__ == '__main__':
    main()
