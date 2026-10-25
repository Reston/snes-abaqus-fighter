# Abaqus: After Hours
<!-- candidate-version: 0.28.0; identity: APPROVED_MAIN_FOCUSED_UI_VERIFIED; rom-sha256: 09eaa47ddc12d419e259f1330eb225f1e56f75d42efdd2faf5c27063f8f2357c; source-freeze: 16e9989497fa7f7bf16271d59555a13b57caeac4 -->

An original four-button fighting game for the **Super Nintendo**, inspired by
Street Fighter II and the people and places of Abaqus in Santiago.
Twelve fighters, three illustrated stages and five original music scores.

<a href="https://abaqus-after-hours.restonjd.workers.dev/">
  <img src="docs/images/abaqus-after-hours-cartridge-v1.png" alt="Abaqus: After Hours — fictional SNES cartridge. Click to play in your browser." width="640">
</a>

**[▶ Play in your browser](https://abaqus-after-hours.restonjd.workers.dev/)** — no download needed.

Press **Play game**, then **Enter** to start. Arcade, Training and local 1v1
use the same native SNES cartridge. [Gameplay preview](docs/screenshots/play-flow-v026/pacing/after-movement.gif).

## Play locally

**Windows:** run **[Play.cmd](Play.cmd)**. On first launch it downloads and
prepares Snes9x locally. Press **Enter** to start; **Alt+Enter** toggles fullscreen.

**Other platforms:** open [dist/abaqus-after-hours.sfc](dist/abaqus-after-hours.sfc)
in a SNES emulator. Original SNES and flash-cartridge support remain unverified.

**Local browser player:** run [Web.cmd](Web.cmd).
[Cloudflare setup](docs/CLOUDFLARE.md) covers hosting your own copy.

## Game modes

- **Arcade:** fight all eleven coworkers, with personal exchanges and endings.
- **Local 1v1 / 2P:** choose two fighters and play a best-of-three match.
- **Training:** practice against a dummy or CPU with input history, combo damage
  and three drills, or enable **P2 Controller** for two-person practice.

## Controls

The four attack buttons are **Y/X for light/strong punches** and **B/A for
light/strong kicks**.

| Action | Player 1 keyboard | Player 2 keyboard |
| --- | --- | --- |
| Move / jump / crouch | Arrow keys | I / J / K / L (up / left / down / right) |
| Light / strong punch | A / S | Numpad 7 / 8 |
| Light / strong kick | Z / X | Numpad 1 / 2 |
| Start / pause | Enter | Space |
| Select / pause guide | Shift | Q |

In menus, **X or Enter** confirms and **Z** goes back for Player 1.
For a super, release directions and attack buttons, then press **Y+B** together
with full energy (**A+Z** on the P1 keyboard).

Enable **Num Lock** for P2. In the browser, use the player's **gamepad** button
to configure controllers. In Snes9x, map them under **Input → Input Configuration**.

Start with [your first minute](docs/PLAYER-GUIDE.md#your-first-minute), then
use the player guide for specials, blocking, combos and Training options.

## Build and test

Development uses Windows x64 and project-local **PVSnesLib 4.6.0**.

| Command | Purpose |
| --- | --- |
| `Build.cmd` | Prepare the toolchain and build the cartridge |
| `Build.cmd --assets` | Regenerate art/audio assets and rebuild |
| `Test.cmd` | Run the six native emulator suites silently and headlessly |

The output is `dist/abaqus-after-hours.sfc`. Downloaded tools and build
intermediates stay in ignored `.tools/` and `build/` directories.

## Documentation

- [Player guide](docs/PLAYER-GUIDE.md) — controls, modes and practice.
- [Current release: v0.28.0](docs/RELEASE-v0.28.0.md) · [Selection animations](docs/REVIEW-v0.28.0.html).
- [Development guide](docs/DEVELOPMENT.md) — native architecture and hardware budgets.
- [Roadmap](docs/ROADMAP.md) — planned work and historical milestones.
- [Credits and art provenance](docs/CREDITS.md) · [License](LICENSE).
