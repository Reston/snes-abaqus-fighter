# Roster animation asset pipeline

`tools/fighter_assets.py` prepares each individual illustrated fighter for the
native OBJ renderer. Every fighter has one legacy master and three authored
four-by-four transparent atlases:

```text
atlas.png                 frames 0..15
animation-motion.png      frames 16..31
animation-actions.png     frames 32..47
animation-airborne.png    frames 48..63
```

The airborne atlas follows the contract in `docs/COMBAT-ANIMATION-CONTRACT.md`:
upright neutral, air punch, air kick, compact apex, thrower/victim frames and
knockdown/get-up recovery. It is required for every fighter. The pipeline does
not invent missing frames, duplicate a grounded pose, or create fallback art.

## Extraction and scale invariants

`extract_atlas(path, alpha_threshold=200)` remains backwards compatible and
returns the original sixteen `POSES` names. Animation callers may pass a
sixteen-name `pose_names` tuple. Connected-component extraction rejects
translucent bridges and requires sixteen substantial fighter silhouettes.

The first 48 frames retain the v0.5.1 pipeline exactly. Motion and action
atlases are each source-normalized once against the legacy idle height; one
uniform physical scale is then selected over those 48 frames. The scale is
never recomputed after adding the airborne atlas. Frame 48 is an upright
neutral anchor, so it is source-normalized once with the legacy idle height;
that conversion applies to all sixteen new figures. The base-48 scale is then
applied unchanged to every frame.

The native canvas is 96×80 with a 94×77 safe region and baseline Y=78. Every
new frame must fit at that existing scale. A drawing over 94×77 raises an
actionable error naming the fighter, frame and measured size; the pipeline
never globally shrinks the old roster to hide an oversized new drawing.

Before replacing generated output, `prepare_roster()` loads the committed
v0.5.1 manifest and OBJ palette binaries. It compares all 48 old indexed-pixel
hashes and palette bytes for every fighter. A changed legacy hash or palette
ordering is a hard failure.

## Palette, metadata and review output

Each fighter’s fifteen-color OBJ palette is derived from the base 48 only.
Airborne pixels are quantized into that fixed palette, so adding new art cannot
silently recolor the established roster. The manifest records 64 complete
frame entries with global index, pose, source role/file/hash, source
normalization, common physical/global/uniform scale, native size/bounds,
baseline and indexed-pixel hash. The fighter entry records all four source
ranges, frame count 64, the shared scale and palette.

`assets/generated/fighterNN.png` is a 6144×80 RGBA review strip. Quantized
source cycles must retain at least three distinct native frames in each
breathing, forward/back walk, air punch, air kick, throw and
knockdown/recovery group. Source-level duplicate checks run before palette
quantization as well. Each airborne source must also have a parseable
`animation-airborne.json` containing its source path and prompt/provenance;
the generated manifest records that metadata file and hash.

## Native banks

Each fighter emits 245,760 bytes as eight LoROM-safe 30,720-byte banks:

```text
fighterXX.bin       frames 0..7
fighterXXb.bin      frames 8..15
fighterXXc.bin      frames 16..23
fighterXXd.bin      frames 24..31
fighterXXe.bin      frames 32..39
fighterXXf.bin      frames 40..47
fighterXXg.bin      frames 48..55
fighterXXh.bin      frames 56..63
```

`src/animation_banks.h` resolves banks G and H while retaining the original
resolver API. Rendering still uploads one 3,840-byte 96×80 frame per actor per
vblank; OAM layout, VRAM pages, palette reservations and scanline budgets do
not change.

The generated preview and manifest are review artifacts. They are regenerated
only after all twelve airborne sources pass extraction, normalization, palette
compatibility and bounds validation, followed by the silent native test suites.
