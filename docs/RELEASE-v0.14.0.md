# v0.14.0 - Clearer menu prompts and motion help
<!-- candidate-version: 0.14.0; rom-sha256: 3de317b43f72bea76cfc2f1a1ebd5c67dd57913b8d9fddfb50a7a846a02ddeaa -->

Fighter and arena menus now show A/Start confirmation, matching the controls
they already accept. The roster footer fits the existing row. The arena's
original opaque glyphs cover only its bottom two rows; the location pictures,
labels and cursor above them remain unchanged. No raster art is regenerated
differently for these prompts.

The pause Specials page explains the twelve-tick motion timeout **per step**.
Controller probes on both ports demonstrate that a longer complete motion still
works when each step arrives in time, while twelve neutral ticks expire an
unfinished step. This clarifies existing controls; attack and motion timing
remain unchanged. The guide uses its existing three-tick, 1,472-byte panel.

Asset-authoring contracts now use explicit conditional raises under both normal
and optimized Python. Invalid stage hashes, altered immutable baselines, short
palettes and incomplete native frame sets are rejected even with python -O.
Valid authoring output retains every existing asset byte (text LF-normalized).

- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- ROM SHA256: `3de317b43f72bea76cfc2f1a1ebd5c67dd57913b8d9fddfb50a7a846a02ddeaa`.
- Header checksum: `D1E2`.
- Cartridge source freeze: `d534af0132440c0de3e1cb5a33a62301026449af`.
- Source tree: `2dd5e2c1b6b4a64f7aa5fbb61bc69e8f522cd3cd`.

## Native preservation

All 219 generated files match the verified v0.13.0 checkpoint, including every
fighter bank, portrait, stage, ambient cell, UI tile, champion image and audio
module. Protected hardware/trace assembly is unchanged. Fighter64/Wave16,
TRACE[0..122], one-actor-per-vblank, OBJ, live DMA and SPC budgets remain.
The [preservation report](preservation-v0.14.0.json) recomputes baseline/freeze
Git objects against approved path changes; this candidate allows none.
Champion artwork and music retain the scopes in [CHAMPION-ENDING.md](CHAMPION-ENDING.md)
and [CHAMPION-AUDIO.md](CHAMPION-AUDIO.md).

## Verification and package status

All six native suites pass on this exact ROM: 2,596
gameplay, 18,084 roster, 3,337
presentation, 1,060 focused input, 8,163
stage and 1,443 Training checks, totaling **34,683**.
The pinned bsnes2014 Accuracy smoke and 48-by-600-frame independent combat run
match. The 288-case native matrix, four deterministic replays and stage/policy/
symmetry checks pass. All three modes complete 216,356 live frames with empty
cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure arrays.

The isolated committed-source rebuild reproduces the ROM, all 219 generated
assets and normalized symbols in 419.844 seconds, from source
`d534af0132440c0de3e1cb5a33a62301026449af` and tree
`2dd5e2c1b6b4a64f7aa5fbb61bc69e8f522cd3cd`. Three separate eleven-opponent controller ladders
prove champion A/Start to title and B to fighter select. Focused audio passes
1,792 capture-only checks across four cues and five scores, including
native repeat structure and earned champion/title transitions. An identified
fixture exercises cues over victory music. The optional WAV archive is separate
and identified by the [listening record](audio-listening-v0.14.0.json).

The [focused menu proof](menu-footer-report.json) passes 4,650 checks,
covering 69 baseline/candidate native states, fifty controller routes and
fourteen final footer images. Package validation recomputes every asset against
approved Git blobs, pins the installed core and shared producer dependencies,
and compares retained PNG pixels/VRAM above the footer. It also recomputes the
fourteen final footer images' text placement and glyph-pixel metrics. Original
PNG/VRAM files are bundled under screenshots/menu-preservation/. These checks
validate recorded capture bytes; they do not replay the emulator execution.

[Authoring evidence](authoring-guards-report.json) records 19 mutation checks
under normal Python and 19 under python -O. Every production Python source in
the authoring inventory and both test helpers is tied to the cartridge freeze.
The runner and release-evidence inventory are tied to a supplementary committed
producer, with source-freeze to producer to release-HEAD ancestry. The shared
preservation helper is covered by the global source-input gate.

The [verification record](verification-v0.14.0.json) collates the exact current
technical evidence. The Windows package contains pinned Snes9x, player guides,
exact QA/provenance records, champion/menu captures and two offline galleries.
Extract the whole ZIP and run Play.cmd. REVIEW.html embeds nine actual native
screens; ROSTER-REVIEW.html offers all twelve generated 64-frame fighter strips
with facing and frame inspection. Its fixed-rate sweep is an art review aid.
The archive checksum is published separately in dist/release-sha256.txt and its
technical audit in docs/release-audit.json.

Human gameplay/balance, full listening, physical controllers, likeness/consent
and team/public-use approval remain open. Original SNES/flash-cartridge support
is unverified; public_release_certified remains false. Historical records retain
their own version and ROM identity.
