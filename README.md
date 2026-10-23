# Abaqus: After Hours
<!-- candidate-version: 0.22.1; rom-sha256: 52725899fa86b4ee3d3f3f022dae374c1ab4ff8777bdab4a7134640c34dc8727 -->

## Current v0.22.1: nine approved improvements

Features 01–07, 09 and 10 are approved for main. **Feature 08 is deferred**:
the camera and ambient art are restored to v0.21.0; its branch/worktree remain
for polish. The six native suites pass 36,253 exact-ROM checks and matching
independent smoke passes. [Current release and scope](docs/RELEASE-v0.22.1.md).
Local 1v1 already works in **Local Versus** with separate controller ports.
Walking improvements and clearer local-play discovery are the next follow-ups.
The v0.22.0 material below is historical, including its ten-feature review gallery.

An original four-button fighting game for the **Super Nintendo**, inspired by
Street Fighter II's arcade structure and the people and places of Abaqus in
Santiago. It runs as a native SNES cartridge in an emulator.

Source, original art, native review evidence and the cartridge are retained in
[Reston/snes-abaqus-fighter](https://github.com/Reston/snes-abaqus-fighter).

The combined **v0.22.0 candidate** is on `integration/ten-improvements-v022`.
All ten feature PRs are merged there: weighted animation, readable contacts,
four-button normal balance, individual fighter gestures, Training tools, CPU
personalities, twelve supers, stage depth, personal Arcade exchanges/endings
and resident sound/announcements. See the [all-ten release guide](docs/RELEASE-v0.22.0.md)
and [player guide](docs/PLAYER-GUIDE.md).

Run **[Play.cmd](Play.cmd) from that integration checkout** to play them together.
**Main remains v0.21.0** until your combined playtest
and [PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1) merge.
The combined cartridge passes 36,253 checks across all six native suites,
matching independent emulator smoke and all ten focused feature proofs. A fresh
committed-source export reproduces the ROM, 219 assets and symbols. See the
[verification record](docs/expansion-v0.22.0-verification.json) and
[native review](docs/EXPANSION-REVIEW-v0.22.0.html).
ROM SHA256 `d4fddaf609a0c29f45353a8d9e22fe1131fc3380838d9c0073d3255474cdf8af`, header `EA9D`; source freeze `b149cdf2d9e25560f61d09a0f49e71ce6fea7042`.
No v0.22.0 human approval, offline ZIP or full release-scale evidence exists;
v0.19.0 remains the latest full offline archive.

Four face buttons remain **Y/X punches, B/A kicks**. A super requires a
fresh **neutral Y+B together** and spends all **96 energy**; Normal/Hard CPUs
can attempt one fallibly after defense. Training adds a third guide page for
input history, combo damage, `SP!` execution feedback and three drills, keeping
the ordinary dummy and CPU-level pause controls. All twelve existing fighter
sets and portraits, including approved Damian v5, remain preserved.

## Main baseline: v0.21.0

The previous source candidate, retained on main, is **v0.21.0**, ROM SHA256
`aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205`, checksum `BEB8`.
Combat uses only the four SNES face buttons: **Y/X punches, B/A kicks**.
The contact shadows sit against the feet. The HUD has gold nameplates,
framed health bars, red low-health feedback and diamond round-win medals.
See the [controls and presentation note](docs/FOUR-BUTTON-HUD.md),
[native comparison](docs/FOUR-BUTTON-HUD-REVIEW.html) and
[candidate verification](docs/RELEASE-v0.21.0.md).
The six native suites pass 33,082 checks and the independent smoke passes
on that cartridge. Full release-scale evidence and a new Windows ZIP have
not been regenerated for it.

## Approved likeness checkpoint

The approved **v0.20.0 Damian likeness build**, ROM SHA256
`6b3544fa09e37a3f70c4eaecf5565718abc467962610ec1ce0437fc023d9f501`,
checksum `3F2A`. The additional user photo guides a longer nose, darker brows,
narrower mouth and short stubble across all 64 frames and both portraits.
See the [comparison](docs/DAMIAN-REVIEW-v5.html) and
[art and prompts](docs/DAMIAN-LIKENESS-v5.md). The current integration cartridge
retains this approved art; its verified ROM identity is recorded above.
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
| Special | Down, Down+toward, toward + A or S |
| Rising uppercut / close throw | Down + S / toward + S |
| Sweep / quick special | Down + X / Down + A |
| Full-gauge super (v0.22.0) | Release directions and A/Z, then press A+Z together |

The [player guide](docs/PLAYER-GUIDE.md) covers both players, controllers,
blocking, cancels, specials, pause pages and Training dummies. Snes9x supports
fullscreen with Alt+Enter and controller mapping under Input Configuration.

The retained v0.19.0 [cross-up practice companion](docs/CROSSUP-PRACTICE-v0.19.0.html)
shows native moving examples for all twelve fighters. Its [practice notes](docs/CROSSUP-PRACTICE.md)
explain different jump setups and record the supplemental 72-case controller proof.

## Included

- Twelve individual illustrated coworkers, each with 64 native animation frames.
- Las Condes, El Castillo and La Oficina, with original cartoon art, subtle scenery scroll and ambient winner reactions.
- Arcade Shift against all eleven coworkers, personal exchanges/endings, two-player Local Versus and Training.
- Four face-button attacks, air attacks, high/low guard, throws, throw tech, uppercuts and confirmed cancels.
- Twelve specials across projectile, rush, low-wave and rising-strike families, plus twelve full-gauge supers.
- Controls/Move List guides, Training Tools page 3, command history, combo damage and three drills; arbitrary/mirror opponents and five dummy behaviors, including CPU.
- Individual intro/victory gestures, CPU fighting habits, weighted transitions and distinct hit/block feedback.
- An earned Office Champion trophy scene after all eleven Arcade victories.
- Five retained original scores, distinct resident combat effects, Round/Fight/K O speech and music ducking.

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

- [v0.22.0 combined candidate and all ten feature PRs](docs/RELEASE-v0.22.0.md)
- [v0.21.0 four-button/HUD baseline](docs/RELEASE-v0.21.0.md)
- [v0.11.0 result-card release note](docs/RELEASE-v0.11.0.md)
- [v0.10.1 Lars and location art provenance](docs/POLISH-v0.10.1.md)
- [v0.10.0 cartoon-stage snapshot](docs/RELEASE-v0.10.0.md)
- [Character profiles](docs/CHARACTERS.md), [art direction](docs/ART-DIRECTION.md) and [menu design](docs/MENU-DESIGN.md)
- [Compatibility scope](docs/COMPATIBILITY.md), [public-release gates](docs/PUBLIC-RELEASE.md) and [credits/licenses](docs/CREDITS.md)

The source, master art, prompts, generated native assets and cartridge are
retained in this repository. Historical release notes identify earlier
evidence by exact version and ROM SHA. The combined v0.22.0 verification record is current.
Team references: [Abaqus Solutions](https://abaqus.io/es/abaqus-solutions/team)
and [Abaqus Wealth Care](https://abaqus.io/es/wealth-care/about-us).
