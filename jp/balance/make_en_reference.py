#!/usr/bin/env python3
"""Build the English-game balance reference: VANILLA (original Capcom data) vs the
owner's shipped v1.1.0 values, one row per dish / character.

Sources (all reproducible, nothing hand-copied):
  vanilla  = git e6e654fe:src/assets/data/*.bin.mid  ("Adding unpacked APKs",
             Airyzz 2023-06-19: the original Capcom EN binaries), decoded with
             the repo's own codec (jp/english/work/rmgr).
  v1.1     = src/assets/data/*.bin.mid.json (working tree). Verified 2026-09-26
             to be value-identical to the shipped ZombieCafe-v1.1.0-Release.apk.

Airyzz's only data edits before the owner's work: 3 characters appended
(idx 216-218: 2 Maids + Lieutenant Colonel, ported from JP), 3 Cost tweaks,
and the cash->Toxin shop rows. Food was untouched.

Output: jp/balance/reference/en_food_vanilla_vs_v11.csv,
        jp/balance/reference/en_characters_vanilla_vs_v11.csv
"""
import csv
import json
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RMGR = os.path.join(REPO, 'jp', 'english', 'work', 'rmgr')
OUT = os.path.join(HERE, 'reference')
VANILLA_COMMIT = 'e6e654fe'


def vanilla(name):
    with tempfile.TemporaryDirectory() as t:
        os.makedirs(os.path.join(t, 'bin'))
        os.makedirs(os.path.join(t, 'json'))
        blob = subprocess.run(['git', '-C', REPO, 'show', f'{VANILLA_COMMIT}:src/assets/data/{name}.bin.mid'],
                              check=True, capture_output=True).stdout
        open(os.path.join(t, 'bin', f'{name}.bin.mid'), 'wb').write(blob)
        subprocess.run([RMGR, '-m', 'unpack', '-i', os.path.join(t, 'bin'), '-o', os.path.join(t, 'json')],
                       capture_output=True)
        return json.load(open(os.path.join(t, 'json', f'{name}.bin.mid.json'), encoding='utf-8'))


def current(name):
    return json.load(open(os.path.join(REPO, 'src', 'assets', 'data', f'{name}.bin.mid.json'), encoding='utf-8'))


def food_metrics(f):
    rev = f['Servings'] * f['PricePerSeving']
    t = max(f['CookTimeMinutes'], 1)
    return rev, rev - f['Price'], round((rev - f['Price']) / t, 3), round(f['ExperiencePoints'] / t, 4)


def char_class(c):
    if c['U14'] == 1:
        return 'playable_chef'
    if c['Cost'] > 0:
        return 'worker_toxin' if c['PurchaseWithToxin'] else 'worker_cash'
    return 'free_or_enemy'


def write(path, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'{os.path.relpath(path, REPO)}: {len(rows)} rows')


def main():
    os.makedirs(OUT, exist_ok=True)

    v, c = vanilla('foodData'), current('foodData')
    rows = []
    for i, (a, b) in enumerate(zip(v, c)):
        va, vb = food_metrics(a), food_metrics(b)
        rows.append({'index': i, 'name': b['Name'], 'image_id': b['ImageID'], 'unlock_level': b['UnlockLevel'],
                     'changed': a != b,
                     'cost_vanilla': a['Price'], 'cost_v11': b['Price'],
                     'servings_vanilla': a['Servings'], 'servings_v11': b['Servings'],
                     'pps_vanilla': a['PricePerSeving'], 'pps_v11': b['PricePerSeving'],
                     'cook_min_vanilla': a['CookTimeMinutes'], 'cook_min_v11': b['CookTimeMinutes'],
                     'xp_vanilla': a['ExperiencePoints'], 'xp_v11': b['ExperiencePoints'],
                     'profit_vanilla': va[1], 'profit_v11': vb[1],
                     'profit_per_min_vanilla': va[2], 'profit_per_min_v11': vb[2],
                     'xp_per_min_vanilla': va[3], 'xp_per_min_v11': vb[3]})
    write(os.path.join(OUT, 'en_food_vanilla_vs_v11.csv'), rows)

    v, c = vanilla('characterData'), current('characterData')
    fields = ['Cost', 'Energy', 'Speed', 'AttackStrength', 'TipRating', 'TipMultiplier',
              'CookSpeedBonus', 'RegenBoost', 'CookXPBonus', 'CafeLevelRequired', 'U10']
    rows = []
    for i, b in enumerate(c):
        a = v[i] if i < len(v) else None
        row = {'index': i, 'name': b['Name'], 'class': char_class(b),
               'art': f"{b['CharacterArtStringHead']}/{b['CharacterArtString']}",
               'currency': 'toxin' if b['PurchaseWithToxin'] else 'cash',
               'origin': 'vanilla' if a else 'added_by_airyzz(from JP)',
               'changed': bool(a) and any(a[k] != b[k] for k in fields)}
        for k in fields:
            row[f'{k}_vanilla'] = round(a[k], 3) if a and isinstance(a[k], float) else (a[k] if a else '')
            row[f'{k}_v11'] = round(b[k], 3) if isinstance(b[k], float) else b[k]
        rows.append(row)
    write(os.path.join(OUT, 'en_characters_vanilla_vs_v11.csv'), rows)


if __name__ == '__main__':
    main()
