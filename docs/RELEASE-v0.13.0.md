# v0.13.0 - Champion music, pause priority and clean builds
<!-- candidate-version: 0.13.0; rom-sha256: eefa712718d52aa536258773596e78cee3f4cfc83b1cd4144e3de1110d2273b4 -->

The eleventh Arcade victory now starts an original sixteen-bar victory score
with the Office Champion trophy scene. Ordinary results retain arena music;
A/Start and B return to title/roster music. See [CHAMPION-AUDIO.md](CHAMPION-AUDIO.md)
and [CHAMPION-ENDING.md](CHAMPION-ENDING.md) for original source and native scope.

Start now resumes paused Training when Select is pressed in the same sample,
including chords split across controller ports. Positions and health are
preserved through normal resumed simulation. A later fresh live Select still
resets the round and preserves the chosen fighters/dummy behavior.

An ordinary clean-source build now regenerates assets if a required generated
header is absent, including the intentionally ignored soundbank.h. Pinned tool
bootstrap also suppresses extraction progress overhead while retaining hash checks.

- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- ROM SHA256: `eefa712718d52aa536258773596e78cee3f4cfc83b1cd4144e3de1110d2273b4`.
- Header checksum: `B2CC`.
- Cartridge source freeze: `9e4b4a6e837bd3c91bba81f9781dab1cecbb79c8`.
- Source tree: `c7f5aeda2c1873ef6450138bbdea1389d58a71e9`.

## Native preservation

The generated set contains 219 files. Relative to verified v0.12.0, 216 files
are preserved, two soundbank outputs change and one original victory IT is added.
Existing four scores, effects and native sample/module payloads are preserved.
The soundbank remains below 32 KiB; the new scene score and resident cues use
6,106 bytes above SPC `$1A00`, with zero echo/streaming allocation.
Fighter64/Wave16, TRACE[0..122], actor/OBJ/live DMA and ambient budgets remain.
Training opponent/mirror selection, champion art, portraits, stage art, Lars's
revised likeness and winner cards are retained.

## Verification and package status

All six native suites pass on this exact cartridge: 2,596
gameplay, 18,081 roster, 2,865
presentation, 1,048 focused input, 8,163
stage and 1,440 Training checks, totaling **34,193**.
The pinned bsnes2014 Accuracy smoke and 48-by-600-frame independent combat run
match. The full 288-case native matchup matrix, four deterministic replays,
stage/policy/symmetry gates and three native live-hour sessions pass. Each mode
completes 216,356 live frames with empty cadence, native-timing, ambient,
PPU-overflow and SPC-FIFO failure arrays.

The isolated committed-source rebuild reproduces the cartridge, all 219
generated assets and normalized symbols in 298.656 seconds, from source
commit `9e4b4a6e837bd3c91bba81f9781dab1cecbb79c8` and tree
`c7f5aeda2c1873ef6450138bbdea1389d58a71e9`. Separate controller-only eleven-opponent ladders prove
champion A/Start to title and B to fighter select.

The focused audio proof passes 1,792 capture-only checks, covering all
four cues and five scores, native repeat structure and earned scene/title
transitions. A separate identified test fixture exercises cues over victory
music. The [listening record](audio-listening-v0.13.0.json) identifies an optional
WAV review archive; no speakers or audio device were used and human listening
remains open. The [verification record](verification-v0.13.0.json) collates the
current technical gates. Preservation is recomputed from pinned baseline and
source-freeze Git objects, including hashes, ancestry and approved path changes.

The Windows offline package includes pinned Snes9x, exact QA/provenance,
champion route captures, player guides and a native-screen gallery. Extract
the whole ZIP and run Play.cmd. REVIEW.html offers native and 2x views.
ROSTER-REVIEW.html embeds all twelve native 64-frame strips for frame/facing
inspection, with a sweep explicitly separate from gameplay timing.
The archive checksum is published separately in dist/release-sha256.txt and
its technical audit in docs/release-audit.json. Historical evidence remains
identified by its own version and ROM.

Human gameplay/balance, full listening, physical-controller sessions,
likeness/consent and team/public-use review remain open. Original SNES and
flash-cartridge support stay unverified. `public_release_certified` is false.
