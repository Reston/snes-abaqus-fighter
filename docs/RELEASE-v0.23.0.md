# v0.23.0 — walking cycles and local 1v1
<!-- candidate-version: 0.23.0; rom-sha256: 19387882aad17cc8184b02c2c2e0dcb3b6487c05522fe5ef7a943202ef0c0359 -->

Main contains the nine approved improvements as v0.22.1 through merged
[PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1). The nine merged
feature worktrees/branches and old integration branch are removed. Feature 08
remains deferred, with its branch and worktree retained. Its parallax, changed
ambient art and winner reactions remain disabled.

[PR #12](https://github.com/Reston/snes-abaqus-fighter/pull/12) is the unmerged
walking/local-play follow-up. Run [Play.cmd](../Play.cmd) from its current
`feature/walking-cycles-v023` checkout to test the native SNES cartridge.

## Walking

All twelve fighters now use eight contact, recoil, passing-foot and extension
poses. The two feet visibly close during the passing phase, then extend for
the next contact. The cycle follows distance traveled: 32 pixels forward or
a slower 32-pixel retreat; retreat reverses the same footfalls. Speeds,
collision/contact rules, damage and input timing remain unchanged. Pause and
hitstop retain their normal animation freeze.

Only native frames 20–27 change. Each of their upper 47 rows—including the
approved face and upper body—retains its exact old pixels.
Original low-hand/waist accents and their ink edge also survive below the
waist cut, so fingertips are not clipped. The base identity hash and final
walking-overlay hash are recorded separately in the generated metadata.
All other 56 poses,
all portraits, OBJ palette bytes, native size/scale and feet baseline remain.
Each fighter has a separate built-in-imagegen walking master at
`assets/art/characters/NN-name/walking-v1.png`, with exact prompt, reference,
source hash and conversion scope in adjacent `walking-v1.json`. The
[selected art/prompt index](../assets/art/walking-v1.json) lists all twelve.
Old masters and likeness contracts remain retained. The importer uses one
conversion scale across each cycle and quantizes only the new legs into the
existing palette. No substitute shared body or new face is generated in the ROM.

## Local 1v1

Local multiplayer already existed. The menu now says **LOCAL 1V1 / 2P** so it
is easier to find. Select it, choose both fighters and an arena, then play a
best-of-three match. The two physical SNES ports have independent commands.

| Player | Move | Punch Y/X | Kick B/A | Start |
| --- | --- | --- | --- | --- |
| P1 keyboard | Arrow keys | A / S | Z / X | Enter |
| P2 keyboard | I / J / K / L | Numpad 7 / 8 | Numpad 1 / 2 | Space |

Enable Num Lock for the numpad layout. Both default Joypads are enabled.
For physical controllers, use Snes9x **Input → Input Configuration** and map
one controller to Joypad 1 and the other to Joypad 2. P1 confirms the mode and
arena; P2 can choose its fighter. Either controller can pause/resume. Physical
controller hardware has not been exercised by the automated host.

## Verification

- ROM SHA256 `19387882aad17cc8184b02c2c2e0dcb3b6487c05522fe5ef7a943202ef0c0359`, header `A013`.
- Source freeze `ae9fc6f308dcba27a4ecc08f9cec8fe0bc277322`.
- All six native suites pass **36,219 exact-ROM checks**; matching pinned
  bsnes2014 Accuracy smoke passes.
- Focused walking/local-port proof passes **3,678 checks** across all
  twelve mirrored pairs, forward and retreat cycles, both ports, P2 pause and
  different simultaneous attacks. Non-frame combat telemetry matches v0.22.1.
- Fresh committed export reproduces the ROM, all 219 generated assets and
  normalized symbols. Authoring mutations pass 20 normal + 20 optimized.
- Exactly 37 generated files differ from v0.22.1: twelve preview strips,
  the two existing walk-containing banks per fighter, and character metadata.
  No generated file is added; the total remains 219. No mutable RAM, actor/OBJ,
  DMA, guide/HUD or audio resource is added.

[Verification](verification-v0.23.0.json) · [Focused proof](walking-report.json)
· [Native gallery](WALKING-REVIEW-v0.23.0.html).
The GIFs are slowed for inspection and their timing is approximate. Human
walking/balance review remains open; no new full offline package or public-use
approval is claimed.
