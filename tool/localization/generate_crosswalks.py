#!/usr/bin/env python3
"""Regenerate JP->EN translation crosswalk CSVs for Zombie Cafe JP 1.7.0.

Reads the JP binary data files (decoded in-process; schemas mirror
tool/file_types/*_jp.go), the English revival JSON data, and optional
translation-memory CSVs (earlier crosswalk files whose proposed_english
columns have been filled in), then emits fresh crosswalk CSVs:

    translation_crosswalk_food.csv
    translation_crosswalk_characters.csv
    translation_crosswalk_furniture.csv
    translation_crosswalk_strings_and_html.csv
    crosswalk_stats.json

Read-only against every input. Typical use:

    python3 tool/localization/generate_crosswalks.py \
        --jp-data   /scratch/jp_apk_extract/assets/data \
        --jp-images /scratch/jp_apk_extract/assets/images \
        --en-data   src/assets/data \
        --tm jp/research/pass1_inventory_schema/translation_crosswalk_food.csv \
        --tm jp/research/pass1_inventory_schema/translation_crosswalk_characters.csv \
        --tm jp/research/pass1_inventory_schema/translation_crosswalk_furniture.csv \
        --tm jp/research/pass1_inventory_schema/translation_crosswalk_strings_and_html.csv \
        --out jp/research/pass2_codecs_quests/crosswalks
"""
import argparse
import collections
import csv
import difflib
import json
import os
import re
import struct

CSV_HDR = ['source_file', 'record_index', 'field', 'jp_text', 'english_reference',
           'proposed_english', 'match_type', 'confidence', 'notes']

QUEST_CSV_HDR = ['source_file', 'template_id', 'first_record_index', 'usage_count',
                 'field', 'jp_text', 'literal_note', 'proposed_english',
                 'placeholders', 'placeholder_check', 'confidence', 'review_note']

# Placeholder tokens that must survive translation with identical multiplicity
# per line. Mirrors stringsJPPlaceholderTokens in tool/file_types/strings_jp.go
# ('#' is the engine's number slot, '\' its line-break escape) — keep in sync.
PLACEHOLDER_TOKENS = ['[NUM]', '[RECIPE]', '[CHARA]', '[GENDER]', '[ITEM]', '#', '\\']

# Piecewise JP->EN line-offset map for strings.bin.mid vs strings_google.bin.mid.
# Boundaries 0-316 verified bilingually in pass 1; every remaining boundary
# (including the former "drift zones" 316-357 / 431-519 / 636-661) verified
# line-by-line in pass 3 (2026-07-11, jp/research/pass3_translation/
# strings_drift_resolution.md). offset None = JP-added line with no EN partner
# (translation comes from TM). 'medium' rows keep proposed_english empty so a
# crafted translation from TM is used instead of the raw EN reference.
# (start, end_exclusive, offset_or_None, confidence, note)
STRING_SEGMENTS = [
    (0,   49,  0,    'high',   ''),
    (49,  50,  0,    'medium', 'service URL (Beeline more-games) — do not blind-copy the EN URL'),
    (50,  317, 0,    'high',   ''),
    (317, 318, None, 'medium', 'JP-added: Close button label'),
    (318, 322, -1,   'high',   ''),
    (322, 323, None, 'medium', 'JP-added: short "not enough Toxin" variant'),
    (323, 358, -2,   'high',   ''),
    (358, 435, 2,    'high',   ''),
    (435, 436, None, 'medium', 'JP-added: short "not enough cash" variant (no store pitch)'),
    (436, 466, 1,    'high',   ''),
    (466, 467, 1,    'medium', 'EN slot scolds clock-cheating; JP is generic overwork — crafted EN in TM'),
    (467, 468, 1,    'high',   ''),
    (468, 470, 1,    'medium', 'billing text: EN references iTunes/App Store, JP build bills Google Play'),
    (470, 472, 1,    'high',   ''),
    (472, 475, 1,    'medium', 'xp-bonus fragment group: JP composes value-first — crafted EN, runtime-verify'),
    (475, 512, 1,    'high',   ''),
    (512, 514, None, 'medium', 'JP-added: stat labels (Stamina/Regen) on the zombie card'),
    (514, 515, -1,   'medium', 'JP shows ??? where EN shows DEFEAT TO UNLOCK — keep ???'),
    (515, 524, -1,   'high',   ''),
    (524, 525, -1,   'medium', 'service URL (bij-games ad redirect) — dead service'),
    (525, 549, -1,   'high',   ''),
    (549, 550, -1,   'medium', 'share message; JP original mis-links to Smurfs Village JP — see resolution doc'),
    (550, 558, -1,   'high',   ''),
    (558, 559, -1,   'medium', 'share message; JP original mis-links to Smurfs Village JP — see resolution doc'),
    (559, 632, -1,   'high',   ''),
    (632, 639, 3,    'high',   ''),
    (639, 641, 3,    'medium', 'reopen-café split pair: value position uncertain — crafted EN, runtime-verify'),
    (641, 645, None, 'medium', 'JP-added: prize-draw rarity tiers (Normal/High Normal/Rare/Super Rare)'),
    (645, 651, -1,   'high',   ''),
    (651, 654, 0,    'high',   ''),
    (654, 662, None, 'medium', 'JP-added: Zombie Dojo move system + event roulette'),
]
JP_ONLY_STRINGS_START = 662
SPLIT_STRING_GROUPS = [
    (318, 319), (451, 452, 453, 454, 455), (472, 473, 474), (475, 476, 477),
    (487, 488), (503, 504), (639, 640), (668, 669), (671, 672), (684, 685),
    (693, 694),
]


def read_bytes(path):
    with open(path, 'rb') as fh:
        return fh.read()


def read_lines(path):
    return read_bytes(path).decode('utf-8').split('\n')


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


class Reader:
    def __init__(self, data):
        self.d = data
        self.o = 0

    def bytes(self, n):
        b = self.d[self.o:self.o + n]
        if len(b) != n:
            raise EOFError(f'wanted {n} bytes at offset {self.o}')
        self.o += n
        return b

    def u8(self):
        return self.bytes(1)[0]

    def i16(self):
        return struct.unpack('>h', self.bytes(2))[0]

    def i32(self):
        return struct.unpack('>i', self.bytes(4))[0]

    def f32(self):
        return struct.unpack('<f', self.bytes(4))[0]

    def s(self):
        return self.bytes(self.i16()).decode('utf-8')

    def expect_eof(self, what):
        if self.o != len(self.d):
            raise ValueError(f'{what}: {len(self.d) - self.o} trailing bytes')


def read_jp_food(path):
    r = Reader(read_bytes(path))
    out = []
    for _ in range(r.u8()):
        out.append(dict(Name=r.s(), Price=r.i16(), UnlockLevel=r.u8(),
                        CookTimeMinutes=r.i16(), Servings=r.i16(),
                        PricePerServing=r.i16(), ExperiencePoints=r.i16(),
                        ImageID=r.i16(), U7=r.u8(), U8=r.u8()))
    r.expect_eof('foodData')
    return out


def read_jp_characters(path):
    r = Reader(read_bytes(path))
    out = []
    for _ in range(r.i16()):
        c = dict(CafeLevelRequired=r.u8(), U2=r.u8(), U3=r.u8(),
                 Name=r.s(), Category=r.s(), CharacterArtString=r.s(), U4=r.u8(),
                 Energy=r.i32(), Speed=r.i16(), AttackStrength=r.i16(),
                 TipRating=r.i16(), U9=r.i16(), U10=r.i16(), U11=r.i16(),
                 U12=r.i16(), IsFemale=r.u8(), Cost=r.i32(),
                 PurchaseWithToxin=r.u8(), PlayableFlag=r.u8(),
                 CookSpeedBonus=r.f32(), TipMultiplier=r.i32(),
                 U19=r.f32(), U20=r.f32(), U21=r.u8(), U22=r.i16(), U23=r.f32(),
                 HumanDescription=r.s(), ZombieDescription=r.s())
        out.append(c)
    r.expect_eof('characterData')
    return out


def read_jp_furniture(path):
    r = Reader(read_bytes(path))
    out = []
    for _ in range(r.i32()):
        f = dict(UnlockLevel=r.u8(), Name=r.s(), Price=r.i32(),
                 PurchaseWithToxin=r.u8(), SizeX=r.u8(), SizeY=r.u8(),
                 ImageIndexNorth=r.i16(), ImageIndexEast=r.i16(),
                 ImageIndexSouth=r.i16(), ImageIndexWest=r.i16(),
                 Type=r.u8(), Category=r.u8(), Color=list(r.bytes(4)),
                 MoneyPerHour=r.i16(), MaximumMoney=r.i16(), UMid=r.i32(),
                 RatingBonus=r.f32(), BuyMoneyAmount=r.i32(),
                 ImagePackIndex=r.u8(), StoveSpeedMult=r.f32(),
                 Description=r.s(), ExperiencePoints=r.f32(),
                 IsAvailableInStore=r.u8(), UTailFloat1=r.f32(),
                 UTailInt=r.i16(), UTailFloat2=r.f32())
        out.append(f)
    r.expect_eof('furnitureData')
    return out


def read_jp_quests(path):
    """Decode quest.bin.mid (schema: pass-2 quest_schema_report.md; codec:
    tool/file_types/quest_jp.go). Only the fields the crosswalk needs are kept,
    but the full record is length-validated to exact EOF."""
    r = Reader(read_bytes(path))
    out = []
    for _ in range(r.i16()):
        q = {}
        q['QuestID'] = r.i32()
        q['LevelGate'] = r.u8()
        r.u8()                        # Flag2
        for _ in range(3):            # condition slots
            r.s()
            r.i32()
        r.i16()                       # MidA
        r.i32()                       # PremiseQuestID
        r.u8()                        # MidC
        r.i32()                       # MidD
        r.i16()                       # MidE
        r.i32()                       # TargetRef
        r.i32()                       # GoalAmount
        r.i32()                       # RewardXP
        r.i32()                       # RewardPacked
        r.u8()                        # TailA
        r.i32()                       # TailB
        r.i16()                       # TailC
        q['Text'] = r.s()
        out.append(q)
    r.expect_eof('quest.bin.mid')
    return out


def read_offsets_names(path):
    r = Reader(read_bytes(path))
    t = r.u8()
    names = []
    for _ in range(r.i16()):
        name = r.s() if t == 2 else ''
        r.bytes(8)
        if t == 2:
            r.bytes(8)
        names.append(name)
    return names


def load_tm(paths):
    """Translation memory: (source_file, field, jp_text) -> full CSV row dict.

    Later --tm files win on key collisions, so pass overlays last. A filled
    proposed_english is never discarded by regeneration: it is carried into
    the fresh crosswalk wherever the auto-generated cell is empty."""
    tm = {}
    for path in paths:
        with open(path, newline='', encoding='utf-8-sig') as fh:
            for row in csv.DictReader(fh):
                proposed = (row.get('proposed_english') or '').strip()
                if proposed:
                    key = (row['source_file'], row['field'], row['jp_text'])
                    tm[key] = row
                    # Distinct records sharing one JP name (e.g. the two
                    # ヒッピーのポスター rows) also get a per-row key so their
                    # per-row EN values survive regeneration.
                    ri = (row.get('record_index') or '').strip()
                    if ri:
                        tm[key + (ri,)] = row
    return tm


def tm_lookup(tm, source_file, field, jp_text, record_index=None):
    row = None
    if record_index is not None:
        row = tm.get((source_file, field, jp_text, str(record_index)))
    if row is None:
        row = tm.get((source_file, field, jp_text))
    return (row.get('proposed_english') or '').strip() if row else ''


def validate_placeholders(jp_text, english):
    """Return '' when every placeholder token keeps its multiplicity, else a
    description of the mismatches. Mirrors ValidateStringsJPReplacement in
    tool/file_types/strings_jp.go."""
    bad = []
    for token in PLACEHOLDER_TOKENS:
        j, e = jp_text.count(token), english.count(token)
        if j != e:
            bad.append(f'{token} {j}->{e}')
    return '; '.join(bad)


def write_csv(path, rows, hdr=CSV_HDR):
    with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(rows)


def apply_tm(tm, rows, tm_override=None):
    """Fill empty proposed_english cells from translation memory. Entries in
    tm_override (curated, human-reviewed overlays) also *replace* a non-empty
    auto-derived proposal — regular TM never does."""
    filled = 0
    for row in rows:
        if tm_override:
            hit = tm_lookup(tm_override, row[0], row[2], row[3], row[1])
            if hit:
                if row[5] and row[5] != hit:
                    row[8] = (row[8] + '; ' if row[8] else '') + \
                        f'auto proposal {row[5]!r} replaced by reviewed override'
                elif not row[5]:
                    row[8] = (row[8] + '; ' if row[8] else '') + 'proposed carried from TM'
                if row[5] != hit:
                    filled += 1
                row[5] = hit
                continue
        if not row[5]:
            hit = tm_lookup(tm, row[0], row[2], row[3], row[1])
            if hit:
                row[5] = hit
                row[8] = (row[8] + '; ' if row[8] else '') + 'proposed carried from TM'
                filled += 1
    return filled


def flag_placeholder_mismatches(rows):
    """Append a PLACEHOLDER note to any row whose proposed_english breaks the
    token contract; returns the number of flagged rows."""
    flagged = 0
    for row in rows:
        if row[5]:
            bad = validate_placeholders(row[3], row[5])
            if bad:
                row[8] = (row[8] + '; ' if row[8] else '') + f'PLACEHOLDER MISMATCH: {bad}'
                flagged += 1
    return flagged


def build_food(jp_food, en_food, tm, tm_override=None):
    en_by_img = {}
    for i, f in enumerate(en_food):
        en_by_img.setdefault(f['ImageID'], (i, f))
    rows, matched = [], 0
    for i, f in enumerate(jp_food):
        m = en_by_img.get(f['ImageID'])
        if m:
            matched += 1
            rows.append(['assets/data/foodData.bin.mid', i, 'Name', f['Name'],
                         m[1]['Name'], m[1]['Name'], 'direct_english_row', 'high',
                         f'ImageID {f["ImageID"]} == EN row {m[0]}'])
        else:
            rows.append(['assets/data/foodData.bin.mid', i, 'Name', f['Name'],
                         '', '', 'jp_only_event', 'low', 'no EN row'])
    filled = apply_tm(tm, rows, tm_override)
    return rows, dict(jp=len(jp_food), en=len(en_food), matched=matched,
                      tm_filled=filled)


def build_characters(jp_chars, en_chars, tm, tm_override=None):
    en_by_key = collections.defaultdict(list)
    for i, c in enumerate(en_chars):
        en_by_key[(c['CharacterArtStringHead'], c['CharacterArtString'])].append(i)
    jp_key_count = collections.Counter(
        (c['Category'], c['CharacterArtString']) for c in jp_chars)
    rows = []
    direct = variant = jp_only = 0
    for i, c in enumerate(jp_chars):
        key = (c['Category'], c['CharacterArtString'])
        en_idxs = en_by_key.get(key, [])
        if en_idxs:
            e = en_chars[en_idxs[0]]
            unique = len(en_idxs) == 1 and jp_key_count[key] == 1
            mt = 'direct_english_row' if unique else 'same_art_or_category'
            conf = 'high' if unique else 'medium'
            direct += unique
            variant += not unique
            note = f'art "{key[0]}/{key[1]}" -> EN row {en_idxs[0]}'
            if not unique:
                note += f' ({jp_key_count[key]} JP rows share this art; qualifier needed)'
            rows.append(['assets/data/characterData.bin.mid', i, 'Name', c['Name'],
                         e['Name'], e['Name'] if unique else '', mt, conf, note])
            for fld in ('HumanDescription', 'ZombieDescription'):
                if c[fld] or e[fld]:
                    rows.append(['assets/data/characterData.bin.mid', i, fld,
                                 c[fld], e[fld], e[fld] if unique else '',
                                 mt, conf, ''])
        else:
            jp_only += 1
            note = f'JP-only; art "{key[0]}/{key[1]}"'
            mt = 'jp_only_event' if c['Name'] else 'needs_human_review'
            rows.append(['assets/data/characterData.bin.mid', i, 'Name',
                         c['Name'], '', '', mt, 'low', note])
            for fld in ('HumanDescription', 'ZombieDescription'):
                if c[fld]:
                    rows.append(['assets/data/characterData.bin.mid', i, fld,
                                 c[fld], '', '', 'jp_only_event', 'low', ''])
    filled = apply_tm(tm, rows, tm_override)
    return rows, dict(jp=len(jp_chars), en=len(en_chars), direct=direct,
                      variant=variant, jp_only=jp_only, tm_filled=filled)


def build_furniture(jp_fur, en_fur, offsets_by_pack, tm, tm_override=None):
    def norm(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())

    def devname(f):
        pack = offsets_by_pack.get(f['ImagePackIndex'])
        idx = f['ImageIndexNorth']
        if pack and 0 <= idx < len(pack):
            return re.sub(r'\.png$', '', re.sub(r'^\d+-', '', pack[idx]))
        return ''

    en_by_norm = {}
    for i, f in enumerate(en_fur):
        en_by_norm.setdefault(norm(f['Name']), (i, f))
    en_keys = list(en_by_norm)

    rows = []
    exact = fuzzy = jp_only = 0
    for i, f in enumerate(jp_fur):
        dn = devname(f)
        dn_norm = norm(dn)
        hit, ratio = en_by_norm.get(dn_norm), 1.0
        if not hit and dn_norm:
            best = difflib.get_close_matches(dn_norm, en_keys, n=1, cutoff=0.75)
            if best:
                hit = en_by_norm[best[0]]
                ratio = difflib.SequenceMatcher(None, dn_norm, best[0]).ratio()
        if hit:
            strong = ratio >= 0.87
            exact += ratio == 1.0
            fuzzy += ratio < 1.0
            conf = 'high' if ratio == 1.0 else ('medium' if strong else 'low')
            mt = 'direct_english_row' if strong else 'same_art_or_category'
            extra = '' if ratio == 1.0 else (
                f' (fuzzy {ratio:.2f}' + ('' if strong else ' — verify, may be wrong item') + ')')
            # Only exact texture-name matches auto-adopt the EN name; fuzzy
            # hits (pass-3 review found several wrong items among them) keep
            # the reference visible but leave the proposal to human review/TM.
            rows.append(['assets/data/furnitureData.bin.mid', i, 'Name', f['Name'],
                         hit[1]['Name'], hit[1]['Name'] if ratio == 1.0 else '', mt, conf,
                         f'texture "{dn}" ~ EN row {hit[0]}{extra}'])
            if f['Description'] or hit[1]['Description']:
                rows.append(['assets/data/furnitureData.bin.mid', i, 'Description',
                             f['Description'], hit[1]['Description'],
                             hit[1]['Description'] if conf == 'high' else '',
                             mt, conf, ''])
        else:
            jp_only += 1
            # The dev texture name is a hint, not a proposal: leaving
            # proposed_english empty lets a reviewed TM value fill it.
            rows.append(['assets/data/furnitureData.bin.mid', i, 'Name', f['Name'],
                         '', '', 'jp_only_event' if dn_norm else 'needs_human_review',
                         'low',
                         f'no EN row; dev texture name "{dn}"' if dn_norm
                         else 'no EN row, no texture name'])
            if f['Description']:
                rows.append(['assets/data/furnitureData.bin.mid', i, 'Description',
                             f['Description'], '', '', 'jp_only_event', 'low', ''])
    filled = apply_tm(tm, rows, tm_override)
    return rows, dict(jp=len(jp_fur), en=len(en_fur), exact=exact, fuzzy=fuzzy,
                      jp_only=jp_only, tm_filled=filled)


def build_strings(jp_lines, en_lines, tm, tm_override=None):
    def segment_for(i):
        for start, end, off, conf, note in STRING_SEGMENTS:
            if start <= i < end:
                return off, conf, note
        return None, 'low', 'unmapped index — extend STRING_SEGMENTS'

    split_flagged = {a for group in SPLIT_STRING_GROUPS for a in group}
    rows = []
    paired = jp_added = downgraded = 0
    for i, line in enumerate(jp_lines):
        if i >= JP_ONLY_STRINGS_START:
            note = 'JP-added UI'
            if i in split_flagged:
                note += '; split-string group — translate together'
            rows.append(['assets/data/strings.bin.mid', i, f'line_{i}', line,
                         '', '', 'jp_only_event', 'low', note])
            continue
        off, conf, seg_note = segment_for(i)
        if off is None:
            jp_added += 1
            note = 'JP-added line, no EN partner'
            if seg_note:
                note += f'; {seg_note}'
            if i in split_flagged:
                note += '; split-string group — translate together'
            rows.append(['assets/data/strings.bin.mid', i, f'line_{i}', line,
                         '', '', 'jp_added_ui', conf, note])
            continue
        paired += 1
        j = i + off
        ref = en_lines[j] if 0 <= j < len(en_lines) else ''
        note = f'index-aligned offset {off:+d} (verified pass 3)'
        if seg_note:
            note += f'; {seg_note}'
        if i in split_flagged:
            note += '; split-string group — translate together'
        proposed = ref if conf == 'high' else ''
        # The EN reference is only auto-adopted when it obeys the same
        # placeholder contract the strings writer enforces; otherwise the row
        # needs a crafted translation (from TM) that keeps the JP structure.
        if proposed:
            bad = validate_placeholders(line, proposed)
            if bad:
                proposed = ''
                conf = 'medium'
                downgraded += 1
                note += f'; EN reference breaks placeholder contract ({bad}) — crafted EN required'
        rows.append(['assets/data/strings.bin.mid', i, f'line_{i}', line, ref,
                     proposed, 'index_aligned_verified', conf, note])
    filled = apply_tm(tm, rows, tm_override)
    mismatched = flag_placeholder_mismatches(rows)
    return rows, dict(jp=len(jp_lines), en=len(en_lines), paired=paired,
                      jp_added=jp_added, jp_tail=len(jp_lines) - JP_ONLY_STRINGS_START,
                      contract_downgraded=downgraded, tm_filled=filled,
                      placeholder_mismatches=mismatched)


def build_quests(jp_quests, tm, tm_override=None):
    """One row per unique quest text template. TM rows regenerated from an
    earlier quest crosswalk keep literal_note/confidence/review_note as well
    as the reviewed proposed_english."""
    templates = collections.OrderedDict()
    for q in jp_quests:
        t = q['Text']
        if t not in templates:
            templates[t] = dict(first=q['QuestID'], count=0)
        templates[t]['count'] += 1

    rows = []
    filled = mismatched = 0
    for idx, (jp, info) in enumerate(templates.items()):
        ph = ' '.join(t for t in PLACEHOLDER_TOKENS[:5] for _ in range(jp.count(t)))
        hit = (tm_override or {}).get(('assets/data/quest.bin.mid', 'text', jp)) \
            or tm.get(('assets/data/quest.bin.mid', 'text', jp))
        proposed = (hit.get('proposed_english') or '').strip() if hit else ''
        literal = (hit.get('literal_note') or '') if hit else ''
        conf = (hit.get('confidence') or 'low') if hit else 'low'
        review = (hit.get('review_note') or '') if hit else ''
        if proposed:
            filled += 1
            bad = validate_placeholders(jp, proposed)
            check = 'OK' if not bad else f'MISMATCH: {bad}'
            mismatched += bool(bad)
        else:
            check = 'PENDING'
        rows.append(['assets/data/quest.bin.mid', f'T{idx:02d}', info['first'],
                     info['count'], 'text', jp, literal, proposed,
                     ph or '(none)', check, conf, review])
    return rows, dict(records=len(jp_quests), templates=len(rows),
                      tm_filled=filled, placeholder_mismatches=mismatched)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--jp-data', required=True,
                    help='extracted JP assets/data directory')
    ap.add_argument('--jp-images', default=None,
                    help='extracted JP assets/images directory '
                         '(default: sibling "images" of --jp-data)')
    ap.add_argument('--en-data', required=True,
                    help='EN revival src/assets/data directory (JSON references)')
    ap.add_argument('--tm', action='append', default=[],
                    help='translation-memory CSV (repeatable); filled '
                         'proposed_english cells are carried forward')
    ap.add_argument('--tm-override', action='append', default=[],
                    help='curated TM CSV (repeatable) whose entries also '
                         'replace non-empty auto-derived proposals')
    ap.add_argument('--out', required=True, help='output directory')
    args = ap.parse_args()

    jp_images = args.jp_images or os.path.join(os.path.dirname(
        args.jp_data.rstrip('/')), 'images')
    os.makedirs(args.out, exist_ok=True)

    jp_food = read_jp_food(os.path.join(args.jp_data, 'foodData.bin.mid'))
    jp_chars = read_jp_characters(os.path.join(args.jp_data, 'characterData.bin.mid'))
    jp_fur = read_jp_furniture(os.path.join(args.jp_data, 'furnitureData.bin.mid'))
    jp_quests = read_jp_quests(os.path.join(args.jp_data, 'quest.bin.mid'))
    jp_strings = read_lines(os.path.join(args.jp_data, 'strings.bin.mid'))

    en_food = load_json(os.path.join(args.en_data, 'foodData.bin.mid.json'))
    en_chars = load_json(os.path.join(args.en_data, 'characterData.bin.mid.json'))
    en_fur = load_json(os.path.join(args.en_data, 'furnitureData.bin.mid.json'))
    en_strings = read_lines(os.path.join(args.en_data, 'strings_google.bin.mid'))

    offsets_by_pack = {}
    for pack, name in enumerate(['furnitureOffsets.bin.mid',
                                 'furnitureOffsets2.bin.mid',
                                 'furnitureOffsets3.bin.mid']):
        path = os.path.join(jp_images, name)
        if os.path.exists(path):
            offsets_by_pack[pack] = read_offsets_names(path)

    tm = load_tm(args.tm)
    tm_override = load_tm(args.tm_override)

    stats = {'tm_entries': len(tm)}
    rows, stats['food'] = build_food(jp_food, en_food, tm, tm_override)
    write_csv(os.path.join(args.out, 'translation_crosswalk_food.csv'), rows)
    rows, stats['characters'] = build_characters(jp_chars, en_chars, tm, tm_override)
    write_csv(os.path.join(args.out, 'translation_crosswalk_characters.csv'), rows)
    rows, stats['furniture'] = build_furniture(jp_fur, en_fur, offsets_by_pack, tm, tm_override)
    write_csv(os.path.join(args.out, 'translation_crosswalk_furniture.csv'), rows)
    rows, stats['strings'] = build_strings(jp_strings, en_strings, tm, tm_override)
    write_csv(os.path.join(args.out, 'translation_crosswalk_strings_and_html.csv'), rows)
    rows, stats['quests'] = build_quests(jp_quests, tm, tm_override)
    write_csv(os.path.join(args.out, 'translation_crosswalk_quests.csv'), rows,
              hdr=QUEST_CSV_HDR)

    with open(os.path.join(args.out, 'crosswalk_stats.json'), 'w') as fh:
        json.dump(stats, fh, indent=1)
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
