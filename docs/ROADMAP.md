# Polish roadmap

The v0.1 release established a playable native cartridge, the requested roster and locations, a reproducible toolchain and emulator-based integration coverage. The v0.2 pass added the cartoon arcade direction. The v0.3 pass introduced twelve individual sixteen-pose atlases and likeness correction. The v0.4.0 pass moves the cartridge to 2 MiB FastROM LoROM, standardizes all fighters on one 96×80 physical scale, adds 32×40 and 64×80 source portraits, redraws the home/select/arena presentation and separates the three stage masters.

## Future art and animation

- Review the seven v0.4 likeness v2 edits and the five retained v2 masters with the team, making targeted identity revisions only where human review finds a mismatch.
- Add in-between idle, walk, landing, recovery, throw and knockout frames beyond the current sixteen-key-pose contract.
- Align hands and feet more closely to gameplay contact points and add per-pose hitboxes.
- Extend the three independent stage compositions with layered parallax and animated coworkers while preserving the native tile and vblank budgets.
- Add a dedicated champion illustration and richer end-of-match presentation beyond the current large selection portraits.

## Next combat pass

- Extend the current four special families with individual effect art, command variations and additional moves.
- Tune frame data, reach, damage, push boxes, jump arcs, throw ranges and meter gain through human playtesting.
- Add input buffering, more reliable command priority, training hitbox display and frame-step tools.
- Improve CPU spacing, anti-air behavior, defensive variety and difficulty progression.
- Add player-selected round length, training reset and more rematch options.

## Release-quality validation

- Run the gameplay, roster and presentation suites against the exact current 2 MiB ROM; each report must retain that ROM's SHA256 before packaging.
- Playtest with two controllers and several keyboard layouts, including keyboard rollover constraints.
- Profile worst-case combat frames, audio streaming and vblank use across Snes9x, Mesen and bsnes.
- Test an original SNES or Super Famicom through a flash cartridge.
- Record regression movies, verify every arcade ending, and run longer stability sessions.
- Create distinct stage compositions, richer hit sounds and an original announcer voice.
- Review branding/portrait usage with the team before a public release.

Commercial fighting-game polish requires repeated art, animation, audio, balance and QA passes. The project is organized so those passes can be reviewed and versioned without replacing the native engine.
