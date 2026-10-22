# Independent-engine compatibility
<!-- candidate-version: 0.11.0; rom-sha256: 1574bb4147605b3a0dd8d463b6403360a386c62334e1d5e29ea5654bd376baa7 -->

The current candidate is v0.11.0, cartridge SHA256
`1574bb4147605b3a0dd8d463b6403360a386c62334e1d5e29ea5654bd376baa7`.
The authoritative evidence is the exact-ROM smoke and bounded-combat JSON
linked below. Both the pinned smoke and the 48-by-600-frame bounded combat
run pass against this cartridge. The release note
[RELEASE-v0.11.0.md](RELEASE-v0.11.0.md) records the final checkpoint status.

The historical v0.9.0 smoke and bounded combat reports passed on
`bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639`.
The current candidate changes Lars's art, location previews and result
presentation; independent-engine coverage retains the scope below.

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
callback, and saves one review frame per stage/phase. The intro, pause, combat
hitstop, and round-end checks require the ambient trace and actual PPU patch to
remain frozen in their respective state. A controls-only Negger/Fernando
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
