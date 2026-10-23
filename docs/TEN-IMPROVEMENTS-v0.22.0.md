# Ten improvements integration

The user authorized all ten improvements in separate worktrees and pull requests,
then one combined PR for testing. Integration starts at main 38519cd. Feature PRs
target integration/ten-improvements-v022. The final integration PR targets main.
Version 0.22.0 is reserved for the combined candidate. This is work in progress;
no current-ROM test or release claim is made by this plan.

## Feature contracts

1. Animation weight: improve transitions, anticipation, recovery, landings and
   knockdown presentation using existing approved frames and physical scale.
2. Impact feedback: readable light/strong/block distinctions in native effects,
   hitstop and restrained shake, preserving OAM and transfer limits.
3. Four-button balance: useful light/strong punch/kick roles, reach/recovery/damage
   tuning and meaningful controller-driven balance evidence for all twelve.
4. Fighter personality: twelve individual intro/victory pose sequences and
   signature presentation details, preserving approved identity art.
5. Training tools: native input history, combo/damage feedback and executable
   practice challenges, accessible without consuming attack/shoulder controls.
6. CPU personalities: readable per-character aggressive/defensive/counter habits,
   retaining fair sampled reactions and difficulty differences.
7. Supers: a distinct named full-gauge super for all twelve, face-button command,
   real energy cost, valid hit/block/whiff and no extra attack buttons.
8. Stage depth: bounded native parallax plus richer ambient action and victory
   reactions in all three stages, retaining stage identities and safe HUD.
9. Personal Arcade: short matchup exchanges, rivalries, individual winner quotes
   and character-specific champion endings with ordinary progression intact.
10. Sound presentation: differentiated resident hits/blocks, musical transitions
    and original short Round/Fight/KO announcements, with silent capture proofs.

## Shared integration rules

Read AGENTS.md and docs/DEVELOPMENT.md. Preserve Fighter64/Wave16 and existing
TRACE 0..122 offsets. New state must be explicit, bounded and audited; do not
insert fields into either ABI. Preserve approved Damian v5, all retained art
masters/prompts and individual fighter scale/palettes. No commercial game assets.
Keep actor-per-vblank, palette, tile, 32 KiB bank, OBJ fetch and SPC limits.
Four face buttons attack; L/R retain Training level controls. Existing menu/pause
and dummy priority must remain. Add feature-specific modules where practical;
keep game.c hooks small so ten branches can integrate cleanly. No placeholders,
web simulations, documentation-only substitutes or tests that bypass gameplay.

Each branch owns its focused test driver, evidence and feature guide. Do not edit
shared six-suite report JSONs, global version/AGENTS/README, or full release docs.
Parent resolves shared tests and generates all six current-ROM reports plus
independent smoke and combined feature evidence after all merges. Full offline
packaging remains separate unless its complete extended gates are regenerated.

Feature PRs are merged only into the integration branch. Main remains available
as the approved v0.21 baseline until the user tests the final combined PR.
