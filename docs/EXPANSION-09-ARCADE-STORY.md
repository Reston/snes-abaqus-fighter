# Personal Arcade exchanges and endings

> Combined v0.22.0: this note retains the original feature-branch design and
> isolated measurements. The linked focused report and native captures are
> regenerated for the combined cartridge. Use the [combined release note](RELEASE-v0.22.0.md)
> and [verification record](expansion-v0.22.0-verification.json) for current
> identity, coverage and integration contracts.

Feature branch: `t3/arcade-story-dialogue`, starting at integration commit
`610537d`. This feature uses the reserved v0.22.0 source identity without
changing the shared version, release notes, assets or six suite reports.

## Player-visible behavior

Each Arcade matchup opens with a short, two-speaker coworker exchange. All
twelve fighters have individual invitations and responses derived from their
existing fictional move names. Six reciprocal rivalries have bespoke exchanges:
Damian/Reston, Ivo/Cote, Cristobal/Mamariaga, Negger/Fernando, David/Roxana and
Cristian/Lars. Both speaker orders work. The copy describes fictional friendly
competition; it makes no claims about real employee roles or private traits.

P1 A skips the exchange into the ordinary Get Ready/Fight countdown. Otherwise
it advances automatically after 360 native ticks, approximately six seconds.
Start retains ordinary pause priority, including simultaneous A. Paused A or
Start restores the exchange; the timer freezes during pause and the move guide.
P2 can still operate pause/guide controls but cannot skip an Arcade exchange
with A. Attack, jump and motion buffers remain discarded during the intro.

Every actual Arcade winner, including a CPU winner, receives one of twelve new
individual winner quotes. Defeating all eleven opponents earns three individual
ending lines below the original trophy, beside the retained portrait and score.
The original champion music remains selected. A/Start returns to title and B
returns to character select. Continue repeats the same opponent after a loss.
The ladder, stage rotation and round rules are unchanged. Versus retains its
existing result quotes and Training retains its ordinary intro/reset/shoulders.

## Small integration hooks

`src/arcade_story.h` owns the story copy and functions. `game.c` has these hooks:

- Include the module after the menu/UI helpers.
- Clear `arcadeStoryTicks` in `resetRoundState`; start it only from `beginMatch`
  in Arcade. There is one conversation per new match or Continue, rather than
  one per round.
- Restore its banner on the two existing pause-resume paths.
- While its timer is nonzero, keep the existing `intro` at 110 and return from
  `fightTick` after drawing the actors. The ordinary countdown follows it.
- Select Arcade-only winner copy in `showResult` and individual footer text in
  `loadChampionEnding`.

Feature 04 retains ownership of all visual gesture/pose sequencing. This module
does not choose a fighter pose or alter animation frames. The story holds the
ordinary intro clock; its visual Get Ready phase starts after the exchange.

The shared test helpers that assume every Arcade intro ends after a fixed
180-frame wait need to press A once after match load or wait for story plus
countdown (470 ticks before transfer settling). The shared result-font oracle
also needs the new Arcade quotes and champion text at rows 22/23/24, with
A/Start at 25 and B at 27. This branch deliberately leaves those shared helpers
and reports to the parent integration task.

## Native storage and transfer bounds

There is one new mutable `u16`, `arcadeStoryTicks`, appended after the existing
game globals at `$7E:29AF` on this standalone candidate. Fighter64, Wave16 and
TRACE[0..122] are unchanged. The 1,241 named allocated runtime symbols checked
by the focused harness retain their addresses. The SDK's trailing eight-byte
libc BSS block and its section boundary labels shift by two bytes; no game
global or initialized guide table moves.

All 96 authored lines and their pointer tables reside in cartridge ROM. Flat,
one-dimensional `const char * const` tables are intentional: this SDK places
multidimensional string or pointer initializers in WRAM. Spoken lines fit 28
cells at x2..29; quotes and ending lines fit 30 cells. Original opaque glyphs
provide the panel background as well as the letters.

Story drawing uses native `drawGuideWord` plus the existing fill/clear helpers.
It reuses BG2 banner rows 9..13 (320 bytes) and footer rows 26..27 (128 bytes),
with the existing actor-upload priority. Champion text is composed during the
existing screen-off transition, below the trophy at y176. No new screen IDs,
VRAM ranges, OBJ entries, palette banks, SPC payloads, assets or DMA paths exist.

The five story functions occupy 1,339 native code bytes on this candidate.
Linker-symbol inspection finds 24 banks without allocated named ROM sections
(banks 104..127); the largest linked section remains 30,720 bytes. Every linked
ROM section stays inside one 32 KiB LoROM bank.

## Reproduction

Use the existing ignored `.tools` junction to the canonical SDK/tool cache; do
not run setup or asset regeneration for this feature:

```powershell
D:/snes-abaqus-fighter/.tools/python/python.exe tools/build.py
D:/snes-abaqus-fighter/.tools/python/python.exe tools/run_background.py --log build/expansion-09-all12.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/test_expansion_09_arcade_story.py
```

The focused driver boots and plays the actual ROM with standard SNES controller
inputs through the headless Snes9x libretro host. Its default runs all twelve
complete Arcade ladders and verifies the actual BG2 map, opaque glyph bytes and
composed PPU pixels. It uses no gameplay fixtures, memory writes or save states,
opens no GUI/audio device and runs below normal priority on two logical CPUs.
It writes only its feature report/captures. `--heroes 4 --report build/pilot.json`
is a bounded single-ladder diagnostic.

## Recorded focused proof

The standalone cartridge is SHA256
`709d9082f794234e52615353b9b199dff1e52d81faca0d840faea3287109ad32`,
header checksum `21B4`. The build exits 0. The exact-ROM
[focused report](expansion-09-report.json) passes 1,744 recorded checks in
401.343 seconds, including:

- All twelve fully earned champion endings, 132 Arcade match victories and
  352,469 ladder video frames. All eleven other opponents appear in order for
  each fighter, with the unchanged three-stage rotation.
- All 96 authored lines delivered through native text, including both orders
  of all six rivalries, twelve winner quotes and twelve three-line endings.
  Text checks compare actual VRAM tiles, opaque glyph pixels and PPU output.
- Original trophy/background and each winner's retained portrait. All twelve
  champion scenes keep music index 4 and remain stable without input.
- Four successful champion exits each for A, Start and B; a real CPU-earned
  loss/Continue; simultaneous Start/A/B result priority; pause, guide, resume,
  P2 controls, Training CPU shoulders and Training Select reset.
- Zero added native lag ticks across conversation idle/pause/guide/resume/auto
  advance, followed by a 600/600 live-combat cadence check without lag.
- All 393 tracked art/generated files byte-identical to the integration base,
  including approved Damian v5, every fighter bank/palette and all audio.

Fifty native PNG captures live under `docs/screenshots/expansion-09/`. Examples:
[Ivo/Cote rivalry](screenshots/expansion-09/01-vs-03.png),
[Negger/Fernando rivalry](screenshots/expansion-09/04-vs-06.png),
[CPU winner and Continue](screenshots/expansion-09/cpu-winner-continue.png),
[Damian champion](screenshots/expansion-09/00-champion.png),
[Roxana champion](screenshots/expansion-09/10-champion.png).

The strict base-asset and standalone address assertions describe this isolated
feature. The parent must reconcile them with intentional changes from the
other nine features when running the combined integration.

Six-suite integration verification, independent compatibility smoke, combined
feature interactions, human copy/gameplay review and release packaging remain
the parent's separate work. This feature does not certify release readiness.
