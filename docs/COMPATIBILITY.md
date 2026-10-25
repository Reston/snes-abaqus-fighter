# Independent-engine compatibility

## Current menu candidate: v0.27.1

<!-- candidate-version: 0.27.1; identity: FOCUSED_UI_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: c6682d3da92ae7ae41f80e62580163c169b4017cb81c83abcdbc611f8b1d7000; source-freeze: 2e6f947a43d148b44f8b7528769bfef1865ed85f -->

Both pinned cores pass the office-menu proof on this ROM: 74 states each,
including rendered backdrop pixels, with zero steady-menu cadence/SDK faults.
Presentation/Training and fresh reproduction also pass. The older full smoke
and six-suite records below retain their historical ROM identities.
[Current evidence](office-menu-review.json) · [Release note](RELEASE-v0.27.1.md).


## Historical native candidate: v0.27.0

<!-- candidate-version: 0.27.0; identity: TECHNICALLY_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: d5263c777cbb3a02ce438e07c1c425f2d39dd73d294cd4d2aa8c2cbc2da78e3d; source-freeze: 4d7e8fe17f1a0a534bc06e3e059fc4c03cd556d0 -->

The pinned Snes9x and bsnes Accuracy menu proofs pass, including all twelve
fighters, both selection steps, mirror badges and all three locations.
The current independent smoke passes on the same cartridge.
[Evidence and scope](classic-menu-review.json) · [Release note](RELEASE-v0.27.0.md).
The older sections below keep their historical cartridge identities.

## Historical native candidate: v0.26.0

<!-- candidate-version: 0.26.0; identity: TECHNICALLY_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: 27223b80377173d9535ccd1374b2470cc138a15324852c8b8833fd4f8fd00c7b; source-freeze: c89239901491a239e10194f1399820527b0ebf74 -->

Pinned Snes9x and bsnes Accuracy checks pass on the cartridge above.
[Verification](verification-v0.26.0.json) binds the actual expanded core pins,
controller-only proofs, live native cadence and source freeze. Fresh isolated
source/tool extraction reproduces all 226 outputs and the cartridge.
The [release guide](RELEASE-v0.26.0.md) states current scope. Hardware remains
unverified. All versioned sections below retain historical identities.


<!-- v025-compat:start -->
<!-- candidate-version: 0.25.0; identity: TECHNICALLY_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: f0223f8240e2338ec57674b465a93cc5b0145a6210b5d5933706bac7277168a2; source-freeze: b41ce034ac12f6aa10740a0075feebd1f392d117 -->

## Historical v0.25 native playtest candidate

The v0.25 cartridge is `f0223f8240e2338ec57674b465a93cc5b0145a6210b5d5933706bac7277168a2` / `FF9C`.
Pinned Snes9x and independent bsnes Accuracy checks pass; the fresh committed export reproduces the cartridge.
The stage oracle checks connected detailed-color scenery/ground, fixed
allocation, pause/guide freezes, hit shake and strict native transfer/cadence
bounds. [Current scope and verification](RELEASE-v0.25.0.md).
Original hardware remains unverified. The sections below are historical.
<!-- v025-compat:end -->






## Approved main walking revision: v0.23.1

The user rejected v0.23.0's torso/legs mismatch. PR #12 now replaces each
fighter's eight complete walking poses with coordinated head, guard, torso,
hip and foot motion, removing the fixed waist splice. Other 56 poses and
original portraits/palettes remain. All six suites pass 36,219 current-ROM
checks, matching independent smoke and fresh reproduction pass. The user
approved the revision and PR #12 merge on 2026-10-23 ("yes good, merge it").
Run `Play.cmd` from main to play v0.23.1.
[Current art, native clips, controls and evidence](RELEASE-v0.23.1.md). Main is
v0.23.1; 08 remains deferred. The notes below retain their historical scope.

## Rejected historical walking candidate: v0.23.0

Main is v0.22.1 with the nine approved improvements merged; feature 08 remains
deferred and its checkout is retained. The old merged branches/worktrees are
cleaned. [PR #12](https://github.com/Reston/snes-abaqus-fighter/pull/12) adds
eight-phase walking to all twelve fighters and the clearer **LOCAL 1V1 / 2P**
menu label. Local two-port multiplayer was already supported. Run `Play.cmd`
from `feature/walking-cycles-v023` to test this unmerged candidate.
All six native suites pass 36,219 current-ROM checks; independent smoke,
all-roster walking proof and fresh-source reproduction pass.
[Walking, two-player controls, art/prompts and evidence](RELEASE-v0.23.0.md).
The older notes below retain their historical scope.

## Current v0.22.1: nine approved improvements

Features 01–07, 09 and 10 are approved for main. **Feature 08 is deferred**:
the camera and ambient art are restored to v0.21.0; its branch/worktree remain
for polish. The six native suites pass 36,253 exact-ROM checks and matching
independent smoke passes. [Current release and scope](RELEASE-v0.22.1.md).
Local 1v1 already works in **Local Versus** with separate controller ports.
Walking improvements and clearer local-play discovery are the next follow-ups.
The v0.22.0 material below is historical, including its ten-feature review gallery.

## Historical v0.22.0 combined notes

The combined v0.22.0 candidate is on `integration/ten-improvements-v022`.
Main remains v0.21.0 until your combined playtest and
[PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1) merge. Run
`Play.cmd` from the integration checkout to try all ten changes. The pinned
bsnes2014 Accuracy smoke passes on ROM `d4fddaf609a0c29f45353a8d9e22fe1131fc3380838d9c0073d3255474cdf8af`,
header `EA9D`, matching all six current native suites.
The [verification record](expansion-v0.22.0-verification.json) binds its report
and the ten feature proofs to the same cartridge.
See the [combined release guide](RELEASE-v0.22.0.md).

The independent smoke must observe the new band scroll and composed impact
shake, updated ambient phases, shared effect priority and synchronized low-wave
fetches on that exact final cartridge. Intro, pause and hitstop retain their
ambient freeze rules. The ordinary ambient clock also freezes at round end,
but a real winner now receives a separate bounded ambient cheer and neutral
settle; draws do not. A blanket round-end pixel-freeze expectation would miss
that deliberate change. Stage comparisons must account for each band's offset.
Training's third guide page and supers do not expand a bounded smoke into a
full second-engine gameplay or Training matrix.

There is no v0.22.0 offline ZIP or regenerated full release-scale evidence.
v0.19.0 remains the latest full offline archive. Human play/controller/listening,
consent and public-use gates stay open; `public_release_certified` is false.
Original-console/flash-cartridge support remains unverified.

## Historical v0.21.0 smoke

The v0.21.0 candidate is cartridge SHA256 `aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205`.
The separate pinned bsnes2014 Accuracy smoke passed on that exact ROM.
Its release note records that historical result; the live
[compatibility-test-report.json](compatibility-test-report.json) must be read
with its own ROM identity as integration proceeds.
It includes all-stage effects/freeze checks and synchronized low waves with
the revised floor-contact shadows. The full independent combat report,
release-scale gates and offline archive still belong to the historical
v0.19.0 checkpoint. See the [v0.21.0 note](RELEASE-v0.21.0.md).

## Smoke contract and reproduction

The pinned smoke check has the bounded scope `independent-engine smoke, stage
ambient/effects freeze, synchronized low-wave, neutral600frame cadence`. It is
a separate Libretro host from the canonical Snes9x tests. The host loads the
current 4 MiB ROM through the official Windows x64 `bsnes2014_accuracy`
Libretro DLL, drives the title/select/arena/fight path with real SNES
controller callbacks, captures PPU and PCM callbacks, and reads the public
WRAM trace without writing emulated memory.

When `assets/generated/stage-dynamics.json` is present, the same independent
host also exercises all three stages. It waits for each of the four authored
ambient phases, hashes the declared patch rectangles from the actual PPU video
callback, and saves one review frame per stage/phase. Intro, pause and combat
hitstop require the ordinary ambient trace and PPU patch to remain frozen.
v0.22.0 round-end observations must distinguish the frozen ordinary clock from
the separate winner reaction and subsequent neutral settle, and comparisons
must use the active scroll-band offsets. A controls-only Negger/Fernando
fixture then synchronizes both low waves, requires the STAT77 OAM range/time
overflow bits (`0xC0`) to stay clear on every frame, and checks every observed
frame delta is one. The raw low revision/status values remain recorded in the
report because those bits are core/PPU-defined.
This remains a bounded pinned smoke check: it does not cover full combat
correctness, the roster suite, long endurance/soak behavior, human play, real
hardware, or public-release readiness.

The pinned source archive is the official [Libretro buildbot
artifact](https://buildbot.libretro.com/nightly/windows/x86_64/latest/bsnes2014_accuracy_libretro.dll.zip).
The expected archive SHA256 is
`CB1211AE6B6838ED60BEB7CC8AE5AD8074327733F1042CCC8BABA32A62C6D18C`; the
extracted `bsnes2014_accuracy_libretro.dll` SHA256 is
`F2AAC1DDB314A001467A26B56604020F0A29C3A4DD1658B072884ACE75343CF4`.
The loaded core identifies itself as `bsnes2014`, version
`v094 (Accuracy) 3c1394e`. The archive URL is rolling; the setup helper and
test fail before DLL loading when either pinned hash changes.

Prepare the ignored local cache and run the check with:

```powershell
powershell -ExecutionPolicy Bypass -File tools/setup-compat.ps1
& .\.tools\python\python.exe tools/test_compatibility.py *> .tools/compat/compatibility-test.log
```

The tracked result is [compatibility-test-report.json](compatibility-test-report.json).
The title/select/arena/fight callback captures and stage ambient review frames
are under `docs/screenshots/compatibility/`. The report records the exact ROM
hash, core identity and hashes, PPU signatures and patch digests, controller
movement/jump evidence, freeze observations, PCM sample/energy/peak checks,
and the per-frame cadence results. The host records the callback's reported
pixel format, dimensions and pitch. The pinned Accuracy DLL reports the
0RGB1555 enum while emitting a four-byte BGRX callback, so the host selects
the decoder from the stride before checking the title/fight images. Each
stage also compares an unobscured native `y=40..100` plate band against its
generated stage master at <=8 RGB levels per channel (with a <=16 guard),
excluding the eight authored ambient cells.

The v0.6.1 smoke host used the reported 16-bit format and produced striped,
incorrectly colored review images. Its WRAM, controller, PCM and cadence
observations remain separate evidence; those older images must not be used
as proof of visual accuracy. The v0.7 host corrects the decoding, replaces
the captures and requires the static plate color agreement above.

The generated stage manifest and the core are test prerequisites. The core is
fetched into `.tools/compat`; it is not bundled in the offline ZIP.

## Bounded independent combat

`tools/test_compatibility_combat.py` complements the smoke test with 48 cases
of 600 combat frames each (28,800 frames total): every fighter as P1 and P2,
neighbor pairs and their mirrors, all three stages, and two deterministic
controller policies. The host checks actual selected IDs/stage, unit video
and TRACE cadence, state bounds, nonblank video and captured PCM. It records
realized attacks, damage, throws, air actions, down and wake events.

Its exact-ROM evidence is
[compatibility-combat-test-report.json](compatibility-combat-test-report.json).
Run it silently with the pinned interpreter:

```powershell
& .\.tools\python\python.exe tools/test_compatibility_combat.py
```

This is bounded second-engine combat evidence. The full 144-pair/two-policy
matrix belongs to the native Snes9x suite; the uninterrupted hour per mode
also runs on that native test core. These scopes do not establish an
independent full ordered-pair sweep, independent per-mode hour, human balance,
listening quality, controller hardware or physical-console compatibility.
The [public-release gates](PUBLIC-RELEASE.md) remain the readiness criteria.

The v0.8 pause move guides, dummy choices, opposite-direction navigation and
contact-to-pause HUD regression have a separate native Snes9x suite,
`tools/test_training.py`. The two bsnes reports above retain their recorded
smoke/combat scope; they do not claim a full second-engine guide or Training
matrix.

The primary source and license references for this specific core are the
[libretro/bsnes2014 source repository](https://github.com/libretro/bsnes2014/tree/libretro),
the [libretro-super bsnes2014 build recipe](https://github.com/libretro/libretro-super/blob/master/recipes/android/cores-android),
the repository's [COPYING file](https://github.com/libretro/bsnes2014/blob/libretro/COPYING),
and the [Libretro bsnes 2014 Accuracy core documentation](https://docs.libretro.com/library/bsnes2014_accuracy/).
The core is GPLv3; these references document the third-party test prerequisite
and do not change the project's existing license notices.
