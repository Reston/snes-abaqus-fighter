# v0.23.1 — coordinated full-body walking
<!-- candidate-version: 0.23.1; rom-sha256: 057139801b64d1d486c91e18f456e01519dd4d25c3d0d6a92e61f311b99da3fd -->

The user rejected v0.23.0: “ok the legs animation improved but know the top
part doesn't fit so this wasn't the goal”. That version preserved the old
upper body and pasted new legs below it. The fixed waist join was the wrong
constraint for the requested walk. It is retained as rejected history.

v0.23.1 replaces the complete eight walking poses for each of the twelve
fighters. Head, shoulders, guarded arms, torso, hips and legs are authored as
one figure in each pose. Hips transfer weight, the torso responds to the step,
and both fists stay in guard. The importer fits each entire body with one
shared isotropic scale for its whole cycle; it performs no waist splice or
fixed upper-body overlay. The original standing-height target and foot
baseline remain. The source faces and costumes guide the new walking art;
the walking face pixels are newly drawn, so likeness review remains open.

Only native poses 20–27 change. All other 56 poses, portraits, original OBJ
palettes, static stages, audio and gameplay timing are preserved. Forward and
retreat still share the existing distance-driven 32-pixel step cycle; no RAM,
DMA, actor/OBJ or audio resources are added. The total generated inventory
remains 219, with the same bounded 37 walking outputs changed from v0.22.1.
The earlier leg-only sources and all approved identity masters remain retained.

Each fighter has an individual built-in-imagegen `walking-v2.png` and adjacent
exact-prompt/reference/hash record. [All twelve art and prompt records](../assets/art/walking-v2.json)
identify their selected sources. [Native walking review](WALKING-REVIEW-v0.23.1.html)
includes enlarged pose loops and real-ROM before/after clips against the
rejected v0.23.0 candidate. Pose-loop timing is slowed for inspection; human
judgment of the complete movement remains the acceptance gate.

PR [#12](https://github.com/Reston/snes-abaqus-fighter/pull/12) remains unmerged.
Run [Play.cmd](../Play.cmd) from `feature/walking-cycles-v023` to test this
native cartridge. Main remains the approved nine-feature v0.22.1; 08 stays
deferred in its retained branch/worktree. Local 1v1 remains available through
**LOCAL 1V1 / 2P** with independent native controller ports.

Verification of ROM `057139801b64d1d486c91e18f456e01519dd4d25c3d0d6a92e61f311b99da3fd`, header `F95B`:

- All six native suites pass 36,219 exact-ROM checks; the matching pinned
  independent Accuracy smoke passes.
- The all-twelve/both-port walking and local-play proof passes 3,914
  checks, including whole-body source scope, continuous silhouettes, changing
  upper poses, grounded feet, forward/retreat, pause and independent attacks.
  Non-frame native combat telemetry matches v0.22.1.
- A fresh export of committed source `cd9b9ffcbbff68c14c1e15c0bc2264a713badcea` reproduces the ROM,
  all 219 generated outputs and normalized symbols. Authoring mutations pass
  20 normal + 20 optimized checks.

[Verification](verification-v0.23.1.json) · [Focused proof](walking-report.json)
· [Preservation](expansion-preservation-v0.23.1.json).
Automated results do not establish visual approval. The corrected full-body
walking and likeness still need the user's review. No new offline package,
physical-controller certification or public-use approval is claimed.
