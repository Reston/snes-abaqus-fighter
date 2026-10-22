# Cross-up practice companion

The [offline companion](CROSSUP-PRACTICE-v0.17.0.html) shows one native moving
example for every fighter. Choose a fighter to see their setup and the included
keyboard controls. The clips use the v0.17.0 cartridge, SHA256
`cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe`.
The companion and its native clips are included in the v0.17.0 Windows package.

Medium kick is **SNES A**, **P1 keyboard X**, or **P2 numpad 2**. Start with
Damian and a stationary opponent. Jump forward and start the kick as you pass
the opponent's center. The rear reach is short; changing your starting distance
or beginning the kick a little earlier can turn a whiff into a hit.

The fighters retain different jump heights, speeds and startup times. Ivo,
Cote, Negger, Fernando and Reston use a step-under example: the defender walks
toward the jumper until their centers cross, while the kick starts slightly
before the crossing. Cote and Fernando start a little farther apart; Negger
starts farther apart again. These examples demonstrate opportunities created
by opponent movement, rather than one timing that works for every fighter.

Try the stationary setup with the Stand dummy in Training. Use Local Versus
with a second player or both keyboard layouts to reproduce the step-under
examples. After a crossing, the defender switches their away direction to
block high. Crouch guard loses to a jump-in. Human feedback is still needed on
readability, timing, fairness and overall fighting feel.

## Native evidence

[Practice proof](crossup-practice-v0.17.0.json) passes 72 controller cases:
twelve fighters, both attacking ports and all three arenas. Each case checks
an actual rear airborne medium-kick hit, locked takeoff facing, five frozen
hitstop ticks, away-directed hurt/body push, native telemetry cadence, landing
and restored positional facing. This supplements the six native suites; the
[release note](RELEASE-v0.17.0.md) records their separate verification scope.

[Capture metadata](crossup-practice-captures-v0.17.0.json) identifies the twelve
native GIFs, source callback-frame hashes, trace landmarks, producer helpers,
pinned core and silent background host contract. Frames are unedited 256x224
callback pixels. The GIF encoder verifies exact decoded RGB pixels; playback
timing uses an approximate 20/20/10ms inspection cycle. The companion keeps one
clip active at a time. Clips show P1 setups; the practice proof also checks the
mirrored P2 routes and every arena. Execution is trusted recorded evidence;
human gameplay/balance approval remains open.

The same first rear-hit case fails on the historical v0.14.0 ROM, SHA256
`3de317b43f72bea76cfc2f1a1ebd5c67dd57913b8d9fddfb50a7a846a02ddeaa`,
with no contact. The negative fixture was run under optimized Python. It
confirms that the proof exercises the rear-hit behavior added in v0.15.0.

## Reproduce in a source checkout

Use the hidden, BELOW_NORMAL, two-CPU Windows runner, with stdin DEVNULL and
no GUI/audio playback. Its retained source is `tools/run_background.py`.
Prepare the ignored runner path recorded by the capture host:

```powershell
New-Item build -ItemType Directory -Force | Out-Null
Copy-Item tools/run_background.py build/run_background.py
```

Run the current-ROM proof before capturing:

```text
.tools\python\python.exe build\run_background.py --log build\crossup-practice.log -- cmd /d /c ".tools\python\python.exe tools\test_crossup_practice.py --report docs\crossup-practice-v0.17.0.json"
.tools\python\python.exe build\run_background.py --log build\crossup-captures.log -- cmd /d /c ".tools\python\python.exe tools\make_crossup_practice_review.py"
```

The probe's `--fighter`, `--port` and `--stage` options allow a bounded case.
Its `--rom` option loads a separate cartridge without replacing the current
deliverable. An expected negative fixture can be run with:

```text
.tools\python\python.exe build\run_background.py --log build\crossup-negative.log -- cmd /d /c ".tools\python\python.exe -O tools\test_crossup_practice.py --rom build\v14-baseline.sfc --fighter 0 --port 0 --stage 0 --report build\v14-crossup-practice-negative.json"
```

That fixture path is a local, source-only copy of the identified historical
ROM. Expected exit status is 1 at the crossing/contact assertion. No probe
writes emulated memory, loads save states, changes fighter profiles or alters
the current cartridge. Package validation checks the fixed clip inventory,
callback pixels, retained durations, helper hashes and embedded HTML media;
recorded emulator execution remains trusted evidence.
