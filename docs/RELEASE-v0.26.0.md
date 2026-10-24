# v0.26 play-flow polish candidate
<!-- candidate-version: 0.26.0; identity: TECHNICALLY_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: 27223b80377173d9535ccd1374b2470cc138a15324852c8b8833fd4f8fd00c7b; source-freeze: c89239901491a239e10194f1399820527b0ebf74 -->

The slower combat and detailed floors from [v0.25](RELEASE-v0.25.0.md) now
have clearer local play, more useful practice and optional comfort settings.
[PR #22](https://github.com/Reston/snes-abaqus-fighter/pull/22) stacks on unmerged
[PR #21](https://github.com/Reston/snes-abaqus-fighter/pull/21). Main remains
approved v0.24.0. Both candidates are ready for a combined human playtest.

Run [Play.cmd](../Play.cmd) and read **V0.26.0** on the title. The launcher
checks that the cartridge matches the checkout before opening it. See the
[native comparison gallery](REVIEW-v0.26.0.html) and [full controls](PLAYER-GUIDE.md).

## What to try

- **Fight rhythm and ground:** walk/projectiles travel about 25% slower than
  v0.24; attacks, jumps and recovery provide more time. Hits visibly recoil.
  All three detailed floors form one connected image with their scenery.
- **Local play:** either pad chooses the arena, rematches or returns to select.
  Mirror results name the winning player. Session match wins persist across
  rematches; round medals still describe only the current best-of-three match.
- **Readable exchanges:** full energy shows **SUPER Y+B**. **PUNISH!** identifies
  a recovery hit; **COUNTER!** remains a startup hit. **THROW TECH!** identifies
  the existing non-damaging simultaneous-throw escape.
- **Training:** prepared drills, real light-to-strong hit confirms, Guard After
  Hit, P2 Controller practice, retained best combo and each fighter's actual
  normal startup/active/recovery timings. X on Tools 3/3 retries the drill.
- **Comfort and navigation:** held directions scroll after a delay; confirm/back
  remain single presses. Full guide pages offer L for music and R for still
  scenery. Combat sounds, fighter recoil and fight timing remain active.
- **Orientation:** roster cards teach special families and costs; Arcade names
  the ladder shift, next challenger and retry opponent. Arena previews derive
  from the current native stage image.

## A short playtest

1. Play a Local mirror match. Win a round, finish the match and rematch from
   P2. Check player labels, round medals and the separate session score.
2. Use Training's Guard After Hit partner. Land Y then X or B then A; compare
   a real link with a deliberately late follow-up that gets blocked. Retry
   with Select or Tools X and check that BEST stays useful.
3. On ordinary Training PAUSED, X selects P2 Controller. Practice both players'
   commands and blocks, then X returns to Stand. Automated dummies ignore P2.
4. On a full guide page, compare music L and background R. Test all three
   floors, a jumping cross-up, a blocked heavy and a recovery punish.
5. Win and lose an Arcade match. Check the next/retry opponent and compare
   the slower rhythm with your earlier feedback.

## Verification

| Identity | Value |
| --- | --- |
| Cartridge | 4 MiB NTSC FastROM LoROM, v0.26.0 |
| ROM SHA256 | `27223b80377173d9535ccd1374b2470cc138a15324852c8b8833fd4f8fd00c7b` |
| Checksum | `3993` |
| Source/test freeze | `c89239901491a239e10194f1399820527b0ebf74` |
| Six native suites | **49,689 exact-ROM checks passed** |
| Current special stress | 432 cases, 720,078 callbacks, zero SDK lag |
| Long native sessions | One live hour in each mode; all twelve CPU Training opponents |
| Unmasked HUD comparison | 244,237 complete logical states, zero changed bytes |
| Session score limit | 200 earned matches, both counters stop at 99 |
| Fresh committed-source build | Same cartridge, 226 generated assets and normalized symbols |
| Complete verification command | All 40 commands passed; source inputs stayed fixed |

Full-roster pacing, supers, CPU difficulty/replays, focused play-flow proofs,
pinned Accuracy smoke and normal/optimized authoring guards pass on this
cartridge. The three long sessions retain strict cadence, PCM, FIFO and OBJ checks;
CPU Training measures 216,363 live callbacks. Its current four-button
coverage is separate from the historical six-attack/champion-within-one-hour
traffic contract. The focused Arcade proof earns all eleven victories.
The stage suite and focused stage appendix share one native run, counted once. Reports and media are bound in
[verification-v0.26.0.json](verification-v0.26.0.json).
The [end-to-end execution ledger](play-flow-v026-execution.json) retains every
command, exit and log hash (ledger SHA256 `5af53f599a3149d8a68f978c56f856206688ea9cead25f294af52d355540b20d`). Logs and full
raw streams stay in ignored build paths and are produced again by the command.

All approved fighter drawings, portraits, palettes, scales, audio and stage
payloads remain. Existing 1,318 RAM addresses and native ABI remain. The
[polish contract](POLISH-v0.26-CONTRACT.md) and [pass notes](POLISH-v0.26.0.md)
record boundaries and retained historical failures. The full verification is
repeatable with the [one-command developer route](DEVELOPMENT.md#complete-current-candidate-verification).
Builds now stage assets
and native outputs, recover interrupted publication and reuse verified assets.

Human playtest is pending. There is no new offline ZIP or public-release
certification; the latest complete Windows archive remains v0.19.0.
