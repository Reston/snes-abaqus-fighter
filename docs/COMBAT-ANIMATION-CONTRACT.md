# Next combat-animation milestone

This defines the v0.6 combat-animation expansion from the v0.5.1 baseline.
Each fighter adds one original transparent four-by-four atlas,
`animation-airborne.png`, with full prompts/provenance in
`animation-airborne.json`. The new range is 48-63; old indices 0-47 stay stable.

| Frame | Required drawing and runtime role |
| --- | --- |
| 48 | Upright neutral guard matching the original idle; source normalization anchor and thrower recovery |
| 49 | Air-punch anticipation, visibly airborne |
| 50 | Air-punch active extension |
| 51 | Air-punch retract toward airborne guard |
| 52 | Air-kick anticipation, visibly airborne |
| 53 | Air-kick active extension |
| 54 | Air-kick retract toward airborne guard |
| 55 | Compact neutral air/apex guard |
| 56 | Thrower contact/grip, arms toward opponent |
| 57 | Thrower release/turn, readable throwing force |
| 58 | Victim lifted/off balance, limbs contained within the cell |
| 59 | Victim ground impact, head left |
| 60 | Knockdown launch/recoil |
| 61 | Knockdown fall, head left |
| 62 | Grounded get-up with a planted hand/foot |
| 63 | Wake-up guard returning to neutral |

The first frame is deliberately upright. An apex pose with bent knees cannot
serve as a standing-height normalization anchor. Existing frame 31 supplies
landing compression; no extra landing slot is needed. Thrower and victim frames
are distinct, rather than asking one drawing to represent both roles.

## Physical and palette invariants

Keep the current 96x80 canvas, 94x77 safe area, baseline 78 and each fighter's
standing height. Derive the physical scale and fifteen-color OBJ palette from
the existing 48-frame sources exactly as before, then normalize the entire new
atlas once against its upright anchor. Apply the same physical scale to all
64 frames. If a new drawing does not fit, repair that drawing rather than
shrinking the old roster. Preserve and compare all old native frame hashes and
palette bytes. The source atlas may not silently recolor the old 48 frames.

The preview becomes 6144x80 RGBA. Eight 30,720-byte banks hold each fighter:
`fighterXX.bin`, then `fighterXXb.bin` through `fighterXXh.bin`. VRAM/OAM pages,
thirty 16x16 pieces per actor and the one-3,840-byte-upload-per-vblank budget
stay unchanged. Extend the existing bank resolver to G/H.

A read-only v0.5.1 section audit found 2,454,978 linked payload bytes, with the
highest linked end at physical `0x274eab`. The extra 24 banks add 737,280 payload
bytes, or 786,432 bytes including full bank slots. This fits the 4 MiB target
with code-growth headroom; verify the actual linked result before acceptance.

## Engine and acceptance

- Airborne normals explicitly select punch/kick anticipation, active and
  recovery drawings. Strength-specific timings remain profile data. Captures
  cover all six buttons, ascent/descent and both facing directions.
- Throws need separate attacker/victim state. A bounded launch/downed/get-up
  sequence defines control lock, contact eligibility and the wake transition.
  State changes, pause, hitstop, round end and Training reset must be explicit.
- Resolve contacts from one snapshot. Mutual throws tech with six ticks of
  separation stun; an active throw beats a simultaneous normal, while an
  active direct special beats a throw. Ordinary strikes may trade. Projectiles
  resolve afterward and may interrupt a thrower during lift, safely releasing
  the victim without applying the pending throw damage.
- A throw has six live lift ticks, followed by ballistic flight. Damage applies
  exactly once on impact. Floor, get-up and wake durations are 18, 10 and 6
  live ticks. A knockout finishes its flight before the result card. Downed
  actors cannot act, guard, separate bodies or receive another contact.
  During lift/flight/floor, the render-facing field follows the launch
  direction so head-left impact/fall drawings mirror correctly. Gameplay
  facing is restored toward the opponent for wake commands.
- Wake restores opponent-facing commands and captures only new attack/jump
  edges in the final six ticks. Pre-down inputs are discarded. Pause/hitstop
  freeze the separate wake buffer. Four free ticks of contact invulnerability
  follow wake; holding UP before the knockdown cannot cause a ghost jump.
- New telemetry appends after TRACE[93]; stable offsets 0-93 must not move.
- All 64 metadata records share the same physical scale, with complete hashes,
  source roles and bounds. Air, throw and recovery groups must remain visibly
  distinct after quantization; no placeholder or relabeled grounded frames.
- Prove exact G/H bank VRAM rows, OAM geometry, pivots, facing and visible PPU
  output through controller input. Recheck all old 48 frames and special timing.
- Preserve the four exact-ROM suites, add air/throw/wake regressions, capture
  native animation for review and check cadence under two-actor combat load.
