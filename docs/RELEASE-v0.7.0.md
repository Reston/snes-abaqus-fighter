# v0.7.0 - Stage atmosphere and readable effects

This development update adds a first ambient animation layer to the three
Abaqus locations, distinct contact effects, visible floor shadows, and a fix
for a measured SNES sprite-fetch overflow. The original stage illustrations,
palettes, fighter pixels, character profiles and combat rules remain intact.

Las Condes gains a small leaf-highlight sway and a moving reflection; El
Castillo gains warm light pulses and a small party gesture; La Oficina gains
monitor activity below the existing speed-test lettering. Each scene uses
eight BG1 tiles at indices 960-967, four phases, and one 256-byte transfer per
phase. Phase zero reproduces the original tiles exactly. The live fight clock
advances the scene every sixteen ticks; pause, intro, hitstop and round-end
states freeze it. Transfers wait for a frame without actor or interface DMA.
This layer adds no sprites and does not yet implement stage parallax.

Code-authored pixel effects now distinguish expanding hit flashes, hollow
guard sparks, high projectiles and grounded amber waves. Shadow pixels occupy
the first six rows of their sprite instead of following six transparent rows.
Their OAM placement moves down by the same six pixels, preserving the intended
floor footprint, and priority 2 makes them visible above the opaque stage.

The old transparent padding was significant to the PPU: two simultaneous low
waves could exceed its 34-tile scanline fetch limit. A controller-driven
instrumented baseline reported STAT77 time overflow; the revised placement
removes that overlap. [OBJ-BUDGET.md](OBJ-BUDGET.md) records the reproduction,
register timing and exact-ROM verification evidence.

## Verification

All five native reports pass on the 4,194,304-byte cartridge with checksum
`0953` and SHA-256:

`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`

| Suite | Passing checks |
| --- | ---: |
| Gameplay and progression | 2,595 |
| Characters and animation | 18,085 |
| Presentation | 215 |
| Input, CPU, recovery, audio and cadence | 854 |
| Stage animation and OBJ budget | 4,537 |
| Total | 26,286 |

The silent five-suite `Test.cmd` batch passed. A subsequent focused stage
extension added nine patch-only PPU assertions and passed again on the
unchanged cartridge. Regenerating every asset and rebuilding reproduced the
same ROM SHA. No original fighter frame or palette bytes changed.

The matching pinned bsnes2014 Accuracy run covers all three four-phase stage
loops, intro/pause/hitstop/round-end freezing, and static background colors.
Every sampled background pixel is within eight RGB levels of its native
plate; the maximum channel difference is seven. A synchronized low-wave
fixture passes 600 strict cadence steps with zero OBJ overflow, alongside
the existing neutral 600-step, controller and captured-audio checks.

This pass also corrects the independent test host's video decoding. The
pinned DLL advertises a 16-bit enum but supplies four-byte BGRX pixels;
callback metadata and palette agreement now guard the captures. Earlier
striped review images are not visual-accuracy evidence. The bounded scope
and core pins are recorded in [COMPATIBILITY.md](COMPATIBILITY.md).

The offline development package passes 214 technical audit checks. It includes
the tested ROM, Snes9x and control defaults, five native reports, scoped
independent evidence, the stage manifest, guides and license notices. Fixed
ZIP metadata and repeated packaging produce identical archive bytes from the
same inputs.

Human motion and balance review, listening sessions, independent full-roster
combat, endurance, controller/console results, and public-use approval remain
open in [PUBLIC-RELEASE.md](PUBLIC-RELEASE.md).
