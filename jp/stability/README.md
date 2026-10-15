# JP stability: the heap crash on modern Android (Scudo, Android 11+)

**Solved 2026-10-09 — see `DEVICEINFO_BUG.md` (finding 19). Fixed in v6.**

Phase 5 work. The JP build has the same crash that stopped the EN Revival (`records/EN_ARCHIVE.md`):
SIGABRT `Scudo ERROR: corrupted chunk header`, raised while freeing an object as the game leaves
the cafe (`GameStateCafe::uninit` → `Cafe::~Cafe`). Scudo is Android 11+'s allocator and checks
each block's header on free. The object being freed when it aborts is a **victim**: some other
code wrote over its header earlier.

## Tools

| File | What |
| --- | --- |
| `make_debug_apk.py` | `--mode malloc` or `--mode gwp`: builds `…_MALLOC_DEBUG.apk` / `…_GWP_ASAN.apk` from the normal build: manifest gains `android:debuggable="true"`, plus `lib/armeabi/wrap.sh` (from `wrap_mallocdebug.sh` / `wrap_gwpasan.sh`) and the `lib_fixes.py` patches. Nothing else changes (the script checks this). Same key, so it installs over v5 and keeps the save. **Never distribute.** |
| `wrap_mallocdebug.sh`, `wrap_gwpasan.sh` | Packed as `lib/armeabi/wrap.sh`; Android runs it at launch for debuggable apps: starts the game under bionic **malloc debug**, or with **GWP-ASan** (settings and why are in each file). Side effect: the game's own `printf` output appears in logcat under tag `wrap.sh`. |
| `lib_fixes.py` | Checked byte patches for the native lib (raid fix; toString and device-info terminator fixes). Applied by `jp/english/build.py` (release, from v6) and `make_debug_apk.py`; `state()` refuses half-patched libs. |
| `offline_patch.py` | Smali patch: `URLManager.a(Context)` always "not connected", so the game sends no server requests. In the release build from v6; `make_debug_apk.py --offline` for test builds. |
| `lock_natives.py` | Test only (5h): every Java → native call behind one Java lock. |
| `tools/auto_loop.py` | Automated launch → Play → Map loop over adb with outcome classification (only taps Play and Map; keeps the screen on while running, then restores it). |
| `STRING_BUG.md` | Full write-up of the unterminated-string bug: code, GWP-ASan evidence, fix, test result. |
| `tools/scan_use_after_delete.py` | Static scan of the native lib for "pointer used after `delete`/`free`": (1) same register (the raid bug's shape; whole lib: only the raid bug), (2) same field reloaded (weak: compiled code rarely re-reads through the same register; 0 hits). Can't see pointers kept in other objects/globals. |
| `logs/` (git-ignored) | Phone log captures, save backups, scan output. |

Debuggable also allows `adb shell run-as com.capcom.zombiecafeandroidJP …` (e.g. back up `files/`).
To go back to normal play, reinstall v5 over it (same key, save kept).

## Findings, 2026-10-09 (Galaxy A54)

1. **v5, no malloc debug**: crashed on the 13th cafe → map trip (about 25 s of trips), Scudo
   "corrupted chunk header". Older crashes on the phone had the same error but failed while freeing
   different objects (`CafeWall`, a `String` in `Cafe`, `EatTask`, a system binder thread).
   One was at 09-25 13:24, before v5 was installed at 13:35, so most likely on v4, which has no
   translation changes.
2. **malloc debug run 1** (`backtrace` option): crashed at startup inside malloc debug. libc's unwinder
   calls the game's bundled 2016 `__gxx_personality_v0`, which crashes. Per-allocation stacks
   (`backtrace`, free_track stacks) can't be used with this lib; `backtrace_full` (libunwindstack) is fine.
3. **malloc debug run 2** (`guard=64 free_track=100 backtrace_full`): **25 cafe ↔ map round trips,
   no crash and no guard errors.** Then the first raid entry (enemy cafe `raidCafe2.dat`) crashed:
   SIGSEGV at `0xefefeff7` in `CapcomOrderableList<Furniture*>::nextItem()` ← `GameStateRaid::init()`.
   `0xef` is malloc debug's fill byte for freed memory, so the game read a pointer out of freed memory.
4. **Raid bug (Capcom source bug, confirmed by disassembly)**, `GameStateRaid::init` `0x172fe4–0x173032`:
   it builds a furniture list (`r6`), walks it, frees it (`0x17300e`), builds a new object list
   (`r4`, `createDistanceSortedObjectList(1,0)`, iterator reset), then walks the **freed** list:
   `0x17302a adds r0, r6, #0` → `nextItem`. The loop body sets `object+0x54 = 0`. It calls
   the `Furniture*` version of `nextItem` on a `CafeObject*` list, so it looks like a copy-paste typo
   (`list` for `objs`). Old allocators gave the new list the memory of the one just freed, so it
   worked by accident. Scudo doesn't, so the loop reads a stale pointer and can **write** through it
   (`nextItem` stores into the freed list; the body writes a byte at `obj+0x54`).
   Likely 1-byte fix: `0x17302a` `30 1c` → `20 1c` (`adds r0, r4, #0`). Not applied.
5. **Scan of the whole lib** for the same idiom (`tools/scan_use_after_delete.py`, output in
   `logs/2026-10-09_use_after_delete_scan.tsv`): the raid bug is the **only** real hit. The other hit
   is inline data that decodes as an instruction. `GameStateRaid::init` only runs when a raid starts
   (map enemy-cafe tap ×2 sites, `EnemyCafeDialog`, `GameStateWeekRaidMenu`); the player's cafe
   (`GameStateCafe`) and friend cafes (`GameStateFriendCafe`) don't contain the bug.
6. **Correction (same day): the raid bug did not cause the v5 map crash.** The v5 crash run did enter
   a raid at 16:04:35 (only `GameStateRaid::init` loads `enemyLayouts`; only `GameStateRaid::saveData`
   writes a full `raidCafe%d.dat`), but the buggy block runs **only when a saved raid is resumed**:
   `Cafe::deserialize(raidCafe%d.dat)` succeeds (`0x172776`) → far jump `0x172782 → 0x1743b8` (builds
   list 1) → `0x172f36`. A newly generated raid exits at `0x172f30 → 0x17307a` and skips it. In the v5 run
   `raidCafe2.dat` didn't exist (`doesFileExist=false`), so the raid was generated; in run 2 it existed
   and was resumed. Also, on the normal allocator the new list (same 40-byte size) almost always
   gets the memory of the list freed just before (Scudo's cache is last-in-first-out), so the typo
   usually walks the right list; it misbehaves only if another thread takes that block in between.
   Real bug, worth fixing, not the map-crash cause. (The 40-byte list is in Scudo's 48-byte class,
   like all EN victims: noted, but irrelevant here.)
7. **Run 3** (5e: raid fix + `free_track=16384`): the resumed raid that crashed run 2 loads fine (fix
   works); 37 cafe ↔ map trips, one process, **0 malloc-debug reports**. With run 2 that's 62 clean trips
   under malloc debug, while plain v5 crashed on trip 13 (16:04) and on the **first** cafe exit after
   launch (16:01: start 16:00:59, cafe loaded 16:01:06, abort 16:01:09.995, no raid). So the map crash
   is not raid-related and not cumulative. The failed server upload right before the 16:04 abort is a
   coincidence (16:01 had none); both aborts come right after the save on cafe exit.
   Leading explanation for why malloc debug shows nothing: the overflowing object is **long-lived**
   (allocated at startup or cafe load, never freed). malloc debug only checks a block's guards when it
   is freed, and the guard absorbs the overflow, so nothing else is damaged. (A timing race is less likely.)
8. **GWP-ASan (5f, run 5)**: libc ignores the `GWP_ASAN_*` variables in programs named `app_process*`
   (to stop them leaking from the Zygote), so `wrap_gwpasan.sh` starts the launcher under another name
   (`exec -a`). Measured ~570k live allocations at the menu (~590k in the cafe); 1-in-24 sampling with
   26,000 slots (2 memory regions each; kernel limit ~65.5k) covers them. Launch 3 of 4 caught:
   `Cause: [GWP-ASan]: Buffer Overflow, 0 bytes right of a 16-byte allocation`, in `memcpy` ←
   `String::operator+=(String)+84` ← `String::operator+(String)` ← `ObjectiveDialog::ObjectiveDialog+4290`
   ← `GameStateCafe::init`. Registers: the **source** pointer (`r1`) was on the guard page, so it was a
   **read** past the end. Launch 4 hit the usual Scudo crash on the first cafe exit.
9. **String bug (Capcom code)**: `String` = {StringRef* (→ char buffer, int16 refcount), int16 offset,
   int16 length}. `StringBuffer::toString()` (`0x2918c2`) does `malloc(total length)` with **no byte for
   a terminator and writes none**. `operator+=(String)` copies `other.length + 1` bytes from the source,
   so it reads 1 byte past such strings (what GWP-ASan caught) and copies that stray byte into the new
   string's last byte, so the result is unterminated too. 153 call sites (cafe, raids, menus, dialogs;
   `StringUtil::replace` uses it, 18 callers). On old allocators the byte after a block was usually 0
   (size rounding, fresh memory), so it worked by accident; on Scudo it's often leftover data. Reads alone
   don't damage memory: whether some code then **writes** using `strlen`/`%s` on such a string (which
   would be the heap corruption) is not yet shown.
10. **toString fix (5g, run 6)**: details in `STRING_BUG.md`. Launch 1: 11 trips, no crash. Launch 2: Scudo
   crash (`CafeWall::~CafeWall` ← `Cafe::~Cafe`) ~1.1 s after the cafe loaded, owner pressed Map at once.
   Real bug, now fixed in debug builds, but **not the map-crash cause**.
11. **Lead: network callbacks race the game thread.** The owner noticed quick Map presses crash (16:01:
   3 s after cafe load; run 6: 1.1 s). Right after the cafe loads the game fires ~6 requests to the dead
   servers (lottery, getGameInfo, savegamestate, getEntry, getgifts_support, getEventReward). Each is a
   Java AsyncTask; its **background thread** calls the native callback directly:
   `NetworkTask.a(String[])` (= `doInBackground`) → `NetworkTask.NewRequestServerCallback`, and
   `URLManager.a(String,String,String,int)` (run from `r.doInBackground`) → `URLManager.NewRequestServerCallback`
   (also when offline: "Internet IS NOT CONNECTING!" then the same callback). Native side:
   `Java_…_NewRequestServerCallback` → `ZombieCafe::NewRequestServerCallback` →
   `CCServer::Android_ServerCallback` (`0x2a8a18`, 5.8 KB switch into game handlers: gifts, events,
   analytics…). No lock was seen between that and the game (GL) thread, which may be tearing down the
   cafe at the same moment. With the servers dead, the failures arrive within milliseconds, right in the
   window the owner hits. Slow debug builds (malloc debug) shift that timing, which would explain 62 clean
   trips. **Not proven yet.**
12. **Native-lock test (5h, run 7)**: `lock_natives.py` wraps all 95 Java → native call sites (51 natives) in one
   Java lock; verified active (Android logged `Long monitor contention`: `AsyncTask #3` in
   `URLManager.zcLocked_NewRequestServerCallback` waited on `GLThread` in `zcLocked_render`). Launch 1: 6 trips, no
   crash. Launch 2: map → raid (cafe 2) → cafe → map → raid (cafe 0) → cafe → map → cafe → Map: Scudo crash in
   `Cafe::~Cafe()+428` (`operator delete[]`) ← `GameStateCafe::uninit`. The native lib imports no `pthread_create`
   (only mutex/cond functions), so game code ran on one thread at a time: **the crash is not a Java-thread race.**
   Finding 11 is ruled out as the cause. The corruption comes from the game thread itself; "quick Map press" may
   mean tearing down a cafe whose multi-frame setup hasn't finished.
13. **What the 5h crash freed, and the victims so far.** `Cafe::~Cafe()+428` is `delete[] cafe->field_0x50`
   (`0x0b0a88`), a 40-byte array the constructor makes (`Cafe::Cafe` `0x0b0b7a`: `new[](0x28)`, 10 slots,
   count at `+0x48`). (`Cafe::tick`'s write to `+0x50` at `0x0b0642` is a *Stove*'s timer, not this.) Timeline:
   raid cafe 2 (18:00:45.8) → own cafe → map → raid cafe 0 (49.1) → own cafe → map → own cafe loaded 52.05 →
   Map → abort 52.44. Victim sizes across crashes: `CafeWall` 72 B (`new(0x48)`, freed in its deleting dtor),
   `EatTask` 68 B (`new(0x44)`), the `Cafe+0x50` array 40 B, `String` buffers (variable). Scudo keeps
   same-size blocks together, so victims in different size groups make "one object type overflowing into
   its neighbour" unlikely (EN had reported all 45 victims in the 48-byte group); a write through a stale
   or wild pointer, or more than one bug, fits better. Not proven.
14. **All Scudo "corrupted chunk header" crashes so far** (where the damage was *detected*; none of these
   frames is the culprit):

   | When | Build | Detected while freeing | Called from |
   | --- | --- | --- | --- |
   | 09-25 13:24 | v4 (probably) | `EatTask` (68 B) | `CharacterInstance::tick` (cafe running) |
   | 09-25 15:16 | v5 | Android's own object | `libgui` `TransactionCompletedListener` (system binder thread) |
   | 10-09 16:01 | v5 | `String` buffer | `Cafe::~Cafe()+96` |
   | 10-09 16:04 | v5 | `CafeWall` (72 B) | `Cafe::~Cafe()+290` |
   | 10-09 17:32 | 5f-measure | `String` buffer | `Cafe::~Cafe()+96` |
   | 10-09 17:39 | 5f | `String` buffer | `Cafe::~Cafe()+96` |
   | 10-09 17:48 | 5g | `CafeWall` (72 B) | `Cafe::~Cafe()+290` |
   | 10-09 18:00 | 5h | 40 B array (`Cafe+0x50`) | `Cafe::~Cafe()+428` |

   6 of 8 during the cafe teardown, at 3 different spots; `+96` (a `String`) 3 times and `+290` (a `CafeWall`)
   twice: the best candidates to watch with a hardware watchpoint.
15. **Hardware-watchpoint plan (not continued).** Checked: the PC reaches the phone over Wi-Fi, and LLDB's server
   can run inside the debuggable game's sandbox. Stopped there this session; the debugger files were removed from
   the phone. Remaining options: the elimination test (no dead-server requests) and the automated GWP-ASan loop.
16. **Automated runs A/B** (`tools/auto_loop.py`: launch → Play → wait for the cafe in the log → random
   0.3–3.0 s → Map → classify; logs `logs/2026-10-09_run{A,B}_*`). Same build except the network:

   | Run | Build | Server requests | Scudo crashes | GWP-ASan |
   | --- | --- | --- | --- | --- |
   | A | 5g (GWP-ASan + raid/toString fixes) | normal | 15/40 (37%) | 1 |
   | B | same + `offline_patch.py` | **0** (no lookups, no "NOT CONNECTING") | 17/39 (44%) | 3 |

   **The server-request code is ruled out**: no requests, same crash rate. Victims A: `String` @ `Cafe::~Cafe+96`
   11, `CafeWall` 3, `MoveTask` 1; B adds `CharacterCommandBar::~CharacterCommandBar+308` (`delete[]`).
17. **Device-info off-by-one (Capcom code), caught by GWP-ASan in A and 3× in B**:
   `javaGetDeviceInfoForURL` (`0x29924c`) does `len = GetArrayLength(info); buf = malloc(len);
   GetByteArrayRegion(...); buf[len] = 0` (`0x29928a strb r3, [r4, r5]`): 1 zero byte past the end, on every
   save upload (`CCServer::SaveMyGameState`) and daily-activity analytics (`MALTAHoover::sendDailyActivity`),
   offline too. The text (`&brand=…&mani=…&dev=…&model=…&prod=…`, from `CC_Android.fromNative_GetDeviceInfoForURL`)
   is 80 bytes on the A54. Scudo's size table read from the phone's libc (`0x227d0`: `0x20, 0x30, 0x40, 0x50,
   0x60…`) puts 80 + 8-byte header in a 96-byte slot, so here the byte lands in spare space: **not this phone's
   crash**, but a device whose text is 88 bytes would corrupt the next header. Fixed in `lib_fixes.py` by
   reusing the toString helper (`0x299274`: `blx malloc` → `bl 0x290ec2`).
18. **v6 and the control (solved).** v6 (v5 + raid, toString, device-info fixes + offline; not debuggable, no checker)
   passed **20/20** automated rounds. Control = v6 with only the 4 device-info bytes reverted: **10/20** crashed,
   victims all exact multiples of 96 bytes apart. Finding 17's "lands in spare bytes" was wrong: Android's Scudo
   uses a 16-byte header area (every victim address is 16-byte aligned), so 80 + 16 fills a 96-byte slot exactly.
19. **Root cause: `DEVICEINFO_BUG.md`.**
20. Run 2 also argues against the EN theory ("a ≤32-byte object overflowing forward"): a forward
   overflow of ≤64 bytes from a block freed during those trips would have hit its guard. None did.

## Next steps (proposed, not done)

- (done, 5h: crash persists) **Serialise the network callbacks with the game thread**, a debug build where
  `CapcomRenderer.onDrawFrame` (game thread) and every Java → native network callback hold the same
  Java lock, so game code never runs on two threads at once. If quick Map presses stop crashing, the race is
  confirmed; the release fix could then be the same lock, or no requests at all (offline game, phase 2).
- (done) **Run 4, GWP-ASan** (normal allocator, so the crash conditions stay the same): sampled blocks get a
  guard page, so an overflow faults at the writing instruction itself. Same debuggable shell; `wrap.sh`
  sets `GWP_ASAN_*` env vars instead of malloc debug (verify it's active via `[anon:GWP-ASan …]` in
  `/proc/<pid>/maps`). Sampling is random: may take several sessions.
- **Or a debugger snapshot**: attach lldb (NDK) to a plain debuggable build; at the abort, dump the
  memory around the damaged header: the bytes written and the block in front of it (its vtable → class).
- Raid fix: in debug builds since 5e; add it to the release build (`build.py`) when the owner says so.
- EN `GameStateRaid::init` may have the same typo (EN crashes also hit raids); unchecked.
