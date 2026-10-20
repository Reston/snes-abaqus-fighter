# v0.8.0 - Move guides and repeatable Training

This native SNES development snapshot adds help during a frozen fight and
useful practice opponents. Human likeness, balance, listening, controller,
physical-console and public-use approval remain separate
[release gates](PUBLIC-RELEASE.md).

- Cartridge: 4,194,304 bytes, NTSC FastROM LoROM; header checksum `6A21`.
- ROM SHA256: `53ef44225c83bd52ee0eea3910ba74ade5ba949af7aa7440c74d959812c13090`.
- Cartridge source commit: `48f3ccb539492247b83f4360a50bdc020bad9dd6`.
- Source tree: `e571aca40019b868bf224bb619390f5ea651434e`.

## Player changes

- Pause with START, then press SELECT to cycle through the controls guide,
  the two live fighters' special moves, and the pause card. LEFT or RIGHT
  switches guide pages. A or START resumes; B returns to the roster. Both
  controllers can use these controls.
- The controls guide shows movement, high/low guard, all six normal buttons,
  throws, uppercuts and the hit-confirm hint. The move list shows each live
  fighter's actual special name and family, the Down + punch shortcut, the
  quarter-circle motion and its 32-energy cost.
- In Training's normal pause card, UP/DOWN selects Stand, Guard High, Guard
  Low or Jump. Guard dummies hold their ground; Jump repeatedly takes off
  after landing. Live SELECT resets the practice situation and preserves the
  selected dummy. Returning to a new match restores Stand.
- Opposite pause directions resolve to neutral on one controller or across
  the two ports, including pressing against an already held opposite.
  START, A, B and SELECT retain their button priority.
- Pausing immediately after contact settles the actual health and energy
  bars on the first quiet paused tick. Combat, stage animation and camera
  shake remain frozen while the player reads the guide.

## Native implementation

Guide text uses opaque variants of the project's original glyphs. It covers
BG2 rows 5-27 while preserving the top HUD. Text is constructed over three
paused ticks and published as one 1,472-byte tilemap range after actor DMA.
Glyph indices 256-383 occupy VRAM words `$5000-$57FF`, below the BG2 map at
`$5800`; the portrait region and fighter data remain unchanged.

Native bounded text/fill/clear helpers replace expensive C pointer loops.
The original `TRACE[0..118]` contract and Fighter/Wave layouts remain intact;
119-122 append pause page, guide build, dummy setting and guide dirty state.
Fighter masters, all 64 native frames per fighter, palettes, stages, combat
profiles and audio assets retain the preceding snapshot's content.

The sixth canonical suite, `tools/test_training.py`, drives real controllers,
captures native PPU output and reads telemetry without writing emulated memory.
It enables the pinned Snes9x core's opposite-direction pass-through so the
cartridge's own SOCD behavior is tested. The offline emulator defaults also
allow both directions through; existing user preferences are not overwritten.

## Verification

All six canonical suites pass against the exact ROM above: 2,595 gameplay,
18,081 roster, 215 presentation, 997 focused input, 8,131 stage and 622
Training checks, totaling **30,641**. The Training report includes actual PPU
captures for both guide pages in all three modes, every special name/family,
same-pad/cross-pad opposite inputs, dummy guard/jump/contact/reset behavior,
projectile/cross-up pause freezes and mirrored contact-to-pause health bars.

The CPU wake fixture keeps its original 260-callback knockdown induction
limit, then stops attacking and observes recovery for at most 120 callbacks.
Hard's first knockdown occurred at callback 234 and its valid wake input at
286, beyond the old shared timeout. The corrected fixture preserves the
single UP edge, wake buffer and airborne assertions, and additionally rejects
KO or scene transitions. No cartridge behavior changed for this correction.
Idle review also observes the complete 64-tick breathing period and requires
all four native idle frames, replacing an entry-phase-dependent half-cycle
observation.

The same cartridge passes the expanded technical gates:

| Gate | Result |
| --- | --- |
| Native matchups | 288 cases: all 144 ordered pairs under two policies, 600 live frames each, all three stages, four deterministic replay digests |
| Independent engine | Pinned bsnes2014 Accuracy smoke and 48 bounded combat cases / 28,800 frames |
| Native endurance | 216,356 live frames in each of Arcade, Local Versus and Training, exceeding one emulated live hour each at 60.0988118623 FPS |
| Isolated rebuild | Fresh pinned tools reproduce the ROM, manifest, 214 generated assets and normalized symbols in 78.375 seconds |

The three uninterrupted native sessions use one boot/unload each and zero
reboots, with frame-counter wraps 4/4/3. Required coverage is complete; all
cadence, native timing, ambient, SPC FIFO and PPU overflow failure arrays are
empty. Stable-fight lag remains zero, resident audio peaks at six queued bytes
and drains, and captured video/PCM remain healthy. These are accelerated
emulated hours. Independent combat remains bounded rather than a full
second-engine ordered matrix or hour-per-mode run.

The shared evidence validator passes. Packaging requires the sixth
authoritative `docs/training-test-report.json` with exact ROM, core and harness
identity. The ZIP carries all six native reports plus the expanded evidence;
the audit requires byte identity with their authoritative source reports.
The offline Windows archive includes the cartridge, Snes9x, player manual,
licenses and this evidence bundle. Its technical audit remains distinct from
the human and release-platform decisions below. The package passes 7,471
technical audit checks.

The repository's `docs/PLAYTEST.md` records human feedback without implying
approval. Reston's current thin crown/high forehead remains a likeness
refinement for a later art pass; the v0.8 changes do not alter roster artwork.
