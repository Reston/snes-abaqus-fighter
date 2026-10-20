# v0.7.1 — CPU openings and sustained frame-budget checks

This verified technical development snapshot fixes a deterministic CPU omission
and keeps combat, pause and Training updates within the native frame budget.
It remains subject to
[the public-release gates](PUBLIC-RELEASE.md).

- Cartridge: 4,194,304 bytes, NTSC FastROM LoROM; header checksum `9496`.
- ROM SHA256: `64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`.
- Cartridge source commit: `6d756749dbc3fa176e26217f2f59525c9af360d8`.
- Source tree: `fa15fea48b5cc2a09608da199810db885872e434`.

## Changes

- Projectile and groundwave CPUs issue an opening special above 110 pixels
  when they have at least 64 energy. Waiting for the global 97-tick phase
  previously let most of these fighters approach inside their casting band
  without ever showing a signature move in an ordinary neutral opening.
  Subsequent casts retain the established cadence. A CPU does not start a new
  wave special while its own wave is active.
- Impact feedback snapshots the resolved hit, combo and counter outcome on
  contact. The first frozen tick lets the second actor upload settle; the
  second frozen tick rebuilds the health/energy bars and banner. Periodic HUD
  work respects that queue. Damage, contact, guard and attack timing remain
  immediate. Simultaneous feedback retains the existing last-contact banner
  policy.
- Training Select resets simulation state immediately and uses three frozen
  ticks for idle uploads and changed interface regions. It keeps the existing
  labels instead of constructing an entire round panel during live display.
  New controller edges can buffer during this freeze, as during hitstop.
- Round-result panels also wait for the second actor upload. Between rounds,
  actor state resets first; the existing intro then rebuilds its panel and HUD
  over separate ticks. Forced-blank loading of a different screen is recorded
  separately from live-fight cadence.
- The effect animation clock resets with the round, making wave phases and
  impact flips independent of the console's initial WRAM contents.
- Resident sound commands use one ready-only FIFO transfer per frame. The
  gameplay loop never polls for an SPC acknowledgement; scene loading retains
  the SDK's synchronous handshakes. This adapter supports the current resident
  samples only. Adding streamed sound requires restoring stream servicing.
- Native helpers preserve the exact hit-reaction field updates, damage-to-stun
  formula, banner/footer/pause fills, actor and shadow bytes, and pose queue
  while reducing compiled pointer arithmetic and indexed loops. A 746-frame
  controller comparison preserves all 544 OAM bytes per frame. Pause UI and
  OAM parity checks also pass. Damage, attack windows and recovery rules are
  unchanged.

## Verification scope

The native input suite now includes 21 ordinary, phase-independent CPU opening
cases: seven projectile/groundwave fighters at three difficulties, with P1
neutral for 180 ticks. Mirrored counter-hit fixtures require real damage,
unit frame cadence and the exact `COUNTER!` banner within three frozen ticks.

All evidence below passes against the exact ROM above:

| Gate | Result |
| --- | --- |
| Canonical `Test.cmd` | 2,595 gameplay + 18,085 roster + 215 presentation + 999 focused input + 8,143 stage checks = **30,037** |
| Native matchup matrix | 288 cases: all 144 ordered pairs under two policies, 600 frames per case, all three stages; four deterministic replay digests match |
| Independent engine | Pinned bsnes2014 Accuracy smoke plus 48 bounded combat cases / 28,800 frames |
| Native endurance | Arcade, Local Versus and Training each complete 216,356 live frames at 60.0988118623 FPS, exceeding one emulated live hour per mode |
| Isolated source rebuild | Fresh pinned tools reproduce the ROM, manifest, all 214 generated assets and normalized symbols from the source commit above in 63.25 seconds |

The uninterrupted sessions use one core boot/unload each, zero reboots, and
observe four, four and three native frame-counter wraps respectively. Every
required coverage flag passes. Cadence, native timing, ambient, audio FIFO and
PPU overflow failure arrays are empty; stable-fight lag increments are zero.
Captured video and PCM remain healthy. These are accelerated emulated hours,
not three hours of human play. Independent combat remains bounded: it is not
an independent full ordered-pair matrix or independent hour-per-mode soak.

The endurance driver now uses the roster's actual 4-by-3 grid controls, taking
at most three cursor pulses per fighter. The former forward-only route could
spend longer than the softlock allowance navigating a healthy menu. Every
720-frame timeout, loaded-character/stage assertion and cadence gate remains
unchanged. The benchmark and full sessions were rerun with the final harness.

Thirty focused pause assertions cover both pads in all three modes and require
unit cadence on pause and resume; the same fixture rejects the previous
cartridge. All automated runs use controller callbacks and read-only telemetry
without playing audio or opening an emulator window.

Packaging requires all four additional reports against the exact current ROM,
including a frozen source commit/tree for the isolated rebuild. Short
benchmarks and ignored checkpoint files cannot substitute for the tracked
full endurance report. The technical audit keeps
`public_release_certified=false`.

The offline Windows archive includes the tested cartridge, Snes9x, controls,
guides, licenses and all release-gate reports. It passes 6,153 technical audit
checks. A test count or scripted matchup result does not establish human
balance, likeness approval, listening quality or physical-console compatibility.
