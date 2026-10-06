# JP Revival Delivery Roadmap

The Colosseum is preserved as shipped but is not a revival target.

## 1. Foundation and Toxin Exchange

- Preserve and hash the untouched JP 1.7.0 APK.
- Maintain byte-identical codecs for editable JP data.
- Port Airyzz's four cash-to-Toxin shop exchanges to JP data.
- Patch the JP Type-10 purchase handler to credit Toxin.
- Build and install a signed test APK; verify all four exchanges and save persistence.

## 2. Offline Playability

- Apply the established Android compatibility fixes to the JP binary and manifest.
- Remove or bypass startup and gameplay dependencies on retired services.
- Retire dead social quests while preserving every live prerequisite chain.
- Replace server-supplied gacha/roulette acquisition with an offline design.

## 3. English Localization

- Apply reviewed English strings, quests, dishes, furniture, and retained roster names.
- Curate the playable roster before translating its remaining descriptions.
- Replace baked Japanese image text where it affects play.
- Audit fonts, text bounds, placeholders, and legal/account text separately.

## 4. Balance and Content

- Port the Revival economy baseline for dishes, furniture, chefs, and characters.
- Normalize JP power creep while retaining useful event and crossover content.
- Define fair offline acquisition, unlock levels, rewards, and Toxin sinks.
- Tune raid/event content that remains playable without servers.

## 5. Stability and Release

- Run binary round trips and automated data validation on every build.
- Test fresh installs, upgrades, saves, purchases, combat, raids, and long sessions.
- Fix crashes on representative 32-bit Android devices/emulators.
- Produce a reproducible signed APK, checksums, known-issues list, and rollback archive.
