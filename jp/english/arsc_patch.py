#!/usr/bin/env python3
"""Replace strings in the global string pool of resources.arsc.

Only the default-locale Japanese values are replaced (the Google Play library
ships its own per-locale translations, which Android already picks by device
language). The pool is re-encoded and every size field is recomputed, so the
replacement strings may be any length.

Output: work/patched/resources.arsc
"""
import os, struct, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPLACE = {
    'ゾンビカフェ': 'Zombie Cafe JP',
    '表示': 'View',
    'あとで': 'Later',
}


def dec_len(buf, pos, utf8):
    if utf8:
        n = buf[pos]
        pos += 1
        if n & 0x80:
            n = ((n & 0x7f) << 8) | buf[pos]
            pos += 1
        return n, pos
    n = struct.unpack_from('<H', buf, pos)[0]
    pos += 2
    if n & 0x8000:
        n = ((n & 0x7fff) << 16) | struct.unpack_from('<H', buf, pos)[0]
        pos += 2
    return n, pos


def enc_len(n, utf8):
    if utf8:
        return bytes([n]) if n < 0x80 else bytes([0x80 | (n >> 8), n & 0xff])
    return struct.pack('<H', n) if n < 0x8000 else struct.pack('<HH', 0x8000 | (n >> 16), n & 0xffff)


def main():
    arsc = zipfile.ZipFile(os.path.join(HERE, 'work', 'base_v4.apk')).read('resources.arsc')
    t_type, t_hsize, t_size, pkg_count = struct.unpack_from('<HHII', arsc, 0)
    assert t_type == 2
    pool_off = t_hsize
    p_type, p_hsize, p_size, count, style_count, flags, s_start, st_start = struct.unpack_from('<HHIIIIII', arsc, pool_off)
    assert p_type == 1
    utf8 = bool(flags & 0x100)
    offs = struct.unpack_from(f'<{count}I', arsc, pool_off + p_hsize)
    style_offs = struct.unpack_from(f'<{style_count}I', arsc, pool_off + p_hsize + 4 * count)
    base = pool_off + s_start
    strings = []
    for o in offs:
        pos = base + o
        if utf8:
            _, pos = dec_len(arsc, pos, True)       # UTF-16 length
            n, pos = dec_len(arsc, pos, True)       # byte length
            strings.append(arsc[pos:pos + n].decode('utf-8'))
        else:
            n, pos = dec_len(arsc, pos, False)
            strings.append(arsc[pos:pos + 2 * n].decode('utf-16-le'))
    hits = 0
    for i, s in enumerate(strings):
        if s in REPLACE:
            strings[i] = REPLACE[s]
            hits += 1
    assert hits == len(REPLACE), f'expected {len(REPLACE)} replacements, got {hits}'

    data, new_offs = bytearray(), []
    for s in strings:
        new_offs.append(len(data))
        if utf8:
            b = s.encode('utf-8')
            data += enc_len(len(s.encode('utf-16-le')) // 2, True) + enc_len(len(b), True) + b + b'\0'
        else:
            b = s.encode('utf-16-le')
            data += enc_len(len(b) // 2, False) + b + b'\0\0'
    while len(data) % 4:
        data += b'\0'
    styles = arsc[pool_off + st_start:pool_off + p_size] if style_count else b''
    header_len = p_hsize + 4 * count + 4 * style_count
    new_s_start = header_len
    new_st_start = header_len + len(data) if style_count else 0
    new_p_size = header_len + len(data) + len(styles)
    pool = struct.pack('<HHIIIIII', 1, p_hsize, new_p_size, count, style_count, flags, new_s_start, new_st_start)
    pool += arsc[pool_off + 28:pool_off + p_hsize]
    pool += struct.pack(f'<{count}I', *new_offs) + struct.pack(f'<{style_count}I', *style_offs) + data + styles
    rest = arsc[pool_off + p_size:]
    out = struct.pack('<HHII', t_type, t_hsize, t_hsize + len(pool) + len(rest), pkg_count) + arsc[16:t_hsize] + pool + rest
    path = os.path.join(HERE, 'work', 'patched', 'resources.arsc')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(out)
    print(f'resources.arsc: {hits} strings replaced ({len(arsc)} -> {len(out)} bytes)')


if __name__ == '__main__':
    main()
