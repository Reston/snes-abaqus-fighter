# Abaqus: After Hours
<!-- candidate-version: 0.21.0; rom-sha256: aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205 -->

An original four-button fighting game for the **Super Nintendo**, inspired by
Street Fighter II's arcade structure and the people and places of Abaqus in
Santiago. It runs as a native SNES cartridge in an emulator.

Source, original art, native review evidence and the cartridge are retained in
[Reston/snes-abaqus-fighter](https://github.com/Reston/snes-abaqus-fighter).

The current source candidate is **v0.21.0**, ROM SHA256
`aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205`, checksum `BEB8`.
Combat uses only the four SNES face buttons: **Y/X punches, B/A kicks**.
The contact shadows sit against the feet. The HUD has gold nameplates,
framed health bars, red low-health feedback and diamond round-win medals.
See the [controls and presentation note](docs/FOUR-BUTTON-HUD.md),
[native comparison](docs/FOUR-BUTTON-HUD-REVIEW.html) and
[candidate verification](docs/RELEASE-v0.21.0.md).
The six native suites pass 33,082 checks and the independent smoke passes
on this cartridge. Full release-scale evidence and a new Windows ZIP have
not been regenerated for it.

## Approved likeness checkpoint

The approved **v0.20.0 Damian likeness build**, ROM SHA256
`6b3544fa09e37a3f70c4eaecf5565718abc467962610ec1ce0437fc023d9f501`,
checksum `3F2A`. The additional user photo guides a longer nose, darker brows,
narrower mouth and short stubble across all 64 frames and both portraits.
See the [comparison](docs/DAMIAN-REVIEW-v5.html),
[art and prompts](docs/DAMIAN-LIKENESS-v5.md), or open the
[review cartridge](dist/abaqus-after-hours.sfc) in the existing emulator.
At that checkpoint, all six native suites pass 35,715 checks and the independent
compatibility smoke passes on that exact ROM. The user approved the revised likeness after
reviewing the photo/previous/revised comparison on 2026-10-22. Extended
release gates and a new Windows ZIP have not been regenerated for this build.
The [v0.20.0 note](docs/RELEASE-v0.20.0.md) records this scope.

## Previous full release checkpoint

The v0.19.0 checkpoint has ROM SHA256 `945da11920112ca11fbc00acec2fc04a1d821209a7e7a920defe5a05c32005e7`,
checksum `05A4`. On Training's first PAUSED card, choose CPU and use
the **L/R shoulder buttons** to change Easy/Normal/Hard without leaving the
match. Either controller can change the setting. The chosen level also
appears at home. The title's lower-right version label identifies the build.
All five behaviors, recovery, the 99 clock and quick reset remain.

All six native suites pass 35,715 checks on this exact ROM. Matching smoke,
full matchup/replays, independent combat, endurance and fresh-source gates pass.
The [v0.19.0 release note](docs/RELEASE-v0.19.0.md) records the evidence.
The Windows archive passes 9,299 technical audit checks. Two
final packages are identical: 22,904,626 bytes, SHA256
`b518ddf6eb6e20bfed1e55758aebb61fa2cca0462b5918412eb0837dc5eb1b07`.
Human gameplay/balance, listening, controllers, likeness/consent and public-use
review remain open.

## Play

On Windows, run **[Play.cmd](Play.cmd)** from the source checkout. The launcher
prepares the pinned official Snes9x tools in `.tools/` on first use and opens
the cartridge. No administrator account or global installation is needed.

Windows ZIPs are local generated outputs and are not tracked in this repository.
For an existing offline copy, extract the whole v0.19.0 Windows ZIP
(`dist/Abaqus-After-Hours-v0.19.0-Windows.zip`) and run its included
`Play.cmd`. Its `manifest.json` and `RELEASE.md` identify the actual cartridge
and verification scope. Older archives contain their own historical versions.

On other platforms, open **[dist/abaqus-after-hours.sfc](dist/abaqus-after-hours.sfc)**
in a SNES emulator. No BIOS or commercial ROM is required. Original SNES and
flash-cartridge support remain unverified.

| Action | Included P1 keyboard |
| --- | --- |
| Move / jump / crouch | Arrow keys |
| Light / strong punch | A / S |
| Light / strong kick | Z / X |
| Confirm / back | X or Enter / Z |
| Pause / pause guide | Enter / Shift while paused |
| Special | Down, toward, then A or S |
| Rising uppercut / close throw | Down + S / toward + S |
| Sweep / quick special | Down + X / Down + A |

The [player guide](docs/PLAYER-GUIDE.md) covers both players, controllers,
blocking, cancels, specials, pause pages and Training dummies. Snes9x supports
fullscreen with Alt+Enter and controller mapping under Input Configuration.

The retained v0.19.0 [cross-up practice companion](docs/CROSSUP-PRACTICE-v0.19.0.html)
shows native moving examples for all twelve fighters. Its [practice notes](docs/CROSSUP-PRACTICE.md)
explain different jump setups and record the supplemental 72-case controller proof.

## Included

- Twelve individual illustrated coworkers, each with 64 native animation frames.
- Las Condes, El Castillo and La Oficina, with original cartoon art and ambient motion.
- Arcade Shift against all eleven coworkers, two-player Local Versus and Training.
- Four face-button attacks, air attacks, high/low guard, throws, throw tech, uppercuts and confirmed cancels.
- Twelve specials across projectile, rush, low-wave and rising-strike families.
- Pause Controls/Specials pages, arbitrary Training opponents, five dummy behaviors, including CPU and a live round reset.
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
