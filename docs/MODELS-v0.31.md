# Ivo, Fernando and Cristian model revision

**Visual follow-up:** the user liked the body improvement but found the faces
off, specifically their eyes and expression. The ROM below remains the tested
v0.31 candidate, not an accepted facial revision. New [expression studies](FACE-EXPRESSION-REVIEW.md)
are awaiting visual feedback before adaptation through the animations.

The user's three supplied native screenshots identified these faces as too
generic. The first restrained atlas edits retained that problem and were
discarded. Fresh photo-based model sheets established distinct facial shapes
before the full pose sets were drawn.

- **Ivo:** longer mature face, natural side part, more restrained eyes and mouth.
- **Fernando:** fuller oval cheeks, thick brows, substantial nose and softly waved hair.
- **Cristian:** broader square jaw, shorter dense hair and a calm adult expression.

All 64 poses and both portraits change for each fighter. Complete body drawings
keep the new faces, clothes and proportions together through walking and
combat. No heads or limbs are pasted onto old sprites. The encoder only
extracts, uniformly scales, anchors and quantizes the generated masters.

The three original palettes and physical heights remain fixed. The other nine
fighter records remain exact. Of 237 generated files, 192 remain exact and
45 change within these fighter banks, portraits, selection art and metadata.
The native rules differ only in the version string; hardware/trace assembly
and all 1,331 prior RAM/data labels remain exact. Contact rectangles follow
the three revised models; timing, damage, input rules and other nine geometry
blocks stay unchanged.

Each generation record retains the exact built-in imagegen prompts, input
roles, unmodified output hashes and selected workspace paths. The external raw
output paths are source-machine provenance; all selected images are retained
locally in the repository. Original source masters are preserved, including
Fernando's v0.30 native contract as `native-revision-v030.json`.

| Fighter | Reference | Model | Exact prompts and provenance |
| --- | --- | --- | --- |
| Ivo | [Photo](../assets/references/fighter-01.jpg) | [Model sheet](../assets/art/characters/01-ivo/model-study-v031.png) | [Generation record](../assets/art/characters/01-ivo/model-v031-generation.json) |
| Fernando | [Photo](../assets/references/fighter-06.jpg) | [Model sheet](../assets/art/characters/06-fernando/model-study-v031.png) | [Generation record](../assets/art/characters/06-fernando/model-v031-generation.json) |
| Cristian | [Photo](../assets/references/fighter-07.jpg) | [Model sheet](../assets/art/characters/07-cristian/model-study-v031.png) | [Generation record](../assets/art/characters/07-cristian/model-v031-generation.json) |

[Native before/after gallery](MODEL-REVIEW-v0.31.html) · [Verification](verification-v0.31.0.json).
Human likeness acceptance and merge remain pending. No new offline archive.
