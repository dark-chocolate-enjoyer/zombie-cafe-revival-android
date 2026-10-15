#!/usr/bin/env python3
"""Stop hook: runs each time Claude is about to finish a reply. If files changed this session but
records/CHANGELOG.md didn't, send Claude back once to do the end-of-session checklist (AGENTS.md)
or to say what's unfinished. It asks again only when more files have changed since the last ask."""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CHANGELOG, snapshot, load_state, save_state  # noqa: E402


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    if data.get('stop_hook_active'):  # already sent back once this turn
        return
    session_id = data.get('session_id')
    state = load_state(session_id)
    if state is None:  # hook added mid-session: start tracking from now
        save_state(session_id, {'baseline': snapshot(), 'reminded': []})
        return

    base, now = state['baseline'], snapshot()
    changed = sorted(p for p in set(base) | set(now) if base.get(p) != now.get(p))
    if not changed or CHANGELOG in changed:
        return
    key = hashlib.sha1('\n'.join(changed).encode()).hexdigest()
    if key in state['reminded']:
        return
    state['reminded'].append(key)
    save_state(session_id, state)

    shown = ', '.join(changed[:8]) + (f' and {len(changed) - 8} more' if len(changed) > 8 else '')
    reason = (f'[stop_check hook] {len(changed)} file(s) changed this session ({shown}) but '
              f'{CHANGELOG} has no new entry. If this piece of work is finished, run the end-of-session '
              'checklist in AGENTS.md now. If it is not finished (you are waiting on the owner, or this '
              'is a draft), say so in one line instead; you will not be asked again until more files change.')
    print(json.dumps({'decision': 'block', 'reason': reason}))


if __name__ == '__main__':
    main()
