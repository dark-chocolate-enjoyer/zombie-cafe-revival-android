# Android Music Recovery Fix

Date documented: 2026-07-01

This note documents the audio recovery/patch process used for the Android Zombie Cafe
revival tree. It is intended to let another maintainer reproduce the fix from a fresh
decompile without redoing the investigation.

## Target Tree

Main working tree:

```text
/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src
```

Patched Android bridge file:

```text
/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src/smali/com/capcom/zombiecafeandroid/CC_Android.smali
```

Recovered music asset folder:

```text
/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src/assets/Music
```

## Problem Summary

The broken build only carried one music file:

```text
src/assets/Music/Zombie Theme V1.ogg
```

The smali audio bridge also forced music slot `0` to load that same theme whenever
native code asked music to start. That meant the game could appear to have working
music while effectively pinning playback to the main cafe theme.

The native library still contains a larger music table and raid/theme strings, so the
one-track behavior is not the original intended structure. The Android bridge and the
asset folder were the practical repair points.

## Source APK Used For Asset Recovery

The Japanese Android APK provided by the project owner contained additional music:

```text
/mnt/c/Users/New/Documents/Balancing Zombie Cafe/ゾンビカフェ_ZombieCafeAndroid+1.7.0_APKPure.apk
```

Inspect the APK music folder:

```bash
JP_APK="/mnt/c/Users/New/Documents/Balancing Zombie Cafe/ゾンビカフェ_ZombieCafeAndroid+1.7.0_APKPure.apk"
unzip -l "$JP_APK" "assets/Music/*"
```

Recovered files found in that APK:

```text
Zombie Cafe Haunted House.ogg
Zombie Mini Cue 1V2.ogg
Zombie Mini Cue 1g.ogg
Zombie Mini Cue 2g.ogg
Zombie Mini Cue 3g.ogg
Zombie Sting 1g.ogg
Zombie Sting 2g.ogg
Zombie Sting 3g.ogg
Zombie Sting 6g.ogg
Zombie Theme V1.ogg
```

Copy them into the main WSL project:

```bash
REPO="/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival"
JP_APK="/mnt/c/Users/New/Documents/Balancing Zombie Cafe/ゾンビカフェ_ZombieCafeAndroid+1.7.0_APKPure.apk"

mkdir -p "$REPO/src/assets/Music"
unzip -j -o "$JP_APK" "assets/Music/*.ogg" -d "$REPO/src/assets/Music"
```

The copy used for this fix was byte-verified against the APK extraction.

If repacking from the repo's generated `build/` staging tree instead of `src`, sync the
same files there too:

```bash
mkdir -p "$REPO/build/assets/Music"
cp -f "$REPO/src/assets/Music/"*.ogg "$REPO/build/assets/Music/"
cp -f \
  "$REPO/src/smali/com/capcom/zombiecafeandroid/CC_Android.smali" \
  "$REPO/build/smali/com/capcom/zombiecafeandroid/CC_Android.smali"
```

This matters because a stale `build/` tree can produce a valid APK that still contains
only `Zombie Theme V1.ogg` or an older version of the smali bridge.

## Native Music Table Evidence

The native library still references more than one track:

```bash
strings "$REPO/src/lib/armeabi/libZombieCafeAndroid.so" \
  | grep -E 'Zombie (Jazz|Sting|Mini|Theme|Cafe Haunted|Stinger)|Cue[_ ]Transition'
```

Observed native music table order:

```text
0  Zombie Jazz.mp3
1  Zombie Sting 1g.mp3
2  Zombie Sting 2g.mp3
3  Zombie Sting 3g.mp3
4  Zombie Sting 4g.mp3
5  Zombie Sting 5g.mp3
6  Zombie Sting 6g.mp3
7  Zombie Mini Cue 1g.mp3
8  Zombie Mini Cue 2g.mp3
9  Zombie Mini Cue 3g.mp3
10 Zombie Theme V3.mp3
11 Zombie Theme V4.mp3
12 Zombie Theme V5.mp3
13 Zombie Theme V1.mp3
14 Zombie Stinger 1g - Short.mp3
15 Zombie Mini Cue 1V2.mp3
16 Cue Transition Groove gr.mp3
17 Cue_Transition_Groove_2_gr.mp3
18 Cue_Transition_Groove_3_grc.mp3
19 Zombie Cafe Haunted House.mp3
```

`CC_Android.fromNative_loadMusic(I, String)` converts `.mp3` to `.ogg` and prepends
`Music/`, so native requests for `Zombie Mini Cue 2g.mp3` resolve to:

```text
assets/Music/Zombie Mini Cue 2g.ogg
```

Other native strings supporting context-specific music:

```bash
strings "$REPO/src/lib/armeabi/libZombieCafeAndroid.so" \
  | grep -E 'Resources::Audio::MUSIC_FILES|ZombieCafe_(NUM_ENEMY_THEMES|BOSS_THEME|MUSIC_CHANNELS)|GameStateCafe_MUSIC_INTERVAL|GAMESTATE RAID|START A RAID|EnemyLevel=%d Theme=%d|Theme=%d'
```

Important strings/symbols:

```text
Constants::GameStateCafe_MUSIC_INTERVAL
Constants::ZombieCafe_MUSIC_CHANNELS
Constants::ZombieCafe_BOSS_THEME
Constants::ZombieCafe_NUM_ENEMY_THEMES
Resources::Audio::MUSIC_FILES
START A RAID
GAMESTATE RAID
EnemyLevel=%d Theme=%d
Theme=%d
GAMESTATE RAID INIT
```

This supports the conclusion that normal cafe music, raid music, stingers, and the
haunted house/boss cafe music were meant to be separate paths.

## Files Still Missing

The Japanese APK did not contain every file referenced by the native table. These
remain missing after the recovery:

```text
Zombie Jazz.ogg
Zombie Sting 4g.ogg
Zombie Sting 5g.ogg
Zombie Theme V3.ogg
Zombie Theme V4.ogg
Zombie Theme V5.ogg
Zombie Stinger 1g - Short.ogg
Cue Transition Groove gr.ogg
Cue_Transition_Groove_2_gr.ogg
Cue_Transition_Groove_3_grc.ogg
```

Because those files are still absent, the smali patch includes a safe fallback to
`Zombie Theme V1.ogg` when native requests a track that cannot be opened.

## Audio Patch Logic

Patch both the Android audio bridge and the native `loadAndPlayMusic` stub.
When editing smali by hand, keep label changes method-local. Labels such as `:cond_2`
are reused in different methods, so never do global label renames across the whole
file.

### 1. Keep music arrays as playback channels

Method:

```text
CC_Android.fromNative_initSound(IIZ)Z
```

Old behavior:

- The static constructor allocated `mMusics` and `mMusicFiles` as one-element arrays.
- `fromNative_initSound` only stored the native sound/music counts.

New behavior:

- Allocate two `MediaPlayer` slots and two music filename slots in the static
  constructor.
- Keep `fromNative_initSound` as a count-storing method only.
- Do not resize the arrays from `numMusics`.

The Japanese 1.7.0 APK confirms that these arrays are playback channels, not the full
music-track table. That version uses two `MediaPlayer` slots while the separate music
table contains about twenty possible filenames.

Earlier testing tried resizing the arrays from native `numMusics`. That was too broad:
`numMusics` is track-table sized, while Java playback uses channel slots. It also risks
clearing already loaded player state if `fromNative_initSound` is called after an
early load.

### 2. Default music volume to audible

Method:

```text
CC_Android.<clinit>()V
CC_Android.fromNative_setMusicVolume(I, F)Z
```

Old behavior:

- `mMusicVolume` initialized to `0.0f`.
- `fromNative_setMusicVolume` only stored `mMusicVolume` after a `MediaPlayer` already
  existed for the requested slot.

New behavior:

- Initialize `mMusicVolume` to `1.0f`, matching the Japanese APK.
- Store `mMusicVolume` as soon as native asks to set music volume, even if the
  requested `MediaPlayer` has not been loaded yet.
- If a player exists, still apply the volume to that live player.

This fixes a silent-music failure mode introduced by lazy/fallback loading: if native
sets the volume before Java has created the `MediaPlayer`, the later fallback-loaded
track must still inherit the requested volume instead of staying at the class default.

### 3. Restore native loadAndPlayMusic

Method:

```text
ZombieCafe::loadAndPlayMusic(int channel, int musicId, float volume, bool loop)
```

Native symbol:

```text
_ZN10ZombieCafe16loadAndPlayMusicEiifb
```

Old behavior:

- The function was a two-byte native stub: `bx lr`.
- `GameStateCafe::tick(long)` still called this function for cafe music rotation, but
  the call returned immediately and never loaded or started the requested music.

Japanese APK behavior:

- The Japanese native function is real. It calls a Java helper equivalent to
  `fromNative_loadAndPlayMusic(channel, musicId, volume, loop)`.
- That Java helper resolves `musicId` through `GetMusicFilename`, unloads the old
  track, loads the requested track, applies the loop flag, and starts playback.

Revival patch:

- The current build does not have the Japanese `javaLoadAndPlayMusic` native helper,
  so raw-copying Japanese bytes is not safe.
- The current stub now branches to a small Thumb trampoline placed in an unused legacy
  Fiksu analytics function body (`javaFiksuPromptForRating`).
- The trampoline uses this build's existing native helpers:

```text
ZombieCafe::unloadMusic(channel)
ZombieCafe::loadMusic(channel, musicId)
CCSound::StartMusic(channel, volume, loop)
```

Patched native disassembly:

```text
0011fc70: b.w #0x17de40

0017de40: push {r4, r5, r6, r7, lr}
0017de42: mov  r4, r0        ; this
0017de44: mov  r5, r1        ; channel
0017de46: mov  r6, r2        ; musicId
0017de48: mov  r7, r3        ; volume bits
0017de4a: mov  r0, r4
0017de4c: mov  r1, r5
0017de4e: bl   ZombieCafe::unloadMusic
0017de52: mov  r0, r4
0017de54: mov  r1, r5
0017de56: mov  r2, r6
0017de58: bl   ZombieCafe::loadMusic
0017de5c: mov  r0, r5
0017de5e: mov  r1, r7
0017de60: ldr  r2, [sp, #0x14] ; loop flag
0017de62: bl   CCSound::StartMusic
0017de66: pop  {r4, r5, r6, r7, pc}
```

This is the native piece that lets the existing `GameStateCafe::tick(long)` music
rotation calls actually reach Java again.

### 4. Make setMusicLoop real

Method:

```text
CC_Android.fromNative_setMusicLoop(I, Z)Z
```

Old behavior:

- Validated that `mMusics[id]` existed.
- Returned success without calling `MediaPlayer.setLooping(...)`.

New behavior:

- Validates the music slot as before.
- Calls:

```text
MediaPlayer.setLooping(loop)
```

This matters because `fromNative_loadMusic` prepares every track with looping enabled
by default. The restored native `loadAndPlayMusic` passes the native loop flag through
`CCSound::StartMusic`, which then calls `fromNative_setMusicLoop`. For normal cafe
cues, the native call sites pass `loop = false`, allowing a cue to finish so the cafe
tick can advance to the next track.

### 5. Remove the forced theme reload from startMusic

Method:

```text
CC_Android.fromNative_startMusic(I)V
```

Old behavior:

- On every start request, it forced:

```text
fromNative_loadMusic(0, "Zombie Theme V1.ogg")
```

That overwrote native music selection with the main cafe theme.

New behavior:

- Log the requested music ID.
- Validate that `mMusics` exists and that the requested ID is within bounds.
- Use the already loaded `MediaPlayer` for that slot.
- If the slot is empty, lazily load `Zombie Theme V1.ogg` into the requested slot as
  a fallback.
- Start playback only if the selected player exists and is not already playing.

The fallback keeps the game from crashing or going silent when the native table asks
for one of the still-missing files.

### 6. Add a loadMusic failure fallback

Method:

```text
CC_Android.fromNative_loadMusic(I, String)Z
```

Existing useful behavior kept:

- Converts `.mp3` filenames from native to `.ogg`.
- Prepends `Music/`.
- Opens the file from the Android asset manager.
- Creates and prepares a `MediaPlayer`.
- Sets looping and music volume.

New behavior:

- If opening/preparing the requested asset throws, clear that music slot.
- If the failed path is not already `Music/Zombie Theme V1.ogg`, recursively call
  `fromNative_loadMusic(id, "Zombie Theme V1.ogg")`.
- If even `Zombie Theme V1.ogg` fails, return failure.

This keeps missing tracks recoverable without hiding the fact that a fallback happened;
the method logs:

```text
fromNative_loadMusic fallback: Zombie Theme V1.ogg
```

## Track Behavior Notes

Based on the native strings, disassembly scan, and owner memory:

- Normal cafe gameplay is expected to use `Zombie Theme V1.ogg`, `Zombie Mini Cue 2g.ogg`,
  and `Zombie Mini Cue 3g.ogg`.
- `Zombie Mini Cue 1g.ogg` is likely raid/enemy-cafe music, not normal cafe background.
- `Zombie Cafe Haunted House.ogg` is boss/Halloween house raid music, not part of the
  normal gameplay loop.
- `Zombie Sting 1g.ogg`, `Zombie Sting 2g.ogg`, `Zombie Sting 3g.ogg`, and
  `Zombie Sting 6g.ogg` are likely stingers or transition cues rather than looping
  background tracks.
- `Zombie Mini Cue 1V2.ogg` may be a revised/alternate cue, but its exact trigger was
  not proven.

If native requests one of the still-missing tracks, the patched bridge falls back to
`Zombie Theme V1.ogg`.

## Verification Commands

Confirm the recovered assets exist:

```bash
cd /home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival
find src/assets/Music -maxdepth 1 -type f -printf '%f\n' | sort
```

Confirm patched smali markers:

```bash
grep -n \
  -e '0x3f800000' \
  -e 'sput p1, Lcom/capcom/zombiecafeandroid/CC_Android;->mMusicVolume:F' \
  -e 'setLooping(Z)V' \
  -e 'fromNative_startMusic id:' \
  -e 'fromNative_startMusic fallback: Zombie Theme V1.ogg' \
  -e 'fromNative_loadMusic fallback: Zombie Theme V1.ogg' \
  src/smali/com/capcom/zombiecafeandroid/CC_Android.smali
```

Confirm native loadAndPlayMusic patch:

```bash
readelf -sW src/lib/armeabi/libZombieCafeAndroid.so \
  | grep -E 'loadAndPlayMusic|javaFiksuPromptForRating|loadMusicEii|StartMusicEjfj'
```

Expected key addresses in the currently patched library:

```text
0x0011fc71  ZombieCafe::loadAndPlayMusic
0x0017de41  javaFiksuPromptForRating trampoline body
0x001236d9  ZombieCafe::unloadMusic
0x00123741  ZombieCafe::loadMusic
0x00192f3d  CCSound::StartMusic(unsigned int, float, unsigned int)
```

Confirm the old forced slot-zero load is gone:

```bash
grep -n -B4 -A4 'Zombie Theme V1.ogg' \
  src/smali/com/capcom/zombiecafeandroid/CC_Android.smali
```

The remaining `Zombie Theme V1.ogg` references should be fallback paths, not an
unconditional `fromNative_loadMusic(0, "Zombie Theme V1.ogg")` at the start of
`fromNative_startMusic`.

Check git status for the expected fix files:

```bash
git status --short -- \
  src/smali/com/capcom/zombiecafeandroid/CC_Android.smali \
  src/assets/Music \
  docs/reverse/android_music_recovery_fix.md
```

Expected changed/added files:

```text
M  src/smali/com/capcom/zombiecafeandroid/CC_Android.smali
M  src/lib/armeabi/libZombieCafeAndroid.so
?? docs/reverse/android_music_recovery_fix.md
?? src/assets/Music/Zombie Cafe Haunted House.ogg
?? src/assets/Music/Zombie Mini Cue 1V2.ogg
?? src/assets/Music/Zombie Mini Cue 1g.ogg
?? src/assets/Music/Zombie Mini Cue 2g.ogg
?? src/assets/Music/Zombie Mini Cue 3g.ogg
?? src/assets/Music/Zombie Sting 1g.ogg
?? src/assets/Music/Zombie Sting 2g.ogg
?? src/assets/Music/Zombie Sting 3g.ogg
?? src/assets/Music/Zombie Sting 6g.ogg
```

`Zombie Theme V1.ogg` may not appear in git status if it already existed.

## Build Note

This process documents source-tree changes. A temporary unsigned APK was built from a
copy of `src`, and another from the synced `build/` staging tree, to verify the smali
compiles and the recovered music files package as stored/uncompressed assets:

```text
/tmp/zc_audio_fix_unsigned.apk
/tmp/zc_audio_fix_buildtree_unsigned.apk
/tmp/zc_loadandplay_unsigned.apk
```

Both temporary builds contained all ten recovered `assets/Music/*.ogg` files with ZIP
method `Stored`. `/tmp/zc_loadandplay_unsigned.apk` additionally verifies the restored
native `loadAndPlayMusic` trampoline and real `setMusicLoop` bridge compile into an
APK. These APKs were not aligned, signed, installed, or runtime-tested.
