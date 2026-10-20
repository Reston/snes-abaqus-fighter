# v0.4.1 — likeness, proportions and presentation

The v0.4.1 patch gives Reston short dark buzz-cut hair across the top and crown,
with a moderately receding hairline matching the user's newly supplied photo.
All sixteen poses and both selection portraits use the corrected master.
The previous atlas is retained beside it, and `likeness-v3.json` records the
complete built-in imagegen edit prompt and validation.

The wider v0.4 presentation and proportion improvements continue below.

The seven remaining face revisions complete a likeness pass across all twelve
fighters. Each person keeps an individual cartoon atlas, costume and palette;
all selection cards and larger profile portraits derive from those masters.

The fighter renderer now uses a 96×80 canvas and one scale across each person's
sixteen poses. Wide kicks and horizontal knockouts no longer force the whole
body into a smaller box. All twelve intended idle heights, 66–74 pixels, fit
the new layout. The floor baseline and signed screen-edge positions remain
stable, and both sprite banks retain their full bottom rows.

Three independent arena paintings revisit the supplied photos: the glass 140
entrance in Las Condes, El Castillo's white party house, and the office's desk
rows and speed-test monitors. The home, four-by-three roster and arena menus
share a navy, gold, cyan and magenta arcade style. Fighter selection shows a
larger portrait and supports Up/Down movement between four-card rows.

The native cartridge is now 2 MiB FastROM LoROM. Graphics pointers are prepared
before vblank, paired OAM stores handle the wider sprites, and the HUD updates
only changed fields to preserve the frame budget.

## Verification

Official Snes9x 1.63 x64 libretro, silently and headlessly:

| Suite | Checks passed |
| --- | ---: |
| Gameplay, controller input, audio capture and arcade progression | 110 |
| All fighters, proportions, rendered pixels, OAM and exact pose uploads | 2714 |
| Menus, twelve exact profile uploads and three arenas | 161 |
| Total | 2985 |

The idle cadence probe measured 600 simulation ticks per 600 emulated NTSC
frames. All three reports record the exact tested SHA256:

`f5b431bc68db8f5f2b909c1c95e40edb62e2518ca06c8671ce6d7f44ab209e4b`

The complete source-assets build reproduces the same cartridge. Screenshots in
`docs/screenshots/` come from the actual core. No emulator window was opened or
refocused, and no audio device was used for verification.

Further in-between animation, layered stage motion, balance playtesting and
real-console checks remain on the roadmap.
