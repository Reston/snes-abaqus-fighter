# Expansion 07: full-gauge supers

Feature branch: `t3/roster-super-moves`, based on integration commit `610537d`.
This is an isolated feature candidate for the parent's v0.22.0 integration.

## Command and rules

Release both buttons, then press **Y+B together on the same native input tick**
with no direction held, while grounded and free to act. The entire **96 energy**
is paid immediately. An existing owned projectile must finish before activation.
Either physical port can use the command in Versus. Training retains its
existing P1 controls and ignores physical P2 gameplay input.

Both edges must be fresh. Adding B to held Y, or Y to held B, cannot activate.
A held chord never fires when the gauge becomes full. A rejected chord consumes
neither energy nor an ordinary attack; Down+Y+B cannot accidentally buy the
32-energy quick special. A valid chord wins over other simultaneous face edges.
L/R remain Training level controls. Existing ordinary attack, motion, jump,
hitstop and wake buffers retain their behavior outside the new chord.

Supers cannot begin during an action, hitstun, knockdown, wake invulnerability,
air movement or death. A valid neutral request sampled during hitstop uses the
existing six-live-tick buffer duration in separate state. Start owns pause and
resume samples; Training Select retains its reset priority and clears all super
state. The native move-list page teaches the command and names both supers.

## Twelve sequences

Timing is in live simulation ticks; hitstop freezes it. Startup is vulnerable.
The recovery column is the final committed recovery after the release window.
Each volley uses one existing projectile slot, waiting for the preceding shot
to hit, clash or expire before releasing the next. Its bounded emission window
shortens to the last release plus three ticks when all shots have left.

| Fighter | Super | Startup | Sequence | Uncontested damage | Recovery |
| --- | --- | ---: | --- | --- | ---: |
| Damian | Kernel Overdrive | 12 | Three high shots, fast balanced cadence | 10+10+12 = 32 | 26 |
| Ivo | Compound Interest | 18 | Two slower high shots, delayed heavy second | 15+19 = 34 | 32 |
| Cristobal | Atomic Cascade | 8 | Three advancing punch/kick rush strikes | 9+9+14 = 32 | 24 |
| Cote | Final Balance | 14 | Two heavy advancing blows, wider gap | 13+21 = 34 | 32 |
| Negger | Macro Collapse | 20 | Two slow low waves, heavy final shock | 15+21 = 36 | 32 |
| David | Final Audit | 9 | Two body punches into a rising finisher | 8+8+18 = 34 | 28 |
| Fernando | Legacy Rollout | 14 | Three low waves with steady pressure | 10+10+13 = 33 | 24 |
| Cristian | Zero Risk | 13 | Long-reaching check into a high rising finish | 12+22 = 34 | 34 |
| Mamariaga | Merge Storm | 8 | Fast low/high/low volley | 8+8+13 = 29 | 22 |
| Reston | Cloud Nine | 16 | High shot followed by a heavy low wave | 14+22 = 36 | 30 |
| Roxana | Closing Bell | 7 | Advancing kick/punch into the highest rising finish | 7+7+17 = 31 | 26 |
| Lars | Absolute Zero | 22 | Slow long-reaching low wave then high finisher | 16+22 = 38 | 28 |

Direct strikes confirm once per pulse; their final real hit knocks down. Earlier
hits use ordinary hitstun, so the slower sequences can have escapable gaps.
Projectile heights, speeds, lives, reach, damage and release spacing differ by
fighter. Rush distance and rising launch velocity differ independently of the
approved art. Existing startup-counter damage (+3), block/chip, recoil, trades,
hitstop and ordinary +8 real-hit energy gain remain. Passive energy regeneration
waits until the super ends. Whiffs and blocked hits provide no hit-energy gain.
There is no added invulnerability, super cancel or cost bypass.

## Implementation and hardware audit

`src/super_moves.h` owns profiles, names, command recognition, sequence clocks,
collision, animation selection, the guide text and all new mutable state.
Small hooks in `game.c` handle input, controls, update, collision damage,
projectile tags, animation and reset. `pause_guide.h` adds one guide hook.
`cpuKeys` is unchanged; a later CPU integration can deliberately generate the
same fresh command under the same eligibility rules.

- Fighter stride 64, Wave stride 16, all their compile-checked offsets, original
  attack IDs 0..9, and TRACE 0..122 stay intact. A private flag distinguishes a
  super using the existing action 7.
- Seven two-entry byte arrays append **14 bytes** after `roundUiPending`.
  All 1,245 existing non-libc RAM/direct-page symbols preserve their addresses,
  including the original initialized guide strings. SDK libc scratch follows
  BSS and moves by those 14 bytes; linker section markers move accordingly.
- Names are ROM string literals, avoiding an initialized WRAM string table.
- All 219 tracked generated files and retained art/source files match the base.
  Approved Damian v5, fighter palettes/scales, stage masters and audio remain.
- No additional OBJ, palette, VRAM tile, transfer, sound slot or streaming load.
  Charge/contact uses the existing single effect sprite; volleys reuse each
  player's single Wave slot. The one-actor-vblank and guide transfer paths stay.
- Released waves retain their own damage/reach tag if the owner is interrupted.
  New ordinary projectile creation clears its tag; expiry, collisions and reset
  cannot leak a later super attack.
- Every linked ROM section remains within its 32 KiB bank; the largest is the
  unchanged 30,720-byte fighter bank. The linked-section audit leaves 924,962
  ROM bytes outside occupied section spans.

## Reproduce and evidence

Use the ignored `.tools` junction to `D:\snes-abaqus-fighter\.tools`; do not run
shared setup or rewrite the tool cache. Build, then run the focused proof:

```powershell
D:\snes-abaqus-fighter\.tools\python\python.exe tools/build.py
D:\snes-abaqus-fighter\.tools\python\python.exe tools/test_expansion_07_supers.py
```

The focused driver creates no window or audio device, never writes WRAM and
never loads a save state. Meter fills by ordinary passive regeneration. All
movement, attacks, guards, jumps, hurt, knockdown, KO, pause, guide and reset
fixtures use native controller input. Read-only linked symbols identify private
sequence state; the public trace, actual HP, PPU VRAM/image and STAT77 prove the
outcomes. Existing frame-bank bytes identify complete uploaded actor poses.

The report covers all twelve fighters on both ports for full-cost activation,
held/partial/low-gauge chords, every tuned hit pulse, every guarded pulse and
startup interruption. It also covers twelve far whiffs, an approach into a real
recovery punish, airborne/hurt/down/wake/KO rejection, Training reset, Start plus
Select priority, guide publication and ordinary Down+Y after a super.

- Exact candidate ROM SHA256:
  `89fc09f725b6ee5ca5e68f6b7238891c701676a0cf178985fd9081403e045da8`.
- Exact-ROM result, controller outcomes, source/test/core hashes and timing:
  [expansion-07-report.json](expansion-07-report.json): **2,151 focused checks
  pass**, with **28,965 monitored native frames**, zero cadence failures and
  zero STAT77 OBJ overflow failures. Runtime: 107.330 seconds.
- Native hit clips: [Damian](screenshots/expansion-07-00-hit.gif),
  [Cristobal](screenshots/expansion-07-02-hit.gif),
  [David](screenshots/expansion-07-05-hit.gif),
  [Mamariaga](screenshots/expansion-07-08-hit.gif),
  [Lars](screenshots/expansion-07-11-hit.gif).
- Native [P2 Cote block clip](screenshots/expansion-07-03-block.gif) and
  [move guide](screenshots/expansion-07-guide.png).

GIFs sample actual callback pictures every three video frames with 50 ms GIF
durations. Playback timing is an inspection approximation; native timing is
measured separately by the proof.

No shared six-suite reports, compatibility report, version file or release
package are changed here. Parent owns combined native suites, independent smoke,
cross-feature hook integration and the final integration PR. Human balance,
controller feel and listening remain review work. Full release-scale evidence
and public-use gates are outside this feature proof.
