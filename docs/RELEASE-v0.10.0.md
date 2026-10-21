# v0.10.0 - Cartoon locations and predictable menus

Las Condes, El Castillo and La Oficina now share the fighters' illustrated
arcade style: stronger outlines, broad color shapes and simpler shadows. The
actual places remain recognizable, and arena selection shows complete
thumbnails made from the same artwork. The original masters, raw generated
outputs and full prompts remain in the repository. See the
[stage-art record](STAGE-CARTOON-v2.md).

Menu navigation now neutralizes held opposite directions, including inputs
from both participating pads during P2 roster selection. Simultaneous action
buttons resolve once: Start confirms first; otherwise Back takes priority over
A. The active combat controls and timing remain unchanged.

- Cartridge: 4,194,304 bytes, NTSC FastROM LoROM; header checksum `BE19`.
- ROM SHA256: `a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445`.
- Cartridge source commit: `8536bb6956212952c17302a62cc6c1de7e12a65d`.
- Source tree: `d524d3f960600dc5c9ff83578ac73675f9798735`.

## Preservation

All 192 generated files outside the stage/arena outputs and their headers
remain byte-identical to v0.9, with LF normalization for text. This includes
all twelve fighters' 64-frame native banks, their palettes and portraits, UI
glyphs, title and character selection, music and resident effects. The
[preservation report](cartoon-preservation-report.json) records the hashes.

The ambient animation follows the new leaves, canopy, party lights and
monitors. The office cursor bars stay below the unchanged `11` and `8.1`
digits. Each stage still uses four 256-byte phases in eight BG1 tiles; phase
zero matches the static source. No extra sprites, palette writes, memory
layout, trace offsets or actor transfers are introduced.

## Verification

`Test.cmd` exits 0 with all six reports on this exact cartridge: 2,595 gameplay,
18,081 roster, 1,756 presentation, 1,020 focused-input, 8,131 stage and 622
Training checks, totaling **32,205**. The new input cases cover held-opposite
menu directions and simultaneous confirm/back priority through result screens.
Native PPU review covers all three stages and the arena picker.

The isolated committed-source rebuild reproduces the ROM, manifest, all 214
generated assets and normalized symbols in 62.031 seconds. The 288-by-600
native matchup matrix, four deterministic replays, all three stages and both
policies pass. Pinned bsnes Accuracy passes its 600-frame smoke and bounded
48-case/28,800-frame combat run. Native endurance passes 216,356 live frames
per mode at 60.0988118623 FPS, with wraps 4/4/3 and empty cadence, timing,
ambient, FIFO and sprite-overflow failure arrays. The shared release-evidence
validator accepts the matching reports.

A separate capture-only audio run passes 1,262 checks across all four effects
and four music scores, with zero clipped samples. This is automated PCM
evidence, not human listening approval.

The [Windows play package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip)
includes the tested cartridge, Snes9x, offline player guide and QA evidence.
Its archive audit passes 7,472 checks, including the new stage-design and
character-preservation document links. ZIPs remain outside Git history.

This is an emulator-first technical snapshot. Human gameplay/balance,
controller sessions, complete listening, likeness/consent and public branding
approval remain open. Original SNES/flash-cartridge support stays unverified;
public-release certification remains false.
