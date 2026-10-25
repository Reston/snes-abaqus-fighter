# Public-release quality target
<!-- candidate-version: 0.27.1; identity: FOCUSED_UI_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: c6682d3da92ae7ae41f80e62580163c169b4017cb81c83abcdbc611f8b1d7000; source-freeze: 2e6f947a43d148b44f8b7528769bfef1865ed85f -->

## Current playtest candidate: v0.27.1

The office-menu revision is unmerged, stacked on the v0.26.2 help revision.
Main remains the approved v0.24.0. [Current scope](RELEASE-v0.27.1.md) and
[native verification](office-menu-review.json) do not certify a public or
offline release. Earlier sections below are historical.

<!-- candidate-version: 0.23.1; rom-sha256: 057139801b64d1d486c91e18f456e01519dd4d25c3d0d6a92e61f311b99da3fd -->

## Historical approved walking revision: v0.23.1

The user rejected v0.23.0's torso/legs mismatch. PR #12 now replaces each
fighter's eight complete walking poses with coordinated head, guard, torso,
hip and foot motion, removing the fixed waist splice. Other 56 poses and
original portraits/palettes remain. All six suites pass 36,219 current-ROM
checks, matching independent smoke and fresh reproduction pass. The user
approved the revision and PR #12 merge on 2026-10-23 ("yes good, merge it").
Run `Play.cmd` from main to play v0.23.1.
[Current art, native clips, controls and evidence](RELEASE-v0.23.1.md). Main is
v0.23.1; 08 remains deferred. The notes below retain their historical scope.

## Rejected historical walking candidate: v0.23.0

Main is v0.22.1 with the nine approved improvements merged; feature 08 remains
deferred and its checkout is retained. The old merged branches/worktrees are
cleaned. [PR #12](https://github.com/Reston/snes-abaqus-fighter/pull/12) adds
eight-phase walking to all twelve fighters and the clearer **LOCAL 1V1 / 2P**
menu label. Local two-port multiplayer was already supported. Run `Play.cmd`
from `feature/walking-cycles-v023` to test this unmerged candidate.
All six native suites pass 36,219 current-ROM checks; independent smoke,
all-roster walking proof and fresh-source reproduction pass.
[Walking, two-player controls, art/prompts and evidence](RELEASE-v0.23.0.md).
The older notes below retain their historical scope.

## Current v0.22.1: nine approved improvements

Features 01–07, 09 and 10 are approved for main. **Feature 08 is deferred**:
the camera and ambient art are restored to v0.21.0; its branch/worktree remain
for polish. The six native suites pass 36,253 exact-ROM checks and matching
independent smoke passes. [Current release and scope](RELEASE-v0.22.1.md).
Local 1v1 already works in **Local Versus** with separate controller ports.
Walking improvements and clearer local-play discovery are the next follow-ups.
The v0.22.0 material below is historical, including its ten-feature review gallery.

## Historical v0.22.0 combined notes

The current integration candidate is **v0.22.0**, with all ten improvements
merged on `integration/ten-improvements-v022`. The [combined release guide](RELEASE-v0.22.0.md)
maps all ten feature PRs and describes the shared controls and native budgets.
Run `Play.cmd` from that checkout for review. Main remains v0.21.0 until
your combined playtest and
[PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1) merge.

The combined candidate passes 36,253 checks across all six native suites,
matching independent smoke, all ten feature proofs and preservation/bank/transfer
checks. Fresh committed source reproduces the cartridge, all 219 assets and
symbols. The [verification record](expansion-v0.22.0-verification.json) records
ROM `d4fddaf609a0c29f45353a8d9e22fe1131fc3380838d9c0073d3255474cdf8af` and source freeze `b149cdf2d9e25560f61d09a0f49e71ce6fea7042`.
These are technical results for the combined playtest.
No v0.22.0 human approval, offline ZIP or full release-scale evidence exists.
The latest full offline archive remains [v0.19.0](RELEASE-v0.19.0.md).

The single combined playtest should cover the normal roles and confirms,
hit/block readability, animation and individual gestures, Training history/
damage/drills, CPU habits and fair super commitments, all three stages,
Arcade dialogue/endings, speech and the music/effects mix. Further balance,
full listening, physical-controller, remaining likeness, team/subject consent
and public-use reviews remain open. Damian's earlier likeness approval and
v0.21.0 feedback do not approve these additions. `public_release_certified`
remains **false**. Emulator-first support remains the selected scope;
original-console/flash-cartridge support remains unverified future work.

## Historical v0.21.0 candidate

The v0.21.0 candidate is cartridge SHA256 `aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205`.
Its [release note](RELEASE-v0.21.0.md) records the focused verification scope.
All six native suites pass 33,082 checks and the matching pinned smoke passes.
The user accepted Damian v5 likeness in v0.20.0; its art is preserved here.
Human review of the four-button controls, contact shadows and new HUD is open.
Full matrix/replays, independent combat, endurance, fresh-export evidence and
an offline package remain at the historical v0.19.0 checkpoint. Human
gameplay/balance, full listening, physical controllers, remaining roster
likenesses, team/subject consent and public-use approval remain open.
`public_release_certified` is false.

## Public quality target and historical evidence

The active project goal is an original native SNES fighting game polished to a
high public-release standard, using Capcom's 16-bit arcade craft as the benchmark
for readability, responsiveness, animation and completeness. The Abaqus roster,
places and cartoon identities remain the game's own. Commercial sprites, ROMs,
music and an implication of Capcom affiliation are outside this project.

v0.9.0 is a historical verified technical snapshot, cartridge SHA256
`bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639`.
Its six native reports pass 32,182 checks. The same cartridge passes 288 native
matchup cases and four deterministic replays, three uninterrupted native
live-hour sessions, and a fresh-source rebuild reproducing 214 generated
assets. Pinned bsnes2014 Accuracy smoke and 48 bounded combat cases provide
second-engine evidence; their scope is recorded in
[COMPATIBILITY.md](COMPATIBILITY.md).
The snapshot corrects selection portrait framing, arena layout and opaque
HUD/result text, and revises Damian's 64-frame likeness under a pinned
per-fighter contract. The other eleven fighters' native bank bytes, and every
fighter's palette and physical scale, are retained. Reston's earlier short-hair
revision remains intact.
Passing these suites is necessary evidence, not a claim that the public-release
bar has been met.
The stricter matchup and uninterrupted-session probes exposed frame overruns
missed by the shorter baseline suites. Bounded native rendering, interface
updates and resident-audio dispatch close those observed failures in v0.7.1.
The public candidate will be designated v1.0 only after the gates below close.
Do not turn a passing check count into a substitute for visual or play review.

The user has since selected **emulators first; hardware support stays
unverified** for the first public release. Original SNES/flash-cartridge
support is future validation, outside that selected first-release scope.
Physical controller and human play sessions still need results. A short audio
replay was heard with no issue noticed; full listening remains open. Gameplay
was playtested in v0.8.1 and revealed portrait, Damian likeness, arena and text
legibility defects. v0.9 addresses those findings; the revised build and combat
feel still need human feedback. These updates do not certify the public release.

The v0.8.0 snapshot adds native pause move guides and selectable Training
dummies. SELECT opens controls and the live fighters' special moves; Training
offers Stand, Guard High, Guard Low and repeated Jump. Opposite pause directions
resolve to neutral across both controllers. Pausing after contact refreshes the
actual health bars without advancing combat. The new sixth native suite,
`tools/test_training.py`, passes alongside the original five suites and is
required before packaging. That snapshot's native reports identify the exact v0.9.0
cartridge; preceding snapshots remain historical.

## Release gates

The baseline-status column below retains the historical v0.9.0 gate assessment.
It does not report v0.22.0 results. Current combined verification and human
review remain pending as described above; the latest full offline evidence is
v0.19.0. New supers, Training tools, CPU choices, stage scroll, story and sound
must be reviewed together before this candidate advances.

| Gate | Required evidence | Baseline status |
| --- | --- | --- |
| Native correctness | Reproducible cartridge, valid header/checksum, all six exact-ROM suites, no known critical/high defects | v0.9 six-suite reports, expanded technical evidence and isolated rebuild pass; no known critical/high defect in the verified scopes |
| Fighter identity and animation | All twelve likenesses reviewed at native size; stable anatomy, costume, palette and floor pivot; readable ground, air, throw, hit, downed and wake sequences in both directions | All 64-frame sets present with native motion captures; geometry and visual continuity review found no clipping/scale defect. Reston v4's fuller short buzz cap is accepted for integration; team likeness and human motion approval remain pending |
| Combat agreement | Visible active attacks match contact and hurt regions; coherent guard, trade, facing, corner, cancel, throw and wake rules; no repeatable uncontrolled damage or input exploits | Controller-driven air/throw/down/wake and guard regressions present; human matchup/contact review pending |
| Balance and CPU | Documented profile envelope; scripted all-pair matchup sweep; CPU approaches, defends and punishes predictably by difficulty; human sessions cover every fighter and all four special families | Profile envelope, bounded CPU probes and 144 ordered pairs under two policies pass; strategic CPU and human balance review pending |
| Stage and interface craft | Three readable locations with finished floor/depth, purposeful ambient motion and cohesive effects; clean selection, pause, results and champion flow; no obstructive instructions | v0.9 fixes the live-review portrait, arena and text defects with native PPU regressions; revised human presentation and ending review pending |
| Audio | Original or cleared assets, readable distinct cues, coherent levels, clean loops, no clipping/dropouts under load; listening review recorded | Original audio and captured-sample checks present; user heard the short title/impact/special preview with no issue noticed. Full score/cue and busy-exchange listening remains pending |
| Player experience | Both player layouts work from a fresh package; quick onboarding and accessible move guidance; useful, deterministic Training; clear pause/rematch/reset paths | v0.8 two-page move guide, four deterministic dummy choices and frozen truthful HUD pass native controller/PPU regressions; human onboarding and fresh-package play review pending |
| Compatibility and endurance | Same release candidate validated in at least two independent SNES engines; worst-case cadence/upload checks and at least one emulated hour per mode without softlocks or corrupt output | Native six-suite/matchup gates, one live hour in each native mode, and bsnes2014 Accuracy smoke plus 48 combat cases pass. Independent full ordered-pair/hour coverage remains outside this evidence. Emulator-first release scope is recorded; user compatibility acceptance remains pending |
| Controller and console checks | Recorded two-controller play sessions; real-console/flash-cartridge result or an explicit release-platform decision | Emulator-first decision recorded; original hardware support stays unverified future work. Human two-controller sessions still need results |
| Distribution | Fresh-checkout build and offline ZIP verified; current guide/credits/licenses; complete source provenance; recorded team approval for public branding and roster use | Current isolated source rebuild and v0.9 archive audit pass. Human package review and public approval remain open |

For the code freeze, critical/high defects must be closed. Other known issues
need a recorded disposition, owner and rationale; unspecified "polish later"
does not close a gate. Optional features may be deferred when the existing
player-facing behavior is finished and the decision is explicit.

## Milestones

1. **Air attacks, throws and recovery.** Separate the aerial visual path from
   planted normals. Give throws distinct attacker/victim feedback and implement
   bounded downed/wake states. v0.6 implements the 64-frame sets and native
   controller regressions; human motion review remains open.
   [COMBAT-ANIMATION-CONTRACT.md](COMBAT-ANIMATION-CONTRACT.md) defines the rules.
2. **Combat and opponent quality.** Align contact with the finished drawings,
   review profile envelopes and meter/throw/cancel behavior, improve active-window
   defense and anti-air decisions, and add reproducible matchup/Training probes.
   [BALANCE-AUDIT-v0.6.md](BALANCE-AUDIT-v0.6.md) records the current profile
   envelope and the original CPU spacing, special-family, low-guard and wake
   findings. v0.6.1 closes those bounded correctness cases; strategic defense,
   matchup balance and human review remain open.
3. **Presentation and audio finish.** Review every fighter in motion; add staged
   ambient life and effects within the hardware budget; finish onboarding,
   Training information, audio mix/loops and champion presentation.
   v0.7 adds the first BG1 ambient layer, distinct effects and a measured OBJ
   overflow fix. v0.8 adds move guidance and selectable Training behavior;
   visual/listening review and deeper presentation remain open.
4. **Release candidate.** Freeze features, complete independent-engine and soak
   coverage, prepare human playtest/controller evidence and team review, close
   defects, then reproduce and verify the final public package.

Phases can overlap where ownership is clear. A new illustration or passing ROM
build alone does not complete a milestone: runtime behavior, native captures,
controller probes and regression evidence must agree.

## Evidence and working rules

- Run `tools/audit_release.py` after the six suites and package generation to
  summarize the current technical baseline in `release-audit.json`. The audit
  deliberately does not certify the qualitative and human gates above.
- Keep every report tied to the current cartridge hash. Maintain native review
  captures and reproducible controller sequences for defects.
- The expanded development-package gate requires the full native ordered-pair
  report (144 pairs under two policies, 288 cases), the separate pinned bsnes
  combat report (48 cases, 28,800 frames), the three native uninterrupted
  per-mode hour sessions, and the isolated committed-source rebuild. The
  independent combat report is bounded second-engine evidence; it is neither
  an independent full ordered-pair matrix nor an independent hour-per-mode soak.
  These reports close only their recorded technical scopes. They do not close
  the human likeness, balance, listening, controller, physical-console or
  public branding/roster approval gates.
- Freeze the cartridge inputs in Git before the fresh-source build. Record its
  source commit and tree; package validation rejects changes to those inputs
  after that commit. Documentation, report and package-output commits may
  follow without changing the cartridge source freeze.
- Include an explicit OBJ scanline-budget probe before the public candidate:
  both fighters, both low projectiles, floor shadows and hit effects must be
  reviewed together, with PPU overflow evidence rather than idle-only captures.
  v0.7 records the fixed-cartridge result in [OBJ-BUDGET.md](OBJ-BUDGET.md);
  repeat it when sprite allocation or effects change.
- Preserve original masters, full prompts, generation provenance and licenses.
  Refine source art when it fails the physical-scale contract; do not hide a
  mismatch by resizing an individual move.
- Automated work stays silent/headless. Authorized live emulator review stays
  muted. Do not publish or send files to other people as a substitute for
  preparing a concrete reviewable candidate.
- Human feedback, equipment results and public-use approval must be recorded
  from actual responses. They cannot be inferred from automated results.
