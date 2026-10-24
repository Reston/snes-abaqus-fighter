# v0.25.0 — deliberate pacing and detailed floors
<!-- candidate-version: 0.25.0; identity: TECHNICALLY_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: f0223f8240e2338ec57674b465a93cc5b0145a6210b5d5933706bac7277168a2; source-freeze: b41ce034ac12f6aa10740a0075feebd1f392d117 -->

The v0.24 merge was complete, but your playtest still felt too fast and its
two-gray floors looked blank. This candidate makes the combat rhythm slower
and restores detailed paving and office material. Technical verification passed; it is ready for your playtest; main remains the approved v0.24 revision.

## What changed

- Walking, retreat and ordinary projectile travel are about 25% slower than
  v0.24. Every normal has more windup/recovery; specials and supers also give
  more preparation and recovery time. The defensive uppercut and close throw
  retain responsive startup.
- Lower gravity lengthens every fighter's jump by at least 15%, with similar
  height and enough clearance for real cross-overs. Takeoff momentum and
  committed airborne facing remain.
- Light/strong/guard contact pauses grow from 4/6/3 to 7/10/5 native ticks.
  Longer hit reactions retain backward recoil. Linked rising supers keep
  their capped drift so follow-up punches still reach.
- CPU decisions leave more space between attacks and sample defensive answers
  less frequently. CPU attack starts in the paired 1,800-tick encounters: 1285 → 862 (32.92% fewer).
- The outdoor floors reuse approved detailed material. The office gets a new
  illustrated carpet strip. The floor now shares the scenery's six 4bpp
  palettes instead of collapsing into two UI grays.

Native video, controller polling, round clock and audio retain normal NTSC
cadence. The game does not slow the emulator or skip simulation frames.
Damage, move reach, energy costs, four-button controls, local two-port play,
all 64 fighter drawings, portraits, palettes and scales remain unchanged.

## Test it

Run [Play.cmd](../Play.cmd) from this branch, or load
[the cartridge](../dist/abaqus-after-hours.sfc) in your SNES emulator.
Choose **Local 1v1 / 2P** or Training. Compare a walking approach, a jab and
strong punch, a jump over the opponent, and the pause/recoil after a hit.
Try all three stage floors. [Native before/after gallery](REVIEW-v0.25.0.html).

## Technical verification

All six native suites pass **49,494 checks** on this exact ROM. Focused pacing, 48 super hit/guard sequences, before/after CPU36 plus twelve Hard replays, and all three stages on both cores pass. Matching pinned Accuracy smoke, normal/optimized authoring guards and a fresh committed-source export reproduce the ROM, all 226 assets and normalized symbols. The shared stage suite and focused stage appendix use one execution, counted once.

| Identity | Value |
| --- | --- |
| ROM SHA256 | `f0223f8240e2338ec57674b465a93cc5b0145a6210b5d5933706bac7277168a2` |
| Checksum | `FF9C` |
| Source/test freeze | `b41ce034ac12f6aa10740a0075feebd1f392d117` |
| Mapping | 4 MiB NTSC FastROM LoROM, PVSnesLib 4.6.0 |
| Generated files / unchanged RAM labels | 226 / 1,318 |

[Exact verification](verification-v0.25.0.json) ·
[Native allocation and pacing contract](COMBAT-v0.25-CONTRACT.md).
BG1 uses 28 KiB for connected scenery/ground; BG3 is disabled. UI, actors,
effects, native ABI and trace assembly retain their allocations. No live
stage DMA/HDMA or extra sprite entries are introduced.

The office strip was created with **built-in imagegen**. Its
[saved source](../assets/art/stages/floor-v025/02-oficina.png) and
[exact prompt, inputs and provenance](../assets/art/stages/floor-v025/02-oficina.json)
are retained. Earlier source art stays available as history.

## Review status

This candidate awaits your gameplay and floor review. It is not merged.
[PR #21](https://github.com/Reston/snes-abaqus-fighter/pull/21) contains this revision.
GIF timing is an inspection approximation; the cartridge is authoritative.
No new full offline package or public-release certification is claimed.
Historical v0.24 evidence remains labeled for its original cartridge.
