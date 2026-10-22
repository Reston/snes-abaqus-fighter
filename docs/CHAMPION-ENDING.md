# Original Office Champion ending
<!-- candidate-version: 0.17.0; rom-sha256: cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe -->

The combined v0.17.0 cartridge has SHA256
`cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe`,
checksum `5EAF`, source freeze `5fcd5cb28f4cf2453cb3310fbab0d6947d7afd9a`.
The eleventh Arcade victory earns an original trophy and Santiago night-office
scene with the winner's portrait, name, actual round score and quote.
A/Start returns to the title; B returns to fighter select. The retained original
[victory score](CHAMPION-AUDIO.md) begins only on the earned champion scene.

The [release note](RELEASE-v0.17.0.md) records the full candidate's verification
and package status. Human approval remains open. The earlier isolated feature
cartridge is historical; its reports here are replaced by combined-ROM evidence.

## Artwork and reproducibility

The source repository retains the original built-in-imagegen output and exact
prompt. The offline archive includes provenance and generation records. Raw
masters and encoder inputs require a source checkout; unavailable source links
in the offline copy are labeled explicitly.

- [Original raw PNG](../assets/art/menu/source-champion-v1/champion-raw-v1.png):
  RGB 1340x1174, SHA256 `5de9abb1669e5c2c9a1c7ad40ae119c4e7392e4a55be72432bf0d3f627bfb62e`.
- [Exact generation record](../assets/art/menu/source-champion-v1/generation-v1.json).
- [Canonical master](../assets/art/menu/champion-ending-v1.png): opaque RGB
  1024x896, an exact 4x native grid with at most 90 colors.
- [Art provenance](../assets/art/menu/champion-ending-v1.json): raw/master hashes,
  exact prompt and deterministic preparation metadata.

In a source checkout, [the encoder](../tools/champion_assets.py) reproduces the
master by cropping `(2,2,1338,1171)` to exact 8:7, sampling at 256x224 with
nearest-neighbor, collapsing near-identical navy shades within twelve channel
levels of RGB `(17,26,61)`, reducing to 90 colors with Pillow MEDIANCUT without
dithering, and enlarging 4x with nearest-neighbor. Normal asset builds verify
the raw bytes, master hash and native grid. The package gate also compares
declared paths, hashes, prompt and image/processing metadata with the retained
inputs. All lettering uses the existing opaque project glyphs.

## Native scene contract

Only the champion branch loads the scene, during the existing screen-off
transition, using BG1 palettes 2..7. The existing 64x80 portrait keeps BG2
palette 1 and VRAM word `$4A00`, anchored at tile `(21,7)` inside one gold
frame. Name/score occupy rows 18/19, ALL 11 / DEFEATED rows 20/21, and
quote/title/roster commands rows 22/24/26. Only footer rows 22..27 receive a
full navy panel, preserving the trophy through pixel row 175.

| Block | Bytes |
| --- | --- |
| Champion tiles | 10,560 (330 tiles) |
| Champion map | 2,048 |
| Champion palette | 192 |

The [native block record](champion-native-budget.json) computes linked start
and last-byte addresses from the actual symbols, checks bank boundaries and
compares each block's cartridge bytes with its generated source. The package
gate recomputes that record so a later link cannot leave stale addresses here.

Each block fits one 32 KiB LoROM bank. Maximum tile index 329 leaves ambient
cells 960..967 untouched. The static art introduces no live DMA, OBJ, combat, Fighter64/Wave16 or
TRACE[0..122] change. The separate victory score loads during screen-off.

Source-only generated inputs are [tiles](../assets/generated/champion_tiles.bin),
[map](../assets/generated/champion_map.bin), [palette](../assets/generated/champion_pal.bin),
[native preview](../assets/generated/champion.png), [header](../assets/generated/assets.h)
and [assembly](../assets/generated/data.asm). The [current preservation report](preservation-v0.17.0.json)
compares the complete 219-file generated set with verified v0.16.0 commit
`0971895da72bf7cdde40571a920b7f9c156d34f0`: all 219 generated files are
preserved, with no additions or modifications. The two protected hardware/trace
assembly files are also unchanged. All three current-ROM controller-only route proofs pass.
[Champion preservation](champion-preservation-report.json) carries the same
current-ROM comparison for the focused package gate.

## Focused route evidence

Separate controller-driven ladders record [A to title](champion-ending-report.json),
[Start to title](champion-ending-start-report.json) and
[B to fighter select](champion-ending-back-report.json). Each proof defeats
all eleven distinct other fighters, follows the three-stage sequence, checks
the BG1 bytes and actual PPU trophy pixels, verifies portrait and opaque text,
waits on a stable ending, then follows the named exit. The main gameplay suite
also checks the ending after its own Arcade ladder.

Proof runs are headless and silent, with controller input only: no emulated
memory writes, save states, GUI or audio device. The package gate requires the
exact current ROM, eleven-opponent ladder, destination and host contract, and
links preservation to the clean-source rebuild.

The offline archive bundles these captures:
[ending](screenshots/champion/ending.png), [earlier result](screenshots/champion/arcade-result.png),
[A exit](screenshots/champion/exit-a.png), [Start exit](screenshots/champion/exit-start.png)
and [B exit](screenshots/champion/exit-b.png).
JSON capture fields retain source paths beginning `docs/screenshots/`; remove
the leading `docs/` to locate these bundled files. JSON evidence remains
byte-for-byte source evidence.

These focused proofs supplement the six native suites and extended release
gates. Original hardware support is unverified; human gameplay, physical
controllers, full listening, likeness/consent and team/public-use review
remain open. `public_release_certified` is false.
