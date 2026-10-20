# Animation expansion contract

Native frames stay 96×80, with one physical fighter scale, baseline 78 and a
94×77 safety region. Frames 0–15 retain the existing key-pose indices. Two new
transparent 4×4 atlases per fighter add genuine drawn animation, giving 48
frames. Each eight-frame bank remains 30,720 bytes. The cartridge expands to
4 MiB FastROM LoROM to keep all twelve individual sets.

The new source files are `animation-motion.png` and `animation-actions.png`
inside each character directory. Preserve the current `atlas.png` and its
likeness corrections, especially Reston's v3 short dark buzz cut. Full prompts,
input roles, hashes and extraction validation go in `animation.json`.

All figures face right, including backward walking. Each new atlas uses a
strict 4-column by 4-row layout with 16 separate full-body figures, a transparent
background, ample gaps and no shadows or labels. The first figure is an upright
neutral guard at the existing idle's body proportions. It provides a single
source-resolution normalization for the entire atlas; poses must never be
independently resized to fit. Source anatomy and costume must remain consistent.

| Frame | Motion atlas, row-major |
| --- | --- |
| 16 | Neutral breathing guard, matching original idle |
| 17 | Gentle inhale, slight chest/shoulder rise and wrist movement |
| 18 | Exhale with subtle weight settling, feet planted |
| 19 | Return guard, completing a quiet breathing loop |
| 20 | Forward walk, lead-foot contact |
| 21 | Forward walk, weight passing over planted lead foot |
| 22 | Forward walk, rear foot passes beneath hips |
| 23 | Forward walk, opposite contact, preparing seamless repeat |
| 24 | Backward walk, rear-foot contact, guard maintained |
| 25 | Backward walk, weight moves onto planted rear foot |
| 26 | Backward walk, lead foot passes beneath hips |
| 27 | Backward walk, opposite contact, preparing seamless repeat |
| 28 | Halfway into crouch, knees bend naturally |
| 29 | Jump anticipation, compact knee compression |
| 30 | Early jump extension, different from the legacy tucked jump |
| 31 | Landing compression, preparing to stand |

| Frame | Action atlas, row-major |
| --- | --- |
| 32 | Upright ready guard matching original idle, slight fist preparation |
| 33 | Jab retracts halfway to guard |
| 34 | Cross windup, torso/hip turn and fist drawn back |
| 35 | Cross retracts, torso returns toward guard |
| 36 | Kick windup, bent knee raised |
| 37 | Kick retracts, bent leg returns under body |
| 38 | Sweep windup, crouch with leg tucked |
| 39 | Sweep recovery, weight returns into crouch |
| 40 | Block impact brace, forearms firm and shoulders absorb force |
| 41 | Hurt recovery, torso returns toward balanced guard |
| 42 | Special charge, both empty hands near waist, no effects |
| 43 | Cast recovery, arms fold back after extending |
| 44 | Uppercut anticipation, crouch and fist near waist |
| 45 | Uppercut recovery, raised arm lowers and legs descend |
| 46 | Victory transition, arms partway raised |
| 47 | Knockout fall, diagonal backward collapse, head left |

Idle uses a slow breathing cycle; walking uses shorter steps synchronized to
distance traveled. Attacks show anticipation, their existing active key pose,
then recovery without changing the gameplay hit timing. Jump, crouch, guard,
hurt, special, victory and knockout sequences use the corresponding transitions.
Hitstop and pause freeze the animation clock.

No commercial sprites, ROMs or copied game audio are included. SFII may be
studied as a reference for rhythm and readability only.
