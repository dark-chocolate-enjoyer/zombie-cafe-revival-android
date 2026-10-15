# Technical write-up

What was changed in the game, and how each problem was found. How I ran the AI agents that did the
work is in [AI workflow](AI_WORKFLOW.md).

---

## English version (game version 1.1.2.0a)

Built on [Airyzz's revival](https://github.com/Airyzz/zombie-cafe-revival) (2023), which decoded the
APK, wrote the Go tools that convert the game's binary data files to JSON and back, and set up the
build. I added three releases: v0.1 (9 June 2026), v1.0 (22 June) and v1.1 (3 July).

### Install and run (v0.1)

Each fix exposed the next problem:

1. Raised `targetSdkVersion` from 14 to 24, since current Android refuses to install apps that
   target very old versions.
2. Removed the game library's text relocation. Targeting 23+ makes Android's linker reject libraries
   that patch their own code while loading (`DT_TEXTREL`). Only 1 of the library's 4,161 relocations
   touched code: an `R_ARM_RELATIVE` at `0x5ddcc` in the `__cxa_finalize` unload path. A 23-byte
   in-place patch makes that function return immediately (`bx lr`), retypes the relocation to
   `R_ARM_NONE`, and replaces `DT_TEXTREL` with `DT_RELCOUNT` (3,977).
3. Made `getDeviceId()` and `getSimSerialNumber()` in `DeviceType.smali` return a constant, because
   Android 10 and later throw a `SecurityException` there.

The game is still 32-bit ARM code, so it needs a phone that supports 32-bit apps.

### Music (v1.1)

The game's music table expected tracks the APK didn't have: it carried only `Zombie Theme V1.ogg`. I
added the 9 missing tracks from the Japanese 1.7.0 APK, stored uncompressed because `MediaPlayer` reads
them straight out of the APK.

Music still stopped after the first track. Five test builds fixed real bugs along the way: a
stubbed-out native `loadAndPlayMusic`, a one-shot Java flag that skipped `start()`, raid tracks
starting at volume 0, the engine's 0–2048 volume scale passed straight to an API that expects 0–1,
and no track rotation. The root cause was in `CCSound::StartMusic`: it keeps a "currently playing" pointer
(`CCSound+0x34`) that nothing ever clears, so every later start request was dropped, and the cafe's
`IsMusicPlaying()` check, which reads the same pointer, thought music was playing forever.

The fix is 82 bytes of Thumb code: remove the early exit, make the cafe check also ask whether Java's
player is really playing, and restart the cafe music about 2.5 seconds after re-entry. A small Java
state machine picks the track: three rotating cafe tracks, silence on the map, and raid and victory
cues.

### The memory crash (July–September 2026, unsolved)

The English version crashes with `Scudo ERROR: corrupted chunk header`, mostly when leaving the cafe.
(How Scudo works is explained in the Japanese section below.) Over two months, several models tried to
fix it by reading the code:

| When | Model | Attempt | Result |
|---|---|---|---|
| 4 Jul | Claude Opus 4.8 | Analysed every crash log | Heap corruption that predates my changes; a control build without the music patch still crashed |
| 5–7 Jul | Claude Fable 5 | Nulled dangling path pointers at 8 sites; checked `Cafe::~Cafe` for double frees | The crash moved but didn't stop; one build crashed 17 s into an idle cafe with no game code on the stack |
| 8 Jul | Claude Fable 5 | Bounds audit of the pathfinding grid | Found a `SetNode(-1)` write that can go out of bounds |
| 17 Jul | "Sol Ultra" | Repair plan built around that write | Never built |
| 7–11 Sep | ASTRA, Claude Opus 5 | Showed the `SetNode(-1)` write lands in padding; all 45 victims were 48-byte blocks, so padded `CafeTile` from 24 to 40 bytes | Passed on the emulator, crashed on the phone in 28 s |

None of it worked because every theory was inferred from the victims, the blocks Scudo caught, and a
victim is just whatever sat next to the real culprit. The emulator couldn't help either: its Android 9
allocator has no header checksums. No tool that catches the bad write as it happens was ever run on
the English build. I paused it on 25 September and moved to the Japanese version, where that approach
found the culprit in a day. The English library doesn't contain that function, so the English cause is
still unknown.

### Rebalance (v1.0 and v1.1)

Every balance change went through the same loop:

- The agent decodes the data and measures every dish (profit and XP per minute, payback) and
  character (stats per cost, cash against Toxin).
- It proposes changes in a report-only workbook with a reason for each row. ChatGPT reviewed the plans
  as a second opinion.
- I review every row, and only approved rows go in.
- A script applies them after checking each current value matches what the proposal expected, keeps
  values within the game's 16-bit limits, and saves a rollback. Then I play-test.

v1.0 changed 164 of 216 dishes and 50 characters; v1.1 reworked the characters, and 187 of 219 now
differ from the original. The checks caught a debug value leaking from a test build and an attempt to
apply a stage twice. A change that went further than I'd asked (cook speed applied to chefs instead
of workers) was rolled back and became a standing rule.

---

## Japanese version (game version 1.7.0)

Capcom's final Japanese release (2016) has far more content than the English game. v0.1 was released
on 10 October 2026 in its own repo,
[Zombie Cafe JP](https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-jp).

### Foundations

- Go readers and writers for 9 Japanese data files, tested to rebuild every file byte for byte.
- One command builds the English APK. Text is copied from the English game wherever the same item
  exists. 761 strings in the native library are overwritten in place, and 84 that didn't fit were
  moved with every reference repointed. Resource strings, Java dialogs and 99 sprites are translated
  too.
- An 8-byte patch at `0x113b88` makes the store's cash packs call `ZombieCafe::addToxin`, giving an
  offline cash-to-Toxin exchange.
- `targetSdkVersion` raised from 16 to 24, and 9 device-ID calls replaced with a constant. This library
  has no text relocations.
- The game is told it has no internet connection, so it sends no requests to the dead servers.

### The cafe → map crash (fixed in v0.1)

The Japanese version had the same crash as the English one: `Scudo ERROR: corrupted chunk header`,
mostly when leaving the cafe for the map or the meat locker.

Scudo is the memory manager Android 11 and later use for apps, and it isn't the cause. It puts a small
header in front of every block of memory the game asks for, with a checksum computed from the block's
size, state and address, and re-checks it when the block is freed. A mismatch means something has
written over the header, so Scudo stops the app. The memory managers of 2016, when the game was last
updated, had no such check, so bugs that did no visible harm back then now crash the game.

Leaving the cafe deconstructs it (`GameStateCafe::uninit` → `Cafe::~Cafe`), freeing hundreds of objects
at once: walls, furniture, tasks, text. That's where the damage is found, not where it happens. The bad
write could have been seconds or minutes earlier, and the crash never names the culprit. In my own
play-testing, the longer I played, the more likely the next trip was to crash; the automated tests
showed every trip in and out is another roll of the dice, and even a single trip straight after launch
crashed about half the time.

So instead of reading code, the agents caught the write as it happened, with debug builds using
GWP-ASan (sampled blocks sit next to a guard page, so a bad access faults at the exact instruction) and
an adb script that launched the game, entered the cafe, pressed Map and recorded the outcome, over and
over. Along the way, experiments ruled out server traffic and a threading race.

GWP-ASan caught it in Capcom's `javaGetDeviceInfoForURL`, which runs on every save, on the way into
and out of the cafe. It writes a terminating zero one byte past the end of its buffer:

```
len = GetArrayLength(info)     // 80 on the Galaxy A54
buf = malloc(len)              // no room for a terminator
copy len bytes into buf
buf[len] = 0                   // strb r3, [r4, r5] at 0x29928a: one byte past the end
```

Scudo stores blocks in fixed-size slots with a 16-byte header, so 80 + 16 fills a 96-byte slot exactly,
and the zero lands on the next block's header:

```
 one 96-byte slot                   the next 96-byte slot
[ header | device-info text (80) ] [ header | a wall, some text... ]
                                    ^
                      the stray zero lands here
```

When that neighbour is freed during the deconstruction, its checksum fails. In 2016 the zero landed
in spare bytes, and even now it only bites when the text plus the header fills a slot exactly, which
depends on the phone. The agent first dismissed it by assuming an 8-byte header.

The fix is 4 bytes: the `blx malloc` at `0x299274` now calls a 20-byte helper that allocates one extra
byte, written over an unused function (`String::Test()`). The build with this fix and the two below
survived 20 of 20 automated rounds. A control build, identical except for those 4 bytes, crashed 10 times in 20, and all
10 crash addresses were exact multiples of 96 bytes apart, the slot size above. That build was released
as v0.1.

### Two more bugs found along the way

The debug builds also found two other bugs in Capcom's code. Neither was the map crash, but both are
fixed in v0.1:

- Resuming a saved raid walks a list the game has just deleted, because of a copy-paste typo
  (`r6` instead of `r4` at `0x17302a`). It worked by accident while old memory managers reused the same
  memory. Fixed with one byte.
- `StringBuffer::toString()` leaves no room for a terminating zero, so joining strings read one byte past
  the end. Its `malloc` call now uses the same 20-byte helper.
