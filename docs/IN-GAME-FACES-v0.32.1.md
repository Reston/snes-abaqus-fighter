# In-game face scope

**Visual revision required:** the user rejected the Ivo in-game face. Technical checks remain valid; likeness is not accepted. [Feedback and retained example](likeness32-visual-feedback.json).
The user clarified: **"I didn't want to change the face in the character
selection, I wanted to change or improve the face in-game of the models of
characters."** The v0.32 photo-head selection change was outside that request.

v0.32.1 restores the exact earlier selection portrait pixels, palette data,
framing and roster artwork. A pinned earlier idle-atlas source now generates
those portraits independently of the current fighting atlas. This prevents
future combat-face edits from silently redrawing the selection faces.

The three revised in-game models keep all 64 full-body animation frames from
v0.32, including their more natural eyes/brows and expression. No new raster
art was generated for this correction. The photo-based studies remain guides
for whole-body atlas edits; they are not used as selection images or pasted
onto a fighting body. The gallery enlarges actual native model pixels.

| Fighter | Animation guide only | Existing in-game source art |
| --- | --- | --- |
| Ivo | [Expression reference](../assets/art/characters/01-ivo/expression-study-v032/head.png) | [Nine full-body edits and prompts](../assets/art/characters/01-ivo/expression-v032-generation.json) |
| Fernando | [Expression reference](../assets/art/characters/06-fernando/expression-study-v032/head.png) | [Nine full-body edits and prompts](../assets/art/characters/06-fernando/expression-v032-generation.json) |
| Cristian | [Expression reference](../assets/art/characters/07-cristian/expression-study-v032/head.png) | [Nine full-body edits and prompts](../assets/art/characters/07-cristian/expression-v032-generation.json) |

All selection portraits/roster assets match v0.31. The three in-game sprite
banks and full contact geometry match v0.32. All other nine fighters, prior
1,331 RAM/data labels and hardware/trace assembly remain exact. Relative to
v0.31, 209 of 237 assets remain exact and
28 change within the three fighter banks/images
and character metadata. [Independent scope checks](likeness321-policy-report.json)
recompute these comparisons from retained Git objects.

[Native model comparison](IN-GAME-FACES-v0.32.1.html) ·
[Current verification](verification-v0.32.1.json).
