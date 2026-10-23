# v0.22.0 combined ten-improvement candidate
<!-- candidate-version: 0.22.0; rom-sha256: d4fddaf609a0c29f45353a8d9e22fe1131fc3380838d9c0073d3255474cdf8af -->

All ten feature PRs are merged into `integration/ten-improvements-v022`.
Run the root [Play.cmd](../Play.cmd) from that checkout to try the combined
native SNES game. **Main remains v0.21.0 until your combined playtest and final merge.** [Final PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1)
collects the integration; the feature mapping comes from
[the retained PR map](expansion-prs-v0.22.0.json).

The cartridge remains a 4 MiB NTSC FastROM LoROM across 128 banks, built from
C and 65816 assembly with PVSnesLib 4.6.0. The authoritative deliverable is
`dist/abaqus-after-hours.sfc`, played in a native SNES emulator.

## Verification status

The combined cartridge passes all six native suites and all ten focused proofs
on one exact ROM. The matching pinned independent emulator smoke, authoring
guards and fresh committed-source export also pass. All tests run silently,
headlessly, through controller inputs with no emulator-memory writes or saves.

| Final record | Result |
| --- | --- |
| ROM SHA256 | `d4fddaf609a0c29f45353a8d9e22fe1131fc3380838d9c0073d3255474cdf8af` |
| Header checksum | `EA9D` |
| Cartridge source freeze | `b149cdf2d9e25560f61d09a0f49e71ce6fea7042` |
| Source tree | `f58da040001f57a12c55b3ce92bde66041164b71` |
| All six native suites | 36,253 passed checks |
| Ten focused feature proofs | 345,546 passed checks; all ten pass |
| Independent emulator | Pinned bsnes2014 Accuracy smoke passes |
| Training and CPU timing | Strict live cadence passes with all tools enabled |
| Authoring guards | 20 normal and 20 optimized mutation tests pass |
| Fresh committed export | Exact ROM, 219 generated assets and normalized symbols reproduced |
| Preservation / bank / transfer audit | Passed; 211 generated files preserved and eight permitted changes |
| Single combined human playtest | Pending; no v0.22.0 human approval recorded |

The [verification record](expansion-v0.22.0-verification.json) pins the report
hashes, source files and merged PRs. The [native review](EXPANSION-REVIEW-v0.22.0.html)
gathers the current captures and playtest steps. The
[integration note](EXPANSION-INTEGRATION-v0.22.0.md) explains shared ownership
and the native performance paths.

There is **no v0.22.0 offline ZIP or regenerated full release-scale evidence**.
The [v0.19.0 checkpoint](RELEASE-v0.19.0.md) remains the latest full offline
archive. Its matrix/replays, bounded independent combat, three native live-hour
sessions and isolated source rebuild are historical evidence. v0.21.0 and older
ROM identities remain in their own release notes.

## All ten improvements

| ID | Combined behavior and what to try | Feature guide | Merged feature PR |
| --- | --- | --- | --- |
| 01 | Weighted breathing, planted steps, strong-attack anticipation and landing/get-up recovery using the approved poses. Walk, jump and throw to compare the transitions. | [Animation weight](EXPANSION-01-ANIMATION-WEIGHT.md) | [#3](https://github.com/Reston/snes-abaqus-fighter/pull/3) |
| 02 | Compact amber light hits, larger gold strong hits and hollow cyan blocks, with different freeze and camera response. Compare Y, X and a guarded attack. | [Readable contacts](EXPANSION-02-IMPACT.md) | [#6](https://github.com/Reston/snes-abaqus-fighter/pull/6) |
| 03 | Y is the quick close jab, X the committed heavy punch, B the spacing/low kick and A the longest normal/cross-up. Confirm Y into X or B into A; test the risk of a close blocked heavy. | [Normal balance](EXPANSION-03-NORMAL-BALANCE.md) | [#7](https://github.com/Reston/snes-abaqus-fighter/pull/7) |
| 04 | Twelve individual intro gestures and winner sequences with signature accents. Watch a round opening and earn a win with different fighters. | [Fighter personality](EXPANSION-04-FIGHTER-PERSONALITY.md) | [#2](https://github.com/Reston/snes-abaqus-fighter/pull/2) |
| 05 | Training gains five-command history, current/last combo damage, an accepted-special cue and three drills on guide page 3. Pause, press Select three times and choose a drill. | [Training tools](EXPANSION-05-TRAINING-TOOLS.md) | [#11](https://github.com/Reston/snes-abaqus-fighter/pull/11) |
| 06 | Individual CPU spacing, pressure, guard, throw and recovery-answer habits. Compare Cristobal's pressure with Ivo's retreat or David's recovery answers at the same level. | [CPU personalities](EXPANSION-06-CPU-PERSONALITY.md) | [#5](https://github.com/Reston/snes-abaqus-fighter/pull/5) |
| 07 | Twelve full-gauge supers use a fresh neutral Y+B chord and spend all 96 energy. Compare volley, rush and rising sequences, then try guarding or interrupting one. | [Supers](EXPANSION-07-SUPERS.md) | [#9](https://github.com/Reston/snes-abaqus-fighter/pull/9) |
| 08 | Scenery bands follow the fighters subtly above a fixed floor; refreshed ambient cells celebrate actual round winners. Walk together across each arena, then win a round. | [Stage depth](EXPANSION-08-STAGE-DEPTH.md) | [#4](https://github.com/Reston/snes-abaqus-fighter/pull/4) |
| 09 | Arcade adds two-speaker exchanges, six reciprocal rivalries, individual winner quotes and personal champion text. Try Damian/Reston; P1 A skips the exchange. | [Arcade story](EXPANSION-09-ARCADE-STORY.md) | [#10](https://github.com/Reston/snes-abaqus-fighter/pull/10) |
| 10 | Distinct light/strong/guard sounds, menu/round and victory chords, spoken Round/Fight/K O and music ducking. Listen to an intro, a blocked heavy and an earned KO. | [Resident sound](EXPANSION-10-SOUND.md) | [#8](https://github.com/Reston/snes-abaqus-fighter/pull/8) |

These feature notes retain their isolated development identities and results.
The combined controls and contracts below take precedence where features meet.
[Review metadata](expansion-review-v0.22.0.json) selects current focused native
captures/audio for all ten and identifies this cartridge. GIF playback timing
is approximate.

## Combined controls and practice

Four face buttons remain the only attack buttons: **Y/X light/strong punch,
B/A light/strong kick**. Down+X uppercuts, toward+X throws at close range,
Down+A sweeps, Down+B gives a low light kick, and Down+Y quick-casts the
32-energy special. The motion is Down, Down+toward, toward+Y/X, with a
twelve-live-tick window per progressing step. Confirmed Y-to-X and B-to-A
chains reward actual hits; a guarded attack or whiff does not enable a cancel.
Only the airborne A strong kick keeps the short rear cross-up reach.

For a super, release both buttons and all directions, then press **Y+B
together with a full 96-energy gauge**, grounded and free to act. Its existing
projectile must have finished. Both presses must be fresh on the same input
sample: adding one to a held button, holding the chord until meter fills, or
holding Down does not activate it. A rejected chord does not spend energy or
fall through to a normal/quick special. Startup is vulnerable, recovery is
committed, and slower sequences can have gaps. Normal/Hard CPUs can make a
fallible full-gauge super choice through the same command rules, after incoming
wave and ordinary attack defense; Easy does not select supers.

Training's pause cycle is **PAUSED -> Controls 1/3 -> Move List 2/3 -> Training
Tools 3/3 -> PAUSED**. Left/Right cycles the guide pages. Tools Up toggles the
live footer and Down changes the drill: Normal -> Special, Block a Low Attack,
or Air Kick Cross-up. The footer records five P1 signatures, oldest first,
using absolute numpad directions plus `YXBA`; `6Y---` means Right+Y.
`NOW`/`LAST` show real combo hits and HP damage. `SP!` means an accepted paid
ordinary special executed, including a whiff; it is not proof of a hit or a
super. The footer can catch up after a busy exchange.

On the ordinary PAUSED card, Up/Down still chooses Stand, Guard High, Guard
Low, Jump or CPU. With CPU selected, either port's L/R shoulders change the
shared Easy/Normal/Hard level; opposing held inputs cancel. Start retains
priority over B, A and Select. B returns to the roster, A resumes, and Select
cycles pages. Live P1 Select resets the round, history and drill progress while
retaining the chosen opponents, dummy, difficulty, drill and display setting.
A new Training match starts with Stand, the display enabled and the first drill.
Physical P2 gameplay input remains ignored in Training. Versus/Arcade keep
two guide pages. The [player guide](PLAYER-GUIDE.md) gives the keyboard layout
and a short combined play route.

Arcade's P1 A skips the conversation into the usual countdown; otherwise the
exchange advances after about six seconds. Pause freezes it and Start retains
priority. A CPU winner also receives an individual quote. Eleven victories
earn the personal ending below the retained trophy and original Champion score.

## Combined native contract

The policy in [tools/expansion_contracts.py](../tools/expansion_contracts.py)
defines the integration's preservation boundary against the v0.21.0 baseline.
The [exact-ROM preservation audit](expansion-preservation-v0.22.0.json) passes.

- All twelve existing 64-frame fighter sets, portraits, palettes, physical
  scales, original masters and prompts are preserved, including approved Damian v5.
  Animation/personality/supers reuse those poses. Static stage tiles, maps and
  palettes, menu/UI assets and all five original scores are preserved.
- The tracked generated inventory stays at 219 files. Exactly eight outputs
  may change: `effects.bin`, `effects.it`, `soundbank.asm`, `soundbank.bnk`,
  `stage-dynamics.json`, `stage0_ambient.bin`, `stage1_ambient.bin` and
  `stage2_ambient.bin`. The other 211 retain their baseline bytes.
- Of 1,276 prior RAM labels, 1,271 retain their addresses. Only five metadata/
  libc labels relocate: `SECTIONSTART_.bss`, `SECTIONEND_.bss` and
  `tccs_libc_c.asm_msys` by 32 bytes; `SECTIONEND_globram.data` and
  `RAM_USAGE_SLOT_3_BANK_127_END` by 331 bytes. Appended allocations are 32 BSS
  bytes at `$7E29AF..$7E29CE` and 331 initialized bytes at `$7F0448..$7F0592`.
  Fighter64/Wave16, action IDs and TRACE0..122 retain their ABI; hardware and
  trace assembly remain preserved. This is not an all-addresses-unchanged claim.
- Each actor retains thirty 16x16 sprites, the 96x80 canvas and one 3,840-byte
  actor upload per vblank. HUD transfer stays 320 bytes; Training uses the
  existing 128-byte footer; guide rows 5..27 stay 1,472 bytes built over three
  paused ticks, with actor priority. Portrait/glyph/VRAM/palette ranges remain.
- Impact/personality/super accents share the existing effect OBJ at OAM byte
  276, entry 69. Visible impacts rotate OBJ priority to that entry after the
  OAM upload, then restore entry zero when quiet; this adds two register writes
  and no DMA bytes or OBJ entries. Volleys reuse one Wave slot per player.
- Stage depth owns HDMA channel 3, mode 2 to BG1HOFS `$210D`: a ten-byte table,
  three bands covering 224 lines and six PPU data bytes per picture. Tables
  publish after vblank; general DMA remains on channel 0. Ambient work retains
  four 256-byte phases, eight cells at VRAM `$3C00..$3C7F`, and yields to actor
  and interface work. The ordinary clock freezes at round end; an actual winner
  gets a separate bounded two-cycle reaction, then phase-zero settle. Draws
  receive no reaction; pause freezes both clocks.
- Eleven resident sound slots load only with the existing screen-off score
  replacement. Slots 0..3 retain the original cues; additional slots provide
  strong/guard, speech and chords. The sound bank stays within LoROM bank 24;
  SPC effects and each score must fit 64 KiB. The scheduler queues at most one
  three-byte SPC command per video tick, keeping cue and envelope work mutually
  exclusive, with no polling or per-hit streaming.
- Story uses existing 320-byte banner and 128-byte footer paths; personal
  ending text is composed during the screen-off champion transition. No new
  screen, OBJ, VRAM or palette allocation is required. Every linked section
  must remain within a 32 KiB LoROM bank.

## Review and release limits

The Training timing fix and combined technical gates are complete on the
cartridge identified above. Automated verification ran silently and headlessly;
authorized GUI review remains muted and separate. The single combined human
playtest is the next step before merging the integration into main.

No v0.22.0 human approval has been recorded. Human combat/balance, onboarding,
animation/contact readability, all new super/CPU behavior, story copy, full
listening, physical controllers, remaining likeness review, team/subject consent
and public-use approval remain open. Earlier approval of Damian's likeness and
the user's v0.21.0 response do not approve these additions.
`public_release_certified` remains **false**. Emulator-first support remains
the selected scope; original SNES/flash-cartridge support is unverified future
work. Full release-scale evidence and package audit are required before a new
offline archive can replace v0.19.0.
