#!/usr/bin/env python3
"""Replace baked Japanese text in the JP sprite sheets.

Two methods per sprite (see SPECS):
  ('en', en_index)            copy the EN game's sprite (same size, same meaning)
  ('text', box, text, style)  erase the Japanese inside `box` (sprite-relative
                              x0,y0,x1,y1) by row-wise inpainting from the
                              surrounding pixels, then draw English in `style`

Only sprite rectangles listed in SPECS are touched; every other pixel of each
sheet is kept byte-for-byte (re-encoded losslessly). Run with PYTHONPATH=.pylib.
Outputs: work/patched/assets/images/<sheet>, work/contact/patched_<sheet>.png
"""
import os
from PIL import Image, ImageDraw, ImageFont
import sheets

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, 'work')
FONT = '/mnt/c/Windows/Fonts/ariblk.ttf'   # Arial Black: closest to the chunky EN button captions

STYLES = {
    'caption': dict(fill=(255, 255, 255, 255), stroke=(0, 0, 0, 255), sw=3, max=19),  # green action buttons
    'hud':     dict(fill=(255, 255, 255, 255), stroke=(0, 0, 0, 255), sw=2, max=12),  # HUD shortcut icons
    'tab':     dict(fill=(255, 255, 255, 255), stroke=(40, 20, 20, 200), sw=1),  # store tabs
    'tabgold': dict(fill=(255, 230, 60, 255), stroke=(60, 20, 20, 220), sw=1),   # "recommended" tabs (bg from a cleaned tab)
    'red':     dict(fill=(230, 20, 20, 255), stroke=(0, 0, 0, 0), sw=0, solid=(0, 0, 0, 255)),  # red text on black box
    'badge':   dict(fill=(255, 255, 255, 255), stroke=(150, 0, 0, 255), sw=2),
    'yellow':  dict(fill=(255, 235, 40, 255), stroke=(0, 0, 0, 255), sw=3, max=20),
    'signred': dict(fill=(170, 20, 20, 255), stroke=(255, 255, 255, 255), sw=2, patch=True),
    'wood':    dict(fill=(255, 255, 255, 255), stroke=(50, 25, 10, 255), sw=3, patch=True),
    'white':   dict(fill=(255, 255, 255, 255), stroke=(40, 20, 20, 255), sw=3),
    'blue':    dict(fill=(90, 170, 240, 255), stroke=(255, 255, 255, 255), sw=2, clear=True),
    'green':   dict(fill=(60, 180, 60, 255), stroke=(255, 255, 255, 255), sw=2, clear=True),
    'redc':    dict(fill=(215, 30, 30, 255), stroke=(255, 255, 255, 255), sw=2, clear=True),
    'purple':  dict(fill=(140, 90, 200, 255), stroke=(255, 255, 255, 255), sw=2, clear=True),
    'orange':  dict(fill=(230, 120, 30, 255), stroke=(255, 255, 255, 255), sw=2, clear=True),
    'gold':    dict(fill=(255, 200, 40, 255), stroke=(90, 40, 0, 255), sw=2, clear=True),
    'burst':   dict(fill=(255, 235, 40, 255), stroke=(170, 0, 0, 255), sw=3, clear=True),   # replaces stylised JP lettering
}

TAB = lambda w, h: (7, 7, w - 7, h - 7)

# ingameUiImages.png ------------------------------------------------------------
HUD = {
    14: ('en', 14), 15: ('en', 15), 43: ('en', 43), 44: ('en', 44), 45: ('en', 45), 53: ('en', 53),
    121: ('en', 113), 122: ('en', 114), 123: ('en', 115), 128: ('en', 120), 129: ('en', 121),
    131: ('en', 123), 137: ('en', 129), 170: ('en', 161), 176: ('en', 167), 185: ('en', 176),
    # store tabs (red = unselected, green = selected)
    20: ('text', TAB(108, 54), 'CAFE 1', 'tab'), 47: ('text', TAB(108, 54), 'CAFE 1', 'tab'),
    21: ('text', TAB(108, 54), 'TABLES', 'tab'), 48: ('text', TAB(108, 54), 'TABLES', 'tab'),
    22: ('text', TAB(108, 54), 'KITCHEN', 'tab'), 49: ('text', TAB(108, 54), 'KITCHEN', 'tab'),
    23: ('text', TAB(108, 54), 'FLOORS', 'tab'), 50: ('text', TAB(108, 54), 'FLOORS', 'tab'),
    79: ('text', TAB(108, 54), 'SPECIAL', 'tab'), 80: ('text', TAB(108, 54), 'SPECIAL', 'tab'),
    81: ('text', TAB(108, 54), 'CAFE 2', 'tab'), 82: ('text', TAB(108, 54), 'CAFE 2', 'tab'),
    125: ('text', TAB(108, 54), 'FEATURED', 'tabgold', 20), 126: ('text', TAB(108, 54), 'FEATURED', 'tabgold', 47),
    218: ('text', TAB(108, 54), 'AMPOULES', 'tab'), 219: ('text', TAB(108, 54), 'AMPOULES', 'tab'),
    51: ('text', (6, 6, 137, 70), 'EATING', 'red'),
    # green action buttons: caption strip along the bottom
    216: ('text', (0, 58, 104, 88), 'STORE', 'caption'),
    223: ('text', (0, 62, 103, 93), 'POWER UP', 'caption'),
    224: ('text', (0, 62, 103, 93), 'SELECT', 'caption'),
    231: ('text', (0, 62, 103, 93), 'PLANT', 'caption'),
    232: ('text', (0, 62, 103, 93), 'PLANT', 'caption'),
    233: ('text', (0, 62, 103, 93), 'HARVEST', 'caption'),
    234: ('text', (0, 62, 103, 93), 'FEED', 'caption'),
    # HUD shortcut icons: caption under the icon
    241: ('text', (0, 46, 69, 71), 'FREE', 'hud'),
    245: ('text', (0, 46, 69, 71), 'GACHA', 'hud'),
    246: ('text', (0, 46, 69, 71), 'MAP', 'hud'),
    247: ('text', (0, 46, 69, 71), 'RECIPES', 'hud'),
    248: ('text', (0, 46, 69, 71), 'STORE', 'hud'),
    249: ('text', (0, 46, 69, 71), 'ZOMBIES', 'hud'),
    250: ('text', (0, 46, 69, 71), 'ORDERS', 'hud'),
    251: ('text', (0, 46, 69, 71), 'RATING', 'hud'),
    252: ('text', (0, 46, 69, 71), 'ROULETTE', 'hud'),
    253: ('text', (0, 46, 69, 71), 'COLLECTION', 'hud'),
    254: ('text', (0, 46, 69, 71), 'HQ', 'hud'),
    255: ('text', (0, 46, 69, 71), 'STORAGE', 'hud'),
    256: ('text', (0, 46, 69, 71), 'LOCKER', 'hud'),
    257: ('text', (0, 50, 69, 77), 'EVENT', 'hud'),
    258: ('text', (0, 46, 69, 71), 'DELIVER', 'hud'),
    # badges / banners
    239: ('text', (36, 3, 236, 39), 'SACRIFICE XP UP!', 'badge'),
    242: ('text', (2, 0, 98, 40), 'SPECIAL OFFER', 'badge'),
    270: ('text', (0, 0, 66, 55), 'ASSAULT', 'burst'),
    271: ('text', (0, 0, 83, 53), 'MINI ASSAULT', 'burst'),
    273: ('text', (0, 0, 90, 62), 'BIG ASSAULT', 'burst'),
    274: ('text', (0, 52, 82, 82), 'GACHA', 'caption'),
    275: ('text', (36, 3, 212, 39), 'SOUL REGEN UP!', 'badge'),
    277: ('text', (0, 0, 81, 23), '1ST FREE', 'burst'),
    280: ('text', (0, 64, 95, 95), 'BOSS+', 'yellow'),
    281: ('text', (0, 64, 95, 95), 'AMPOULES', 'yellow'),
    282: ('text', (0, 64, 95, 95), 'SPECIAL', 'yellow'),
    288: ('text', (0, 64, 115, 95), 'SURVIVAL', 'yellow'),
}

ZC = {
    9: ('text', (22, 10, 372, 66), 'ZOMBIE COLLECTION', 'signred'),
    11: ('text', (12, 10, 348, 66), 'MEAT LOCKER', 'signred'),
    15: ('text', (10, 8, 112, 48), 'BOUGHT', 'redc'),
    17: ('text', (18, 36, 318, 108), 'ZOMBIE DOJO', 'wood'),
    18: ('text', (0, 0, 70, 43), 'BASIC', 'blue'),
    19: ('text', (0, 0, 72, 43), 'MID', 'green'),
    20: ('text', (0, 0, 66, 40), 'BIG', 'redc'),
    24: ('text', (14, 55, 152, 112), 'ROULETTE!', 'white'),
    32: ('text', (12, 12, 340, 88), 'FURNITURE ROULETTE', 'white'),
    33: ('text', (0, 0, 70, 43), '3RD\nRATE', 'blue'),
    34: ('text', (0, 0, 69, 42), '2ND\nRATE', 'green'),
    35: ('text', (0, 0, 69, 36), '1ST\nRATE', 'redc'),
    39: ('text', (0, 0, 80, 56), 'RARE', 'gold'),
    45: ('text', (48, 14, 322, 76), 'SACRIFICE KITCHEN', 'white'),
    46: ('text', (30, 28, 190, 100), 'SACRIFICE', 'white'),
    47: ('text', (8, 6, 114, 50), 'OFFERED', 'purple'),
    49: ('text', (26, 26, 128, 128), 'SOUL\nREGEN\nFASTER!', 'white'),
    51: ('text', (0, 0, 410, 52), 'ZOMBIE SURVIVAL', 'white'),
    53: ('text', (0, 0, 82, 69), 'ASSAULT', 'burst'),
    54: ('text', (8, 10, 350, 92), '* SPECIAL OFFER', 'white'),
    56: ('text', (8, 6, 92, 38), 'SOUL', 'white'),
    58: ('text', (0, 0, 97, 48), 'CANNIBAL', 'redc'),
    59: ('text', (8, 6, 118, 38), 'STAMINA', 'white'),
    71: ('multi', [((8, 84, 149, 140), 'BASIC', 'white'), ((8, 146, 149, 174), 'SOUL COST: 1', 'white')]),
    72: ('multi', [((8, 84, 149, 140), 'MEDIUM', 'white'), ((8, 146, 149, 174), 'SOUL COST: 1', 'white')]),
    73: ('multi', [((8, 84, 149, 140), 'EXPERT', 'white'), ((8, 146, 149, 174), 'SOUL COST: 1', 'white')]),
    74: ('multi', [((8, 84, 149, 140), 'MASTER', 'white'), ((8, 146, 149, 174), 'SOUL COST: 1', 'white')]),
    75: ('text', (26, 26, 128, 128), 'BONUS\nPOINTS\nUP!', 'white'),
    86: ('multi', [((8, 84, 149, 140), 'TRUE HELL', 'white'), ((8, 146, 149, 174), 'SOUL COST: 1', 'white')]),
    96: ('text', (26, 26, 128, 128), 'ZOMBIE\nDROPS\nUP!', 'white'),
    98: ('text', (0, 0, 97, 48), 'CANNIBAL', 'green'),
}

MENU = {
    51: ('text', (40, 14, 216, 88), 'TRANSFER', 'white'),
}

SPECS = {
    'ingameUiImages.png': ('ingameUiOffsets.bin.mid', HUD, ('ingameUiImages.png', 'ingameUiOffsets.bin.mid')),
    'zcImages.png': ('zcImagesOffsets.bin.mid', ZC, None),
    'menuimages.png': ('menuOffsets.bin.mid', MENU, None),
}


def is_text(px):
    r, g, b, a = px
    if a < 120:
        return False
    lo, hi = min(r, g, b), max(r, g, b)
    return (lo > 165 and hi - lo < 60) or hi < 70      # white fill or dark outline


def erase(spr, box):
    """Row-wise inpaint: replace text pixels in box with a blend of the nearest
    non-text pixels to the left and right on the same row."""
    x0, y0, x1, y1 = box
    px = spr.load()
    w, h = spr.size
    mask = [[False] * w for _ in range(h)]
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            if is_text(px[x, y]):
                for dy in (-1, 0, 1):          # 1px dilation removes anti-aliased halos
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if y0 <= yy < y1 and x0 <= xx < x1 and 0 <= yy < h and 0 <= xx < w:
                            mask[yy][xx] = True
    for y in range(max(0, y0), min(h, y1)):
        row = [px[x, y] for x in range(w)]
        for x in range(max(0, x0), min(w, x1)):
            if not mask[y][x]:
                continue
            l = x
            while l >= 0 and mask[y][l]:
                l -= 1
            r = x
            while r < w and mask[y][r]:
                r += 1
            left = row[l] if l >= 0 else (0, 0, 0, 0)
            right = row[r] if r < w else (0, 0, 0, 0)
            if left[3] < 60 or right[3] < 60:
                px[x, y] = left if left[3] >= 60 and x - l <= 2 else right if right[3] >= 60 and r - x <= 2 else (0, 0, 0, 0)
                continue
            t = (x - l) / (r - l)
            px[x, y] = tuple(int(left[i] * (1 - t) + right[i] * t) for i in range(4))


def patch(spr, box):
    """Flat fill with the average colour of the pixels just outside the box."""
    x0, y0, x1, y1 = box
    px = spr.load()
    w, h = spr.size
    ring = [px[x, y] for x in range(max(0, x0), min(w, x1)) for y in (y0 - 1, y1) if 0 <= y < h]
    ring += [px[x, y] for y in range(max(0, y0), min(h, y1)) for x in (x0 - 1, x1) if 0 <= x < w]
    ring = [p for p in ring if p[3] > 200] or [(0, 0, 0, 0)]
    avg = tuple(sum(p[i] for p in ring) // len(ring) for i in range(4))
    spr.paste(avg, box)


def clean(spr, box, st):
    if st.get('clear'):
        spr.paste((0, 0, 0, 0), box)
    elif st.get('solid'):
        spr.paste(st['solid'], box)
    elif st.get('patch'):
        patch(spr, box)
    else:
        erase(spr, box)


def draw_text(spr, box, text, style):
    text = text.replace('\\n', '\n')
    st = STYLES[style]
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0 - 2, y1 - y0 - 2
    d = ImageDraw.Draw(spr)
    size = min(bh, st.get('max', 99))
    while size > 6:
        f = ImageFont.truetype(FONT, size)
        l, t, r, b = d.multiline_textbbox((0, 0), text, font=f, stroke_width=st['sw'], align='center', spacing=0)
        if r - l <= bw and b - t <= bh:
            break
        size -= 1
    l, t, r, b = d.multiline_textbbox((0, 0), text, font=f, stroke_width=st['sw'], align='center', spacing=0)
    x = x0 + (x1 - x0 - (r - l)) / 2 - l
    y = y0 + (y1 - y0 - (b - t)) / 2 - t
    d.multiline_text((x, y), text, font=f, fill=st['fill'], stroke_width=st['sw'], stroke_fill=st['stroke'],
                     align='center', spacing=0)


def main():
    en_cache = {}
    for sheet, (offs_name, spec, en_src) in SPECS.items():
        raw = open(os.path.join(W, 'images_jp', sheet), 'rb').read()
        img, hdr = sheets.read_sheet(raw)
        offs = sheets.read_offsets(open(os.path.join(W, 'images_jp', offs_name), 'rb').read())
        if en_src and en_src not in en_cache:
            en_img, _ = sheets.read_sheet(open(os.path.join(W, 'images_en', en_src[0]), 'rb').read())
            en_offs = sheets.read_offsets(open(os.path.join(W, 'images_en', en_src[1]), 'rb').read())
            en_cache[en_src] = (en_img, en_offs)
        en_img, en_offs = en_cache.get(en_src, (None, None))
        cleaned = {}
        for i, action in sorted(spec.items(), key=lambda kv: len(kv[1]) > 4):
            x, y, w, h, _ = offs[i]
            if action[0] == 'en':
                ex, ey, ew, eh, _ = en_offs[action[1]]
                assert (ew, eh) == (w, h), f'{sheet}[{i}] size {w}x{h} != EN[{action[1]}] {ew}x{eh}'
                spr = en_img.crop((ex, ey, ex + ew, ey + eh))
            elif action[0] == 'multi':
                spr = img.crop((x, y, x + w, y + h))
                for box, text, style in action[1]:
                    clean(spr, box, STYLES[style])
                    draw_text(spr, box, text, style)
            else:
                _, box, text, style = action[:4]
                st = STYLES[style]
                if len(action) > 4:                     # background borrowed from an already-cleaned sprite
                    spr = cleaned[action[4]].copy()
                else:
                    spr = img.crop((x, y, x + w, y + h))
                    clean(spr, box, st)
                    cleaned[i] = spr.copy()
                draw_text(spr, box, text, style)
            img.paste(spr, (x, y))
        out = os.path.join(W, 'patched', 'assets', 'images', sheet)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'wb').write(sheets.write_sheet(img, hdr))
        idx = sorted(spec)
        sheets.contact_sheet(img, [offs[i] for i in idx], os.path.join(W, 'contact', f'patched_{sheet}.png'))
        print(f'{sheet}: {len(spec)} sprites replaced')


if __name__ == '__main__':
    main()
