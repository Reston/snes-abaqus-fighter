# v0.5.0 — clean menus, character animation and responsive inputs

The native cartridge expands to 4 MiB FastROM LoROM. Each of the twelve
fighters has 48 native frames: the sixteen existing key poses and 32 newly
drawn motion/action frames. All corrected likeness masters remain intact,
including Reston's short-hair correction.

## Presentation

Home, fighter selection and arena selection use restrained navy/royal fields,
clear white lettering and one gold cursor. Statistics, badges, numbered tabs
and extra panel borders are removed. The twelve-card grid and large selected
portrait retain their controller navigation and native rendering.

## Animation

Four breathing frames, four forward steps and four backward steps give every
fighter independent idle and walking cycles. Walking phase follows distance
travelled. Crouch, jump and landing transitions accompany attack anticipation,
active key poses, recovery, block impact, hurt, victory and knockout sequences.
Fighter animation freezes during pause and hitstop.

The two new source atlases per fighter are original built-in imagegen art.
Their complete prompts and provenance are in each character's `animation.json`.
Each source atlas is normalized once to its neutral guard; all 48 frames then
share one physical scale and a fixed 96×80 canvas. No pose is independently
shrunk. The six eight-frame banks remain below each 32 KiB LoROM boundary.

## Control feel

- Six-tick attack and jump buffers retain short taps through brief recovery
  windows. Pads remain sampled during hitstop while buffer expiry freezes.
- Quarter circles recognize Down → Down+Forward → Forward+Punch within a
  twelve-tick directional window. Down+Punch remains an accessible shortcut;
  Down+Back+Punch produces a normal attack.
- Simultaneous opposite directions resolve to neutral on each axis.
- Diagonal jumps commit momentum at takeoff and keep facing until landing;
  neutral jumps stay vertical. A held Up input can repeat a jump on landing.
- Hit-confirm cancels have an explicit early recovery window. Blocking has
  eight ticks of stun and reduced impact pushback.
- Select resets Training immediately; the included P1 keyboard binding is
  Shift. Aerial normals retain their existing key art and generic transitions.

## Verification

The gameplay, roster/animation, presentation and input suites run the actual
cartridge silently in the official Snes9x libretro core. Reports record the
exact current ROM SHA256. Roster checks compare all streamed rows against the
six native banks, inspect OAM, check proportions, and capture native animation
GIFs for review. Release packaging requires matching successful reports.

All four suites pass against ROM SHA256
`e0c733a607abe6db27b9aaf68056d5153ef8cc43d4a82bf3d83e8d87135eeccc`:

| Suite | Passed checks |
| --- | ---: |
| Gameplay and arcade progression | 188 |
| Roster, proportions and native animation | 4,574 |
| Menus, portraits and stages | 161 |
| Input, jumps, guard and Training reset | 97 |
| **Total** | **5,020** |

The cadence probe records 600 game ticks over 600 emulated frames. Review
captures include 36 native idle, walk and attack GIFs across all twelve fighters.

Human controller playtesting, detailed balance work, dedicated air-attack art,
additional in-betweens, stage parallax and real-console checks remain future
work. This release does not claim an exact reproduction of SFII frame data.
