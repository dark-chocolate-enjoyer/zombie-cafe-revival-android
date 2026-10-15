# Follow-up Prompt for Claude Code — JP Revival Pass 2 (safe tooling only)

Copy-paste the block below as the next session's prompt. It stays inside the
same safety envelope: parsers, text tooling, crosswalk generation, and balance
snapshots. No APK modification, no repacking, no billing/network/signature work.

---

You are continuing the JP Zombie Cafe 1.7.0 preservation project. Pass 1
(complete) lives in `jp/research/pass1_inventory_schema/` in the
`zombie-cafe-revival` repo — read its `README.md`, `jp_data_schema_report.md`,
and `build_pipeline_questions.md` first.

This pass is implementation of **safe, read-only tooling and data work only**:
no APK/lib/smali modification, no repacking or signing, no billing/network/DRM
work, no balance edits applied to game files.

Paths:
- English revival repo: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival`
- Preserved JP APK (verify SHA-256 `015D265D0C1A6E68AAFF50E3E01EE792A41D6192CE7823476581E4D573508942` before use, extract to scratch space only):
  `C:\Users\New\Documents\Balancing Zombie Cafe\outputs\backups\jp_original\ZombieCafeAndroid_JP_1.7.0_APKPure.original.apk`
- Output folder: `jp/research/pass2_codecs_quests/`

Tasks, in priority order:

1. **Go parsers for the JP formats** (documented in pass 1's schema report),
   following the existing `tool/file_types/*.go` conventions:
   `food_jp.go`, `furniture_jp.go` (reader + writer), and wire them into
   `resource_manager -jp` deserialize/serialize maps. Acceptance gate:
   decode → re-encode **byte-identical round-trip** for
   `foodData.bin.mid`, `furnitureData.bin.mid`, and `characterData.bin.mid`
   (fix `character_jp.go`'s bool-tolerance for record 148's flag byte = 10:
   read/write it as a byte, never panic). Add a round-trip test.

2. **quest.bin.mid schema reverse-engineering** (data-only, no lib changes):
   derive the record structure (count ≈ 1,020; fields include `level`/`na`
   markers, reward values, and text with `[NUM]/[RECIPE]/[CHARA]/[GENDER]`
   placeholders), validate by exact-EOF parse, document it in the same style as
   pass 1's schema report, and emit `quest_text_inventory.csv`
   (`record_index, field, jp_text, placeholders, notes`).

3. **Bitmap font audit:** decode `assets/fonts/toge20/28.fnt.mid` and
   `thunder_12pt.fnt.mid` (BMFont-like; derive schema), and report ASCII glyph
   coverage per atlas in `font_coverage_report.md`.

4. **Baked-text image sweep:** use `cctpacker`/existing unpack tooling to dump
   the JP-only sheets (`shopImages`, `iphone4_gatyaImages`,
   `iphone4_prizeMenuImages`, `zcImages`, `menutitleimages`, `dialogImages`)
   to PNGs in scratch space, view them, and update the pass-1 image-text list
   with confirmed yes/no per sheet.

5. **Crosswalk regeneration tool:** port pass 1's ad-hoc crosswalk build into a
   repeatable script (Go or Python under `tool/`), reading the decoded JSON +
   EN revival JSON and emitting the same CSV columns, so translation progress
   can be re-merged as columns fill in. Include the strings piecewise offset
   table from pass 1 and its split-string flags.

6. **Native-lib string inventory (read-only):** run a `strings`-style scan of
   the JP `libZombieCafeAndroid.so` from the scratch extraction, filter to
   likely player-visible text/format templates, and write
   `jp_lib_string_inventory.md`. Do not disassemble beyond string extraction
   and do not modify anything.

7. Resolve the strings-file drift zones (JP lines 316–357, 431–519, 636–661)
   into exact JP↔EN line pairings, updating
   `translation_crosswalk_strings_and_html.csv` confidences to high.

Deliverables: updated tools under `tool/` (committed only if asked), the new
reports/CSVs under `jp/research/pass2_codecs_quests/`, and a short summary of
schema discoveries appended to a `SCHEMA_CHANGELOG.md`.

---

## Explicitly deferred (needs separate authorization, not in the next pass)

- Any repack/build of a JP APK, even unmodified.
- Offline conversion (billing/GCM/AppDriver surface changes).
- Applying any balance change to data files.
- Native-lib patches of any kind.
