# v0.24 readable combat: shared implementation contract

Approved scope: slower, more readable combat and stronger backward hit recoil,
plus attack art, contact accuracy, stage depth, jumps/landings and dedicated
super art. Proposals6–10 are excluded. Final integration remains unmerged for
one combined human playtest. Baseline main is f75005d (v0.23.1), cartridge
057139801b64d1d486c91e18f456e01519dd4d25c3d0d6a92e61f311b99da3fd.

## Ownership and PRs

Six feature PRs target `integration/readable-combat-v024`, followed by its one
final PR into main. Each child works in its assigned T3 worktree and commits
only its production module/source art and focused test/report/captures. Do not
commit local dist outputs, shared six-suite reports, version/release documents,
global preservation policy or other owners' files. Parent owns those files and
integration conflicts. Keep full art prompts/provenance, including raw output
and selected source hashes. Use the built-in imagegen skill for new art.

1. Pacing/recoil: characters.h movement/timing values, cpu_personality.h
   reaction cadence, a dedicated pacing/recoil module and narrow game.c hooks.
   Keep jumps/gravity unchanged (jump owner). Keep reach/damage unchanged unless
   a demonstrated combo/fairness defect requires coordination with parent.
2. Attack art: `assets/art/attack-v1.json`, per-fighter versioned attack sources,
   src/animation_weight.h grounded attack/hurt/guard branches only. Full body,
   coordinated support foot/hip/shoulder/guard; no limb splice. Contact owner
   reads the resulting raster geometry; root integrates shared hook conflicts.
3. Contacts: src/contact_geometry.h and bounded game.c canHit/verticalContact
   changes, with independent renderer/geometry diagnostics and both-port proofs.
   Do not edit characters.h. Derive/refresh geometry against final art before
   final combined proof. Include fair hurt regions; avoid per-pixel hit jitter.
4. Stages: versioned stage source art, bounded native stage-depth module and
   stage generator. Rebuild from CURRENT baseline, using old08 only as reference.
   Preserve floor/feet alignment and UI; no architectural objects split by
   moving bands. Prototype one stage before completing all3. Declare every
   new/changed generated file and VRAM/CGRAM/HDMA allocation explicitly.
5. Jumps: `assets/art/jump-v1.json`, per-fighter versioned jump sources,
   src/animation_weight.h airborne/landing branches and character jump physics
   only if needed. Coordinate full body and held guard, genuine apex/descent,
   grounded compression. Keep four-button air attacks/cross-ups reliable.
6. Supers: `assets/art/super-v1.json`, per-fighter versioned super sources,
   superFrame mapping only in src/super_moves.h. Distinct charge/contact/recovery
   drawing for each fighter's super family; keep super gameplay/energy unchanged.

## Exact native frame ownership (64 frames, no extra pose banks)

- Preserve all approved walking frames20–27, idle16–19 and source portraits.
- Attack: frames5,6,7,8,9,10,12,13,15,32–45,47 (24 targets).
- Jump: frames29,30,31,49–55 (10 targets).
- Super: frames1,2,4 (3 dedicated targets). These legacy walk/jump slots are
  absent from animateFighter's ordinary selection and intro/victory tables.
  Keep legacy0 as standing identity/portrait anchor. Parent will audit every
  runtime selection and shared fixture before final integration.
- Preserve28 crouch,11/46 victory,14 floor,48/56–63 throw/down/get-up drawings.
  The new request authorizes the targeted combat/jump revisions; old masters,
  baseline/revision pins, portraits and fixed15-color palettes remain exact.
- One isotropic conversion per fighter/feature source set, anchored to a
  neutral standing figure in that source set. No per-frame body resizing.
  Fit96x80, safe94x77, sole baseline78, approved standing-height targets.

## Common art manifest schema

Parent's fighter_assets hook applies optional attack/jump/super indices after
the immutable baseline checks and approved walking overlay. Each index has
schema1, scope `attack-v1` / `jump-v1` / `super-v1`, baseline_commit, and exactly
12 fighters with id, slug (`00-damian` etc), provenance and provenance_sha256.
Each individual provenance record has fighter_id, scope, reference and its
reference_sha256, palette_sha256, generation mode, prompt(s), sources and anchor.
Sources: list of {file, sha256, count:8|16, poses:[names], frames:[nativeID|null]}.
All generated silhouettes must be full figures. `anchor` is {source:0,pose:0}
(or another chosen neutral figure). Source neutral may map to null. Optional
`height_target` must equal the approved standing height. Index's scope owns
exactly the target set above; every target occurs exactly once. Extraction and
native quantization use tools/pose_revision_assets.py. Retain selected source
PNGs in each fighter's directory and every exact prompt/source/reference hash.

## Runtime and validation

Keep native60Hz rendering and controller sampling, full audio cadence and
menu/clock speed. Prototype roughly15–20% slower walking/projectiles, longer
heavy telegraphs/recoveries and fallible CPU reactions. Jabs remain distinct.
Scale projectile life to preserve intended travel range. Hit and block recoil
must use latched CONTACT side (including cross-ups/trades), readable hurt pose,
bounded easing, light/strong/guard separation, corner clamps and no stun loops.
Prove legal confirms and block/punish opportunities after timing/recoil changes.

Fighter64, Wave16, TRACE0..122 and controller commands stay ABI-stable. Keep
one3840-byte actor DMA/vblank,30 16x16 OBJ per actor, existing HUD/guide budget,
32KiB bank boundaries and native overflow checks. Prefer no added mutable RAM.
Pacing may propose up to8 appended bytes after all existing initialized state;
declare exact symbols/order, do not insert before prior state. Stage should
reuse its16 reserved bytes. Other streams add no mutable state without parent
coordination. No foreground changes or speaker audio during automated tests.

Each feature supplies a focused silent/headless native proof and small visual
before/after clips. Use tools/run_background.py and canonical local Python;
measure consecutive live ticks/OBJ/transfer/audio health, both ports and roster
coverage. Parent owns final six suites, matching pinned Accuracy smoke, combined
focused reruns, fresh committed-source export, review gallery and final SHA.
Isolated proofs are historical until regenerated on the final combined ROM.
