# Abaqus: After Hours
<!-- candidate-version: 0.16.0; rom-sha256: feb73416224a7bbe6317f0c8a2b88abc403383c5017e151e1e6e2a8c3478cebd -->

An original six-button fighting game for the **Super Nintendo**, inspired by
Street Fighter II's arcade structure and the people and places of Abaqus in
Santiago. The game runs as a native SNES cartridge in an emulator.

The current checkout is the **v0.16.0 CPU anti-air review candidate**, ROM SHA256
`feb73416224a7bbe6317f0c8a2b88abc403383c5017e151e1e6e2a8c3478cebd`, checksum `FA49`.
Normal and Hard opponents can deliberately uppercut a nearby jump-in. Their
sampled decisions use visible position and an available grounded startup;
ordinary startup/recovery and missed commitments remain. Easy retains its
previous behavior. Existing wave/attack defense and signature specials keep
priority. All 219 generated art/audio assets and the native memory contracts
are retained. Cross-ups, practice help, revised Lars art and location previews
remain available.

All six native suites pass 35,147 checks on this exact ROM. Matching smoke,
full matchup/replays, independent combat, endurance and fresh-source gates pass.
The [v0.16.0 release note](docs/RELEASE-v0.16.0.md) records the evidence.
The offline Windows archive passes 8,729 technical audit checks. Two
consecutive final packages are identical: 21,689,220 bytes, SHA256
`e8736a6f9a786fd7e9b66e639e7ba220928cd36411159da4b0ba59db08426679`.
Human gameplay/balance, listening, controllers, likeness/consent and public-use
review remain open.

## Play

On Windows, run **[Play.cmd](Play.cmd)** from the source checkout. The launcher
prepares the pinned official Snes9x tools in `.tools/` on first use and opens
the cartridge. No administrator account or global installation is needed.

For offline play, extract the whole [v0.16.0 Windows ZIP](dist/Abaqus-After-Hours-v0.16.0-Windows.zip) and run its included
`Play.cmd`. Its `manifest.json` and `RELEASE.md` identify the actual cartridge
and verification scope. Older archives contain their own historical versions.

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

The current candidate includes a [cross-up practice companion](docs/CROSSUP-PRACTICE-v0.16.0.html)
with native moving examples for all twelve fighters. Its [practice notes](docs/CROSSUP-PRACTICE.md)
explain different jump setups and record the supplemental 72-case controller proof.

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
