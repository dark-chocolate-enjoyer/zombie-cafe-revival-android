#!/usr/bin/env python3
"""Read/write the game's packed sprite sheets.

Sheets are either real PNGs or CCTX files (28-byte header + zlib RGBA4444,
byte0 = B<<4|A, byte1 = R<<4|G). Offsets files: u8 type, be16 count, then per
sprite [type 2: name string] be16 x, y, w, h [type 2: 4 more be16].
"""
import io, os, struct, zlib
from PIL import Image, ImageDraw

SHEETS = {
    # sheet file                      offsets file
    'ingameUiImages.png': 'ingameUiOffsets.bin.mid',
    'zcImages.png': 'zcImagesOffsets.bin.mid',
    'menuimages.png': 'menuOffsets.bin.mid',
    'shopImages.cct.mid': 'shopOffsets.bin.mid',
    'iphone4_gatyaImages.cct.mid': 'iphone4_gatyaOffsets.bin',
    'iphone4_prizeMenuImages.cct.mid': 'iphone4_prizeMenuOffsets.bin.mid',
    'mapTiles.cct.mid': 'mapTilesOffsets.mid',
}


def read_offsets(data):
    typ = data[0]
    n = struct.unpack_from('>H', data, 1)[0]
    pos, out = 3, []
    for _ in range(n):
        name = ''
        if typ == 2:
            ln = struct.unpack_from('>H', data, pos)[0]
            name = data[pos + 2:pos + 2 + ln].decode('utf-8', 'replace')
            pos += 2 + ln
        x, y, w, h = struct.unpack_from('>hhhh', data, pos)
        pos += 8
        if typ == 2:
            pos += 8
        out.append((x, y, w, h, name))
    return out


def read_sheet(data):
    if data[:4] == b'CCTX':
        hdr = data[:28]
        w, h = struct.unpack_from('<II', data, 8)
        raw = zlib.decompress(data[28:])
        img = Image.new('RGBA', (w, h))
        px = []
        for i in range(0, len(raw), 2):
            b0, b1 = raw[i], raw[i + 1]
            px.append(((b1 >> 4) * 17, (b1 & 15) * 17, (b0 >> 4) * 17, (b0 & 15) * 17))
        img.putdata(px)
        return img, hdr
    return Image.open(io.BytesIO(data)).convert('RGBA'), None


def write_sheet(img, hdr):
    if hdr is None:
        buf = io.BytesIO()
        img.save(buf, 'PNG', optimize=True)
        return buf.getvalue()
    raw = bytearray()
    for r, g, b, a in img.getdata():
        raw.append(((b >> 4) << 4) | (a >> 4))
        raw.append(((r >> 4) << 4) | (g >> 4))
    comp = zlib.compress(bytes(raw), 9)
    hdr = bytearray(hdr)
    struct.pack_into('<I', hdr, 24, len(comp))
    return bytes(hdr) + comp


def contact_sheet(img, offs, path, cols=6, cell=220, start=0):
    rows = (len(offs) + cols - 1) // cols
    out = Image.new('RGBA', (cols * cell, rows * (cell + 16)), (40, 40, 40, 255))
    d = ImageDraw.Draw(out)
    for i, (x, y, w, h, _) in enumerate(offs):
        if w <= 0 or h <= 0:
            continue
        spr = img.crop((x, y, x + w, y + h))
        spr.thumbnail((cell - 8, cell - 8))
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 16)
        out.alpha_composite(spr, (cx + 4, cy + 16))
        d.text((cx + 4, cy + 2), f'{start + i} ({w}x{h})', fill=(255, 255, 0, 255))
    out.save(path)
