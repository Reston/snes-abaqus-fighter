# Native simultaneous-special and CPU contact timing

This is isolated performance evidence for the v0.24 integration, not final
combined release certification. PR #14 remains unmerged for human playtest.

The retained baseline is parent `22495b9a945a5c7903bc7e9972e2d0f2d2a34c5a`,
ROM `28d770aca1cc489c70d7370329e785cb223c0703d807f07d627d461ba8dbdb85`,
checksum `5872`. A local canonical rebuild reproduces those exact ROM bytes.

Two real failures were reproduced without writing emulated memory:

- Cristobal mirror ordinary specials, after 120 retreat callbacks and the
  seven complete attack sequences: native/trace frame 1039 repeats at special
  tick 9, SDK lag increases by one, both HP remain 128, hitstop remains zero.
- Fernando Hard CPU, `cpu.boot(6,2)` and the unchanged `cpu.p1_script`, 1,800
  physical callbacks: callback 54 repeats frame 480, lag 66 to 67, VBlank 550
  to 551, HP 107/128 and hitstop 6. Two baseline replays reproduce the parent's
  complete diagnostic trace hash
  `12f3ce84296bd2f7a39da889670d87cb2ea9a7e4fd05de2d1655e4efcd186b41`.

`canHit` now rejects ordinary pose strikes when their 96-pixel canvases cannot
overlap. The independent profile-based throw returns before this gate. Both
half-open geometry rectangles are bounded by their canvases, so separation
of at least 96 pixels cannot produce contact. The existing direct-super gate,
geometry bytes, contact order, atomic trade snapshots and recoil fixes remain.

`animateFighter` uses one C selector template expanded for each of the two
ordinary actors. Its expressions and writes retain their original order;
816-tcc emits direct WRAM operands instead of repeatedly reconstructing a far
fighter pointer. The emitted function has 4 indirect accesses instead of 118,
and 29 bytes of compiler stack locals instead of 128. Its section grows from
6,985 to 9,200 bytes, within one 32 KiB bank. The canvas-only counterfactual
still reproduces Fernando's exact failure; the combined optimization removes
it. No CPU policy module or native assembly is changed.

The broader 432-case matrix rejected that first combined candidate,
`8dd3d1e54e20da60888f4925a0838a7bef58c8685cb8daf0a0f3c0cfdbebbb39` /
`333C`: fourteen current-candidate cases failed. Six Cote phase-zero close
super cases and eight David close-contact cases retain their original failed
outcomes and raw streams. Fresh exact Cote and David reproductions fail on
both Snes9x and pinned Accuracy. Passing subsets on that ROM are historical.
The recovery script's mechanical "Historical baseline" label on those failed
candidate details was incorrect; their failures were never baseline failures.

The next C-only refinement uses direct actor operands in `updateFighter`,
`canHit` and contact pose queries. The update template reduces indirect
accesses from 106 to 30 and stack locals from 36 to 14 bytes; it alone still
fails the two primary repros. Direct `canHit` operands reduce indirect
accesses from 27 to 8 and clear Cote's close super, while David's phase-two
close jab still fails. Localizing contact actor reads then clears both on
both cores, plus David's stage-one phase-zero close case. The exact candidate
is `408cadfdddef97a24215e40f6ddb366140bc68fc80e7f1de82ee87e4084beb79`,
checksum `4857`. ContactActionFrame/Body/Strike/WorldHit indirect accesses
change from 10/7/6/7 to 4/0/4/4. The paired ROM reads, rectangle arithmetic,
selection conditions, helper calls and write order remain unchanged.

The final isolated proof passes all 432 fresh Snes9x cases and 692,612 native
callbacks. The complete unmasked comparison passes those same 692,612 logical
ticks, collapsing only 118 historical baseline callbacks and zero candidate
callbacks. Fresh CPU proof passes 36 Snes9x cases / 64,799 replay ticks with
whole Fighter/Wave/RNG/CPU/pad equality, and twelve Hard CPUs / 21,600 pinned
Accuracy callbacks with strict cadence. Exact Cote/David contact replays pass
both cores; the original Cristobal Accuracy and Fernando Snes9x replays also
pass. All 1,318 RAM addresses, 226 generated assets and exact geometry bytes
are preserved. These isolated results do not replace parent's combined gates.

The focused drivers retain every physical callback, controller input, whole
128-byte Fighter pair, whole 32-byte Wave pair, public trace and native SDK
counters. CPU streams additionally retain RNG, CPU state, private super state
and sampled pad/edge words. Baseline failures remain explicit. Only the
behavioral comparison collapses repeated baseline logical frames; candidate
cadence, VBlank, lag, OBJ, actor DMA and SPC/PCM checks remain strict.

The native producer remains byte-exact at commit `f3273d6`. A separate
`compare_special_24_state.py` enforces the explicitly approved first-publication
rule: retain the deterministic first callback for each baseline trace frame,
require Trace==Native there, and compare every unmasked byte and the complete
ordered logical frame/input/segment sequence. The 432-case baseline control
has 118 repeated callbacks, zero incoherent first publications and twelve
later straddle groups. Those later callbacks repeat the preceding trace while
native frame and live structs have already advanced. They remain diagnostic
failures. Ordinary coherent duplicates must have identical whole state/input.
No candidate callback is collapsed; every candidate sample must have matching
Trace/Native frames, consecutive frame/VBlank counters, zero SDK lag and all
original native case checks passing. The unchanged last-duplicate comparator's
failed reports remain retained. Eleven negative/control checks cover padding,
reserved bytes, missing/repeated candidate frames, counters, input edges,
incoherent baseline first samples and changed coherent duplicates.

The special matrix uses all twelve fighters, three stages, both approach
ports, offsets 0/1/2 and wide/close spacing. Each case starts with the exact
120-callback separation and seven complete move sequences. Short normal
trades remain simultaneous; ordinary specials and supers also exercise
staggered starts, with each pad holding its command for three logical ticks.
An earlier probe setup incorrectly required an interrupted staggered jab to
remain visible after the contact callback; its failed report and driver are
retained, and no production or existing-driver assertion was changed.

Accuracy cold-boots random WRAM, including untouched struct padding. Its
[system power implementation](https://github.com/libretro/bsnes-libretro/blob/libretro/sfc/system/system.cpp)
seeds from wall-clock seconds, and its
[CPU power implementation](https://github.com/libretro/bsnes-libretro/blob/libretro/sfc/cpu/cpu.cpp)
fills WRAM from that generator. Unmatched cold-boot comparisons remain
explicit failures. An experimental wall-clock launch barrier also failed to
produce identical initial padding on the pinned DLL; its source and failed
comparison are retained. There is no supported seed option in this core.
No padding is masked, no DLL is patched, and no Accuracy whole-byte equality
claim is made. Accuracy supplies independent strict cadence/behavior checks;
the unmasked whole-state comparison uses deterministic Snes9x cold boots.
Parent explicitly accepted this evidence split. A same-ROM control compares
666 callbacks from two independent Accuracy cold boots of the identical
candidate: controller inputs and native-frame sequences are identical, yet
the first sample already differs at Fighter offsets 31/95 and both Waves'
reserved offsets 10..15. The unmasked control fails as expected and remains
retained in `build/special-timing/accuracy-same-rom-control.json`.
That control uses the rejected `8dd3` ROM and the same pinned Accuracy core;
it is retained evidence of cold-boot nondeterminism, not current-candidate
byte-equivalence evidence.

All native jobs use the worktree's canonical Python and `run_background.py`,
from a job-local PowerShell process with affinity 768 (logical CPUs 8/9) or
3072 (logical CPUs 10/11), two CPUs per job.
They remain below normal priority, headless and silent. For example:

```powershell
$job = Get-Process -Id $PID
$job.ProcessorAffinity = 768
$job.PriorityClass = 'BelowNormal'
& .tools/python/python.exe tools/run_background.py --log build/special.log -- `
  (Join-Path (Get-Location) '.tools/python/python.exe') `
  tools/test_special_24_timing.py --report build/special.json
```

Use `--observe` only when retaining an expected failing baseline. The native
driver's unchanged `--compare BEFORE AFTER` retains the historical last-policy
comparison and static contract audit. Use
`compare_special_24_state.py BEFORE AFTER --report OUTPUT` for the approved
complete first-publication comparison. `test_special_24_cpu_timing.py --replay BEFORE` replays the
baseline's logical input stream and compares whole Fighter/Wave/RNG/CPU state.
The unchanged all-roster attack driver runs separately with its full native
captures and report retained under ignored build evidence for the rejected
`8dd3` candidate. Parent owns the fresh all-roster/both-port attack proof on
the final integrated ROM; its result must be bound separately.

The server restart interrupted both long Snes9x matrix workers before their
final aggregate reports were written. Parent accepted recovery of only
closed, decompressible whole-state streams with recorded original `run_case`
outcomes tied to the same ROM, source and harness. The original stdout and
parsed outcomes are retained with hashes. Cases without both a complete
stream and an outcome run again through the unchanged committed CLI, with a
persisted report for each case. No native assertion is changed. Exact peak,
PCM-total and event summaries lost from the original workers remain unknown;
a retained passed outcome proves the original bounds, not an invented peak.
The final logical comparison still covers all 432 cases, requiring equal
complete ordered frame sets and controller edges. The immutable original
baseline streams are reused; the refined candidate runs all 432 cases afresh
in two shards, with one complete persisted native report per case.

Exact final counts, hashes, remaining limitations and retained artifact
locations are recorded in `combat-24-special-timing-report.json` and ignored
`build/v024-special-timing-handoff.json`. Initial implementation commit
`e415d5bab247fde833d45f8c012ffd5bb440261e` and driver commit
`f3273d6e634225653c02af81cac795522e874327` precede production refinement
`09b8a97965f0ac83b220fbd5983338d91e1ff740` and separate comparison helper
`e6c653db6fb591573db44ca8e75330f3598f3f1e`. Parent owns the source freeze and
regeneration of every final combined gate on the exact integrated ROM.
