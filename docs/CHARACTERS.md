# Character combat profiles

`Abaqus: After Hours` uses one shared six-button ruleset, with a data-driven
combat profile for each roster slot. The concepts below are fictional game
design: they do not describe the real jobs, personalities, or abilities of
the people whose public names inspired the roster.

The normal buttons remain `Y / X / L` for light, medium, and heavy punches and
`B / A / R` for light, medium, and heavy kicks. `Down + Y/X` or a
quarter-circle-forward Y/X spends 32 meter for action 7. `Down + L` keeps the
existing uppercut and forward + L keeps the existing throw. Action 7 uses four
families: projectile `0`, rush strike `1`, low shockwave `2`, and rising strike
`3`.

| ID | Fighter | Style | Normal profile | Action 7 special | Frame tuning (startup / active / recovery) | Throw (range / base damage) |
|---:|---|---|---|---|---:|---:|
| 0 | Damian | Balanced cobalt veteran | 20 walk, 14 back; original balanced normals | **Kernel Burst** — forward projectile | 10 / 1 / 23 | 27 / 18 |
| 1 | Ivo | Emerald control | 17 walk, 12 back; long reach, slower recovery | **Capital Wave** — slow, durable projectile | 14 / 2 / 27 | 31 / 18 |
| 2 | Cristobal | Lean orange rush | 24 walk, 17 back; quick, lighter normals | **Atomic Push** — advancing rush strike | 5 / 8 / 18 | 25 / 17 |
| 3 | José “Cote” | Crimson close power | 21 walk, 15 back; heavy damage and commitment | **Balance Break** — close-range power rush | 8 / 7 / 24 | 29 / 23 |
| 4 | Gonzalo “Negger” | Purple broad bruiser | 16 walk, 11 back; longest recovery, biggest normals | **Macro Shock** — slow low shockwave | 13 / 2 / 28 | 33 / 26 |
| 5 | David | Amber boxer | 20 walk, 14 back; fast, compact normals | **Audit Strike** — rising strike | 4 / 6 / 22 | 28 / 20 |
| 6 | Fernando | Teal stocky low pressure | 17 walk, 12 back; slow ground control | **Legacy Flash** — persistent low shockwave | 10 / 2 / 27 | 30 / 21 |
| 7 | Cristian | Navy sweater defense | 18 walk, 13 back; tall reach and safer recovery | **Risk Reversal** — defensive rising strike | 7 / 7 / 25 | 34 / 19 |
| 8 | Ignacio “Mamariaga” | Chartreuse speed | 26 walk, 18 back; fastest, lightest normals | **Merge Force** — fast low shockwave | 6 / 2 / 18 | 24 / 17 |
| 9 | José “Reston” | Copper pressure | 18 walk, 12 back; heavy pressure normals | **Cloud Crash** — heavy projectile | 12 / 1 / 29 | 32 / 22 |
| 10 | Roxana | Magenta athletic agility | 24 walk, 17 back; quick normals and agile jump | **Close Out** — fast rising strike | 4 / 8 / 18 | 26 / 19 |
| 11 | Rodrigo “Lars” | Ice-blue long reach | 19 walk, 14 back; longest normal reach | **Nordic Byte** — long-life low shockwave | 15 / 2 / 24 | 36 / 22 |

Jump strength and gravity are also profile values. Damian keeps the original
`-91` jump velocity and gravity `5`, so established jump and special timing
checks remain stable. The other profiles vary their jump arcs, back-step
speed, normal startup/recovery/damage/reach, throw range, and special tuning.
Low shockwaves are defeated by crouch guard; rising strikes count as airborne
attacks; rush strikes advance during startup and active frames; projectiles
travel independently after their startup.

## Verification trace

The read-only WRAM trace keeps the existing fields at offsets `0..31`. The
roster contract begins at offset `32` (16-bit words):

| Offset | Field |
|---:|---|
| 32 / 33 | Player 1 / Player 2 fighter ID |
| 34 / 35 | Player 1 / Player 2 action 7 family |
| 36 / 37 | Player 1 / Player 2 walk speed |
| 38 / 39 | Player 1 / Player 2 signed jump velocity, stored as raw `u16` |
| 40 / 41 | Player 1 / Player 2 facing (`0` left, `1` right) |
| 42 / 43 | Back-step speed |
| 44 / 45 | Special startup |
| 46 / 47 | Special active |
| 48 / 49 | Special recovery |
| 50 / 51 | Special base damage |
| 52 / 53 | Special contact reach |
| 54 / 55 | Throw range |
| 56 / 57 | Active wave low flag |
| 58 / 59 | Active wave speed |
| 60 / 61 | Active wave life |
| 62 / 63 | Requested native animation frame, `0..47` |
| 64 / 65 | Animation state |
| 66 / 67 | Per-fighter animation tick |
| 68 / 69 | Buffered action ID |
| 70 / 71 | Attack buffer ticks remaining |
| 72 / 73 | Jump buffer ticks remaining |
| 74 / 75 | Quarter-circle command stage |
| 76 / 77 | Raw controller keys, before opposite-direction cleaning |
| 78 / 79 | Landing transition ticks remaining |
| 80 / 81 | Committed horizontal jump velocity, raw signed `u16` |

The trace remains under the reserved 256-byte region and is read-only from the
test host.

## Remaining limitations

Logical combat poses retain their sixteen-index contract. The renderer maps
them to 48 native animation frames per fighter across six banks, streaming at
most one 3,840-byte actor frame per vblank. The requested trace frame can lead
the uploaded frame by one video frame when both actors change together.
Per-fighter animation clocks and drawn transitions are included; dedicated
aerial attack art, per-frame hit silhouettes and human balance playtesting
remain future polish work. The ROM is verified in the official Snes9x
libretro core; real-hardware testing is still outstanding.
