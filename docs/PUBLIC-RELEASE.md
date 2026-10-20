# Public-release quality target

The active project goal is an original native SNES fighting game polished to a
high public-release standard, using Capcom's 16-bit arcade craft as the benchmark
for readability, responsiveness, animation and completeness. The Abaqus roster,
places and cartoon identities remain the game's own. Commercial sprites, ROMs,
music and an implication of Capcom affiliation are outside this project.

v0.6.1 is the current verified development baseline. Its four native suites
cover the 64-frame roster, air attacks, throws, knockdown, wake and bounded CPU
policy. A separate bsnes2014 Accuracy smoke check covers basic independent-engine
operation; its scope is recorded in [COMPATIBILITY.md](COMPATIBILITY.md).
Passing these suites is necessary evidence, not a claim that the public-release
bar has been met.
The public candidate will be designated v1.0 only after the gates below close.
Do not turn a passing check count into a substitute for visual or play review.

## Release gates

| Gate | Required evidence | Baseline status |
| --- | --- | --- |
| Native correctness | Reproducible cartridge, valid header/checksum, all four exact-ROM suites, no known critical/high defects | Automated baseline verified; expand regression coverage as features land |
| Fighter identity and animation | All twelve likenesses reviewed at native size; stable anatomy, costume, palette and floor pivot; readable ground, air, throw, hit, downed and wake sequences in both directions | All 64-frame sets present with native motion captures; team likeness and human motion review pending |
| Combat agreement | Visible active attacks match contact and hurt regions; coherent guard, trade, facing, corner, cancel, throw and wake rules; no repeatable uncontrolled damage or input exploits | Controller-driven air/throw/down/wake and guard regressions present; human matchup/contact review pending |
| Balance and CPU | Documented profile envelope; scripted all-pair matchup sweep; CPU approaches, defends and punishes predictably by difficulty; human sessions cover every fighter and all four special families | Profile envelope, bounded policy and three-difficulty/four-family probes present; strategic CPU, all-pair and human balance review pending |
| Stage and interface craft | Three readable locations with finished floor/depth, purposeful ambient motion and cohesive effects; clean selection, pause, results and champion flow; no obstructive instructions | Menus/floor/results improved; stage motion, effects and ending review pending |
| Audio | Original or cleared assets, readable distinct cues, coherent levels, clean loops, no clipping/dropouts under load; listening review recorded | Original audio and captured-sample checks present; mix/listening review pending |
| Player experience | Both player layouts work from a fresh package; quick onboarding and accessible move guidance; useful, deterministic Training; clear pause/rematch/reset paths | Basic modes and controls work; onboarding and Training depth pending |
| Compatibility and endurance | Same release candidate validated in at least two independent SNES engines; worst-case cadence/upload checks and at least one emulated hour per mode without softlocks or corrupt output | Snes9x canonical suites and bsnes2014 Accuracy basic smoke present; second-engine combat/roster and endurance matrix pending |
| Controller and console checks | Recorded two-controller play sessions; real-console/flash-cartridge result or an explicit release-platform decision | Requires human equipment/play sessions; not yet verified |
| Distribution | Fresh-checkout build and offline ZIP verified; current guide/credits/licenses; complete source provenance; recorded team approval for public branding and roster use | Development packaging/provenance present; public approval and final package review pending |

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
   envelope and concrete CPU spacing, special-family, low-guard and wake gaps.
3. **Presentation and audio finish.** Review every fighter in motion; add staged
   ambient life and effects within the hardware budget; finish onboarding,
   Training information, audio mix/loops and champion presentation.
4. **Release candidate.** Freeze features, complete independent-engine and soak
   coverage, prepare human playtest/controller evidence and team review, close
   defects, then reproduce and verify the final public package.

Phases can overlap where ownership is clear. A new illustration or passing ROM
build alone does not complete a milestone: runtime behavior, native captures,
controller probes and regression evidence must agree.

## Evidence and working rules

- Run `tools/audit_release.py` after the four suites and package generation to
  summarize the current technical baseline in `release-audit.json`. The audit
  deliberately does not certify the qualitative and human gates above.
- Keep every report tied to the current cartridge hash. Maintain native review
  captures and reproducible controller sequences for defects.
- Include an explicit OBJ scanline-budget probe before the public candidate:
  both fighters, both low projectiles, floor shadows and hit effects must be
  reviewed together, with PPU overflow evidence rather than idle-only captures.
- Preserve original masters, full prompts, generation provenance and licenses.
  Refine source art when it fails the physical-scale contract; do not hide a
  mismatch by resizing an individual move.
- Automated work stays silent/headless. Authorized live emulator review stays
  muted. Do not publish or send files to other people as a substitute for
  preparing a concrete reviewable candidate.
- Human feedback, equipment results and public-use approval must be recorded
  from actual responses. They cannot be inferred from automated results.
