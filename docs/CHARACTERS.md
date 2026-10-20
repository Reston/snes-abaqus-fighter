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

## v0.6 combat presentation

Each fighter's native animation set now has 64 frames across eight banks. Frames
48-63 provide dedicated air punch and air kick anticipation, active and recovery
cycles, separate thrower and victim roles, and distinct knockdown and wake
drawings. A successful throw delays its damage until the victim reaches the
floor; simultaneous throws tech without damage. Heavy uppercuts, heavy low
kicks and rising specials can begin the lift, flight, floor, get-up and wake
sequence. Wake grants four invulnerability ticks, and its final six ticks
accept buffered attack or jump input. Training health recovery waits until a
fighter is free of hurt, downed and wake-invulnerable states; Select resets the
round and clears pending throw/down/wake state.

The original 48 frame pixels and shared fifteen-color palette bytes remain
locked. Each fighter keeps one physical scale and feet baseline across all 64
frames, so air, throw, knockdown and wake poses do not independently resize the
character.

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
| 62 / 63 | Requested native animation frame, `0..63` |
| 64 / 65 | Animation state |
| 66 / 67 | Per-fighter animation tick |
| 68 / 69 | Buffered action ID |
| 70 / 71 | Attack buffer ticks remaining |
| 72 / 73 | Jump buffer ticks remaining |
| 74 / 75 | Quarter-circle command stage |
| 76 / 77 | Raw controller keys, before opposite-direction cleaning |
| 78 / 79 | Landing transition ticks remaining |
| 80 / 81 | Committed horizontal jump velocity, raw signed `u16` |
| 82 / 83 | Remaining hurt/guard-stun ticks |
| 84 / 85 | Guard state |
| 86 / 87 | Direct contact outcome: `0` none, `1` guard, `2` real hit |
| 88 / 89 | Current displayed combo count |
| 90 / 91 | Cosmetic combo/counter banner ticks, independent of hit linking |
| 92 / 93 | Counter-hit flag |
| 94 / 95 | Downed state (`0` free, `1` lift, `2` flight, `3` floor, `4` rise, `5` wake) |
| 96 / 97 | Downed-state tick |
| 98 / 99 | Remaining invulnerability ticks |
| 100 / 101 | Delayed down/throw damage |
| 102 / 103 | Downed-state owner fighter ID |
| 104 / 105 | Air-action flag |
| 106 / 107 | Throw-victim fighter ID |
| 108 / 109 | Buffered wake action ID |
| 110 / 111 | Wake age |
| 112 / 113 | Buffered wake jump flag |
| 114 | Post-wait PPU `STAT77` status; bit 7 is the OBJ overflow flag |
| 115 | Completed BG1 ambient phase, `0..3` |
| 116 | Live ambient clock |
| 117 | Pending BG1 ambient phase, `255` when none is pending |
| 118 | Pending ambient phase age in live ticks |
| 119 | v0.8 pause page: `0` normal, `1` controls, `2` specials |
| 120 | v0.8 guide build stage: `0` settled, `1..3` staged |
| 121 | v0.8 Training dummy: `0` stand, `1` guard high, `2` guard low, `3` jump |
| 122 | v0.8 guide dirty flag: `0` settled, `1` pending |

The trace remains under the reserved 256-byte region and is read-only from the
test host. `src/trace.asm` writes the Fighter/Wave contract directly at stable
offsets `0..113` and ambient fields at `115..118`; `main` samples post-wait PPU
`STAT77` into `114` before DMA. Changing the packed `Fighter` or `Wave` layout
requires updating its assembly offsets and this trace table together. The v0.8
fields append after the unchanged Fighter/Wave and ambient contract; they do not
change the packed `Fighter` or `Wave` layout.

## Remaining limitations

Logical combat poses retain their sixteen-index contract. The renderer maps
them to 64 native animation frames per fighter across eight banks, streaming at
most one 3,840-byte actor frame per vblank. The requested trace frame can lead
the uploaded frame by one video frame when both actors change together.
Per-fighter animation clocks, dedicated air attacks and throw/knockdown/wake
transitions are included. Per-frame hit silhouettes remain future polish work.
The historical v0.7.0 canonical silent batch passes all five native suites against
ROM SHA256
`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`, with
2,595 gameplay, 18,085 roster, 215 presentation, 854 focused-input and 4,537
stage checks in the v0.7.0 report snapshot. The canonical `Test.cmd` stage
portion recorded 4,528 checks; a focused extension added nine patch-only PPU
assertions and reran the unchanged ROM/engine. CPU coverage spans three
difficulties and four special families for 600 live ticks each, with explicit
spacing, low-guard, wake and no-KO lookahead cases. The separate pinned
bsnes2014 Accuracy smoke passes against the same ROM and covers all three
ambient stage roles, freeze behavior and synchronized low-wave cadence. The
CPU and stage passes keep the profile tables, fighter art and native ABI
unchanged. Human balance playtesting, independent full-combat/soak runs and
real-hardware testing remain outstanding.
Actor-bank and action-timing selection, as well as unchanged OAM
and shadow work, are cached by the native fast path. Interface impact feedback
may settle one to three video frames later when its DMA yields to an actor
upload; hitstop keeps combat state frozen.

The historical v0.7 stage/effect integration adds four-phase ambient stage tiles and
original strike, guard, high-wave and ground-wave effect variants without
changing the fighter profiles, the `0..113` combat ABI or the one-actor
transfer budget. The stage report and expanded compatibility smoke pass against
the verified v0.7.0 baseline ROM. The archive passes 214 technical checks and repeated packaging
produces identical bytes. No public,
human-balance, independent full-combat/soak or real-console release claim is
made here.

## v0.8.0 historical profile and guide contract

The verified v0.8.0 source-freeze snapshot leaves all twelve combat profiles, movement
values, special families and native fighter frame data unchanged. The pause
Specials page reads the two live fighter IDs and displays each character name,
special name and family type; it does not copy a static roster table into the
fight. The Controls page documents the same six-button rules, including the
twelve-tick quarter-circle and 32-energy cost.

Training's pause dummy modes are Stand, Guard High, Guard Low and Jump. Guard
holds relative back without retreat, and the Jump dummy automatically jumps
again after landing. Live Select resets the round while preserving the chosen dummy; a new
Training match starts at Stand. These controls are a review target, not a
balance or release approval.

The verified v0.8.0 source freeze is commit
`48f3ccb539492247b83f4360a50bdc020bad9dd6`, tree
`e571aca40019b868bf224bb619390f5ea651434e`; its ROM is
`53ef44225c83bd52ee0eea3910ba74ade5ba949af7aa7440c74d959812c13090`, header
`6A21`. All six native reports pass on the exact SHA with 30,641 checks. Matching
compatibility, matchup, bounded independent-combat, endurance and fresh-source
evidence also pass. The offline package passes 7,471 technical audit checks; Reston's
remaining likeness review and the other human gates remain open.

The v0.7.1 historical technical snapshot leaves all twelve combat profiles,
movement values and native frame data unchanged. The source freeze is commit
`6d756749dbc3fa176e26217f2f59525c9af360d8`, tree
`fa15fea48b5cc2a09608da199810db885872e434`; the canonical ROM is
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`. The
five native reports record 2,595 gameplay, 18,085 roster, 215 presentation,
999 focused-input and 8,143 stage checks (30,037 total). Full 288-case native
coverage at 600 frames plus four replays passes, as do the independent smoke
and bounded 28,800-frame run. Its CPU neutral opening skips an already active
own wave, while impact feedback uses a quiet first frozen tick and combined
second-tick HUD/banner construction. Training Select applies the round state
immediately and flushes HUD, banner and footer over three frozen reset frames.
Fresh export, full native endurance and the package audit pass. Human
likeness/balance, listening, controller, real-console and branding gates remain
open.

## v0.8.1 verified Reston v4 art

The verified v0.8.1 snapshot changes Reston's art sources only. Combat profile data,
special family, movement, jump, throw, normal timing and native gameplay remain
unchanged. Reston's complete 64-frame set and selected portrait use
`atlas-v4.png`, `animation-motion-v4.png`, `animation-actions-v4.png` and
`animation-airborne-v4.png`, with the original v3 sources retained. The adjacent
`likeness-v4.json`, `animation-v4.json`, `animation-airborne-v4.json` and
`native-revision.json` preserve imagegen provenance and the source/native
revision record.

The immutable v0.8.0 baseline pins all twelve prior 64-frame sets. The other
eleven fighter bank bytes are identical, all twelve palettes and uniform scales
are unchanged, and Reston's source normalization, palette and scale remain
locked. The expected v4 native frame-hash digest is
`7fe74ce9c1d771203191606d8f9ea05398eebb2507f7ab7dc538c766c274bfda`; the
palette SHA256 remains
`0fa34b1d226a993d001bd2df79e0b4f69827c214668446fe7b3b19bb3c64aa1d`, with
uniform/physical scale `0.2280130293159609`.

Full64 native visual review accepted Reston v4 for integration. Actual human
likeness and consent feedback remains pending. All six native reports and
matching expanded evidence pass against ROM SHA256
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`, header
`A358`. The v0.8.1 package and its 7,471-check audit pass; balance, listening,
controller, real-console and branding gates remain open.
