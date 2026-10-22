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

The optional review pages keep native pixels clear in 2x view. The gallery
allows for its card borders, and the practice companion wraps its lesson
below when needed so the clip can reach 512x448 pixels on wider windows.
Narrow windows fit the image to the available space. The roster viewer's
guide toggle hides both the floor baseline and frame overlay. Native capture
bytes are unchanged.

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

All six native suites pass on this exact ROM: 2,596
gameplay, 18,084 roster, 3,337
presentation, 1,521 focused input, 8,163
stage and 1,805 Training checks, totaling **35,506**.
The new Training cases cover five-choice navigation on either pause controller,
held buttons/opposite directions/chord priorities, the native CPU label, all
three difficulties, arbitrary/mirror opponents, actual movement/attacks/damage
and recovery, low-wave guard, three pause pages, HUD health and quick reset.
A 360-frame replay proves P2 gameplay buttons do not take control. Intro and
round-state checks retain the untimed Training contract. The focused fifth-
choice test fails on v0.16.0 and passes on this candidate. Independent review
compares all 219 generated assets and 1,276 existing WRAM/direct-page addresses.

The pinned bsnes2014 Accuracy smoke, 48-by-600-frame independent combat run,
288-case native matrix, four deterministic replays and stage/policy/symmetry
checks pass. All three modes complete at least 216,356 live frames in one
uninterrupted native session each, with empty cadence, native-timing, ambient,
PPU-overflow and SPC-FIFO failure arrays. Training completes **216,356 live
CPU frames**, including controller-driven resets and roster transitions. The
gate requires a full CPU live hour and all twelve CPU opponent profiles in
addition to the existing coverage. Reset
health is checked at the actual reset callback, before the active opponent can
deal new damage. Existing Arcade champion/restart and Versus routes remain.

The first 04aa387c.../3C3C candidate passed short suites but failed the original
CPU live-hour cadence test, including overruns at native frames 52,560 and
54,000. The first batched-HUD fix, 1ac5d976.../4C8C, passed the original policy
but failed the expanded twelve-opponent hour at callbacks 137,337, 174,198 and
175,243. The current fix evaluates the shared recovery timer only when a
fighter is eligible, using a low-bit prefilter before the original unsigned
modulo. Direct fighter accesses, the HUD's unchanged-field fast path, locally
cached action/tick reads and skipping an empty throw-link call reduce repeated
work. Both eligible fighters restore health before one cached refresh. Health
recovery conditions, timing and full-health HUD/energy refresh remain. The current gates above
verify this ROM. Negative diagnostics under ignored build/v17-timing-negative
and build/v17-all-roster-timing-negative are source-checkout records, outside
the archive.

The isolated committed-source export reproduces the ROM, all 219 generated
assets and normalized symbols in 498.672 seconds, from
commit `5fcd5cb28f4cf2453cb3310fbab0d6947d7afd9a` and tree `5e3ef5c5f4be06fbd0bad8a37ef215a449f1c2a1`.
Three eleven-opponent controller ladders prove champion A/Start to title and
B to fighter select. Focused audio passes 1,792 capture-only
checks across four cues and five scores. The separate optional WAV archive is
identified by the [listening record](audio-listening-v0.17.0.json); no playback
or listening approval is implied.

[Menu evidence](menu-footer-report.json) passes 4,650 checks over 69 paired
native states, fifty controller routes and fourteen footer images. Baseline
Git blobs, current core/helpers, actual PNG/VRAM and footer glyphs are checked.
[Authoring evidence](authoring-guards-report.json) passes nineteen mutation
checks in each of normal and optimized Python, bound to frozen production
sources and committed producers. The [verification record](verification-v0.17.0.json)
collates current gates; package/audit independently bind its identity and totals.

The [CPU Training review](training-cpu-review.json) binds the native suite's
pause card and a 180-callback Cristobal-versus-Lars practice clip at Hard in
La Oficina. It retains 144 moving-opponent,
83 attacking and 130 damaged-player frames, the 99 clock and CPU choice.
The [anti-air review](cpu-anti-air-review.json) retains native hit/retreat-whiff
clips. The [practice proof](crossup-practice-v0.17.0.json) passes 72 cases over
all twelve fighters, both attacking controllers and all three arenas. Its
[capture record](crossup-practice-captures-v0.17.0.json) retains twelve unedited
native GIFs, embedded one at a time in the [practice companion](CROSSUP-PRACTICE-v0.17.0.html).
Use Stand Training for stationary setups and Local Versus for step-under examples.

Package checks bind fixed inventories, current ROM/core/helper hashes,
consecutive callback telemetry, decoded RGB pixels, GIF durations, landmarks
and embedded companion images. Normal and optimized mutations change actual
media/core/helper files in isolated copies and reject incomplete CPU live-hour
evidence. Execution remains trusted recorded evidence; these checks do not
authenticate emulator execution. GIF playback timing is approximate.

The Windows archive includes pinned Snes9x, player guides, exact QA/provenance,
champion/menu captures and practice/CPU media. Extract the whole ZIP and run
Play.cmd. REVIEW.html opens on the CPU Training card and clip, with results
and other menus under filters. ROSTER-REVIEW.html offers twelve generated
64-frame fighter strips and frame/facing inspection; its fixed-rate sweep is
an art inspection aid. Package checksum/audit are published separately in
dist/release-sha256.txt and docs/release-audit.json.

Human gameplay/balance, full listening, physical controllers, likeness/consent
and team/public-use approval remain open. Original SNES/flash-cartridge support
is unverified; public_release_certified remains false. Historical evidence
retains its own version and ROM identity.
