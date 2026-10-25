# Six improvements for v0.29

The user authorized one implementation subagent per topic, then combined
verification and merge for a single playtest. The approved baseline is main
commit c7510c30e129465bcca0b32e2142daec60546d0f, native v0.28.0 ROM
09eaa47ddc12d419e259f1330eb225f1e56f75d42efdd2faf5c27063f8f2357c.
The integration branch is integration/six-improvements-v029. Main stays on
the approved baseline until all six are combined and tested.

## Feature ownership

1. Defense: bounded timed throw escapes and fair knockdown recovery.
2. Office bonus rounds: short playable challenges between Arcade fights.
3. Automatic start: remove redundant launch/intro confirmation, retain
   deliberate mode/fighter/arena selection and normal pause ownership.
4. Random selection: discoverable random fighter/arena picks, both ports.
5. Audio: better original music/contact sounds and independent music,
   effects and announcer levels in the native game and browser player.
6. Arenas: original animated spectators/environment and event reactions.

Each child owns new feature-prefixed headers, tools, art and focused evidence.
Small integration hooks in game.c, shared generators and guide code are
permitted and must be recorded for the parent. Children must not rewrite
README, AGENTS, version, release summaries, shared tests or root reports.
The parent owns combined conflicts, source freeze, final generated outputs,
dist, six-suite evidence, integration/release docs and final main merge.
Feature PRs target the integration branch; never merge main from a child.

## Native constraints

The authoritative deliverable remains the 4 MiB NTSC FastROM LoROM cartridge.
Preserve approved slower combat except the specific defensive changes;
native video/input/audio cadence, Fighter64/Wave16/TRACE ABI, all prior WRAM
variable/data addresses, hardware/trace assembly instructions, fighter art,
portraits/likenesses/scales, current menu identity and detailed stage floors.
No imported commercial game assets, emulator slowdowns or dropped ticks.
No rejected band parallax or blank-floor conversion.

New art is original built-in imagegen with saved prompts, source/output hashes
and references. Deterministic native palette/tile conversion is expected.
Retain old masters and historical audio. Music replacement/new cues are
authorized for feature 5; preserve cues' semantic hooks and bounded resident
SPC scheduling. Bank24 and every LoROM section must remain below 32 KiB.

The old ambient destination $3C00 is now the right half of BG1's 64x32 map:
never restore that unsafe DMA. Stage animation must prove its actual reserved
tile addresses, palette ownership and queued transfers; yield to actors/UI.
Actor uploads remain at most one 3840-byte pose per vblank. Prove OBJ budgets
and no added native lag on both pinned cores, especially combined supers.

## State reservations

expansion29.h declares six explicitly initialized arrays, defined only in
expansion29_state.h after existing menu-preview state at game.c's bottom:
Defense 16 bytes; Bonus 64; Auto 8; Random 8; Audio 32; Arenas 48.
Use only the assigned reservation; no independent mutable global definition.
Do not edit these shared headers without parent coordination. Clear only the
feature's own state as needed. Existing SDK variables must not move.

Scene value 5 is reserved for BONUS. Preserve TITLE0/SELECT1/ARENA2/FIGHT3/
RESULT4 and mode Arcade0/Local1/Training2. Shared pause priority stays
Start > B > A > Select; Training reset and guide routes remain intact.
Random selection uses fresh SELECT on roster/arena (both participating pads),
with a visible short hint; no new attack button or changed combat input.
Audio adds a compact native sound page while retaining existing guide routes;
coordinate page numbers during parent integration. Preferences reset on cold
boot and persist across matches; saving/account systems are outside scope.

Bonus results return automatically to the correct next Arcade opponent;
short optional skip never loses ladder progress or blocks the ending.
Bonus art/runtime is separate from combat arena animation. Arena reactions
consume existing visible hit/super/KO events without changing gameplay/RNG.

## Focused delivery and host use

Each child compiles and runs meaningful controller-only/headless proofs on
its actual ROM, both ports/all relevant fighters/stages and pinned Accuracy
cases. Do not mutate WRAM, use save states, normalize failures away or loosen
native cadence/SDK/OBJ/SPC checks. Old fixtures may be adapted with measured
explanations. Reports bind exact ROM, source/harness/dependency hashes.
Feature-only preservation is not a claim about the later combined ROM.

Keep build/diagnostics ignored. Do not commit generated assets/dist in child
PRs; retain their exact tested copies under ignored build and restore tracked
generated/dist before final commit. Own focused reports/captures may commit.
Return branch/head/PR, commands, counts, known limits, changed files and hook
notes. Parent reruns final combined evidence after freeze.

Use .tools/python/python.exe and tools/build.py in each worktree. A shared
.tools junction is a read-only cache while other native jobs run: do not run
setup/download/replacement against shared SDK/core/Python. Native jobs must be
silent/headless, below-normal, on assigned logical processor pairs: Defense
2/3; Bonus4/5; Auto6/7; Random8/9; Audio10/11; Arenas12/13. Parent uses14/15.
Set wrapper affinity before tools/run_background.py, which inherits that pair.
Keep progress/log publication robust to readers; final reports publish once.
No self-imposed multi-hour matrices for isolated changes; bound focused proofs
to meaningful requirements, then return for parent integration.
