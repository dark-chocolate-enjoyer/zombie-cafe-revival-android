#!/usr/bin/env python3
"""Export the CURRENT built JP data (English names, balance overrides applied)
to review CSVs in jp/balance/snapshots/. Run after `python3 jp/english/build.py`.

These CSVs are the starting point for the owner's review spreadsheets; they
are regenerated, never hand-edited (proposals go in overrides/ instead).
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JP = os.path.dirname(HERE)
OUT_JSON = os.path.join(JP, 'english', 'out', 'json')
BASE_JSON = os.path.join(JP, 'english', 'work', 'base_json')
CURATION = os.path.join(JP, 'research', 'pass4_systems_curation', 'roster_curation_candidates.csv')
SNAP = os.path.join(HERE, 'snapshots')
REF = os.path.join(HERE, 'reference')


def en_reference(name, key):
    """First EN row per join key from reference/en_*_vanilla_vs_v11.csv (run make_en_reference.py)."""
    path = os.path.join(REF, name)
    out = {}
    if os.path.exists(path):
        for r in csv.DictReader(open(path, encoding='utf-8-sig')):
            out.setdefault(key(r), r)
    return out


def load(name, root):
    return json.load(open(os.path.join(root, f'{name}.bin.mid.json'), encoding='utf-8'))


def write(path, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'{os.path.relpath(path, JP)}: {len(rows)} rows')


def role(c):
    if c['PlayableFlag'] == 1:
        return 'playable_chef'
    if c['Category'] == 'enemyChef' or 'Chef' in (c['Name'] or '') and c['Cost'] == 0:
        return 'enemy_or_event_chef'
    if c['Cost'] > 0:
        return 'worker_toxin' if c['PurchaseWithToxin'] else 'worker_cash'
    return 'event_reward_or_customer' if c['Name'] else 'generic_customer'


def main():
    os.makedirs(SNAP, exist_ok=True)

    foods, foods_jp = load('foodData', OUT_JSON), load('foodData', BASE_JSON)
    en_food = en_reference('en_food_vanilla_vs_v11.csv', lambda r: int(r['image_id']))
    rows = []
    for i, (f, j) in enumerate(zip(foods, foods_jp)):
        e = en_food.get(f['ImageID'], {})
        revenue = f['Servings'] * f['PricePerServing']
        mins = max(f['CookTimeMinutes'], 1)
        rows.append({'index': i, 'name': f['Name'], 'jp_name': j['Name'], 'unlock_level': f['UnlockLevel'],
                     'cost_price': f['Price'], 'cook_minutes': f['CookTimeMinutes'], 'servings': f['Servings'],
                     'price_per_serving': f['PricePerServing'], 'xp': f['ExperiencePoints'],
                     'revenue': revenue, 'profit': revenue - f['Price'],
                     'profit_per_min': round((revenue - f['Price']) / mins, 2),
                     'xp_per_min': round(f['ExperiencePoints'] / mins, 3),
                     'image_id': f['ImageID'], 'U7': f['U7'], 'U8': f['U8'],
                     'en_match': e.get('name', ''), 'en_row': e.get('index', ''),
                     'jp_equals_en_vanilla': bool(e) and all(
                         str(f[a]) == e[b] for a, b in [('Price', 'cost_vanilla'), ('Servings', 'servings_vanilla'),
                                                        ('PricePerServing', 'pps_vanilla'),
                                                        ('CookTimeMinutes', 'cook_min_vanilla'),
                                                        ('ExperiencePoints', 'xp_vanilla')]),
                     **{f'en_{k}': e.get(k, '') for k in (
                         'unlock_level', 'cost_vanilla', 'cost_v11', 'servings_vanilla', 'servings_v11', 'pps_vanilla',
                         'pps_v11', 'cook_min_vanilla', 'cook_min_v11', 'xp_vanilla', 'xp_v11',
                         'profit_per_min_vanilla', 'profit_per_min_v11', 'xp_per_min_vanilla', 'xp_per_min_v11')}})
    write(os.path.join(SNAP, 'foods_current.csv'), rows)

    cur = {}
    if os.path.exists(CURATION):
        for r in csv.DictReader(open(CURATION, encoding='utf-8-sig')):
            cur[int(r['record_index'])] = r
    chars, chars_jp = load('characterData', OUT_JSON), load('characterData', BASE_JSON)
    en_char = en_reference('en_characters_vanilla_vs_v11.csv',
                           lambda r: (r['art'], r['class'] == 'playable_chef', r['currency']))
    rows = []
    for i, (c, j) in enumerate(zip(chars, chars_jp)):
        k = cur.get(i, {})
        e = en_char.get((f"{c['Category']}/{c['CharacterArtString']}", c['PlayableFlag'] == 1,
                         'toxin' if c['PurchaseWithToxin'] else 'cash'), {})
        rows.append({'index': i, 'name': c['Name'], 'jp_name': j['Name'], 'role': role(c),
                     'curation_suggestion': k.get('candidate_decision', ''), 'curation_reason': k.get('reason', ''),
                     'acquisition': k.get('acquisition_dependency', ''), 'collab_group': k.get('collab_event_group', ''),
                     'cafe_level_required': c['CafeLevelRequired'], 'cost': c['Cost'],
                     'currency': 'toxin' if c['PurchaseWithToxin'] else 'cash',
                     'energy': c['Energy'], 'speed': c['Speed'], 'attack': c['AttackStrength'],
                     'tip_rating': c['TipRating'], 'cook_speed_bonus': round(c['CookSpeedBonus'], 3),
                     'tip_multiplier': c['TipMultiplier'], 'U19_regen?': round(c['U19'], 3),
                     'U20_cookxp?': round(c['U20'], 3), 'U9': c['U9'], 'U10': c['U10'], 'U11': c['U11'],
                     'U12': c['U12'], 'U21': c['U21'], 'U22': c['U22'], 'U23': round(c['U23'], 3),
                     'is_female': c['IsFemale'], 'art': f"{c['Category']}/{c['CharacterArtString']}",
                     'playable_flag': c['PlayableFlag'], 'toxin_flag_raw': c['PurchaseWithToxin'],
                     'en_match': e.get('name', ''), 'en_row': e.get('index', ''),
                     **{f'en_{k}': e.get(k, '') for k in (
                         'Cost_vanilla', 'Cost_v11', 'Energy_vanilla', 'Energy_v11', 'Speed_vanilla', 'Speed_v11',
                         'AttackStrength_vanilla', 'AttackStrength_v11', 'TipRating_vanilla', 'TipRating_v11',
                         'TipMultiplier_vanilla', 'TipMultiplier_v11', 'CookSpeedBonus_vanilla', 'CookSpeedBonus_v11')}})
    write(os.path.join(SNAP, 'characters_current.csv'), rows)

    furn, furn_jp = load('furnitureData', OUT_JSON), load('furnitureData', BASE_JSON)
    rows = []
    for i, (f, j) in enumerate(zip(furn, furn_jp)):
        rows.append({'index': i, 'name': f['Name'], 'jp_name': j['Name'], 'unlock_level': f['UnlockLevel'],
                     'price': f['Price'], 'currency': 'toxin' if f['PurchaseWithToxin'] else 'cash',
                     'in_store': f['IsAvailableInStore'], 'type': f['Type'], 'category': f['Category'],
                     'size': f"{f['SizeX']}x{f['SizeY']}", 'money_per_hour': f['MoneyPerHour'],
                     'max_money': f['MaximumMoney'], 'rating_bonus': round(f['RatingBonus'], 4),
                     'stove_speed_mult': round(f['StoveSpeedMult'], 3), 'xp': round(f['ExperiencePoints'], 2),
                     'buy_money_amount': f['BuyMoneyAmount'], 'UMid': f['UMid'],
                     'UTailFloat1': round(f['UTailFloat1'], 3), 'UTailInt': f['UTailInt'],
                     'UTailFloat2': round(f['UTailFloat2'], 3), 'description': f['Description']})
    write(os.path.join(SNAP, 'furniture_current.csv'), rows)


if __name__ == '__main__':
    main()
