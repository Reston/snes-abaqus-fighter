# v0.17.0 - CPU opponent in Training
<!-- candidate-version: 0.17.0; rom-sha256: cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe -->

Training adds **CPU** as its fifth behavior. Open the first PAUSED card and use
Up/Down to cycle Stand, Guard High, Guard Low, Jump and CPU. The first four
choices keep their behavior and a new match starts on Stand. CPU uses the
existing opponent AI at the Easy/Normal/Hard difficulty selected with L/R at
home. The 99 clock, health recovery and P1 Select reset remain available.
Reset keeps the chosen opponent and behavior. P2 gameplay buttons do not
control the Training opponent; either port can navigate the pause selector.

No AI policy, combat timing, damage, roster profile or native asset changes
are introduced. The v0.16 anti-air choices and earlier cross-up behavior remain.
Training's health-recovery timer is evaluated once only when a fighter is
eligible, with a low-bit prefilter before the original unsigned modulo.
Direct fighter accesses, a HUD fast path, locally cached action/tick reads
and skipping an empty throw-link call reduce repeated work. Original recovery
conditions, timing and full-health energy/HUD refresh remain.

- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- ROM SHA256: `cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe`.
- Header checksum: `5EAF`.
- Cartridge source freeze: `5fcd5cb28f4cf2453cb3310fbab0d6947d7afd9a`.
- Source tree: `5e3ef5c5f4be06fbd0bad8a37ef215a449f1c2a1`.

## Native preservation

All 219 generated art/audio/UI assets match verified v0.16.0. The approved
baseline is `0971895da72bf7cdde40571a920b7f9c156d34f0`; no changed or added assets are allowed.
All 1,276 existing WRAM/direct-page symbol addresses match. Fighter64/Wave16,
TRACE0..122, hardware/trace assembly, actor/OBJ/UI transfers, stage ambient
and SPC budgets remain. The CPU label uses a ROM literal to retain the
four-entry initialized label array's existing WRAM footprint.
[Champion art](CHAMPION-ENDING.md) and [victory music](CHAMPION-AUDIO.md) remain.

## Verification and package status

The initial 04aa387c.../3C3C candidate passed its short suites but failed full
CPU Training cadence at native frames including 52,560 and 54,000. Duplicate
health/HUD work was investigated with preserved controller-only diagnostics.
The first batched-HUD fix, 1ac5d976.../4C8C, passed that original policy but
failed the expanded twelve-opponent hour at callbacks 137,337, 174,198 and
175,243. The follow-up avoids timer work when neither fighter is eligible,
filters impossible recovery ticks and reduces repeated HUD/hit/animation work.
This candidate is being reverified; earlier results do not verify the new
cartridge. Negative
diagnostics remain source-only under ignored build/v17-timing-negative and
build/v17-all-roster-timing-negative.

Current-ROM gates are running: all six native suites, pinned independent
smoke, full matchup/replays, bounded independent combat, three native live-hour
sessions, isolated committed-source rebuild and focused champion/audio/menu/
authoring/practice evidence. The Training endurance session now requires a full
216,356 live frames with CPU selected and all twelve opponent profiles; its
reset and roster transitions retain the choice using controller input.
Historical reports do not verify this ROM.

The latest verified offline Windows checkpoint remains v0.16.0. Current-ROM
CPU Training clips and a pause card will accompany the existing anti-air,
cross-up and twelve-fighter practice media after verification. A new package
will be audited and reproduced twice after the current gates pass.

Human gameplay/balance, full listening, physical controllers, likeness/consent
and team/public-use approval remain open. Original SNES/flash-cartridge support
is unverified; public_release_certified remains false.
