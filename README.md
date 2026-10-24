# Abaqus: After Hours
<!-- candidate-version: 0.26.1; identity: FOCUSED_UI_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: 00029816d23adfe6fb950640ed4fa45fa0de05af46f3a802890333d4b4322aa3; source-freeze: 3feabef37f45a96e1ab7a82eea5d5af9159132cd -->

An original four-button fighting game for the **Super Nintendo**, inspired by
Street Fighter II and the people and places of Abaqus in Santiago.
Twelve fighters, three illustrated stages and five original music scores.

**Ready to playtest:** [v0.26.1](docs/RELEASE-v0.26.1.md), with slower combat,
detailed floors and shorter game text. [Native comparisons](docs/REVIEW-v0.26.1.html).
The approved main revision is [v0.24.0](docs/RELEASE-v0.24.0.md).

<img src="docs/screenshots/play-flow-v026/pacing/after-movement.gif" alt="Current native combat and detailed floor" width="640">

## Play

**Windows:** run **[Play.cmd](Play.cmd)**. On first launch it downloads and
prepares Snes9x locally. Press **Enter** to start; **Alt+Enter** toggles fullscreen.

**Other platforms:** open [dist/abaqus-after-hours.sfc](dist/abaqus-after-hours.sfc)
in a SNES emulator. Original SNES and flash-cartridge support remain unverified.

## Game modes

- **Arcade Shift:** fight all eleven coworkers, with personal exchanges and endings.
- **Local 1v1 / 2P:** choose two fighters and play a best-of-three match.
- **Training:** practice against a dummy or CPU with input history, combo damage
  and three drills, or enable **P2 Controller** for two-person practice.

v0.26 adds shared local menus, clear feedback, Training confirms and comfort options.
It retains v0.25's slower fight rhythm; video, inputs and audio keep native speed.

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

Enable **Num Lock** for P2. To use controllers, map each one to **Joypad 1** or
**Joypad 2** in Snes9x under **Input → Input Configuration**.

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
- [Current text polish](docs/RELEASE-v0.26.1.md).
- [Development guide](docs/DEVELOPMENT.md) — native architecture and hardware budgets.
- [Roadmap](docs/ROADMAP.md) — planned work and historical milestones.
- [Credits and art provenance](docs/CREDITS.md) · [License](LICENSE).

Text pass: 6,606 presentation/Training checks pass; human playtest is pending.
The latest full Windows archive remains v0.19.0.
