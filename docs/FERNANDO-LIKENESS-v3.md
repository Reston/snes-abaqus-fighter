# Fernando likeness and Madariaga spelling

The v0.30.0 review candidate corrects **Madariaga** in the roster, HUD, results,
winner/Champion text and current guides. The internal `08-mamariaga` asset path
stays stable so historical art and provenance remain reproducible.

Fernando's face was redrawn from the retained [reference photo](../assets/references/fighter-06.jpg).
The revision uses a rounder oval face, natural side-swept hair, straighter brows,
a fuller nose and a calmer mouth. Nine complete atlases carry the same facial
design through all 64 native frames, including walking, attacks, jumps and supers.
The selection portraits use the revised idle figure. No heads or body parts were
pasted onto the original art.

[Before/after review](FERNANDO-REVIEW-v3.html) · [Native ROM](../dist/abaqus-after-hours.sfc).

Fernando retains his teal jacket, white collar, fixed physical scale, 15-color
OBJ palette, frame roles and support baseline. All eleven other fighter records
are identical to v0.29. Of 237 generated files, 218 are unchanged; the 19 changes
belong to Fernando, the selection page and their metadata. His collision
rectangles are regenerated from the revised pixels; the other eleven geometry
blocks remain exact. Native move timing, damage, movement rules, hardware/trace
assembly and all prior RAM/data addresses are preserved.

The [generation record](../assets/art/characters/06-fernando/likeness-v3-generation.json)
retains every exact prompt, unmodified output hash and saved source path. All ten
selected images, including the facial study, were produced with built-in imagegen
and true transparency. The established native encoder performs extraction,
uniform scaling and palette conversion. Original masters remain intact.

The [native revision contract](../assets/art/characters/06-fernando/native-revision.json)
pins the four base atlases. The versioned walking, attack, jump and super
provenance pins their disjoint frame replacements.

Technical results and exact cartridge identity are recorded in
[verification-v0.30.0.json](verification-v0.30.0.json). Likeness acceptance remains
for the user's visual review; this candidate is separate from the deployed v0.29.
