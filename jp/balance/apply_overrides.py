#!/usr/bin/env python3
"""Owner-approved balance overrides for the JP build.

Every balance change is one row in jp/balance/overrides/*.csv:

    file,record_index,field,expected_current,new_value,note
    foodData,0,CookTimeMinutes,5,3,"Mystery Meat: faster starter dish (approved 2026-10-01)"

  file              foodData | characterData | furnitureData | quest
  record_index      0-based row in that file (same index as the snapshots)
  field             exact JSON field name (see jp/START_HERE.md, "Data fields")
  expected_current  the value the row has BEFORE this override (JP original
                    unless an earlier override file changed it). A mismatch
                    aborts the build - this catches double-applies and stale
                    proposals.
  new_value         the value to write (parsed to the field's existing type)
  note              why / approval reference (required)

Files are applied in filename order, so later files may build on earlier ones
(their expected_current must then be the earlier file's new_value).

Text fields (names/descriptions) belong to the translation pipeline and are
rejected here.

jp/english/build.py calls apply_all() after translation and before packing, and
writes out/balance_applied.csv listing every change it made.
"""
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OVERRIDES = os.path.join(HERE, 'overrides')
TEXT_FIELDS = {'Name', 'Description', 'HumanDescription', 'ZombieDescription', 'Text',
               'Category', 'CharacterArtString', 'Cond1Type', 'Cond2Type', 'Cond3Type'}
FILES = {'foodData', 'characterData', 'furnitureData', 'quest'}


class OverrideError(Exception):
    pass


def _parse(template, raw, where):
    raw = raw.strip()
    try:
        if isinstance(template, bool):
            if raw.lower() in ('true', '1'):
                return True
            if raw.lower() in ('false', '0'):
                return False
            raise ValueError(raw)
        if isinstance(template, int):
            return int(float(raw)) if float(raw).is_integer() else int(raw)
        if isinstance(template, float):
            return float(raw)
    except ValueError:
        raise OverrideError(f'{where}: cannot parse {raw!r} as {type(template).__name__}')
    raise OverrideError(f'{where}: field type {type(template).__name__} is not overridable')


def _same(current, expected):
    if isinstance(current, float):
        return abs(current - expected) < 1e-4
    return current == expected


def load_rows():
    rows = []
    for path in sorted(glob.glob(os.path.join(OVERRIDES, '*.csv'))):
        with open(path, encoding='utf-8-sig', newline='') as f:
            for n, row in enumerate(csv.DictReader(f), start=2):
                if not any((v or '').strip() for v in row.values()):
                    continue
                row['_where'] = f'{os.path.basename(path)}:{n}'
                rows.append(row)
    return rows


def apply_all(datasets, log=print):
    """datasets: {'foodData': [records...], ...} (mutated in place).
    Returns the list of applied changes."""
    applied, problems = [], []
    for row in load_rows():
        where = row['_where']
        try:
            fname, field = row['file'].strip(), row['field'].strip()
            if fname not in FILES:
                raise OverrideError(f'{where}: unknown file {fname!r}')
            if field in TEXT_FIELDS:
                raise OverrideError(f'{where}: {field} is a text field (edit the translation TMs instead)')
            if not (row.get('note') or '').strip():
                raise OverrideError(f'{where}: note is required')
            recs = datasets[fname]
            i = int(row['record_index'])
            if not 0 <= i < len(recs):
                raise OverrideError(f'{where}: record_index {i} out of range (0..{len(recs) - 1})')
            if field not in recs[i]:
                raise OverrideError(f'{where}: {fname}[{i}] has no field {field!r}')
            cur = recs[i][field]
            expected = _parse(cur, row['expected_current'], where)
            new = _parse(cur, row['new_value'], where)
            if not _same(cur, expected):
                raise OverrideError(f'{where}: {fname}[{i}].{field} is {cur!r}, expected {expected!r} '
                                    f'(already applied, or proposal is stale)')
            recs[i][field] = new
            applied.append({'source': where, 'file': fname, 'record_index': i,
                            'name': recs[i].get('Name', ''), 'field': field,
                            'old': cur, 'new': new, 'note': row['note'].strip()})
        except (OverrideError, KeyError, ValueError) as e:
            problems.append(str(e))
    if problems:
        raise OverrideError('balance overrides rejected:\n  ' + '\n  '.join(problems))
    log(f'  balance: {len(applied)} override(s) applied')
    return applied
