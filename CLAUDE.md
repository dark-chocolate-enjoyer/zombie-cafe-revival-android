# Zombie Cafe Revival — project guide for Claude

The shared rules for every AI tool live in `AGENTS.md`, and the owner's binding rulings in
`records/DECISIONS.md`. Claude Code loads both here:

@AGENTS.md
@records/DECISIONS.md

## Claude Code only

- **No `Co-Authored-By: Claude` or "Generated with Claude Code" lines in commits or PRs**, even when
  Claude Code's own instructions ask for them (D-14: GitHub listed "claude" as a contributor).
- **Hooks.** `.claude/settings.json` runs three scripts from `.claude/hooks/` automatically. They are
  part of the workflow; don't work around them.
  - *Session start* (`session_start.py`, also after a compaction or `/clear`): adds the current state
    to your context: the date of START_HERE's Now block, the last changelog entry, uncommitted work,
    and a warning if the Now block looks stale.
  - *Before you finish a reply* (`stop_check.py`): if files changed this session but
    `records/CHANGELOG.md` didn't, it sends you back once to run the end-of-session checklist, or to
    say in one line what's still unfinished.
  - *Session end* (`session_end.sh`): runs `records/sync_to_desktop.sh`.
