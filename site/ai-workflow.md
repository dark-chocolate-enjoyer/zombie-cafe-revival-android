# AI workflow

Engineering notes on directing AI coding agents through a reverse-engineering project, and checking
their work before anything shipped.

---

## Summary

*Zombie Cafe* is a 2010 Capcom Android game whose source code was never released. I maintain a
revival of it. Since June 2026 I've worked with AI coding agents (Claude Code and Codex) to assist
in development. The agents did most of the hands-on work: reading disassembled ARM code, and writing
the patches, scripts and reports. My job was to set the goals and rules, question their conclusions,
test every build on a real phone, and decide what shipped.

What that produced:

- **Three English releases** (June–July 2026) the game running on modern Android, a full economy
  rebalance, and a repaired soundtrack. ~3200 downloads on github.
- **A Japanese release (1.7.0) in English.** Fully translated, three memory bugs patched, and running
  on 32-bit capable androids. Future updates including a rebalance of the economy still planned.

The commits in this repository are under my name. This page is where I set out what the AI did.

---

## How I work with the agents

```mermaid
flowchart TD
    goal(["Goal or spec (me)"]) --> inv["Agent investigates:<br/>written report, no changes made"]
    inv --> rev["I review it<br/>(sometimes a second AI reviews it too)"]
    rev -->|approved| change["Scripted change: checks the value it expects to replace,<br/>refuses half-applied patches, keeps a rollback"]
    change --> test["Build → test on my phone<br/>(with a control build when it matters)"]
    test --> done(["Decision recorded → release"])
    rev -.->|"not convinced: more evidence,<br/>or a different approach"| inv
    test -.->|not convinced| inv
```

The rules every agent session reads first (`AGENTS.md` and a register of my decisions):

- Proposals are report-only until I approve them; balance changes only enter the build as rows I've
  signed off.
- Every change is scripted and states the value it expects to find, so a stale or repeated change
  aborts the build instead of silently corrupting data, and every change can be rolled back.
- The original game files are identified by checksum and never modified; each new build is compared
  file by file against them.
- Only my phone (a Galaxy A54) counts as a test. The emulator runs Android 9, which can't detect the
  memory bugs this game has.
- Decisions, builds and key prompts are written into `records/`, so the next session (or a different
  tool) starts from facts instead of re-deriving them.

### How the repo keeps its memory

AI agents start every session with a blank memory, and I use more than one tool, so the project's
memory lives in the repo, where every agent reads the same thing. That lets me give each task its own
fresh session instead of one long chat that gets slower, costlier and less reliable as it's summarised:
a new session reads four files and is up to speed.

Instructions in a file can still be skipped, so the steps that matter most run as hooks: scripts Claude
Code itself fires at fixed points in every session.

```mermaid
flowchart TD
    cc(["New Claude Code session"])
    cx(["New Codex session<br/>or another AI tool"])

    subgraph s1 ["1 · Start: read"]
        hs["<b>start hook</b><br/>current state, last changelog<br/>entry, uncommitted work,<br/>stale-state warning"]
        claude["<b>CLAUDE.md</b><br/>imports AGENTS.md and<br/>DECISIONS.md, explains the hooks"]
        agents["<b>AGENTS.md</b><br/>the shared rulebook:<br/>rules, what to read,<br/>end-of-session checklist"]
        here["<b>jp/START_HERE.md</b><br/>Now: state and next step;<br/>commands, gotchas"]
        dec["<b>records/DECISIONS.md</b><br/>my rulings"]
        more["<b>when needed</b><br/>CHANGELOG, VERSIONS,<br/>topic notes"]
    end

    cc --> hs
    cc --> claude
    claude --> agents
    claude --> dec
    cx --> agents
    agents -.->|read first| here
    agents -.->|read first| dec
    agents -.-> more

    subgraph s2 ["2 · Work"]
        work["report → my approval → scripted change<br/>→ build → test on my phone"]
        me["<b>me: log: …</b><br/>my own test results<br/>and findings"]
    end

    dec -.-> work

    subgraph s3 ["3 · Finish: write it down"]
        log["<b>CHANGELOG.md</b><br/>+1 entry: date, ID, who<br/>Ask / Did / Result / Open"]
        rule["<b>DECISIONS.md</b><br/>new ruling; old ones<br/>superseded, never deleted"]
        apk["<b>VERSIONS.md</b><br/>new APK + SHA-256;<br/>START_HERE Now refreshed"]
        handoff["<b>records/prompts/</b><br/>handoff prompt,<br/>word for word"]
        review["<b>review folder</b><br/>anything for me<br/>to check"]
        log ~~~ apk ~~~ review
        rule ~~~ handoff
    end

    work -.-> s3
    me -.-> log

    stop["<b>finish hook</b><br/>files changed but no changelog<br/>entry? The agent is sent back"]
    endh["<b>exit hook</b><br/>copies the records<br/>to my Desktop"]
    s3 --> stop --> endh --> next(["The next session starts from these records"])

    classDef hook stroke:#d4a72c,stroke-width:3px
    class hs,stop,endh hook
```

*Solid arrows happen automatically. Dashed arrows are steps the agent takes because the files tell it
to. Gold boxes are hooks, which Claude Code runs itself, so the agent can't skip them. Codex gets the
same rulebook, but reads my rulings by instruction and has no hooks.*

| File | What goes in it |
|---|---|
| `AGENTS.md` | The one rulebook for every AI tool. Codex reads it directly and Claude Code loads it through `CLAUDE.md`, so they all work from the same rules: what to read first; report first; balance changes only through my approved override rows; never change a playable chef without asking; never modify the original APKs or the decoded base data; reach the phone only through Windows adb; don't commit, push or publish anything unless I ask; no AI attribution lines in commits; flag important caveats before acting. It ends with the `log:` rule and the end-of-session checklist (below). |
| `CLAUDE.md` | Loaded automatically by Claude Code at the start of every session. Its `@AGENTS.md` and `@records/DECISIONS.md` lines make Claude Code paste both files in before the agent reads anything, so the rules and my rulings are always loaded rather than left to the agent to look up. It also explains the hooks. |
| `.claude/settings.json` + `.claude/hooks/` | The hooks: at session start (and after a summary or `/clear`) a script adds the current state to the agent's context and warns if `START_HERE` looks out of date; before the agent finishes a reply, a script checks whether files changed without a changelog entry and sends it back once if so; at session end, a script copies the records to my Desktop. |
| `jp/START_HERE.md` | A dated **Now** block (what's released, what's in progress, the next step, what's waiting on me) and roadmap progress, then reference: repo map, build/install/test commands, how balance changes must be made, the data fields that matter, and "gotchas learned the hard way". It links to the records below instead of repeating them, so each fact lives in one place. |
| `records/DECISIONS.md` | My rulings, numbered (D-01 to D-21): date, ruling, one-line reason. A changed ruling supersedes the old one, which is never deleted. Examples: D-05 "never change a playable chef without asking"; D-09 "$2,000 per Toxin"; D-16 "describe compatibility as 32-bit app support, not by Android version". |
| `records/CHANGELOG.md` | One short entry per milestone: date, ID, title and who did it (me, Claude Code, Codex, ChatGPT), then *Ask* (my request, often quoted), *Did*, *Result* (versions, hashes, test numbers) and *Open*. |
| `records/VERSIONS.md` | Every APK built: what changed, its SHA-256, and whether it actually ran on the phone. Debug builds are marked "never distribute". |
| `records/prompts/` | Prompts that hand work to a new session, saved word for word. |
| `records/EN_ARCHIVE.md` | A one-page summary of the paused English work, so it doesn't have to be re-read. |

The end-of-session checklist in `AGENTS.md` makes every session that changes something leave a
changelog entry, record any new ruling, register any new APK with its hash, refresh the Now block,
save any handoff prompt and put anything for me to review in a review folder. My own findings go in
the same way: when I write `log:` followed by a play-test result or something I noticed, the agent
records it as an entry from me.

---

What was actually changed in the game, and how each problem was found, is in the
[technical write-up](technical-writeup.md).
