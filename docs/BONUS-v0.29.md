# Office bonus rounds (isolated topic 2)

The Arcade ladder offers a short optional printer-jam round after the third
earned opponent win, and an inbox-overload round after the seventh. Each
starts immediately on the earned RESULT-to-next handoff. Their 12/15-second
clocks stop during pause. A 90-tick result automatically loads the next
opponent; success, timeout, and skip all advance exactly once. Local and
Training retain their ordinary flow. The eleven-opponent ladder and ending
remain the original ones.

Move left/right, jump with Up, and use Y/X for light/strong punches and B/A
for light/strong kicks. Fresh attacks score one/two clearance points when
within 62 pixels of the target and no more than 20 pixels above the floor.
There are 12 printer points / 18 inbox points. The target rolls across the
office twice as points accumulate. Strong attacks trade longer recovery
for two points. Held face buttons do not repeat attacks. Simultaneous
horizontal directions cancel. No HP, ladder reward, or combat stat changes.

Start from either controller pauses/resumes both the challenge and its result;
Start owns simultaneous skip/attack. Fresh Select from either pad skips a
live or paused challenge. Bonus pause uses only Start/Select; the normal
combat pause menu remains separate. P2 face buttons do not control the solo
hero. B is always a light kick during the live bonus. Entry and resume wait
for face-button release before accepting new attack edges.

## Integration hooks

- `src/bonus29.h` is included immediately before `menuTick`, after all existing
  game/UI/combat helpers. It contains the entire bonus engine.
- Call `bonus29TryBegin()` **before** a successful Arcade RESULT increments
  `arcade` or `arena`. If it returns 1, return from the result handler: BONUS
  owns handoff. The automatic-start topic must retain this call in its timed
  RESULT-to-next path. The hook expects zero-based won indices 2 and 6.
- Dispatch scene 5 to `bonus29TickFrame()` in the main active-display phase.
  The existing actor DMA slot consumes its queued approved hero pose. Keep
  BONUS's BG1 scroll at 16 to show the approved office viewport; no combat
  camera update or old ambient DMA runs there.
- `showSelect()` clears only `v29BonusState[0]`, starting a fresh milestone
  history. Continue does not clear it. Other feature state is untouched.
- Bonus exit increments `arcade` and rotates `arena` once, then calls the
  existing `beginMatch()`. That restores both fighters, palettes, actor bank
  pointers, combat/reset state and the original fight intro. Automatic-start
  may shorten that intro through its normal begin-match hook.

## Assets and native ownership

Original built-in imagegen source is
`assets/art/bonus-v029/office-targets-v1.png`; its adjacent JSON retains the
exact prompt, no-reference record and output SHA256. Old art is retained.
`tools/bonus29_assets.py` crops each complete authored transparent half,
fits it proportionally inside 90x76 at native baseline 78, quantizes to 15
colors plus transparent zero, and encodes a 96x80 / 3840-byte actor stream.

The two-line `tools/make_assets.py` hook installs into the private `OUT`
**after** stage-depth install and **before** source-input recheck and
transactional publish. Never publish these files independently into the live
asset directory. Asset-cache dependency discovery follows the import.

Expected new output allowlist (7): `bonus29-assets.json`, and
`bonus29_printer.bin`, `bonus29_printer_pal.bin`, `bonus29_printer.png`,
`bonus29_inbox.bin`, `bonus29_inbox_pal.bin`, `bonus29_inbox.png`.
Only the existing `data.asm` and `assets.h` append declarations/size macros;
the other 224 original generated outputs remain exact. Four `superfree`
LoROM sections hold two 3840-byte streams and two 32-byte palettes, 7744
bytes total. No output exceeds a 32 KiB bank. Version stays parent-owned.

All mutable bonus state lives in `v29BonusState[64]`: bytes 0..15 are earned
mask, variant, result, pause, seconds, subtick, progress, target x, action,
tick, connection, pose, queued pose, walk phase, flash and facing; signed
16-bit fixed-point x/y/vy occupy 16..21; bytes 22..28 are result ticks, goal,
rolling stage, hits, button coverage, attack release gate and destination x.
Bytes 29..63 remain unused. Existing Fighter64/Wave16/TRACE and ASM are exact.

BONUS borrows actor0 for the selected hero and actor1 for the target, at
VRAM words `$6000..69FF` / `$6A00..73FF`, OBJ palettes 0/1. Both streams load
under forced blank on entry. During the live bonus only one approved actor0
pose can be queued per vblank (3840 bytes). Actor1 never receives live DMA.
HUD 320-byte and banner 320-byte updates use the existing dirty queues and
yield to the actor slot. No new full-map UI transfer occurs during play.
The existing effects page/palette supplies the two ordinary shadows. OAM
contains 30 pieces per actor plus 2 shadows each (64 entries total, padded
actor blocks retained). Actor rows have at most 12 intersecting 16x16
pieces = 24 fetch tiles; the two shadow pairs at y200 add at most 4 pieces,
for 16 pieces / 32 tiles, below SNES's 32-object/34-tile per-line limits.

Office BG1 tiles/map/palettes and detailed floor bytes are reused intact.
The 64x32 map spans words `$3800..3FFF`; no animation writes to `$3C00`.
BG3 and HDMA remain disabled. No new resident audio or SPC allocation is
needed; existing contact/confirmation cues play through the usual queue.

## Focused verification

`tools/test_bonus29.py` drives actual SNES controllers and reads telemetry,
VRAM, PPU frames and captured PCM. It never writes memory or uses save states.
Reports bind the exact ROM, source/harness inventory, encoder/art/dependencies,
core hashes, commands and host affinity/priority. They publish atomically.

Final focused evidence and exact commands are recorded here after the frozen
candidate run. The parent owns the combined six suites, freeze/reproduction,
generated assets and cartridge publication, and merge to main. This child
does not claim combined verification, hardware playtesting or human acceptance.
