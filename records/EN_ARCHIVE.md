# English Revival — archive summary (paused 2026-09-25, see D-01)

Everything worth knowing about the paused EN work, in one page. Full detail lives in the
linked folders; the Claude memory notes this replaces are backed up in
`en_archive/claude_memory_backup_2026-10-08/`.

## Where things are

| Topic | Location |
|---|---|
| Shipped data (v1.1.0) | `src/assets/data/*.json` (= release APK, verified) |
| Vanilla data | git `e6e654fe:src/assets/data/*.bin.mid` |
| Food balance stages (v0.2 → v1.0) | `docs/balance/rebalance_v0.2_*`, `rebalance_v1_stage_e/f_*`, summary `docs/balance/v1.0_balance_summary.md` |
| Character stages (G–N, then Stage O steps 1–9) | `docs/balance/rebalance_v1_stage_*`, summary `.../rebalance_v1_stage_o_character_rebalance/STAGE_O_SUMMARY.md` (rollbacks + `.bak` per step) |
| Android compatibility | `docs/compat/` |
| Music fix | `docs/reverse/music-debug/` (+ commit `65cd1615`) |
| Crash hunt | `docs/reverse/crash-debug/` (start with `SOL_ULTRA_MEMORY_CORRUPTION_SOLUTION.md`, then `SMALL_ALLOC_48CLASS_SITES.md`) |
| APKs, logs, review workbooks | `Desktop/ZCafeStuff/English APK Restoration/` (`INDEX.md`) |

## Build gotchas (EN)

- Ship the **combined** native lib: music patch (82 bytes) + TEXTREL patch (23 bytes) — the
  music lib alone reintroduces TEXTREL and crashes BlueStacks/Android 6+.
- `build_tool` skips the 9 recovered Music `.ogg` files (gitignored) — copy them in manually.
- Build with a temp `GOWORK` that excludes `tool/server`; keystore password `zombiecafe`.
- apktool 3.0.1 is installed (2.11.1 gone); use zip-swap of `classes.dex` where possible.
- Never copy data from debug/fast-track scratch builds (Dishwater Soup cook time 1 leaked once).

## Crash hunt — conclusions (unsolved)

- Symptom: SIGABRT "Scudo: corrupted chunk header" seconds after leaving the café (map, Meat Locker,
  raids); fastest repro = map round trips (crash in ~28 s / 6 trips on the A54, 2026-09-11).
- It's an out-of-bounds **write** (checksum failure), not a double free. All 45 victims were in
  the 48-byte allocation class → corruptor is a ≤32-byte object overflowing forward (prime
  suspects CafeTile 24 B, PathTween 28 B). Victim identity never names the writer.
- Exonerated by static analysis: teardown loops (JP-faithful), deleteTasks, CFPathFinder,
  population/ownership, path-grid writers. A `SetNode(-1)` out-of-bounds write exists but lands in
  padding (hardening only). The JP 1.7.0 library shares much of the same code and is **not** a gold
  standard (it has memory issues too) — JP parity never proves correctness.
- Trial patches that failed on the A54: ScudoPathFix, MoveTaskOwnerFix, ASTRA arm 1 (CafeTile
  padding). BlueStacks (Android 9, jemalloc) can't detect this bug — only the A54 counts.
- Untried next step if ever resumed: runtime writer-catch (GWP-ASan / HWASan, malloc-debug) on the
  A54; the unexecuted "Sol Ultra" repair plan G0→G3.

- **2026-10-09, JP:** the same "corrupted chunk header" crash in the JP build was solved: a one-byte overrun
  in `javaGetDeviceInfoForURL` (`jp/stability/DEVICEINFO_BUG.md`). The EN lib has no such function (older
  engine); whether the EN crash is a similar Java → native text off-by-one is unchecked. Note the EN
  "all victims in the 48-byte group" observation: a block filling a slot exactly would produce that.

## Balance outcome (what JP should imitate)

Measured in `jp/balance/EN_BALANCE_DIRECTION.md`. Rules carried into `DECISIONS.md`.
