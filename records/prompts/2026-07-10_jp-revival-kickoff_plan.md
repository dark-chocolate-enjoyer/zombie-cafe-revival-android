# Zombie Cafe JP Revival - Fable Starting Plan

Date: 2026-07-10

## Objective

Create a Japanese Zombie Cafe revival build that is translated into natural, player-facing English, playable on modern/32-bit-capable Android runtimes, has an offline way to acquire toxin, and is balanced to the same fairness standard as Zombie Cafe Revival v1.1.

This should start as a preservation, audit, translation-inventory, and tooling pass. Do not jump straight to patching the APK.

## Reference Locations

- English revival repo: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival`
- JP APK in Windows workspace: `C:\Users\New\Documents\Balancing Zombie Cafe\ゾンビカフェ_ZombieCafeAndroid+1.7.0_APKPure.apk`
- Preserved JP backup APK: `C:\Users\New\Documents\Balancing Zombie Cafe\outputs\backups\jp_original\ZombieCafeAndroid_JP_1.7.0_APKPure.original.apk`
- Preserved JP backup SHA-256: `015D265D0C1A6E68AAFF50E3E01EE792A41D6192CE7823476581E4D573508942`
- JP temp decompile used for this audit: `/tmp/zombiejp/apktool`
- JP temp extracted native lib: `/tmp/zombiejp/libZombieCafeAndroid_jp.so`
- JP temp decoded character JSON: `/tmp/zombiejp/unpacked-data/characterData.bin.mid.json`
- JP temp parsed food JSON prototype: `/tmp/zombiejp/food_jp_parsed.json`

## Important English-Revival Docs

- Toxin exchange: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/docs/balance/rebalance_v1_stage_i_toxin_exchange/README.md`
- Toxin patch plan: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/docs/balance/rebalance_v1_stage_i_toxin_exchange/toxin_exchange_patch_plan.md`
- Runtime extension source: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src/lib/cpp/ZombieCafeExtension.cpp`
- English food data: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src/assets/data/foodData.bin.mid.json`
- English character data: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src/assets/data/characterData.bin.mid.json`
- English furniture data: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src/assets/data/furnitureData.bin.mid.json`
- English help text: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/src/assets/data/help_amazon.html`
- Food balance summary: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/docs/balance/v1.0_balance_summary.md`
- Character final summary: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/docs/balance/rebalance_v1_stage_o_character_rebalance/STAGE_O_SUMMARY.md`
- Android target/device-ID fix: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/docs/compat/device_id_security_exception_fix.md`
- TEXTREL test build notes: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/docs/compat/textrel_patch_test_build.md`

## Findings So Far

### JP APK Identity

- Package: `com.capcom.zombiecafeandroidJP`
- Version: `ZombieCafeAndroid 1.7.0`
- versionCode: `78`
- minSdkVersion: `10`
- targetSdkVersion: `16`
- Native ABI: `lib/armeabi/libZombieCafeAndroid.so` only
- No `libZombieCafeExtension.so` is present in the JP APK.
- `ZombieCafeAndroid.smali` loads only `System.loadLibrary("ZombieCafeAndroid")`.

### JP Native Library

- Path: `/tmp/zombiejp/libZombieCafeAndroid_jp.so`
- SHA-256: `e0fbd1736894a0bd87f2ba0db930a47db9e110a5f2015ddb2e594add3ab30433`
- Size: `5,086,832` bytes
- ELF: 32-bit ARM, EABI5, ARMv5TE / Thumb-1
- `readelf -d` shows no `DT_TEXTREL` / `TEXTREL`.
- This is not byte-compatible with the English revival library. Do not reuse English offsets.
- Useful exported symbols exist:
  - `ZombieCafe::addCash(int)` at `0x00229f41`
  - `ZombieCafe::addToxin(int, bool)` at `0x00229fa1`
  - `ZombieCafe::getCash()` at `0x00229f31`
  - `ZombieCafe::getToxin()` at `0x0022a025`
  - `javaBuyStuff` at `0x0029913d`
  - `ZombieCafe::GiveBoughtToxin(int, int)` at `0x0023fbe9`
  - `GameStateCafe::completeStorePurchase(GameStateCafe*)` at `0x00113711`

### Existing English Toxin Patch

English revival uses `libZombieCafeExtension.so`.

Relevant source in `src/lib/cpp/ZombieCafeExtension.cpp`:

```cpp
/* Patch to change Money Buy to Toxin Buy
  000ab018  d623       movs    r3, #0xd6    <-- change this offset to 0xb8
  000ab01a  5b00       lsls    r3, r3, #1   <-- prevent this leftshift
*/
Memory::setProtection((void*)(base + 0xab018), 50, PROT_READ | PROT_WRITE | PROT_EXEC);
*(char*)(base + 0x000ab018) = 0xb8;
Memory::setNop((char*)(base + 0x000ab01a), 2);
```

This redirects the credit from money to toxin. The data rows then define the exchange amounts/prices.

English final toxin exchange rows, `furnitureData.bin.mid.json`, rows 182-185:

| Row | Name | Price | PurchaseWithToxin | Type | Category | BuyMoneyAmount |
|---:|---|---:|---|---:|---:|---:|
| 182 | 10 Toxin | 30000 final / 20000 original Airyzz | false | 10 | 5 | 10 |
| 183 | 30 Toxin | 75000 final / 50000 original Airyzz | false | 10 | 5 | 30 |
| 184 | 175 Toxin | 375000 final / 250000 original Airyzz | false | 10 | 5 | 175 |
| 185 | 750 Toxin | 1500000 final / 1000000 original Airyzz | false | 10 | 5 | 750 |

### JP Currency Cluster

JP `furnitureData.bin.mid` has the matching row neighborhood, but currently as cash packs. Raw offsets around `0x6357` show:

| Likely Row | JP Name | Price | PurchaseWithToxin | Type | Category | BuyMoneyAmount | Description |
|---:|---|---:|---|---:|---:|---:|---|
| 182 | `10000ドル` | 10 | true | 10 | 6 | 10000 | `10000ドルを購入。` |
| 183 | `50000ドル` | 25 | true | 10 | 6 | 50000 | `50000ドルを購入。` |
| 184 | `250000ドル` | 100 | true | 10 | 6 | 250000 | `250000ドルを購入。` |
| 185 | `1000000ドル` | 350 | true | 10 | 6 | 1000000 | `1000000ドルを購入。` |

This strongly suggests the Airyzz-style change is:

1. Convert these four data rows from toxin-cost cash packs into cash-cost toxin packs.
2. Add a JP-native equivalent of the money-credit-to-toxin-credit patch.
3. Ensure the UI display, affordability check, deduction, and credit all agree.

Do not do this as a brittle same-length hex edit. Labels/descriptions and file lengths should be handled by a real parser/packer.

### JP Data Tooling State

The existing resource manager has partial JP support:

- `tool/resource_manager/main.go` has `-jp`.
- `tool/file_types/character_jp.go` parses JP character records.
- JP character decode succeeded: 1,724 records.
- JP food uses a different schema but is easy to parse:
  - Count: one byte.
  - 234 rows.
  - Strings are 16-bit big-endian length + UTF-8.
  - Fields validated to EOF:
    `Name, Price, UnlockLevel, CookTimeMinutes, Servings, PricePerSeving, ExperiencePoints, ImageID, U7, U8`.
- JP furniture differs from English around rating/tail fields. Full parser/packer still needed.

### Translation Requirement

The JP revival must be fully translated into English before release. The goal is not a literal translation. The goal is text that reads like a polished English Zombie Cafe build from the player's point of view.

Translation principles:

- Prefer natural game/UI language over strict word accuracy.
- Cross-reference the English revival data first. If the JP row clearly corresponds to an English revival row, use the English name/description as the primary reference and adapt only when JP content differs.
- Preserve jokes, flavor, and character personality where possible, but rewrite awkward literal phrasing.
- Keep gameplay clarity ahead of literary flourish for buttons, store text, help text, errors, tutorials, and purchase confirmations.
- Preserve JP-only/event content as JP-version flavor, translated into idiomatic English.
- Maintain a translation memory/crosswalk so every JP source string can be traced to its English result and source.
- Flag text that is embedded in images, native strings, or smali hardcoded strings separately from data-file strings.
- Check font and layout impact. English strings may be longer in some UI boxes and shorter in others; final translation requires render/playtest review.

Translation surfaces to inventory:

- `assets/data/foodData.bin.mid`
- `assets/data/characterData.bin.mid`
- `assets/data/furnitureData.bin.mid`
- `assets/data/strings.bin.mid`
- HTML assets: `about.html`, `help.html`, `errorMsg.html`, EULA if shown in-game
- Android resources under `res/values*`
- hardcoded smali strings, especially in `ZombieCafeAndroid.smali` and billing/support flows
- native `.rodata` strings if they appear in UI
- image assets with baked Japanese text

### Go Tooling Note

The repo-level `go.work` says `go 1.23`, but WSL currently has Go `1.22.2`. The individual tools are `go 1.20`.

Temporary workaround used:

```bash
printf 'go 1.22

use (
    /home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/tool/build_tool
    /home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/tool/resource_manager
    /home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/tool/file_types
    /home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival/tool/cctpacker
)
' > /tmp/zombiejp/go.work
```

Then run tools with:

```bash
GOWORK=/tmp/zombiejp/go.work go run ./tool/resource_manager ...
```

## Where We Begin

Begin with a Fable first pass that preserves the original JP APK, builds a translation/data inventory, and creates a patch plan/tool plan. It may create new audit artifacts and parser prototypes, but it must not modify the preserved backup or overwrite the original APK.

Recommended output folder:

```text
fable_jp_revival_first_pass_v1/
```

Required deliverables:

- `README.md`
- `backup_manifest.md`
- `jp_apk_inventory.md`
- `jp_data_schema_report.md`
- `jp_food_balance_snapshot.csv`
- `jp_character_balance_snapshot.csv`
- `jp_furniture_currency_rows.md`
- `translation_scope_inventory.md`
- `translation_style_guide.md`
- `translation_crosswalk_food.csv`
- `translation_crosswalk_characters.csv`
- `translation_crosswalk_furniture.csv`
- `translation_crosswalk_strings_and_html.csv`
- `translation_unmatched_or_jp_only_review.md`
- `text_layout_and_font_risk_report.md`
- `toxin_exchange_reverse_engineering_plan.md`
- `android_compatibility_plan.md`
- `balance_porting_strategy.md`
- `build_pipeline_plan.md`
- `claude_code_followup_prompt.md`

## Ready-To-Paste Fable Prompt

You are auditing the Japanese Android version of Zombie Cafe 1.7.0 so we can create a JP revival build. The target build must be translated into natural English, balanced like Zombie Cafe Revival v1.1, support offline toxin acquisition, and run on the same Android/BlueStacks targets. Do not edit source files and do not build an APK yet. Produce a first-pass technical and translation plan under `fable_jp_revival_first_pass_v1/`.

Context:

- English revival repo: `/home/itzsweetz/projects/zombie-cafe/repos/zombie-cafe-revival`
- JP APK: `C:\Users\New\Documents\Balancing Zombie Cafe\ゾンビカフェ_ZombieCafeAndroid+1.7.0_APKPure.apk`
- Preserved JP backup APK: `C:\Users\New\Documents\Balancing Zombie Cafe\outputs\backups\jp_original\ZombieCafeAndroid_JP_1.7.0_APKPure.original.apk`
- Preserved JP backup SHA-256: `015D265D0C1A6E68AAFF50E3E01EE792A41D6192CE7823476581E4D573508942`
- The English revival already has a balanced food/character economy, an Airyzz toxin exchange patch, and Android compatibility notes.
- The JP build has more content and different data schemas, so do not blindly copy row edits.
- Translation must read like an English game, not like a literal translation worksheet.

Your job:

1. Preservation and inventory.
   - Confirm the preserved backup exists and matches SHA-256 `015D265D0C1A6E68AAFF50E3E01EE792A41D6192CE7823476581E4D573508942`.
   - Treat that backup as immutable.
   - Decompile with apktool into a temp folder.
   - Confirm package, SDK versions, permissions, native libs, and smali loadLibrary sequence.
   - Verify whether `libZombieCafeAndroid.so` has `DT_TEXTREL`.
   - Record native hash, size, ELF type, and useful symbols.

2. Data schemas.
   - Inspect the existing tools in the English repo.
   - Confirm JP character parser behavior: `tool/file_types/character_jp.go`.
   - Implement or design read-only parsers for JP food and furniture.
   - For food, verify the 234-row schema described above and produce a CSV snapshot.
   - For furniture, fully map the JP schema and prove parser alignment to EOF.
   - Identify rows 182-185 or the equivalent Type 10 currency rows and document all fields.

3. Translation inventory and first-pass localization plan.
   - Inventory every player-facing text source:
     - food names
     - character names
     - human/zombie descriptions
     - furniture names/descriptions
     - strings data
     - help/about/error HTML
     - Android resources
     - smali hardcoded strings
     - native strings
     - image assets with baked Japanese text
   - Cross-reference against English revival files first:
     - `src/assets/data/foodData.bin.mid.json`
     - `src/assets/data/characterData.bin.mid.json`
     - `src/assets/data/furnitureData.bin.mid.json`
     - English help/about text where available
   - Create translation crosswalk CSVs with columns:
     `source_file, record_index, field, jp_text, english_reference, proposed_english, match_type, confidence, notes`.
   - Use match types:
     `direct_english_row`, `same_art_or_category`, `mechanical_ui`, `jp_only_event`, `needs_human_review`, `image_text`, `native_or_smali`.
   - Translation style:
     - player-natural English
     - playful Zombie Cafe tone
     - clear UI verbs
     - no stiff literal phrasing
     - preserve JP-only jokes/events when fun
   - Do not bulk-apply translations yet. Produce the inventory, style guide, and high-confidence first-pass proposals.

4. Toxin exchange reverse engineering.
   - Study English `src/lib/cpp/ZombieCafeExtension.cpp`, especially the `base + 0xab018` / `0xab01a` money-to-toxin redirect.
   - Do not reuse those offsets in JP; the JP lib is different.
   - Use JP symbols as anchors: `javaBuyStuff`, `GameStateCafe::completeStorePurchase`, `ZombieCafe::addCash`, `ZombieCafe::addToxin`, `ZombieCafe::GiveBoughtToxin`.
   - Determine the safest JP patch approach:
     - inject a JP `libZombieCafeExtension.so` and add a smali `System.loadLibrary("ZombieCafeExtension")`, or
     - apply an in-place binary patch to a scratch copy of the JP `.so`.
   - The target behavior is cash-to-toxin:
     - 10 toxin costs 30000 cash
     - 30 toxin costs 75000 cash
     - 175 toxin costs 375000 cash
     - 750 toxin costs 1500000 cash
   - If the JP economy later proves harsher than English final, recommend whether to start at Airyzz original prices first: 20000 / 50000 / 250000 / 1000000.
   - Verification must include displayed price, affordability check, cash deduction, toxin credit, insufficient-cash behavior, and save persistence.

5. Android compatibility.
   - JP APK targetSdkVersion is 16; plan a target bump to 24 if needed for modern Android install gates.
   - JP native library currently appears to have no `DT_TEXTREL`; verify this independently.
   - Search and patch restricted hardware identifier calls:
     - `TelephonyManager.getDeviceId()`
     - `TelephonyManager.getSimSerialNumber()`
   - Known JP call sites found during preliminary audit:
     - `/tmp/zombiejp/apktool/smali/com/capcom/zombiecafeandroidJP/ZombieCafeAndroid.smali`
     - `/tmp/zombiejp/apktool/smali/com/capcom/zombiecafeandroidJP/m.smali`
   - Use the English `device_id_security_exception_fix.md` as the model: replace restricted values with a stable fake `"000000000000000"` while preserving `ANDROID_ID`-based uniqueness where possible.
   - Check whether manifest needs `android:extractNativeLibs="true"` after target changes.

6. Balance strategy.
   - Use English final data and reports as the fairness target, not as a direct row-copy source.
   - JP has 1,724 character records and 234 food rows, versus English 219 characters and 216 foods.
   - First produce snapshots and identify categories:
     - playable chefs vs infectables/staff
     - cash vs toxin or other purchase gates
     - event/promo/special records
     - extreme stat outliers
   - Recreate the same staged approach:
     - food traps/outliers
     - premium/special food value
     - XP pacing
     - playable chef identities
     - infectable stat/cost fairness
     - toxin exchange
   - Preserve JP-only/event identity where it is fun, but remove dead purchases, strict dominations, and impossible grinds.

7. Build and verification plan.
   - Do not build yet, but document exact commands.
   - Account for the local Go issue: repo `go.work` wants Go 1.23, WSL has 1.22.2.
   - Plan apktool rebuild, signing, and logcat tests.
   - Test matrix:
     - launch on BlueStacks / 32-bit Android-capable runtime
     - launch on modern Android if available
     - open cafe, store, currency pack screen
     - buy each toxin pack
     - cook/serve early and late dishes
     - hire/use several chefs and infectables
     - raid
     - map/cafe transition stress loop
     - translation layout review in store, cookbook, character detail, help, dialogs, and map

Output a concise `claude_code_followup_prompt.md` that can be handed to Claude Code for the first implementation pass. That first implementation pass should focus on preserving the backup, parsers/packers, text inventory, translation crosswalks, and data snapshots, not native patching.
