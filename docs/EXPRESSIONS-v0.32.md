# Ivo, Fernando and Cristian — eyes and expression

Historical reference: selection portrait replacement was rejected scope. [Current in-game model revision](IN-GAME-FACES-v0.32.1.md).
The user accepted the body improvement but found the eyes and expressions off.
They then approved the photographed head studies: **"Yes, use this direction"**.
That approval covers the reference direction; final native likeness remains
for playtest review.

Each of the three fighters has nine built-in imagegen atlas edits. The previous
v0.31 sheet is the body/pose target, the approved head is the expression guide,
and the photographic crop is the identity reference. Their natural eyelids,
brows, gaze and mouth replace the earlier stock scowl throughout all 64 poses.
Whole figures are edited together; no heads or limbs are pasted onto bodies.
The encoder only extracts, uniformly scales, anchors and quantizes the masters.

Both selection portraits use the complete approved head master in the existing
32×40 and 64×80 slots. The original OBJ palette and physical height remain fixed
for fighting sprites. The other nine fighter records and geometry blocks remain
exact; only the three revised models refresh their pixel-derived contact boxes.

| Fighter | Expression guide | Full-body generation provenance |
| --- | --- | --- |
| Ivo | [Approved study](../assets/art/characters/01-ivo/expression-study-v032/head.png) | [Nine edits and exact prompts](../assets/art/characters/01-ivo/expression-v032-generation.json) |
| Fernando | [Approved study](../assets/art/characters/06-fernando/expression-study-v032/head.png) | [Nine edits and exact prompts](../assets/art/characters/06-fernando/expression-v032-generation.json) |
| Cristian | [Approved study](../assets/art/characters/07-cristian/expression-study-v032/head.png) | [Nine edits and exact prompts](../assets/art/characters/07-cristian/expression-v032-generation.json) |

Every record retains the exact prompt, input roles, selected path and raw/output
hashes. All selected inputs/outputs remain in the repository. External raw paths
describe the source machine, not extra reproduction prerequisites. Original
masters and previous native contracts remain historical. The approved head
studies are also documented in [the reference review](FACE-EXPRESSION-REVIEW.md).

Of 237 generated files, 192 stay exact and 45 change within the three fighter
banks, portraits, selection art and metadata. All 1,331 prior RAM/data labels,
hardware/trace assembly, input rules, damage and pacing remain. Native C differs
only in the version string. [Preservation](likeness32-preservation-report.json)
and [verification](verification-v0.32.0.json) record the exact candidate.

[Native comparison and animation gallery](EXPRESSION-REVIEW-v0.32.html).
