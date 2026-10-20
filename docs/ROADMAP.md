# Polish roadmap

The v0.1 release established a playable native cartridge, the requested roster and locations, a reproducible toolchain and emulator-based integration coverage. The v0.2 pass set the cartoon arcade direction. v0.3 introduced twelve individual sixteen-pose atlases and likeness correction. v0.4 standardized the 96x80 physical scale and rebuilt the presentation. v0.5.0 adds animation, simpler menus and buffered inputs. v0.5.1 tightens contact, hit-confirm and combo rules, clears live-fight instructions, adds result scores and corrects emulator scaling. Four silent suites verify the current native ROM.

## v0.5.0 integration pass

The current pass adds the following source and asset contracts:

- The target cartridge is a 4 MiB NTSC FastROM LoROM image across 128 banks.
- Every fighter has 48 uniform 96x80 frames. Legacy frames 0-15 are followed by 16 motion/transition frames and 16 action frames, for 576 native frames across the 12-fighter roster.
- Twenty-four built-in imagegen animation atlases provide 32 new drawn in-between frames for each fighter. Each new atlas is normalized once against the existing neutral idle, then shares one physical scale across all 48 frames. The original identity masters remain unchanged, including Reston's v3 short-hair correction.
- Native frame data is divided into six 30,720-byte banks per fighter, with a shared fifteen-color OBJ palette and 4,608x80 native review strip for each 48-frame set.
- Per-fighter animation clocks use distance for forward/backward gait and cover idle, forward, backward, crouch, jump, landing, attack windup/active/recovery, guard, hurt, victory and knockout. Pause and hitstop freeze the clock.
- The input path adds six-tick attack/jump buffering, held-Up landing autojump, opposite-axis neutralization, a twelve-tick Down -> Down+Forward -> Forward punch motion and hit-confirm normal/special cancels. The legacy Down+P shortcut remains available; Down+Back+P is not a special.
- Guard stun is eight simulation ticks with about one pixel of blocked pushback; real hits use about two pixels. Training exposes a Select quick reset.
- Home, fighter select and arena menus use a minimal royal-navy, white and gold layout with one cursor, the four-by-three roster grid and the selected large portrait. The old profile statistics/family panel is removed from the visual hierarchy.

These changes preserve the native emulator requirement and the fixed actor canvas. The new air attack path still uses a legacy key pose plus a generic transition frame; dedicated air-specific art is future work.

## Future art and animation

- Add more unique in-between drawings for character-specific weight, footwork, air attacks, throws and knockdowns after human review of the v0.5 motion sets.
- Align hands and feet more closely to gameplay contact points and add per-pose hitboxes.
- Extend the three independent stage compositions with layered parallax and animated coworkers while preserving the native tile, OBJ and vblank budgets.
- Add a dedicated champion illustration and richer end-of-match presentation beyond the current large selection portraits.

## Next combat pass

- Tune frame data, reach, damage, push boxes, jump arcs, throw ranges and meter gain through human playtesting. The v0.5 values are an integration baseline, not a balance conclusion.
- Improve CPU spacing, anti-air behavior, defensive variety and difficulty progression.
- Add training hitbox display, frame-step tools, command history and more rematch options.
- Extend the four special families with individual effect art, command variations and additional moves.
- Review aerial normal collision and the generic transition art once dedicated air illustrations are available.

## Release-quality validation

- Keep running the gameplay, roster, presentation and focused input suites after changes. The four reports must retain the exact current ROM's SHA256 before packaging; v0.5.1 passes all four.
- Playtest with two controllers and several keyboard layouts, including keyboard rollover constraints, SOCD edge cases, motion buffering and hitstop inputs.
- Profile worst-case combat frames, six-bank animation uploads, audio streaming and vblank use across Snes9x, Mesen and bsnes.
- Test an original SNES or Super Famicom through a flash cartridge. Real-console and flash-cartridge testing have not yet been performed.
- Record regression movies, verify every arcade ending and run longer stability sessions.
- Review branding and portrait usage with the team before a public release.

Commercial fighting-game polish requires repeated art, animation, audio, balance and QA passes. The project is organized so those passes can be reviewed and versioned without replacing the native engine.
