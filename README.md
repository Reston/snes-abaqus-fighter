# Abaqus: After Hours
<!-- candidate-version: 0.14.0; rom-sha256: 3de317b43f72bea76cfc2f1a1ebd5c67dd57913b8d9fddfb50a7a846a02ddeaa -->

An original six-button fighting game for the **Super Nintendo**, inspired by
Street Fighter II's arcade structure and the people and places of Abaqus in
Santiago. The game runs as a native SNES cartridge in an emulator.

The current checkout is the **v0.14.0 review candidate**, ROM SHA256
`3de317b43f72bea76cfc2f1a1ebd5c67dd57913b8d9fddfb50a7a846a02ddeaa`, checksum `D1E2`.
Fighter and arena menus now show A/Start confirmation. The arena footer uses
native opaque lettering while preserving every generated art asset and palette.
The Specials guide clarifies the twelve-tick timeout between motion steps.
Asset-authoring contracts now remain active under Python optimization.
Champion music, Training opponent/mirror selection, Lars's revised likeness,
clearer location previews and winner cards are retained.
All six native suites pass 34,683 checks on this exact ROM. Matching smoke,
full matchup/replay, independent combat, endurance and fresh-source gates pass.
The [v0.14.0 release note](docs/RELEASE-v0.14.0.md) records the evidence.
The offline package passes 8,698 technical audit checks. Two consecutive final
ZIPs are identical at 13,479,437 bytes, SHA256
`dd880e6b5b068e0172b92cdad8a52011938df0d0f6adbc1b528d64ce3f9e6339`.
Human gameplay, listening, controller, likeness/consent and public-use review
remain open.

## Play

On Windows, run **[Play.cmd](Play.cmd)** from the source checkout. The launcher
prepares the pinned official Snes9x tools in `.tools/` on first use and opens
the cartridge. No administrator account or global installation is needed.

For offline play, extract the whole [v0.14.0 Windows ZIP](dist/Abaqus-After-Hours-v0.14.0-Windows.zip) and run its included
`Play.cmd`. Its `manifest.json` and `RELEASE.md` identify the actual cartridge
and verification scope. The release note above identifies the latest candidate
package when available; older archives contain their own historical versions.

On other platforms, open **[dist/abaqus-after-hours.sfc](dist/abaqus-after-hours.sfc)**
in a SNES emulator. No BIOS or commercial ROM is required. Original SNES and
flash-cartridge support remain unverified.

| Action | Included P1 keyboard |
| --- | --- |
| Move / jump / crouch | Arrow keys |
| Light / medium / heavy punch | A / S / D |
| Light / medium / heavy kick | Z / X / C |
| Confirm / back | X or Enter / Z |
| Pause / pause guide | Enter / Shift while paused |
| Special | Down, toward, then A or S |
| Rising uppercut / close throw | Down + D / toward + D |

The [player guide](docs/PLAYER-GUIDE.md) covers both players, controllers,
blocking, cancels, specials, pause pages and Training dummies. Snes9x supports
fullscreen with Alt+Enter and controller mapping under Input Configuration.

## Included

- Twelve individual illustrated coworkers, each with 64 native animation frames.
- Las Condes, El Castillo and La Oficina, with original cartoon art and ambient motion.
- Arcade Shift against all eleven coworkers, two-player Local Versus and Training.
- Six normal attacks, air attacks, high/low guard, throws, throw tech, uppercuts and confirmed cancels.
- Twelve specials across projectile, rush, low-wave and rising-strike families.
- Pause Controls/Specials pages, arbitrary Training opponents, four dummy behaviors and a live round reset.
- An earned Office Champion trophy scene after all eleven Arcade victories.
- Original tracker music and resident combat effects.

Human gameplay/balance, full listening, physical-controller sessions,
likeness/consent and team/public-use review remain open.
`public_release_certified` remains false. The [human playtest route](docs/PLAYTEST.md)
records actual feedback; emulator checks do not replace those reviews.

## Build and verify

On Windows x64, run `Build.cmd` to build with project-local PVSnesLib 4.6.0.
Use `Build.cmd --assets` to regenerate the committed art and audio assets.
`Test.cmd` runs the six native suites silently and headlessly. Each report
records the exact ROM hash. See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for memory,
transfer and ABI contracts and the separate release-scale gates.

Packaging requires all six exact-ROM suites, pinned independent-engine smoke,
matchups/replays, bounded independent combat, native live-hour sessions and an
isolated committed-source rebuild. `tools/package.py` creates the offline ZIP;
`tools/audit_release.py` checks the result. Downloaded tools, emulator saves,
build intermediates and release ZIPs stay outside Git history.

## Source and history

- [v0.11.0 result-card release note](docs/RELEASE-v0.11.0.md)
- [v0.10.1 Lars and location art provenance](docs/POLISH-v0.10.1.md)
- [v0.10.0 cartoon-stage snapshot](docs/RELEASE-v0.10.0.md)
- [Character profiles](docs/CHARACTERS.md), [art direction](docs/ART-DIRECTION.md) and [menu design](docs/MENU-DESIGN.md)
- [Compatibility scope](docs/COMPATIBILITY.md), [public-release gates](docs/PUBLIC-RELEASE.md) and [credits/licenses](docs/CREDITS.md)

The source, master art, prompts, generated native assets and cartridge are
retained in this repository. Historical release notes identify earlier
evidence by exact version and ROM SHA. No remote repository is configured.
Team references: [Abaqus Solutions](https://abaqus.io/es/abaqus-solutions/team)
and [Abaqus Wealth Care](https://abaqus.io/es/wealth-care/about-us).
