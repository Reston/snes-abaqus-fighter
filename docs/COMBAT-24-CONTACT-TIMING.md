# v0.24 native close-contact timing

This is bounded implementation evidence for the combined six-feature source,
based on `14f4fd6`. It does not replace the parent's frozen-ROM gates or the
unmerged combined human playtest. The implementation commit is `58e9018`.

The candidate cartridge is SHA256
`28d770aca1cc489c70d7370329e785cb223c0703d807f07d627d461ba8dbdb85`,
header checksum `5872`. Retained runtime artifacts are under the assigned
checkout's ignored `build/contact-timing/` directory. Tracked `dist/` and
generated files are restored to the assigned base after retaining that copy.

## Reproduction

The original `a15a496f04dc005fba5a9d424cf3c8005922c758a0712476a68eb68e254ec47e`
cartridge (`E0BB`) reproduces the parent's David mirror case exactly:

- Cold boot Local Versus, David 5 versus David 5, stage 2.
- Three neutral callbacks, P1 Right for 94 callbacks, two neutral callbacks.
- At native frame 536 the positions are 2560 and 3040 in 12.4 units.
- Both players press Y for one callback, then remain neutral.
- Callback 102 applies symmetric 10-damage contact: HP 118, connection 2,
  hurt 15, hitstop 4, recoil latch 33.
- Callback 103 repeats direct native frame 539. The SDK lag counter changes
  71 to 72, vblank count 614 to 615, and vblank flag becomes 1. Native screen
  remains FIGHT; pause, intro and round end remain zero.

`before-repro.json` retains every controller run, whole Fighter/Wave bytes and
direct counter samples. The pinned Accuracy core independently reproduces
the same callback failure in `before-accuracy.json`. Failures stay failures;
baseline `--observe` changes only the process exit code so evidence can finish.

## Change

Paired 16-bit loads read the unchanged little-endian contact rectangle bytes.
Local action/tick and connected/hurt words avoid repeated field loads. Small
unsigned local values avoid unnecessary signed comparison machinery. The
original signed 12.4 transforms, mirrors and strict half-open comparisons remain.
The geometry generator, table layout, digest and physical table bytes remain exact.

Those changes alone are insufficient. The existing `hurtWithRecoil` C function
now specializes its two ordinary player pairs to direct WRAM field operands,
using one macro template with the original operation order. Its original generic
path remains for other caller pairs. Immediate recoil uses the already resolved
victim address; its macro keeps the action adjustment for linking supers private
to recoil. All impulses, latches, easing, presentation and super rules are retained.

This removes repeated far-pointer construction and helper argument setup. It adds
no global state, native assembly source, assembly section or hardware transfer.
The existing hit-resolution section grows to 7,744 bytes at `$81:DE60..FCA0`,
within one LoROM bank. The former `beginRecoil` function is expanded inside the
existing contact section. Restoring that helper call reintroduces the measured
Cristian/Reston strong-kick stalls, so the bounded recoil change is required.
Compiler stack locals for hit resolution increase from 24 to 68 bytes; the
former separate recoil call had 12 local bytes. These are transient stack
locals, with no appended global RAM or moved prior state.

Rejected experiments are retained only under ignored `build/`: paired reads
alone, repeated canvas conversion, fused relative coordinates, helper inlining
and wider table-index shifts. None is claimed as a passing candidate. The final
implementation retains the original coordinate arithmetic and hit-resolution
operation order.

## Verification and reproduction commands

The timing matrix passes 648/648 sessions and 104,166 callbacks, with zero
direct-counter, trace-cadence or SDK lag failures. The baseline has 90 failed
sessions and 90 SDK lag increments. Removing those 90 duplicated old callbacks
only for behavioral comparison gives 104,076 matching logical ticks, including
every Fighter/Wave byte. All 16 pinned Accuracy sessions pass 2,674 callbacks.

The unchanged contact fixtures cover 108 distinct sessions and 61,472 measured
callbacks. Every native timing/OBJ/actor/SPC budget passes. Gameplay assertions
pass in 106 fixtures; the two Fernando rear air-A failures are retained below.
These figures describe this exact cartridge and do not certify the parent's
six shared suites, fresh-source export or combined human review.

Use the assigned checkout's absolute `.tools/python/python.exe`. Every launch
sets affinity only on its own PowerShell process; the canonical launcher inherits
processors 10/11 and keeps the child below normal priority:

```powershell
$taskProc = Get-Process -Id $PID
$taskProc.ProcessorAffinity = 3072
$taskPython = Join-Path (Get-Location) '.tools/python/python.exe'
& $taskPython tools/run_background.py --log build/contact-timing/candidate-full-matrix.log -- $taskPython tools/test_contact_24_timing.py --report build/contact-timing/candidate-full-matrix.json --matrix --stages 0 1 2
```

The complete matrix has 648 cold boots: all twelve mirrors, simultaneous Y/X/A
normals, both approach ports, all three stages, and three consecutive contact
phase offsets on each stage. Each session measures every callback, including
startup, contact, hitstop and recovery. Native frame and trace frame must both
advance by exactly one; vblank must advance by one and lag by zero. There is
no frame allowance or assertion suppression.

For the retained baseline, add `--rom build/contact-timing/before/abaqus-after-hours.sfc`
and `--symbols build/contact-timing/before/abaqus-after-hours.sym`, use a separate
report, and add `--observe`. For behavioral comparison and static contracts:

```powershell
& $taskPython tools/run_background.py --log build/contact-timing/comparison.log -- $taskPython tools/test_contact_24_timing.py --summarize build/contact-timing/baseline-full-matrix.json build/contact-timing/candidate-full-matrix.json --report build/contact-timing/comparison.json
```

Only the explicit behavior comparison collapses repeated old logical frames,
using the last sample for a duplicated frame because the earlier callback can
observe a partially completed contact. The failed baseline timing samples remain
in their raw report. Both controller streams remain neutral after the contact
press. Every shared logical tick compares all 128 Fighter bytes, all 32 Wave
bytes, recoil, clock, round, hitstop and combo state. Candidate-only tail ticks
are counted explicitly; they are the progress gained by removing old stalls.

The report also checks all 1,318 prior RAM labels, no added RAM labels,
Fighter64/Wave16/TRACE0..122, cartridge mapping/size/region, table/digest bytes
and bank containment. It compares all 226 tracked generated files and both
native assembly files with `14f4fd6`. Packed-edge checks are host arithmetic
checks, counted separately from native callbacks.

The unchanged parent contact driver is copied to ignored build storage and run
against this checkout through `run-root-driver.py`, with its report redirected
to build. It covers ordinary boundaries, guard, air/rear cross-ups, trades,
throws, ordinary specials and supers for every fighter and both ports. The
authoritative parent suites, independent smoke, media and fresh-source export
remain the parent's responsibility after cherry-picking this implementation.

The full driver stops at the existing Fernando `06/P1/crossups` assertion
`Air A connects behind locked facing`. The retained baseline reproduces the
same failure at frame 600, positions 3691/3238, with no damage or native timing
failure. All 163 measured callbacks, controller runs and trajectory digest
`7f8300c4cf968019cb3b129a51797662a6fe3861e3021ad8d7e3aec79cb92efa`
are identical before and after. This is an open combined contact-proof gate,
not a passing full feature proof. Remaining fixtures are run separately and
their failures remain explicit in the report; no contact reach or fixture
assertion is changed in this timing fix.
The P2 version also fails identically on both cartridges, with shared digest
`977edcc532a001698b6a6a1aff0f3b504dca28002ae54886969a325d24d17679`.

Machine-readable results and exact artifact hashes are in
`combat-24-contact-timing-report.json`; the complete retained artifact inventory
is in `build/v024-close-contact-timing-handoff.json`.

After tracked dist files are restored, replay the retained candidate with
`--rom build/contact-timing/candidate/abaqus-after-hours.sfc --symbols build/contact-timing/candidate/abaqus-after-hours.sym`,
or rebuild the committed source first. The default dist ROM then remains the
assigned baseline until the next build.
