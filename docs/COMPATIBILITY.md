# Independent-engine compatibility

The pinned smoke check has the bounded scope `independent-engine smoke, neutral600frame cadence`.
It is a separate Libretro host from the canonical Snes9x tests. The host loads
the frozen 4 MiB candidate ROM through the official Windows x64
`bsnes2014_accuracy` Libretro DLL, drives the title/select/arena/fight path
with SNES controller callbacks, captures PPU and PCM callbacks, reads the
public WRAM trace, and checks 600 consecutive neutral runs for a one-frame
trace increment.

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
The four callback captures are under
`docs/screenshots/compatibility/`. The report records the exact ROM hash,
core identity and hashes, PPU signatures, controller movement/jump evidence,
PCM sample/energy/peak checks, and the per-frame cadence result.

This smoke test does not cover full combat correctness, the roster suite,
long endurance/soak behavior, human play, real hardware, or public-release
readiness. The core is a test prerequisite fetched into `.tools/compat`; it is
not bundled in the public ZIP.

The primary source and license references for this specific core are the
[libretro/bsnes2014 source repository](https://github.com/libretro/bsnes2014/tree/libretro),
the [libretro-super bsnes2014 build recipe](https://github.com/libretro/libretro-super/blob/master/recipes/android/cores-android),
the repository's [COPYING file](https://github.com/libretro/bsnes2014/blob/libretro/COPYING),
and the [Libretro bsnes 2014 Accuracy core documentation](https://docs.libretro.com/library/bsnes2014_accuracy/).
The core is GPLv3; these references document the third-party test prerequisite
and do not change the project's existing license notices.
