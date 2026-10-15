#!/usr/bin/env python3
"""SessionStart hook: give a new, resumed, cleared or compacted session the project's current state,
and record a snapshot of the working tree so stop_check.py can tell what this session changed."""
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, CHANGELOG, git, snapshot, load_state, save_state, prune_old_states  # noqa: E402


def read(rel):
    try:
        with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    session_id, source = data.get('session_id'), data.get('source', 'startup')

    prune_old_states()
    if load_state(session_id) is None:  # keep the original baseline on resume/compact
        save_state(session_id, {'baseline': snapshot(), 'reminded': []})

    today = datetime.date.today()
    lines = [f'Project state at session start ({source}), from .claude/hooks/session_start.py:']

    now_date = None
    m = re.search(r'^## Now \(updated (\d{4}-\d{2}-\d{2})\)', read('jp/START_HERE.md'), re.M)
    if m:
        now_date = datetime.date.fromisoformat(m.group(1))
        lines.append(f'- jp/START_HERE.md Now block: updated {now_date} ({(today - now_date).days} days ago).')
    else:
        lines.append('- jp/START_HERE.md: no "## Now (updated YYYY-MM-DD)" heading found.')

    changelog = read(CHANGELOG)
    heads = list(re.finditer(r'^\*\*(\d{4}-\d{2}-\d{2})[^\n]*?\*\*$', changelog, re.M))
    last_date = None
    if heads:
        head = heads[-1]
        last_date = datetime.date.fromisoformat(head.group(1))
        span_end = re.match(r'\*\*\d{4}-\d{2}-\d{2} → (\d{4}-)?(\d{2}-\d{2})', head.group(0))
        if span_end:  # a ranged entry ("2026-10-10 → 10-15") counts from its last day
            last_date = datetime.date.fromisoformat((span_end.group(1) or f'{last_date.year}-') + span_end.group(2))
        lines.append(f'- Last changelog entry: {head.group(0).strip("*")}')
        body = changelog[head.end():].split('\n**')[0]
        open_line = re.search(r'^Open:[^\n]*', body, re.M)
        if open_line:
            lines.append(f'  {open_line.group(0)}')

    status = git('status', '--porcelain=v1', '-uall').splitlines()
    staged = sum(1 for s in status if s[0] not in ' ?')
    modified = sum(1 for s in status if s[1] in 'MD')
    untracked = sum(1 for s in status if s.startswith('??'))
    if status:
        lines.append(f'- Uncommitted work: {staged} staged, {modified} modified, {untracked} untracked '
                     'files (run git status for details).')
    else:
        lines.append('- Working tree clean.')

    if now_date and last_date and last_date > now_date:
        lines.append(f'- WARNING: the last changelog entry ({last_date}) is newer than the Now block '
                     f'({now_date}). The Now block may be stale; check it against the changelog.')
    if source == 'compact':
        lines.append('- This session was just compacted: re-read the records for rulings and exact '
                     'wording rather than relying on the summary.')
    lines.append('Rules and the read-first list are in AGENTS.md.')

    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart',
                                             'additionalContext': '\n'.join(lines)}}))


if __name__ == '__main__':
    main()
