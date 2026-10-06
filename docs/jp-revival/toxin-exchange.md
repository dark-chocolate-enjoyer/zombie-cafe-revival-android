# JP Cash-to-Toxin Exchange

## Status

The JP-specific data and native patches are implemented and packaged in an
aligned, debug-signed test APK. The owner confirmed the core exchange path in
BlueStacks: purchasing the first tier deducted cash and credited Toxin.

The preserved JP APK remains unchanged:

`015d265d0c1a6e68aaff50e3e01ee792a41d6192ce7823476581e4d573508942`

## Exchange Data

JP furniture rows 182 through 185 are the same Type-10 cash packs repurposed by
Airyzz in the English build. The JP patch applies the original exchange:

| Cash cost | Toxin granted |
| ---: | ---: |
| $20,000 | 10 |
| $50,000 | 30 |
| $250,000 | 175 |
| $1,000,000 | 750 |

The generated 835-row JP furniture binary packs, unpacks, and repacks
byte-identically. Its current SHA-256 is:

`df2e00f4ce44cad87c72f5bbb81e007f160533321eb501d955735f650c55ce12`

## Store Artwork

JP furniture rows 182 through 185 use furniture-atlas indices 110 through 113:

| JP atlas index | Original sprite | Replacement source |
| ---: | --- | --- |
| 110 | `10k.png` | EN index 63, `10 Toxin` |
| 111 | `50k.png` | EN index 64, `30 Toxin` |
| 112 | `250k.png` | EN index 65, `175 Toxin` |
| 113 | `1M.png` | EN index 66, `750 Toxin` |

The English sprites are the same artwork used by Airyzz's exchange. They are
slightly larger than the JP cash sprites, while the 2048x2048 JP atlas has no
unused rectangle large enough for the 180x184 maximum replacement. The
`tool/cctpacker/cmd/patch_toxin_icons` command therefore supports
`-fit-existing`: each replacement is resized to the corresponding JP rectangle
without cropping, then written over that rectangle.

The atlas was unpacked again after patching. All 405 extracted sprites were
compared; exactly indices 110 through 113 changed. The offsets file remained
byte-identical:

`7fb2c027e85746ed28bc1a0286bdc3795873a5ab6a174f9f1f9dc0aa3a398aaf`

## Native Patch

The English Airyzz instruction patch cannot be copied because JP stores cash
and Toxin at different offsets and has a different purchase-handler layout.
The JP Type-10 block at file/virtual offset `0x113b88` is replaced with:

```text
ldr r0, [r4, #12]   ; ZombieCafe instance
ldr r1, [r3, #88]   ; Type-10 BuyMoneyAmount
movs r2, #0         ; match Airyzz's direct-credit behavior
bl 0x229fa0         ; ZombieCafe::addToxin(int, bool)
b 0x114126          ; existing common purchase exit
```

The verified patched library SHA-256 is:

`e2acf2b537f07c786a8f06b0b7044b71ff0ebe55281440c3fc67b26f0add4524`

`tool/jp_revival/apply_toxin_exchange.py` requires the exact JP 1.7.0 source
library hash and exact original instruction bytes. It writes new outputs only.

## Test APKs

The runtime-confirmed Toxin-only test APK is outside the repository at:

`outputs/builds/jp-toxin-test/ZombieCafe_JP_1.7.0_toxin-test-debug.apk`

Its SHA-256 is:

`3b2dcbf38d83744c990e5f349552a4234487c4b9c9cdd9e56b82b7b02f9d41d2`

`zipalign -c` passes, and `apksigner verify` confirms v1, v2, and v3
signatures. The embedded library and furniture binary match the hashes above.
This is a development build signed with the repository debug key, not a
release artifact.

The same build with the four Airyzz store sprites applied is:

`outputs/builds/jp-toxin-test/ZombieCafe_JP_1.7.0_toxin-icons-debug.apk`

Its SHA-256 is:

`0040ef37b3039399e480c9f5846be62efc57be3796a287981f10c2213fdf265a`

The manifest, DEX, native library, furniture data, and furniture offsets match
the runtime-confirmed APK. Only the furniture atlas and APK signatures differ.
Alignment passes, and v1, v2, and v3 signatures verify.

## Remaining Regression Checks

Install the icon build, confirm that all four store entries display the
10/30/175/750 Toxin artwork, then exercise the remaining three exchange tiers.
Confirm each tier deducts the listed cash, credits Toxin once, updates the UI
immediately, persists after restart, and does not corrupt an existing save.

### BlueStacks install note

The existing BlueStacks JP installation is byte-identical to the preserved
original APK and is signed by Beeline Japan:

`39f18977d3a8507ba6002d1f34cbbc4b57ab346dedcef986932556309312a3fd`

The test APK is signed by the repository debug key:

`6e2a2239864fdd32995156422459736fb55c2b8b4916ede785628e7f7bef96a6`

Android therefore rejects an in-place update with
`INSTALL_FAILED_UPDATE_INCOMPATIBLE`. This is expected certificate enforcement,
not an invalid APK. Test on a fresh BlueStacks instance, or back up any needed
save and uninstall the Beeline-signed package before installing the test build.
