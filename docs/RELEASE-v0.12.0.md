# v0.12.0 - Training matchups and an earned champion ending
<!-- candidate-version: 0.12.0; rom-sha256: 33502fba12bf2cf02e6244174449c678ad1dd704afc754e7819f815489c6fa83 -->

Training now lets the player choose any opponent or a mirror match. Confirm
PLAYER 1 to open the existing second roster step, headed DUMMY. The cursor
starts on the next roster entry; either controller can choose the dummy.
Confirm to choose an arena, or press B to return to PLAYER 1. Start > B > A
priority and directional neutralization remain intact. Live Select reset
preserves the chosen fighters and dummy behavior; a new match starts at Stand.

Defeating all eleven Arcade opponents now earns an original Office Champion
trophy scene with the winner's portrait, name, actual round score and quote.
A/Start returns to the title; B returns to fighter select. Earlier match
results retain their existing stage and winner-card layout. The original art,
exact prompt and raw output are retained; see [CHAMPION-ENDING.md](CHAMPION-ENDING.md).

- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- ROM SHA256: `33502fba12bf2cf02e6244174449c678ad1dd704afc754e7819f815489c6fa83`.
- Header checksum: `222B`.
- Cartridge source freeze: `9134d4307037a935e1de31f08efd405409ac8ef7`.
- Source tree: `38dc1d16565d7bc0d941f272339ccd4382fbe594`.

## Native preservation

Training reuses the existing second selection state. The champion background
loads only during screen-off, using 330 BG1 tiles / 10,560 bytes, the existing
2,048-byte map and six scene palettes 2..7. Its portrait retains BG2 palette 1
and VRAM word `$4A00`. The 218-file generated set adds four champion files;
only the assembly/header registration changes among existing generated files.
Fighter64/Wave16 layouts, TRACE[0..122], one-actor-per-vblank budget, live
combat, AI, balance, audio, fighter banks, portraits, stages and ambient cells
remain unchanged. Human artwork approval remains pending.

## Verification and package status

All six native suites pass on this exact cartridge: 2,596 gameplay, 18,081
roster, 2,865 presentation, 1,048 focused input, 8,163 stage and 756 Training
checks, totaling **33,509**. The pinned bsnes2014 Accuracy smoke and
48-by-600-frame independent combat run match. The full 288-case native matrix,
four deterministic replays, stage/policy/symmetry gates and three native
live-hour sessions pass. Each mode completes 216,356 live frames with empty
cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure arrays.

The isolated committed-source rebuild reproduces the cartridge, all 218
generated assets and normalized symbols in 126.672 seconds.
It uses source commit `9134d4307037a935e1de31f08efd405409ac8ef7` and tree
`38dc1d16565d7bc0d941f272339ccd4382fbe594`. Bootstrap progress is suppressed during fresh tool
extraction; official archive and member pins remain enforced.

The [verification record](verification-v0.12.0.json) collates the current-ROM
gates. Three separate controller-only eleven-opponent ladders prove A/Start
to title and B to fighter select from the champion scene. Native presentation
checks compare the trophy and portrait's VRAM bytes and actual PPU pixels;
DUMMY captures verify arbitrary and mirror selection identities.

The Windows offline package includes the pinned Snes9x executable, cartridge,
player guide, exact QA reports, champion provenance/route captures and a
self-contained native-screen gallery. Extract the whole ZIP and run
`Play.cmd`; `REVIEW.html` offers native and 2x views. The source checkout
publishes the archive checksum in `dist/release-sha256.txt`; its separate audit
is recorded in `docs/release-audit.json`. Historical evidence is kept separately.

## Known pause-priority issue

In this frozen review cartridge, pressing Start+Select together while paused
in Training resumes and resets the round in the same sample. Start alone
resumes without resetting. A controller-only probe confirmed the difference
after moving P1 away from the start position. The narrow priority fix is
being prepared separately; this snapshot does not claim that behavior is fixed.

Human gameplay/balance, full listening, physical-controller sessions,
likeness/consent and team/public-use review remain open. Original SNES and
flash-cartridge support stay unverified. `public_release_certified` is false.
