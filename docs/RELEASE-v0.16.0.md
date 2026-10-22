# v0.16.0 - Bounded CPU jump-in defense
<!-- candidate-version: 0.16.0; rom-sha256: feb73416224a7bbe6317f0c8a2b88abc403383c5017e151e1e6e2a8c3478cebd -->

Normal and Hard opponents can choose the universal Down+L uppercut against
visible nearby jump-ins. The decision requires a free grounded startup and a
live, unharmed target in front, within forty pixels and 12..56 pixels above
the floor. Normal samples ten-tick opportunities with a 16/32 threshold; Hard
samples every six ticks with 24/32. Ordinary startup and recovery remain, and
a retreat can make the commitment whiff. Decisions use no opponent input or
future collision data. Existing wave defense, active-attack guard and
family-specific specials keep priority. Easy retains its previous behavior.

The offline package adds an [all-roster cross-up practice companion](CROSSUP-PRACTICE-v0.16.0.html). Each
fighter keeps their existing movement and timing; some setups use an opponent
stepping under the jump. Current-ROM practice captures and the 72-case proof
cover both attacking controllers and all three arenas. Native CPU hit and
retreat-whiff clips show the new commitment and its counterplay.

- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- ROM SHA256: `feb73416224a7bbe6317f0c8a2b88abc403383c5017e151e1e6e2a8c3478cebd`.
- Header checksum: `FA49`.
- Cartridge source freeze: `c5b64914b35af11897210701a2394a540a20a6b6`.
- Source tree: `82c5128473b62ee0d9fd40394485f9b400242d5b`.

## Native preservation

All 219 generated art/audio/UI assets match verified v0.15.0. Hardware/trace
assembly, Fighter64/Wave16, TRACE0..122, WRAM storage, controls, actor/OBJ/UI
transfers, stage ambient and SPC budgets remain. The approved baseline is
`e9d4313af3fff74ca9857f8a6fb0d704464fac8f`; no asset changes or additions are
allowed. [Champion art](CHAMPION-ENDING.md) and [victory music](CHAMPION-AUDIO.md)
retain their original scopes.

## Verification and package status

All six native suites pass on this exact ROM: 2,596
gameplay, 18,084 roster, 3,337
presentation, 1,521 focused input, 8,163
stage and 1,446 Training checks, totaling **35,147**.
The new controller cases prove Normal/Hard decisions, four fighter families,
empty-jump interception, all five pre-contact startup ticks, retreat whiffs,
difficulty distinctions and grounded/far/behind/busy/hurt/hitstop/KO exclusions.
Seven positive cases fail on the parent ROM and pass on this candidate; eight
Easy replays retain their prior traces. Parent review also compares existing
WRAM/direct-page addresses and all 219 generated assets with the baseline.

The pinned bsnes2014 Accuracy smoke, 48-by-600-frame independent combat run,
288-case native matrix, four deterministic replays and stage/policy/symmetry
checks pass. All three modes complete at least 216,356 live frames in one
uninterrupted native session each, with empty cadence, native-timing, ambient,
PPU-overflow and SPC-FIFO failure arrays. The first Arcade endurance attempt
reached the live-hour target but missed champion/restart coverage. The harness
now completes an observed controller-only ladder before its mixed combat macro,
with explicit L release edges. The successful rerun retains the full live-hour
target and every original combat, stage, transition and timing requirement;
its initial ladder policy spans 67,139 tracked combat-policy ticks.
No cartridge bytes or difficulty setting were changed for this harness repair.

The isolated source export reproduces the ROM, all 219 generated assets and
normalized symbols in 348.547 seconds, from source commit
`c5b64914b35af11897210701a2394a540a20a6b6` and tree `82c5128473b62ee0d9fd40394485f9b400242d5b`.
Three eleven-opponent controller ladders prove champion A/Start to title and
B to fighter select. Focused audio passes 1,792 capture-only
checks across four cues and five scores. The optional WAV archive remains
separate, identified by the [listening record](audio-listening-v0.16.0.json).

[Menu evidence](menu-footer-report.json) passes 4,650 checks over 69 paired
native states, fifty controller routes and fourteen footer images. Baseline
Git blobs, current core/helpers, actual PNG/VRAM and footer glyph comparisons
are independently checked. [Authoring evidence](authoring-guards-report.json)
passes nineteen mutation checks in each of normal and optimized Python, bound
to frozen production sources and committed producer dependencies. The
[verification record](verification-v0.16.0.json) collates current technical
gates; package/audit independently bind its cartridge, freeze and native totals.

The [CPU review record](cpu-anti-air-review.json) retains native hit and retreat-
whiff clips. The [practice proof](crossup-practice-v0.16.0.json) passes 72 cases:
all twelve fighters, both attacking controllers and all three arenas. Its
[companion capture record](crossup-practice-captures-v0.16.0.json) retains twelve
unedited native GIFs. The [practice companion](CROSSUP-PRACTICE-v0.16.0.html)
embeds those clips, one active at a time, with fighter-specific instructions.
Some existing jump profiles need an opponent-step-under setup in Local Versus;
stationary examples can be practiced with the Stand dummy in Training.

Packaging checks fixed media inventories, current ROM/core/helper identity,
consecutive callback telemetry, decoded RGB pixels, retained GIF durations,
contact/startup/landing landmarks and exact embedded companion images. Bounded
normal/optimized mutations also change actual media, expanded core and helper
files in an isolated copy. Execution remains trusted recorded evidence; these
checks do not replay or authenticate emulator execution. GIF playback timing
is approximate. The original two-direction [cross-up record](crossup-review.json)
and current Controls cue are retained alongside the new clips.

The Windows archive includes pinned Snes9x, player guides, exact QA/provenance,
champion/menu captures, practice/CPU clips and offline review pages. Extract
the whole ZIP and run Play.cmd. REVIEW.html opens on the CPU hit/whiff examples;
ROSTER-REVIEW.html offers twelve generated 64-frame fighter strips, facing
and frame inspection. Its fixed-rate sweep is an art inspection aid. Package
checksum and audit are published separately in dist/release-sha256.txt and
docs/release-audit.json.

Human gameplay/balance, full listening, physical controllers, likeness/consent
and team/public-use approval remain open. Original SNES/flash-cartridge support
is unverified; public_release_certified remains false. Historical evidence
retains its own version and ROM identity.
