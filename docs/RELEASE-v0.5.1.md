# v0.5.1 — clearer combat and sharper presentation

The 4 MiB native cartridge keeps all twelve 48-frame character sets and their
corrected likenesses. This pass focuses on contact, feedback and the experience
of playing the game in the supplied emulator.

## Combat

- Standing, crouching and airborne contact uses feet-relative body rectangles
  and action-specific vertical bands. Equal-center facing is symmetric, throws
  use their exact profile range, and recoil stays within the stage bounds.
- A direct contact distinguishes a blocked strike from a real hit. Hit-confirm
  cancels require real damage; a guarded attack finishes its recovery.
- Combos link while the defender remains in an uninterrupted hit reaction.
  Blocks and interruptions break the chain. The 45-tick banner lifetime is
  independent of this rule, so a later isolated hit cannot create a false combo.
- Receiving a real hit discards previously buffered attacks and jumps. New taps
  during hitstop are still sampled, with buffer expiry frozen during hitstop.
  The attacker's deliberate buffered follow-up remains available for a cancel.
- The CPU samples one decision per tick and resolves neutral facing before
  choosing directions. Training's opponent remains passive.

## Presentation

The first intro shows the control hint. Its bottom two rows clear before live
combat, pause and Training reset, revealing the full fighting floor. The result
card shows the actual P1/P2 best-of-three score, with the quote below it.

The Windows configuration now uses the supported `Stretch:IntegerScaling` and
`Stretch:BilinearFilter` options. A fresh muted Snes9x 1.63 GUI launch showed
sharp pixels, and the emulator's saved configuration retained the requested
display settings and both keyboard layouts. The option names and key mapping
format were checked against the [official Snes9x 1.63 configuration source](https://github.com/snes9xgit/snes9x/blob/1.63/win32/wconfig.cpp).

## Verification

All four silent native suites pass against ROM SHA256
`cbacf3fd8f13412bed0d756de233c7fb7ad49625170be2a32a5de40854e6a201`:

| Suite | Passed checks |
| --- | ---: |
| Gameplay and arcade progression | 188 |
| Roster, proportions and native animation | 4,574 |
| Menus, portraits, stages and results | 178 |
| Input, contact, combos and reset | 133 |
| **Total** | **5,073** |

The cadence probe records 600 game ticks across 600 emulated frames. All reports
identify the same cartridge. The existing 36 native animation GIFs are refreshed
without the live-fight footer, and a result-score capture is included.

The contact rectangles are a shared gameplay baseline. Per-frame limb hitboxes,
dedicated aerial art, human controller balance sessions and real-console testing
remain future work; this release does not claim exact SFII frame data.
