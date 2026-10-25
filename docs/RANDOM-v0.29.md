# Random fighter and arena selection (topic 4)

Fresh **SELECT** picks a fighter on the roster or an arena on the location
screen. Both screens show **SELECT: RANDOM** in their existing footer.
The highlighted result stays on screen until the player confirms it.
Repeated outcomes and mirrors are valid; there is no forced shuffle or
anti-repeat bias. Fighter confirmation retains the original 18-tick,
three-pose gesture and standing preview.

P1 owns the first fighter. P1 or participating P2 can choose the second
fighter in Local or the Training dummy. Either pad can randomize the shared
Local arena; Arcade and Training arena selection belongs to P1. Start wins
over B, B over A, and A over SELECT, including chords split across pads.
Up/Down still moves six roster slots. Opposite directions cancel, SELECT
requires a fresh edge, and the existing Back and held-confirm routes remain.

## Implementation and integration hooks

- `src/random29.h` owns the menu clock and independent 16-bit PRNG. Only
  bytes 0..3 of the eight-byte `v29RandomState` reservation are used. Bytes
  4..7 remain unused. There are no new mutable definitions.
- `game.c` includes that module beside `menu_preview.h`, advances the clock
  from `menuTick`, masks lower-priority SELECT edges, and invokes one pick
  from the roster/arena SELECT branches. The other hooks draw the two hints.
- The clock advances on title/roster/arena samples. Each request mixes that
  clock and the native frame into the independent stream, then takes the
  upper byte of a full-period 16-bit LCG (`109*x+89`). Samples 252..255 are
  rejected: each fighter owns 21 accepted byte values and each arena 84.
  An exhaustive host calculation over all 65,536 starting states finds at
  most three PRNG advances for a pick. The algorithm is deterministic;
  different user timing produces different sequences. Combat `rng()` and
  `randomseed` are untouched, and all eight menu-state bytes freeze in fights.
- No generator hook or changed generated output is expected: **allowlist is
  empty**. All 226 generated assets, hardware/trace ASM, fighter art, portraits,
  palettes and stage floors remain exact against approved main `c7510c3`.
- Keep the random hooks when resolving the automatic-start feature's menu
  edits. The parent must adapt its shared menu/footer assertions to the new
  strings and rerun combined proofs after integrating the six topics.

## Native resources

There are no new OBJ entries, palettes, VRAM allocations, DMA paths, audio
cues or combat work. Random uses the existing cursor sound. The standing
preview still uses actor 0's thirty 16x16 entries and the existing 3,840-byte
pose upload plus 32-byte palette; its 972-byte hover UI transfer owns a
separate blank. Arena publication uses the existing 2,048-byte UI transfer.
No transfer targets the obsolete ambient tile address `$3C00`.

The linked random tick/pick sections use 61/150 bytes; the complete `menuTick`
section is 2,036 bytes. Every linked section fits its 32 KiB LoROM bank.
All 1,321 existing variable/data RAM labels retain their addresses. Only the
two end markers grow by the parent's existing 176-byte reservation for all
six topics; the six reservation labels are the only added RAM labels.
Fighter64, Wave16 and TRACE0..122 remain unchanged.

## Exact focused proof

Source/harness freeze: `c20a80533bf4bb76c63b27b29ccb4faa8710e316`.
Tested native ROM: `cc020350b8f4bc94a0c6d5e01e37ae4066dd953b2ac0807f422e62be85acd80e`,
checksum `AA9F`, 4,194,304 bytes, NTSC FastROM LoROM, PVSnesLib 4.6.0.
The tested ROM/symbols/manifest remain in ignored `build/random29-tested/`;
tracked dist outputs are restored before delivery.

Both commands ran silently/headlessly, below-normal, on logical CPUs 8/9
(mask 768), and exited **0**:

```powershell
$taskProcess = Get-Process -Id $PID
$taskProcess.ProcessorAffinity = 768
$taskPython = (Resolve-Path .tools/python/python.exe).Path
& $taskPython tools/run_background.py --log build/random29-build.log -- $taskPython tools/build.py
& $taskPython tools/run_background.py --log build/random29-final.log -- $taskPython tools/test_random29.py
```

The [focused report](random29-report.json) passes **21,311 focused assertions**
and **13,106 shared presentation assertions** in 27.563 seconds. Six complete
mode sessions and four short timing sessions cover 6,206 strict callbacks:
every frame/VBlank delta is one, SDK lag delta zero, and OBJ overflow clear.

| Pinned core | Arcade callbacks | Local callbacks | Training callbacks | Timing callbacks |
| --- | ---: | ---: | ---: | ---: |
| Snes9x 1.63 | 707 | 1,232 | 1,057 | 135 |
| bsnes2014 Accuracy | 608 | 1,213 | 1,119 | 135 |

Every relevant mode/role reaches all twelve fighters within a bound of 96
requests (observed 22..47), and all three arenas within 32 (observed 3..7).
Both participating pads, real random mirrors, ignored nonparticipating P2,
held SELECT, opposite cancellation, input priority, Back, confirmation locks
and confirmed live-fight identities pass. Actual VRAM and rendered pixels
verify every randomly reached fighter's approved standing art; all four
breathing poses and the signature/victory gesture remain. All three rendered
arena cards/cursors, the visible hints and unchanged original portraits pass.
Each mode hands off to 36 strict live-fight callbacks. PCM is captured silently,
active and unclipped. No emulator-memory writes or save states are used.

Snes9x's existing `snes9x_up_down_allowed=enabled` frontend option permits
the physical opposing-direction test. Accuracy can accept a new controller
sample one callback later; the report records acceptance latency separately,
checks every idle callback, and asserts the exact native lock values 1..18.
The report verifies frozen producer/harness/ROM bytes and all 46 final capture
hashes. Examples: [fighter](screenshots/random29/snes9x/mode0-random-00.png),
[Local arena](screenshots/random29/snes9x/mode1-arena-2.png),
[Training mirror](screenshots/random29/accuracy/mode2-random-mirror.png).

SHA256, canonical LF for source/harness:

| Input | SHA256 |
| --- | --- |
| `src/game.c` | `96d214160d1c176ba75e350ae9864db0c35805ad1c6814cc50ec1c4d9a3f0514` |
| `src/random29.h` | `2425fbd5e562e49862e337d58096d1c3f2ea4fffb99815a71da84ccc313a98b5` |
| `tools/test_random29.py` | `ca33b36f45fc82f4206e0f07dead90adc9521a561e1d09941d0bbee0a03af49e` |
| `docs/random29-report.json` | `47014223c21e920b6e514ce4bc043cfebfd9fed236747c8a71b66e7f965861b7` |

The report includes every source/harness dependency hash and both pinned
core archive/DLL identities. The Snes9x DLL is
`f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343`;
Accuracy is `f2aac1ddb314a001467a26b56604020f0a29c3a4dd1658b072884ace75343cf4`.

This evidence covers this isolated topic's ROM. The parent owns combined
six-suite/freeze/reproduction evidence and final integration/main merge.
Physical controllers, original hardware and human combined playtest are
outside this focused proof. No offline package or combined verification is
claimed.
