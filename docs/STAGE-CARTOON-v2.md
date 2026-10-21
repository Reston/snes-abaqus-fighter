# Cartoon locations, v2

The v0.10 pass redraws all three Abaqus locations with the same illustrated
arcade direction as the fighters: stronger navy contours, broad cel-color
shapes, simpler material shadows and small expressive background coworkers.
Street Fighter II is a composition and readability reference; these are
original images, with no commercial sprites or stage art imported.

The master/provenance links below refer to the source repository. The offline
game package retains this design note and the preservation report; raw art is
kept with the project rather than duplicated in the play package.

| Location | Selected master | Full prompt and provenance |
| --- | --- | --- |
| Las Condes | [Glass entrance and address 140](../assets/art/stages/00-las-condes-cartoon-v2.png) | [Generation record](../assets/art/stages/00-las-condes-cartoon-v2.json) |
| El Castillo | [Balcony, patio and party](../assets/art/stages/01-castillo-cartoon-v2.png) | [Generation record](../assets/art/stages/01-castillo-cartoon-v2.json) |
| La Oficina | [Desks, coworkers and dual monitors](../assets/art/stages/02-oficina-cartoon-v2.png) | [Generation record](../assets/art/stages/02-oficina-cartoon-v2.json) |

All three use built-in imagegen in edit mode. The earlier stage is the edit
target, the original location photograph supplies place identity, and Damian's
approved cartoon atlas supplies line and color direction. Raw selected outputs
are retained under [source-v2](../assets/art/stages/source-v2). Hardware preparation
uses a centered 8:7 crop, nearest reduction to 256x224, at most 90 colors without
dithering, and a nearest 4x enlargement to a 1024x896 RGB master.

[stages.json](../assets/art/stages/stages.json) selects the reviewed masters and
pins their hashes, raw outputs and full provenance. The earlier manifest is
retained as [stages-v0.4.json](../assets/art/stages/stages-v0.4.json); the original
three PNGs remain unchanged. The build validates the selected artifacts before
encoding. Complete-scene arena thumbnails come from these same masters.

Ambient tiles are derived from the actual encoded map and palette. Las Condes
uses leaf and canopy highlights; El Castillo uses party lights, a small gesture
and a warm window; La Oficina uses monitor activity. Phase zero is identical to
the static source. Four phases still occupy eight BG1 tiles and 256 bytes per
upload, with no extra sprites or palette writes. Actor/interface DMA retains
priority, and intro, pause, hitstop and round end freeze the stage clock.

The stage-art pass preserves all twelve fighters' 64 native frames, shared
palettes, physical scales, portraits, combat profiles and audio assets. A
separate menu-input correction neutralizes held opposite directions and gives
Start, Back and A a single, explicit action priority. Human approval of the new
stage style remains open; emulator evidence is recorded against the built ROM.
