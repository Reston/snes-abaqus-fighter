# Native in-game faces — all twelve fighters

The user rejected the tiny Ivo face and requested **“do it for everyone.”**
This revision applies the same native pixel-art treatment to all twelve
fighters and all 64 poses each. Final human likeness acceptance is pending.

The face now has separate readable eye, brow, nose, cheek, mouth and jaw
clusters. Each existing fifteen-colour actor palette reserves six natural skin
values and nine costume/hair values. Muted skin colours cannot accidentally
map to saturated orange or red clothing. No additional OBJ palettes, sprite
entries or transfers are allocated.

The source edit uses the actual earlier 64-pose grid, a native-size style guide
and the person's photograph. Complete figures are extracted and uniformly
scaled; the importer never assembles a face from pasted anatomical pieces.
Physical heights, costume designs and pose roles remain. Selection portraits,
their palette data/framing and the roster backdrop remain byte-exact.

[All twelve sources, palettes and 768 native frame hashes](../assets/art/native-faces-v033/roster.json)
are pinned by the importer. Each source PNG has an adjacent JSON containing
the exact **built-in image_gen** prompt, reference hashes and original output
hash. Original source masters, the rejected Ivo trial and Cote's cropped-sole
attempt remain as history; only the selected sources in the roster are used.

Game rules, move timing, damage, input, slower pacing, stages, audio, RAM/ABI and
hardware/trace assembly remain. Contact rectangles are regenerated from the
final quantized drawings. [Current technical verification](verification-v0.33.0.json) and
[native comparison media](NATIVE-FACES-v0.33.html) bind this exact candidate.

PR [#36](https://github.com/Reston/snes-abaqus-fighter/pull/36) stays draft for
native likeness review. The public player remains v0.30; no new offline package
or physical-hardware certification is claimed.
