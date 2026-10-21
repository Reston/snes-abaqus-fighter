# v0.9.0 - Portraits, arenas and clean combat text

This native SNES development snapshot addresses the user's live presentation
review of v0.8.1. All twelve selection portraits keep their full head and face
inside the grid and large profile. Damian's face is revised from his reference
photograph across all 64 frames. Arena selection uses complete scene thumbnails
with separate labels and a gold cursor outside the artwork. HUD and result
letters now have opaque backgrounds, preventing the stage from showing through
their cells.

- Cartridge: 4,194,304 bytes, NTSC FastROM LoROM; header checksum `6D41`.
- ROM SHA256: `bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639`.
- Cartridge source commit: `76f0a08a7562800df01507db83c6877745c3bdcf`.
- Source tree: `f37852da57a42d2d6819374db5d23278d12587a5`.

## Preservation

Original character masters remain retained beside the versioned revisions and
full image-generation provenance. Damian's approved contract pins all 64 native
frame hashes, the original palette and native physical scale. Each complete new
sheet is normalized once to his original 311-pixel upright source height;
individual poses are never fitted separately. His native idle height remains
69 pixels. The other eleven fighters retain all 88 original native bank files,
and every fighter retains the same OBJ palette.

Combat profiles, controls, physics, modes, audio assets and audio runtime are
unchanged. The FIGHT/RESULT renderer reuses the opaque glyph bank already
allocated to the pause guide. VRAM layout, trace offsets, actor DMA, OAM geometry
and palette reservations remain unchanged. See [presentation details](PRESENTATION-v0.9.md).

## Verification

`Test.cmd` exits 0 with all six native reports on this exact ROM: 2,595 gameplay, 18,081 roster,
1,756 presentation, 997 focused input, 8,131 stage and 622 Training checks,
totaling **32,182**. Presentation includes decoded native portrait/PPU comparisons for
all twelve fighters, full roster-card crops, arena geometry and opaque
HUD/result glyph pixels. The opaque pause guide is checked for visible light
text over its dark card rather than depending on stage colors leaking through.

The isolated committed-source rebuild reproduces the ROM, manifest, 214
generated assets and normalized symbols in 75.078 seconds. The shared release
evidence validator passes these matching technical gates:

| Gate | Result |
| --- | --- |
| Native matchups | 288 ordered cases under two policies, 600 live frames each, all three stages, four deterministic replays |
| Independent engine | Pinned bsnes2014 Accuracy smoke and 48 combat cases / 28,800 live frames |
| Native endurance | 216,356 live frames per mode at 60.0988118623 FPS; one uninterrupted boot/unload in each mode |
| Isolated rebuild | Exact cartridge, manifest, 214 generated assets and normalized symbols |

The independent combat run is bounded; it is not a second-engine full matrix
or hour-per-mode run. Endurance reports have complete required coverage and
empty cadence, native timing, ambient, audio FIFO and OBJ-overflow failure
arrays. No frontend window or speaker playback is used by automated tests.

The offline Windows archive includes the cartridge, Snes9x, player manual,
license notices and matching technical reports. Its audit passes **7,471
checks**, including report/archive byte identity. The audit deliberately keeps
`public_release_certified=false`.

## Support and review

The first supported target is emulators. Original SNES and flash-cartridge
support remain unverified. The user accepted Reston's earlier short buzz cut as
closer and heard no issue in the short v0.8.1 audio preview; neither response
constitutes full team/public approval. Damian's revised likeness and the new
presentation are ready for another human playtest. Human balance, complete
listening, controller and branding/consent gates remain open; this snapshot is
not certified as a public release.
