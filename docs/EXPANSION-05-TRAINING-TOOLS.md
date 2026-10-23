# Expansion 05: native Training tools

This feature adds a live practice footer and a third Training pause-guide page.
It is isolated on `t3/training-combat-tools`, based on integration commit
`610537d3da8f7005c28ea31d0a45a7c17f8f7ba8`. It does not change the shared version,
release records, art, palettes, combat tuning or attack commands.

## Use on a SNES controller

Training starts with the two-row display enabled. Pause with Start, then press
Select three times for **Training Tools 3/3**. Select still visits Controls and
Specials first; another Select returns to the normal pause card. Left/Right
cycle the three guide pages. These controls work from either pad.

On Training Tools, Up toggles the live display and Down chooses the next drill.
A/Start resumes and B returns to the roster, retaining Start > B > A > Select
priority. The normal pause card still uses Up/Down for Stand, Guard High, Guard
Low, Jump and CPU. Its CPU L/R level controls and opposite-input cancellation
remain. Versus and Arcade retain their two-page guide cycle.

The live footer shows five recent P1 command signatures, oldest to newest. A
signature has the absolute numpad direction followed by `YXBA`; `-` means an
unpressed button. For example, `6Y---` is Right+Y and `1----` is Down+Left.
Directions use the ordinary cleaned input, so opposites cancel before recording.
Neutral releases do not evict useful motion steps, but separate repeated presses
still enter separately. Paused controls, Select, Start and shoulders do not
become history commands. Recording continues while the display is hidden.

`NOW 02H 024D` gives the active P1 chain's hit count and actual HP damage.
`LAST` keeps those figures after real hit stun ends, including after ordinary
Training health recovery. A fresh unlinked real hit starts a fresh total;
blocked contacts and chip do not inflate a combo. Damage clamps at 999 and
the display clamps at 99 hits. `SP!` means an actual accepted action-7 special
executed and paid energy. It can appear on a whiff; it does not imply a hit.
An energy-rejected command does not trigger it. Its 90-live-tick timer freezes
with hitstop and pause.

The three drills display `READY`, `LINK!`, `DONE!` or `RETRY`:

1. **Normal -> Special:** land a normal, cancel/link into a special, and land
   the special while the defender is still in the same real hit-stun chain.
   Start with a close Stand dummy. A quick normal followed by Down+Y is the
   suggested route; slower special profiles can use the longer stun of A.
   A guarded normal, a whiff or a late special cannot complete the drill.
2. **Block a Low Attack:** choose CPU on the ordinary pause card, then use
   Down+Away against a low attack. A real low block completes it. Taking
   damage shows Retry; a high block alone does not count. After a failed
   close encounter, Select can restore space for another low-wave attempt.
3. **Air Kick Cross-up:** jump past a Stand dummy and press A just after
   crossing. Completion requires an actual rear airborne action-5 hit using
   the existing short rear contact box. A front air kick or blocked contact
   does not complete it.

Completion remains until Select resets practice progress or Down selects
another drill. Live P1 Select retains the chosen drill, visibility and dummy,
while clearing the history, damage, cue and completion along with the ordinary
round reset. New matches restore the default visible display and first drill.

## Native implementation and integration hooks

`src/training_tools.h` contains a read-only combat observer, cached strings and
the footer scheduler. It uses no Fighter/Wave fields, new trace words, OBJ,
palette, audio command, tile asset or hardware assembly. Its declaration include
follows the text helpers; its implementation include follows `pause_guide.h` so
all existing guide table allocations precede the added data.

Small hooks in `game.c` call it at scene/reset initialization, P1 live input
capture, accepted action startup, actual HP/guard resolution, P1 direct/wave
contact classification, and the end of a Training fight tick. The contact
classification uses the original action snapshot and actual hurt() outcome.
Wave impacts explicitly identify action 7; delayed throw damage still reaches
the damage observer through the existing common hurt path. No hook writes
combat state or changes the controller command returned by the game.

The Training-only pause additions own page 3 and preserve the existing ordinary
pause-card dummy/level branches. A guide close queues restoration of the footer.
The existing first-intro hint still has the footer until intro ends.

There are **101 bytes of bounded mutable state** at `$7F0448-$7F04AC`, followed
by **90 bytes of lookup text** through `$7F0506`. Explicit zero initializers
append the state to initialized `.data`; 816-tcc otherwise extends `.bss` and
moves an existing SDK string. All 1,242 prior named RAM/direct-page symbols keep
their addresses. Of the 1,276 prior RAM labels including linker metadata, only
`SECTIONEND_globram.data` and `RAM_USAGE_SLOT_3_BANK_127_END` change to describe
the new allocation. Fighter64/Wave16 and TRACE0..122 remain intact.

Normal HUD DMA is unchanged at 320 bytes. Tools reuse only the existing
128-byte footer DMA at BG2 rows 26-27; page 3 uses the existing 1,472-byte guide
range built over three ticks. The one-actor-per-vblank arbitration is unchanged.
Status construction yields to guide, impact, HUD and banner work. Outside
settled hitstop, it also yields during attacks, knockdowns, air/landing and
hurt states. Input is still captured each live sample. History formats one
token per eligible alternate tick and publishes the completed cached row.
Consequently the panel can trail a busy exchange until a safe gap; gameplay
never waits for a Training display update.

## Focused evidence

Build using the shared tool cache without running setup:

```powershell
D:\snes-abaqus-fighter\.tools\python\python.exe tools/build.py
D:\snes-abaqus-fighter\.tools\python\python.exe tools/run_background.py --log build/expansion-05-test.log -- D:\snes-abaqus-fighter\.tools\python\python.exe tools/test_expansion_05_training_tools.py
```

The tested native 4 MiB FastROM LoROM SHA256 is
`4c830b6ad309511ef67f550c668ceecf240565cfd9a24a4d4a5469b340cf51b2`.
The focused report is [expansion-05-report.json](expansion-05-report.json).
It records the exact ROM, three source hashes, harness/core hashes, controller
states, native text and screenshot hashes. Captures are in
[screenshots/expansion-05](screenshots/expansion-05).
The final focused run passes **608 checks**, across 17 sessions and 23,179
native samples, including 19,287 FIGHT samples. Native cadence, SDK timing,
OBJ-overflow and SPC failure arrays are empty. Linked sections consume
3,264,578 bytes, leaving 929,726 bytes of aggregate ROM section space; every
section fits its 32 KiB LoROM bank.

The driver exercises show/hide/restoration, hidden recording, reset, actual
motion history, SOCD/multiple face buttons, accepted and rejected specials,
exact current/last combo damage, true combo completion, expired-link rejection,
low-guard success/failure and real rear-air-kick success/front-kick rejection.
It also exercises the original arbitrary/mirror selection, guard dummies,
repeated Jump behavior, CPU levels from both pads, opposing inputs, pause/reset
priority, roster return and non-Training guide cycle.

A bounded 1,200-frame changing-input combat load runs against each of twelve
CPU opponents, spanning all three stages and difficulty levels. Every adjacent
native fight callback checks the SDK lag counter and VBlank counter, the
public trace cadence, STAT77 OBJ flags, and the resident SPC FIFO. Captured
audio is never played. This is focused feature evidence, not the six-suite
combined-ROM gate or a live-hour/endurance/release certification.

All original/generated assets remain byte-identical to the base. No ROM,
symbol file, manifest, release archive or shared suite report is committed by
this branch. The parent owns the combined build/tests, source version and PRs.

Integration should retain the footer ownership and deferred scheduler when
merging shared HUD/impact changes. New supers can coexist with the physical
input history; `SP!` and drill 1 deliberately identify the existing action-7
special, not the new super. Tuning changes may alter each fighter's executable
normal-to-special route and should be covered by combined controller checks.
