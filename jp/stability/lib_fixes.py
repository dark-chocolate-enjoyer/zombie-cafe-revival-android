"""Native-lib bug fixes for libZombieCafeAndroid.so, as checked byte patches (D-08).

Each fix: (name, file offset, expected bytes, new bytes, why). apply() aborts if the bytes at an
offset aren't exactly the expected ones, so a fix can't land on the wrong lib or twice.
Offsets are file offsets; for this lib's code segment they equal the addresses in the disassembly.
Used by jp/english/build.py (release builds from v6) and make_debug_apk.py; owner-approved 2026-10-09.
"""

FIXES = [
    ('raid-resume list typo', 0x17302a, bytes.fromhex('301c'), bytes.fromhex('201c'),
     'GameStateRaid::init block 6 walks the furniture list it just deleted (r6) instead of the new '
     'object list (r4): adds r0, r6, #0 -> adds r0, r4, #0. See README.md finding 4.'),

    # StringBuffer::toString() did malloc(length) and never wrote a terminating 0 (STRING_BUG.md).
    # Part 1: a 20-byte helper written over String::Test() const (0x290ec2, 66 bytes; no callers,
    # its address appears only in .dynsym):
    #   push {r4, lr} / adds r4, r0, #0 / adds r0, #1 / blx malloc / cmp r0, #0 / beq done /
    #   movs r1, #0 / strb r1, [r0, r4] / done: pop {r4, pc}      = malloc(len + 1); buf[len] = 0
    ('toString terminator: helper', 0x290ec2,
     bytes.fromhex('70b50622855e041c681c13f658ed061c002d12dd'),
     bytes.fromhex('10b5041c013013f65aed002801d00021015510bd'),
     'String::Test() const (unused) -> helper: malloc(len + 1), then buf[len] = 0.'),
    # Part 2: in StringBuffer::toString(), `blx malloc` -> `bl helper`.
    ('toString terminator: call', 0x2918de, bytes.fromhex('13f650e8'), bytes.fromhex('fff7f0fa'),
     'StringBuffer::toString(): blx malloc -> bl 0x290ec2 (the helper).'),

    # javaGetDeviceInfoForURL did buf = malloc(len); copy; buf[len] = 0 -> 1 byte past the end, on every save
    # upload (caught by GWP-ASan, auto run A round 27). Reuses the toString helper: malloc(len + 1), buf[len] = 0.
    # THE cafe -> map crash: on the A54 the text is 80 B, + Scudo's 16-byte header = one 96-byte slot exactly,
    # so the zero lands on the next block's header (DEVICEINFO_BUG.md; v6 0/20 vs control 10/20).
    ('device-info terminator: call', 0x299274, bytes.fromhex('0bf684eb'), bytes.fromhex('f7f725fe'),
     'javaGetDeviceInfoForURL: blx malloc -> bl 0x290ec2 (the helper).'),
]


def state(lib):
    """'none' (pristine), 'all' (every fix already in) or 'partial' (anything else: refuse to touch it)."""
    have = [bytes(lib[o:o + len(n)]) == n for _, o, _, n, _ in FIXES]
    was = [bytes(lib[o:o + len(x)]) == x for _, o, x, _, _ in FIXES]
    return 'all' if all(have) else 'none' if all(was) else 'partial'


def apply(lib):
    lib = bytearray(lib)
    for name, off, old, new, _ in FIXES:
        assert len(old) == len(new)
        got = bytes(lib[off:off + len(old)])
        assert got == old, f'{name}: expected {old.hex()} at {off:#x}, found {got.hex()}'
        lib[off:off + len(new)] = new
    return bytes(lib)
