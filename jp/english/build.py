#!/usr/bin/env python3
"""Build the English JP Zombie Cafe APK.

Inputs (all under jp_english/work/, never modified):
  base_json/            JP data decoded from the toxin-icons build (Versions/3)
  base_strings.bin.mid  JP strings file from the same build
  base_v4.apk           Android-14 compat build (Versions/4), the APK shell

Translation sources, in priority order:
  1. jp_english/tm/*.tsv          hand-authored overrides (jp<TAB>en, or key<TAB>en)
  2. pass-3 crosswalks            EN text copied from the English game where a
                                  matching row exists, otherwise pass-3 drafts

Output: jp_english/out/ZombieCafe_JP_English.apk (+ report.txt)
"""
import csv, json, os, re, shutil, subprocess, sys, textwrap, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))   # jp/english -> repo root
WORK = os.path.join(HERE, 'work')
OUT = os.path.join(HERE, 'out')
XW = os.path.join(REPO, 'jp', 'research', 'pass3_translation', 'crosswalks')
BT = os.path.expanduser('~/Android/Sdk/build-tools/35.0.0')
JP_RE = re.compile(r'[぀-ヿ一-鿿！-～　-〿]')
NON_ASCII = re.compile(r'[^\x00-\x7e]')
PLACEHOLDERS = ['[NUM]', '[RECIPE]', '[CHARA]', '[GENDER]', '[ITEM]', '#', '\\']

report = []


def log(msg):
    report.append(msg)
    print(msg)


def load_tm(name):
    """Load jp_english/tm/<name>*.tsv files as {key: en}."""
    tm = {}
    d = os.path.join(HERE, 'tm')
    for f in sorted(os.listdir(d)):
        if f.startswith(name) and f.endswith('.tsv'):
            for line in open(os.path.join(d, f), encoding='utf-8'):
                line = line.rstrip('\n')
                if not line or line.startswith('#') or '\t' not in line:
                    continue
                k, _, v = line.partition('\t')
                tm[k] = v
    return tm


def load_crosswalk(name):
    return list(csv.DictReader(open(os.path.join(XW, f'translation_crosswalk_{name}.csv'), encoding='utf-8-sig')))


ASCII_MAP = {'\u00e9': 'e', '\u00c9': 'E', '\u00e8': 'e', '\u00ea': 'e', '\u00e0': 'a', '\u00f1': 'n',
             '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-',
             '\u2026': '...', '\u00a0': ' ', '\u2605': '*', '\u2606': '*'}


def asciify(s):
    """The JP fonts only carry ASCII for Latin text (no accents or curly quotes)."""
    return ''.join(ASCII_MAP.get(c, c) for c in s)


def clean(s):
    return asciify(re.sub(r'  +', ' ', s.strip()))


def pick(row):
    """EN-game text wins when the row is a direct match; otherwise the draft."""
    ref, prop = row['english_reference'].strip(), row['proposed_english'].strip()
    if row['match_type'] == 'direct_english_row' and ref:
        return clean(ref)
    return clean(prop) if prop else None


def placeholders_ok(jp, en):
    return all(jp.count(p) == en.count(p) for p in PLACEHOLDERS)


def translate_records(records, fields, xw_rows, tm, label, en_rows=None):
    by_key = {(int(r['record_index']), r['field']): r for r in xw_rows}
    by_text = {}
    for r in xw_rows:
        v = pick(r)
        if v and r['jp_text']:
            by_text.setdefault((r['field'], r['jp_text']), v)
    # Same character in the EN game (same slot, same translated name): copy its
    # text verbatim, and reuse that copy for any other row with identical JP text.
    en_copy, learned = {}, {}
    if en_rows:
        for i, rec in enumerate(records[:len(en_rows)]):
            name = tm.get(f'{i}:Name') or tm.get(rec['Name']) or (pick(by_key[(i, 'Name')]) if (i, 'Name') in by_key else None)
            name = name or by_text.get(('Name', rec['Name'])) or rec['Name']
            if en_rows[i]['Name'].strip() != asciify(name.strip()):
                continue
            for f in fields:
                if f != 'Name' and JP_RE.search(rec.get(f) or '') and en_rows[i].get(f, '').strip():
                    en_copy[(i, f)] = clean(en_rows[i][f])
                    learned.setdefault((f, rec[f]), en_copy[(i, f)])
    missing = {}
    for i, rec in enumerate(records):
        for f in fields:
            jp = rec.get(f) or ''
            if not NON_ASCII.search(jp) and f'{i}:{f}' not in tm:
                continue
            en = en_copy.get((i, f)) or tm.get(f'{i}:{f}') or learned.get((f, jp)) or tm.get(jp)
            if en is None and (i, f) in by_key:
                en = pick(by_key[(i, f)])
            if en is None:
                en = by_text.get((f, jp))
            if en is None:
                missing.setdefault(f, set()).add(jp)
                continue
            if not placeholders_ok(jp, en):
                log(f'  !! {label}[{i}].{f} placeholder mismatch, kept JP: {jp!r} -> {en!r}')
                continue
            if label == 'furnitureData' and f == 'Name' and en.startswith('Ampoule'):
                en = en.replace('Stamina', 'Energy')
            rec[f] = asciify(en)
    for f, s in missing.items():
        log(f'  {label}.{f}: {len(s)} unique JP strings still untranslated')
    return missing


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'json'))
    os.makedirs(os.path.join(OUT, 'bin'))
    todo = {}
    datasets = {}

    # --- food / furniture / characters ---------------------------------
    for fname, xw, fields in [
        ('foodData', 'food', ['Name']),
        ('furnitureData', 'furniture', ['Name', 'Description']),
        ('characterData', 'characters', ['Name', 'HumanDescription', 'ZombieDescription']),
    ]:
        recs = json.load(open(os.path.join(WORK, 'base_json', f'{fname}.bin.mid.json'), encoding='utf-8'))
        en_rows = json.load(open(os.path.join(WORK, 'en_char_vanilla.json'), encoding='utf-8')) if fname == 'characterData' else None
        todo[fname] = translate_records(recs, fields, load_crosswalk(xw), load_tm(xw), fname, en_rows)
        if fname == 'characterData':
            # The zombie/customer bio box wraps per character (JP style) at 13-14
            # half-width cells, splitting English words; pre-wrap at word boundaries.
            for rec in recs:
                for f in ('HumanDescription', 'ZombieDescription'):
                    if rec[f] and not NON_ASCII.search(rec[f]):
                        rec[f] = '\n'.join(textwrap.wrap(rec[f], 13))
        datasets[fname] = recs

    # --- quests (template text shared by many records) ------------------
    quests = json.load(open(os.path.join(WORK, 'base_json', 'quest.bin.mid.json'), encoding='utf-8'))
    qtm = {r['jp_text']: clean(r['proposed_english']) for r in load_crosswalk('quests') if r['proposed_english'].strip()}
    qtm.update(load_tm('quests'))
    qmiss = set()
    for q in quests:
        en = qtm.get(q['Text'])
        if en and placeholders_ok(q['Text'], en):
            q['Text'] = asciify(en)
        elif JP_RE.search(q['Text']):
            qmiss.add(q['Text'])
    log(f'  quest.Text: {len(qmiss)} templates untranslated')
    todo['quest'] = {'Text': qmiss}
    datasets['quest'] = quests

    # --- owner-approved balance overrides (jp/balance/overrides/*.csv) ---
    sys.path.insert(0, os.path.join(REPO, 'jp', 'balance'))
    import apply_overrides
    applied = apply_overrides.apply_all(datasets, log)
    with open(os.path.join(OUT, 'balance_applied.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, ['source', 'file', 'record_index', 'name', 'field', 'old', 'new', 'note'])
        w.writeheader()
        w.writerows(applied)
    for fname, recs in datasets.items():
        json.dump(recs, open(os.path.join(OUT, 'json', f'{fname}.bin.mid.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)

    # --- pack the JSON with the byte-identical JP codecs ---------------
    subprocess.run([os.path.join(WORK, 'rmgr'), '-m', 'pack', '-jp', '-i', os.path.join(OUT, 'json'),
                    '-o', os.path.join(OUT, 'bin')], check=True, stdout=subprocess.DEVNULL)

    # --- strings.bin.mid: index-addressed, newline-joined --------------
    lines = open(os.path.join(WORK, 'base_strings.bin.mid'), encoding='utf-8').read().split('\n')
    stm = load_tm('strings')
    xrows = {int(r['record_index']): r for r in load_crosswalk('strings_and_html')
             if r['source_file'].endswith('strings.bin.mid')}
    new, smiss = list(lines), []
    for i, jp in enumerate(lines):
        if not JP_RE.search(jp):
            continue
        en = stm.get(str(i))
        if en is None and i in xrows:
            en = xrows[i]['proposed_english'].strip() or None
        if en is None:
            smiss.append(i)
            continue
        if not placeholders_ok(jp, en):
            log(f'  !! strings[{i}] placeholder mismatch, kept JP: {jp!r} -> {en!r}')
            continue
        new[i] = asciify(en)
    assert len(new) == len(lines)
    log(f'  strings: {len(smiss)} lines untranslated')
    todo['strings'] = {'lines': set(map(str, smiss))}
    open(os.path.join(OUT, 'bin', 'strings.bin.mid'), 'w', encoding='utf-8', newline='').write('\n'.join(new))

    # --- remaining-work dump -------------------------------------------
    with open(os.path.join(OUT, 'untranslated.tsv'), 'w', encoding='utf-8') as f:
        for k, fields in todo.items():
            for fld, s in fields.items():
                for t in sorted(s):
                    f.write(f'{k}\t{fld}\t{t}\n')

    # --- assemble APK from the v4 shell --------------------------------
    replace = {f'assets/data/{n}': open(os.path.join(OUT, 'bin', n), 'rb').read() for n in os.listdir(os.path.join(OUT, 'bin'))}
    for extra in (load_extra_files()):
        replace[extra[0]] = extra[1]
    src = zipfile.ZipFile(os.path.join(WORK, 'base_v4.apk'))
    unsigned = os.path.join(OUT, 'unsigned.apk')
    with zipfile.ZipFile(unsigned, 'w') as out:
        for info in src.infolist():
            if info.filename.startswith('META-INF/'):
                continue
            data = replace.pop(info.filename, None)
            if data is None:
                data = src.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type, zi.external_attr = info.compress_type, info.external_attr
            out.writestr(zi, data)
    assert not replace, f'files not in base APK: {list(replace)}'
    aligned = os.path.join(OUT, 'aligned.apk')
    final = os.path.join(OUT, 'ZombieCafe_JP_English.apk')
    subprocess.run([f'{BT}/zipalign', '-p', '-f', '4', unsigned, aligned], check=True)
    subprocess.run([f'{BT}/apksigner', 'sign', '--ks', os.path.join(REPO, 'debug.keystore'), '--ks-key-alias', 'alias_name',
                    '--ks-pass', 'pass:zombiecafe', '--out', final, aligned], check=True)
    os.remove(unsigned); os.remove(aligned)
    log(f'built {final}')
    open(os.path.join(OUT, 'report.txt'), 'w').write('\n'.join(report) + '\n')


def load_extra_files():
    """Patched non-data files (native lib, dex, html) produced by the other
    jp_english scripts land in work/patched/<apk path>."""
    root = os.path.join(WORK, 'patched')
    out = []
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            out.append((os.path.relpath(p, root).replace(os.sep, '/'), open(p, 'rb').read()))
    return out


if __name__ == '__main__':
    main()
