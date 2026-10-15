"""Shared helpers for the Claude Code hooks in this folder (see CLAUDE.md, "Hooks")."""
import hashlib
import json
import os
import subprocess
import time

ROOT = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
STATE_DIR = os.path.expanduser('~/.cache/zombie-cafe-hooks')
CHANGELOG = 'records/CHANGELOG.md'


def git(*args):
    return subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True).stdout


def snapshot():
    """Every changed, staged or untracked (not ignored) file -> hash of its content ('deleted' if gone).
    Comparing two snapshots shows what changed in between, including edits to already-dirty files."""
    snap = {}
    entries = git('status', '--porcelain=v1', '-z', '-uall').split('\0')
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if 'R' in status or 'C' in status:
            i += 1  # the next field is the rename/copy source
        try:
            with open(os.path.join(ROOT, path), 'rb') as f:
                snap[path] = hashlib.sha1(f.read()).hexdigest()
        except OSError:
            snap[path] = 'deleted'
    return snap


def state_path(session_id):
    return os.path.join(STATE_DIR, f'{session_id or "unknown"}.json')


def load_state(session_id):
    try:
        with open(state_path(session_id)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_state(session_id, state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(state_path(session_id), 'w') as f:
        json.dump(state, f)


def prune_old_states(days=14):
    cutoff = time.time() - days * 86400
    try:
        for name in os.listdir(STATE_DIR):
            p = os.path.join(STATE_DIR, name)
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
    except OSError:
        pass
