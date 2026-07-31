# Fable 5 — Music State Fix (v5)

**Date:** 2026-07-02. **Author:** Claude Fable 5 session (round 4; follows `FABLE_music_fix_diagnosis.md` v3 and Codex's v4).
**Input state:** v3 smali fixes + Codex v4 (onCompletion rotation, Sting 1g→2g redirect) applied; combined lib `f302a82c…`.
**Symptom being fixed (v4 report):** first cafe session cycles music, but after leaving and returning to the own cafe by any route (map return, raid return, any state reload) cafe music is dead for the rest of the app session. Also: raid themes never started, map cue never started, cafe rotation never fired natively.

**Output:** 4 surgical native patches (new combined lib `67db8c6a…`) + 5 smali changes → APK
`ZombieCafe-v1.1.0-MusicFix-v5.apk`, sha256 `4f4af9faa39677e787b7b5b13706c158c8979b1788f5574a42d584d74a49df52`, on the Desktop.

---

## 1. Root cause (finally, the single native bug behind all of it)

All music in this build flows through one native path. `CCSound::LoadMusicTrack(j)` and
`CCSound::StartMusic(j,f,j)` are called **only** by the restored `ZombieCafe::loadAndPlayMusic`
trampoline, and `loadAndPlayMusic` is called from every game state's tick:

| Caller | Call | Meaning |
|---|---|---|
| `GameStateCafe::tick` @0xaef52/0xaef9e | ch0, ids 8–11 alt. random 16–18, fade 5.0, loop=0 | cafe cue rotation (gated, see below) |
| `GameStateCafe::tick` @0xafef0 | ch1, id 3 (Sting 3g), fade 0 | tutorial/door sting |
| `GameStateMap::tick` @0xc8124 | ch0, id 15 (Mini Cue 1V2), fade 0, loop=1, once per map | map music |
| `GameStateRaid::tick` @0xd260a / 0xd2a0e | ch0, id 7 (Mini Cue 1g) / id 0x13 (Haunted House if boss flag +0x12), loop=1, once, after a short intro countdown | raid combat theme |
| `GameStateRaid::tick` @0xd20d0/0xd2786/0xd2a98/0xd2b72 | ch1, Sting 2g / 2g / 6g / 1g by outcome flags (+0x4d lose/retreat → 6g; +0x4e win → 1g or 2g) | end-of-raid stings |
| `GameStateFriendCafe::tickAttackMode` ×4 | ch1, Stings 1g/2g/2g/6g | friend-attack stings |

`CCSound::StartMusic(Pv,j,f,j)` @0x192ee9 keeps a **"currently playing" pointer at
`CCSound+0x34`** (the per-channel `SSoundEffect*`). Two fatal properties:

1. **It early-exits (`beq 0x192f32`, @0x192f0c) when `current == requested`.** All game music is
   channel 0 (stings are channel 1), so after the first successful channel-0 start in a process,
   *every* later channel-0 start — map cue, raid themes, cafe re-entry, cafe rotation — is
   silently swallowed. (This is why v1/v2 raids were silent and the "preloads without start" in
   the logs were not preloads at all: the starts were eaten here.)
2. **Nothing ever clears `+0x34`.** `CCSound::StopMusic` (the only clearer) has zero callers in
   the whole lib; the vanilla clearers `ZombieCafe::playMusic`/`stopMusic` are 2-byte `bx lr`
   stubs (stubbed by whoever stubbed `loadAndPlayMusic` in the revival). `UnloadMusicTrack` and
   the fade-out in `L_TickMusic` don't touch it either.

On top of that, `GameStateCafe::tick`'s music gate (@0xaeb98) is:
`if (!ZombieCafe::IsMusicPlaying() ) { timer -= dt; if (timer <= 0) start-next-cue; }`
where `ZombieCafe::IsMusicPlaying` → `CCSound::IsMusicPlaying` → **`current != 0` — native belief,
never Java truth**. Once the first cue starts, belief is stuck "playing" forever, so the
countdown at `ZombieCafe+0x2bc` freezes and the cafe never rotates *and never restarts on
re-entry* (re-entry start comes from this same gated tick block — `GameStateCafe::init` starts
nothing itself).

Why the first entry works: the menu Theme V1 is started by **Java** (`ZombieCafeAndroid.onResume`
→ `fromNative_startMusic(0)` fallback), which native never sees, so `current` is still 0 when the
cafe first ticks. Why v4's "first session cycles" worked: Java's onCompletion rotation is pure
Java, invisible to (and unaffected by) native state. Why it never recovered: recovery required a
native channel-0 start, which properties 1+2 made impossible.

Historical footnote that unlocked the diagnosis: the "cafe re-entry worked at 12:41:50 in v2"
event was a red herring — the pid changed 7430→8865 in that log; the app had crashed (Scudo) and
restarted, so 12:41:50 was a *first* entry with virgin CCSound state.

## 2. What was changed

### Native (both `src/lib/armeabi/libZombieCafeAndroid.so` and the shipped combined lib)

All patches are Thumb, PC-relative only — no new relocations, no `DT_TEXTREL`;
`readelf -d` still shows **RELCOUNT 3977, no TEXTREL**. New combined lib sha256
`67db8c6a8613e2ec7ba840b8add245f28c419ae7b1e219d66b918cfcf1cec764` (base was `f302a82c…`; the
trampoline and the textrel fix are untouched and disjoint).

| # | Addr | Change |
|---|---|---|
| P1 | 0x192f0c | `CCSound::StartMusic`: `beq exit` (current==requested swallow) → `nop`. Every native start request now reaches `L_StopMusic(old)`/`L_StartMusic(new)` → Java. |
| P2 | 0x1235ca | `ZombieCafe::IsMusicPlaying`: its `bl CCSound::IsMusicPlaying` retargeted to the new gate thunk (P4). Only caller of this function is the cafe tick gate — verified. |
| P3 | 0xaef76/7c/80 | Cafe tick start block: the reload of `Constants::GameStateCafe_MUSIC_INTERVAL` replaced with constant **2496 ms** (`movs r1,#0x9c; lsls r1,#4; nop`). This is the silence gap before the next native cue start — i.e. cafe music returns ≈2.5 s after re-entry. |
| P4 | 0x17e5c0 | 18-byte gate thunk written over **`javaFiksuRecordEvent`** (64 B, verified zero callers and no address-taken refs — same precedent as the `javaFiksuPromptForRating` trampoline): returns `CCSound belief (+0x34 != 0) AND javaIsMusicPlaying(0)`. |

Why belief **AND** truth (P2/P4): pure Java-truth would freeze the gate on the looping Java-side
menu theme at first cafe entry (regression); pure belief is the original bug. The AND keeps
first-entry behaviour identical (belief 0 → start immediately, replacing the menu theme) and
makes re-entry work (stale belief=1 but Java says silent → gate opens → cue starts ≈2.5 s in).

### Java (`src/smali/com/capcom/zombiecafeandroid/CC_Android.smali` only)

New static `mMusicMode:I` (0=CAFE, 1=MAP, 2=RAID), set from the filename of every **channel-0**
`fromNative_loadMusic` — this is reliable because every native music intent begins with a load
through the trampoline:

1. `"Zombie Mini Cue 1g"` → RAID, and with 50 % probability the load is swapped to
   `Zombie Mini Cue 1V2.ogg` (owner spec: normal raids randomly 1g or 1V2).
2. `"Haunted House"` → RAID (boss cafes; native picks it via the +0x12 boss flag).
3. `"Zombie Mini Cue 1V2"` → MAP (native only requests 1V2 for the map screen).
4. anything else on ch0 (Theme V1, Cue 2g/3g, missing grooves/V3/V4 that fall back to Theme V1) → CAFE.
5. `fromNative_startMusic(0)` returns true **without starting** when mode==MAP (map = silence;
   logs `startMusic suppressed: map mode`). Stings (ch1) are never suppressed.
6. `onCompletion` now (a) only rotates when mode==CAFE, and (b) calls `setLooping(false)` on the
   newly rotated player — v4 forgot this, so the Java rotation stopped after one hop
   (`loadMusic` defaults every new player to looping).
7. Kept from v3/v4: volume clamp/ignore, start-time volume re-apply, robust stop/load, completion
   listener wiring, Sting 1g→2g redirect (so the victory sting is always 2g).

## 3. Why this can't false-positive on map/raid/menu

There is no watchdog and no timer on the Java side; Java only acts on explicit native calls:

- **Map:** native *does* try to start Cue 1V2 (that's vanilla design, discovered in
  `GameStateMap::tick`); the mode machine suppresses exactly that start. Nothing else starts
  channel 0 on the map — the cafe rotation gate only runs in `GameStateCafe::tick`.
- **Raid:** raid music starts only from `GameStateRaid::tick`'s once-guarded start after the raid
  actually loads (map click → `GAMESTATE RAID INIT`), never from map browsing.
- **Victory sting:** fired by native only through the outcome-flag dispatcher (+0x4e = win →
  Sting 1g/2g → redirected to 2g). Retreat/loss takes the +0x4d path → Sting 6g, which is left
  untouched (it is not the victory sting; if the owner wants retreats fully silent, suppressing
  ch1 loads of `Sting 6g` is a 5-line follow-up).
- **Menu:** unchanged Java fallback (onResume → Theme V1, looping). Mode starts as CAFE so it is
  never suppressed.

## 4. Also answered this round

- **§4d A/B (Scudo crash):** the no-trampoline control APK still crashed (2+ crashes in
  `logcat_no_trampoline_control_dump_after.txt`, e.g. 14:42:38 raid → restart 14:42:59) — **the
  trampoline is NOT the heap corruptor**; it's a pre-existing game bug exposed by Android 14's
  Scudo. Separate work item; v5 does not change it.
- The "raid preload" reading of the logs was wrong — those were swallowed starts (see §1).
- The music constants (`MUSIC_INTERVAL`, `BOSS_THEME`, `NUM_ENEMY_THEMES`) are runtime-loaded
  from `assets/data/constants.bin.mid` (positional binary); P3 sidesteps needing its layout.

## 5. Build / verification

- build_tool (temp GOWORK) → staged `build/`; smali in build byte-identical to src.
- `build/lib/armeabi/`: patched combined lib `67db8c6a…` + extension `bff77676…`; RELCOUNT 3977, no TEXTREL.
- 10/10 `assets/Music/*.ogg` present and **Stored**.
- apktool **2.11.1** assembled (validates the smali), zipalign 4, apksigner (debug.keystore /
  `alias_name` / `zombiecafe`) → verify v1/v2/v3 **true**.
- In-APK: embedded lib sha = `67db8c6a…` ✔, dex contains `mMusicMode` + suppression string ✔.
- **APK:** `build/out/ZombieCafe-musicfix-v5.apk` = Desktop `ZombieCafe-v1.1.0-MusicFix-v5.apk`,
  sha256 `4f4af9fa…df52`. Not installed, not committed (per rules).

## 6. On-device test script (owner)

```bash
/mnt/c/platform-tools/adb.exe logcat -c
/mnt/c/platform-tools/adb.exe logcat -v time > logcat_v5.txt
```
1. Sideload the Desktop v5 APK. Launch → menu should play Theme V1 (regression check).
2. Enter cafe → within ~3 s a cafe cue should start (5 s fade-in). Let a track end → it should
   rotate V1 → Cue 2g → Cue 3g → V1 **continuously, more than one hop**.
3. Open the **map** and idle 30 s → must stay silent (log shows `startMusic suppressed: map mode`).
4. Return to cafe from the map → music must restart within ~3 s. **This is the v4 dead case.**
5. Enter a normal raid → a raid theme (Mini Cue 1g or 1V2 — random) should start after the intro
   moment and loop. Win → raid music stops, **Sting 2g** plays. Return to cafe → music back within ~3 s.
6. Raid again and **white-flag retreat** → the victory sting must NOT play (a different short
   sting, 6g, may play — report whether you want it removed).
7. Repeat cafe↔map↔raid a few times in one session — cafe music must come back every time.
8. Haunted House raid last (crash risk unchanged — Scudo bug is separate): boss theme should play.

Useful greps: `filename: Music/`, `fromNative_startMusic id:`, `suppressed: map mode`,
`fadeIn > 0`, `index:0 volume:`.

## 7. Remaining risks

1. **Scudo heap-corruption crash unchanged** (proven not the trampoline; needs its own hunt).
2. If the owner stays in the cafe for very long unbroken stretches, the native 2.5 s gap timer can
   accumulate (it ticks a few hundred ms during each Java rotation hand-off) and eventually fire
   one spurious native cue start mid-track (≈ once per ~10 track-ends). Harmless (track swaps to
   a cafe cue); can be tuned by raising the P3 constant.
3. Retreat/defeat sting (6g) still plays — awaiting owner verdict (see §6.6).
4. Friend-cafe attack stings use the same 1g→2g redirect (win sting there is also 2g now).
5. `javaFiksuRecordEvent` is now the gate thunk; any future patch must not "restore" Fiksu.
