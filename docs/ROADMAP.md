# Polish roadmap

The active public-release target and evidence gates are in
[PUBLIC-RELEASE.md](PUBLIC-RELEASE.md). Treat this roadmap as the work backlog;
the release gates decide when the public candidate is actually ready.

The v0.1 release established a playable native cartridge, the requested roster and locations, a reproducible toolchain and emulator-based integration coverage. The v0.2 pass set the cartoon arcade direction. v0.3 introduced twelve individual sixteen-pose atlases and likeness correction. v0.4 standardized the 96x80 physical scale and rebuilt the presentation. v0.5.0 adds animation, simpler menus and buffered inputs. v0.5.1 tightens contact, hit-confirm and combo rules, clears live-fight instructions, adds result scores and corrects emulator scaling. The v0.6.0 source integration adds the final airborne, throw, knockdown and wake frame range and combat flow; the canonical silent batch now passes on one ROM SHA, with public gates still open.

## v0.5 baseline

The v0.5 baseline added the following source and asset contracts:

- The target cartridge is a 4 MiB NTSC FastROM LoROM image across 128 banks.
- Every fighter has 48 uniform 96x80 frames. Legacy frames 0-15 are followed by 16 motion/transition frames and 16 action frames, for 576 native frames across the 12-fighter roster.
- Twenty-four built-in imagegen animation atlases provide 32 new drawn in-between frames for each fighter. Each new atlas is normalized once against the existing neutral idle, then shares one physical scale across all 48 frames. The original identity masters remain unchanged, including Reston's v3 short-hair correction.
- Native frame data is divided into six 30,720-byte banks per fighter, with a shared fifteen-color OBJ palette and 4,608x80 native review strip for each 48-frame set.
- Per-fighter animation clocks use distance for forward/backward gait and cover idle, forward, backward, crouch, jump, landing, attack windup/active/recovery, guard, hurt, victory and knockout. Pause and hitstop freeze the clock.
- The input path adds six-tick attack/jump buffering, held-Up landing autojump, opposite-axis neutralization, a twelve-tick Down -> Down+Forward -> Forward punch motion and hit-confirm normal/special cancels. The legacy Down+P shortcut remains available; Down+Back+P is not a special.
- Guard stun is eight simulation ticks with about one pixel of blocked pushback; real hits use about two pixels. Training exposes a Select quick reset.
- Home, fighter select and arena menus use a minimal royal-navy, white and gold layout with one cursor, the four-by-three roster grid and the selected large portrait. The old profile statistics/family panel is removed from the visual hierarchy.

These changes preserve the native emulator requirement and the fixed actor canvas.
The v0.6 integration supersedes the legacy air-attack placeholder with
dedicated source art; its latest evidence snapshot is documented below.

## v0.6.0 combat-animation integration

The current source milestone carries the following contracts forward from the
v0.5.1 baseline:

- Every fighter has 64 uniform 96x80 frames: legacy 0-15, motion/transition
  16-31, action 32-47 and airborne/throw/knockdown/wake 48-63. The original 48
  frame pixels and palette bytes remain locked.
- Twelve new `animation-airborne.png` atlases and adjacent provenance files
  provide dedicated air punch and kick anticipation, active and recovery art,
  thrower/victim roles, knockdown poses and wake poses. Identity masters and
  costumes remain separate.
- Native data uses eight 30,720-byte banks per fighter and a 6,144x80 review
  strip, with one shared fifteen-color palette and one uniform physical scale
  across all 64 frames.
- Combat distinguishes throw lift, flight, floor, get-up and wake. Throw damage
  lands at ground impact; simultaneous throws tech; heavy uppercuts, heavy low
  kicks and rising specials can cause knockdown; wake grants four invulnerability
  ticks and accepts buffered attack or jump input during its final six ticks.
- Training health recovery is gated while a fighter is hurt, downed or
  wake-invulnerable, and Select resets the round while clearing active
  throw/down/wake state.
- The native fast path caches actor-bank and per-action timing selection, uses
  compile-checked `Fighter` stride 64 and `Wave` stride 16 layouts, and caches
  unchanged OAM/shadow work by integer position and facing. Native health and
  energy bars preserve their glyph formulas; impact HUD and empty-banner clear
  continue through hitstop ticks while interface DMA yields to actor uploads.
  The engine and VRAM contract are unchanged, although interface feedback may
  settle one to three video frames after the combat event.
- `src/trace.asm` writes read-only telemetry directly at stable `TRACE[0..113]`
  offsets. Any packed `Fighter` or `Wave` layout change requires updating the
  assembly offsets and the trace documentation together. The earlier four-family
  600-frame probe was too narrow to characterize worst-case timing; two-actor
  attack/impact scenarios exposed additional audio and interface lag, so it is
  not used as worst-case evidence.
- The original streamed-BRR combat cues caused real stalls under simultaneous
  attack/impact cases. The v0.6 audio path loads four resident SPC effects from
  `effects.it` at scene load, keeps music module IDs 1-4, uses `spcEffect` at
  pitch 2 and 8 kHz with the existing mix values, and coalesces same-frame cues
  by round, impact, special, then swing priority.
- The latest four reports pass against ROM SHA256
  `0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`:
  2,595 gameplay, 18,085 roster, 215 presentation and 604 focused-input
  checks (21,499 total). The canonical silent `Test.cmd` batch passes on that
  image; this evidence does not close public, human-playtest,
  independent-emulator or real-console gates.

## Future art and animation

- Review the new airborne, throw, knockdown and wake drawings, then add more
  character-specific in-between art for weight and footwork after human review.
- Align hands and feet more closely to gameplay contact points and add per-pose hitboxes.
- Extend the three independent stage compositions with layered parallax and animated coworkers while preserving the native tile, OBJ and vblank budgets.
- Add a dedicated champion illustration and richer end-of-match presentation beyond the current large selection portraits.

## Next combat pass

- Tune frame data, reach, damage, push boxes, jump arcs, throw ranges and meter
  gain through human playtesting. The v0.6 values are an integration baseline,
  not a balance conclusion.
- Improve CPU spacing, anti-air behavior, defensive variety and difficulty progression.
- Add training hitbox display, frame-step tools, command history and more rematch options.
- Extend the four special families with individual effect art, command variations and additional moves.
- Audit aerial normal collision, throw contact and wake input timing against the
  dedicated air and recovery illustrations.

## Release-quality validation

- Keep running the gameplay, roster, presentation and focused input suites after
  changes. The latest reports share the exact SHA above and the canonical silent
  `Test.cmd` batch passes, so the exact-ROM evidence gate for packaging is
  satisfied. Human playtesting, independent-emulator, real-console and
  public-release review remain open.
- Playtest with two controllers and several keyboard layouts, including keyboard rollover constraints, SOCD edge cases, motion buffering and hitstop inputs.
- Profile worst-case combat frames, eight-bank animation uploads, audio
  streaming and vblank use across Snes9x, Mesen and bsnes.
- Test an original SNES or Super Famicom through a flash cartridge. Real-console and flash-cartridge testing have not yet been performed.
- Record regression movies, verify every arcade ending and run longer stability sessions.
- Review branding and portrait usage with the team before a public release.

Commercial fighting-game polish requires repeated art, animation, audio, balance and QA passes. The project is organized so those passes can be reviewed and versioned without replacing the native engine.
