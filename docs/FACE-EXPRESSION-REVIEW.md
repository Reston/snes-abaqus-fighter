# Eyes and expression review

Historical reference: selection portrait replacement was rejected scope. [Current in-game model revision](IN-GAME-FACES-v0.32.1.md).
The user liked v0.31's body improvement but rejected its faces. Their specific
feedback is **eyes and expression**. These three studies translate the reference
photos' relaxed eyelids, natural brows, gaze and closed mouths directly, without
the fighting scowl introduced by the earlier character drawings.

[Visual comparison](FACE-EXPRESSION-REVIEW.html).

| Fighter | Unmodified generated study | Exact prompt, references and hashes |
| --- | --- | --- |
| Ivo | [Head](../assets/art/characters/01-ivo/expression-study-v032/head.png) | [Generation record](../assets/art/characters/01-ivo/expression-study-v032/generation.json) |
| Fernando | [Head](../assets/art/characters/06-fernando/expression-study-v032/head.png) | [Generation record](../assets/art/characters/06-fernando/expression-study-v032/generation.json) |
| Cristian | [Head](../assets/art/characters/07-cristian/expression-study-v032/head.png) | [Generation record](../assets/art/characters/07-cristian/expression-study-v032/generation.json) |

All three were made with **built-in imagegen**. Each directory retains the
unmodified transparent output, exact photographic crop, complete prompt and
64x80 portrait-sized preview. External raw paths are source-machine provenance;
the selected outputs and input crops are retained in the repository.

The `head-small-palette-test.png` files are diagnostic reductions into each
fighter's original OBJ colors. They demonstrate that the facial marks still
need deliberate adaptation at fighting-sprite size; they are not approved
native faces. No heads were pasted onto existing bodies.

The user approved this reference direction with **"Yes, use this direction"**.
The v0.32 implementation carries it through nine full-body atlas edits for each
fighter and uses each complete head master in the existing portrait slots.
The native fighter reductions are independently authored whole figures; the
diagnostic small-head tests are not inserted into them. Original body designs,
palettes and physical heights remain. Final native likeness review and merge
approval remain separate from this reference-direction approval.

[Applied native portraits and animations](EXPRESSION-REVIEW-v0.32.html) ·
[Implementation and full-body prompts](EXPRESSIONS-v0.32.md).
