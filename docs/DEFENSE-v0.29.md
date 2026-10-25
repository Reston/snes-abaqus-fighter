# Defensive options for the v0.29 integration

Topic 1 only, based on integration commit `29fee83`. The authoritative
deliverable remains the native 4 MiB NTSC FastROM LoROM cartridge. The parent
owns the combined six-feature ROM, full suites, reproduction and final merge.

## Timing and player behavior

The baseline was built and measured before implementation, with real
controller streams on expanded Snes9x for all twelve fighters and both roles,
plus both roles on pinned bsnes2014 Accuracy. Its integration-reservation ROM
is `46108c5e955733820f92c8baab4088a0f054e2b4986fb5d8093c1352e1023738`;
this includes the parent's v0.29 identity and six appended initialized feature
reservations. The baseline measurement is retained under
ignored `build/defense29/baseline-measurement.json` and summarized, with hashes,
in the focused report.

Measured baseline throw startup is four live ticks. A grab starts a
three-video-tick contact pause, then six live lift ticks before launch.
Damage remains deferred until landing. Depending on gravity, landing occurs
43 or 53 callbacks after grab; complete recovery occurs at callback 87 or 97.
The floor, rise and wake-input phases last 18, 10 and 6 live ticks. Recovery
retains four invulnerability units: the recovery contact tick and the next
four ticks are protected against all attacks. No existing timing is changed.

A fresh **Toward + X** during live lift ticks **1 through 5** now escapes.
Toward means toward the actual grabbing opponent, including after crossing;
the victim's lift drawing deliberately faces away and is not used to decode
this command. Down+X keeps its uppercut meaning. Opposite directions retain
the existing input cleaning. A held X, a direction change while holding X,
an edge during the contact pause, and a sixth-tick or airborne edge do not
escape. The contact pause and a normal pause never spend live lift ticks.
An edge entirely inside hitstop is not queued. Start owns its resume sample;
release and press X again during an eligible live tick.

Successful late tech cancels both ownership links and the pending landing
damage, puts both fighters on the floor, restores facing and gives both the
existing six-live-tick guard recovery and three-video-tick tech pause. They
separate to exactly 40 pixels, preserving their left/right order. At a wall,
the fighter with available space takes the remaining displacement. The
existing deferred, opaque **THROW TECH!** banner and guard spark are reused.
The original simultaneous-throw tech function and its original spacing,
recovery and cue remain unchanged.

Knockdown recovery starts **ten throw-protected contact ticks**, numbered
0 through 9 with recovery as tick 0. Existing general invulnerability still
covers ticks 0 through 4. On ticks **5 through 9**, ordinary strikes can hit
or be guarded, while throws cannot connect. At tick 10, throws work normally.
No strike invulnerability, movement change, roll, parry or new button is
added. Existing released wake attack/jump buffers and held guard still work.
The controls guide describes both defenses within its existing three-phase
construction and 1,472-byte queued publication.

Easy CPUs do not attempt late tech. Normal and Hard make one decision after
two visible live lift ticks, accepting respectively one or two of four
existing frame phases. A successful decision emits ordinary Toward+X through
the same capture and resolution path. There is no retry, opponent pad read,
future-state access, guaranteed escape or PRNG call. All CPU decisions outside
a linked lift retain the prior code path.

## Ownership and integration hooks

`src/defense29.h` owns the implementation. Only bytes 0 and 1 of
`v29DefenseState[16]` are mutable timers; the remaining fourteen bytes stay
zero. No new mutable definition is introduced. Reset clears exactly those
sixteen reserved bytes. Prior variables, initialized data and SDK addresses,
Fighter64, Wave16, TRACE and hardware/trace assembly remain pinned.

Small hooks are deliberately explicit:

- `game.c`: two forward declarations; reset call; one direct wake-transition
  timer assignment in the existing fighter-update template; two direct timer
  decrements at live combat entry; rare linked-lift tech calls after the
  original downed updates; one throw-only gate in `canHit`.
- `cpu_personality.h`: a linked-lift branch before its existing downed return.
- `pause_guide.h`: updated tech help and one recovery help row. The existing
  page numbers, footer and three-phase schedule are retained.
- Late tech calls `soundImpact(SOUND_GUARD)`. Feature 5 must preserve that
  semantic hook. The existing resident scheduler still sends at most one
  queued command per video tick; no dedicated sample is required here.

No asset generator hook or changed-output allowlist is needed: all 226
generated files are expected to stay byte-identical. There is no new raster
art, palette, pose, OBJ, audio payload, DMA, HDMA or background animation.
Actor uploads retain one 3,840-byte pose per vblank, with interface publication
yielding to the actor as before. The unsafe old BG1 map destination `$3C00`
is not used by this feature.

The native symbol audit includes all 1,329 prior direct-page/WRAM variable,
data, SDK and allocation labels from the integration reservation build, with
no relocation or added label. Defense uses `$7F:0598..0599`; its other fourteen
reserved bytes remain zero. The three helpers occupy 2,088 ROM bytes in total;
their compiler stack locals are 1, 4 and 24 bytes for reset, CPU input and late
tech respectively. Every linked ROM section fits one 32 KiB LoROM bank; the
largest section remains a 30,720-byte fighter asset bank. No resident audio
payload or Bank24 asset change is needed.

## Reproducing the focused proof

Run from this worktree with inherited CPU affinity mask 12 and below-normal
priority. Resolve the local Python executable to an absolute Windows path
when passing it as a child executable to the background wrapper:

```powershell
[System.Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity = 12
$defensePython = (Resolve-Path .tools/python/python.exe).Path
& $defensePython tools/run_background.py --log build/defense29-build.log -- $defensePython tools/build.py
& $defensePython tools/run_background.py --log build/defense29-proof-final.log -- $defensePython tools/test_defense29.py
```

The initial pre-change measurement used the same wrapper with
`tools/test_defense29.py --measure`. `--fighter N` writes an ignored diagnostic
instead of the committed focused report. No host creates an emulator window,
opens an audio device, modifies emulated WRAM or creates/loads save states.
The proof reads native pads, Fighter/Wave bytes, the public trace, VRAM, SDK
counters, OBJ overflow flags and resident SPC FIFO indices. Both frame and
vblank must advance exactly once with zero SDK lag, and only one actor page
may change per callback. Accuracy can sample a pad across a frontend callback
boundary; its selected cases hold across that boundary and retain both the
requested stream and observed native input. Expanded Snes9x proves the exact
first/last accepted and first rejected live-tick boundaries.

Final results and exact source, harness, core, cartridge, capture and retained
stream hashes are in `defense29-report.json`. The tested cartridge and symbols
are retained under ignored `build/defense29/candidate/`; generated/dist outputs
are restored before committing this feature PR. The child proof is focused
evidence, not combined verification, hardware/controller acceptance or a new
offline package.

The full fighter/role proof uses real strict-range walking rather than a
one-pixel target band: Cristobal's movement can skip such a band near the
22-pixel body-separation floor. Wake-pressure fixtures continue the approach
through the wake phase so slower fighters, including Ivo, actually reach
throw range before the test. Held standing guard is exercised against a
connecting jab; a crouching authored hurtbox can legitimately fall below a
jab at longer spacing. These fixtures keep the exact range, damage, native
cadence, general-invulnerability and throw-only-window assertions.

The isolated preservation gate intentionally pins all unowned native source
and all 226 generated outputs to `29fee83`. To reuse the focused tool after
combining the six features, the parent must supply the retained baseline
artifacts, adapt that source/asset allowlist to the combined contract, and
account for the other features' menu routes. The live cadence, damage and
defense-window assertions must remain strict. This tool does not replace the
parent's six native suites or combined transfer/stress proof.

The ordinary-play byte comparison begins after the native menu/intro boot
helper has reached fully initialized live combat. Both complete boot streams
remain retained and hashed separately. The first full run found Reston's
candidate loader one frontend callback later than its parent while forced
blank was active: one stream had already initialized FIGHT/intro, while the
other still exposed ARENA and the core's old `$55` fill bytes. This is not
live simulation state. No live callback, game-frame value, Fighter/Wave/RNG
byte or native input is masked, shifted or omitted from the subsequent
ordinary-play comparison. That failed attempt remains under ignored
`build/defense29/failed-loader-preservation-report.json` with its original log.

## Final isolated result

Both commands above exited **0**. The final native proof took 598.047 seconds
and passed **1,353,426 focused assertion executions**. Earlier diagnostic and
failed-run counts are not included. This is the topic-1 cartridge, not the
later combined six-feature verification.

- Source/test freeze: `26c5c4d5f9df6bb8a34c4e35a54421912f5d3448`.
- Source-inventory SHA256: `09a97fa8801cda33ccec3bc82efc24a2bdcd9ed2a022b1c3c34a2d195f7d9a9b`.
- Harness SHA256: `6fdacc1962cae1c30c1fba02ddca80eec21e07be8e72f2acf35f8c7a478c087e`.
- ROM SHA256: `26ed8e783629e3cf413d4daa509f273122db9805bb21c7805c539347923d1f1d`;
  native checksum `E20B`, 4 MiB NTSC FastROM LoROM, parent identity v0.29.0.
- Focused report SHA256: `088496852b631fcc322f1d402581564f84e821d1342cc9fa45f90c3b76fc009f`.

The report contains 32 complete defensive sessions (all twelve/both roles on
Snes9x; Damian, Ivo, Mamariaga and Lars/both roles on Accuracy), 16 fallible CPU
cases, 32 both-role KO cases with the same roster coverage, 24 complete
unmasked ordinary-live-play comparison pairs and 24 exact throw/down/recovery
comparison pairs. The final harness also reproduces the pre-implementation
throw measurements from the retained baseline ROM. Every report input and all
44 pinned Python/core/compiler/SDK dependency files remain byte-stable during
the proof.

Strict health covers **209,423 Snes9x + 54,420 Accuracy fight callbacks**:
frame/vblank delta one, zero SDK lag, no OBJ overflow, at most one changed
actor VRAM page and advancing silent PCM. The observed resident FIFO peak is
zero pending bytes at the sampling point, within the existing six-byte bound.
Host priority is below normal (`16384`), affinity is logical CPUs `[2,3]`, and
no GUI or audio device was opened. Ten native PPU captures are hash-bound in
the report. No shared suite/report, generated asset or tracked dist file is
part of this feature change; the exact tested ROM/symbol/manifest/report copies
remain under `build/defense29/candidate/`.
