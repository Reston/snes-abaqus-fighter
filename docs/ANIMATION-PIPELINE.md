# Roster animation asset pipeline

`tools/fighter_assets.py` keeps the original `atlas.png` as the first sixteen
native key poses for each fighter. Two additional, independently authored
four-by-four transparent atlases are required in every fighter directory:

```text
animation-motion.png    frames 16..31
animation-actions.png   frames 32..47
```

Each source atlas is extracted with the same connected-component rules as the
legacy atlas. Its first neutral figure supplies one source-resolution
normalization against the legacy idle height. That conversion is applied to
the whole atlas once. After the two conversions, all 48 figures share one
physical scale selected over the full set so the resulting RGBA frames fit a
96x80 canvas, a 94x77 safe region and baseline 78. No pose is independently
fit or compressed.

`prepare_roster()` returns `indices` as 48 native indexed frames and writes
`assets/generated/fighterNN.png` as a 4608x80 review strip. The expanded asset
writer divides each strip into six eight-frame 30,720-byte banks. The
character manifest retains a list under `frames`; every record includes its
global index, source file/hash, source normalization, common physical/global/
uniform scale, native box, baseline and indexed-pixel hash. The fighter entry
also records `source_legacy`, `animation_sources` and `frame_count`.

The extractor remains backwards compatible:

```python
extract_atlas(path, alpha_threshold=200)
```

returns the original sixteen `POSES` names. Animation callers pass an explicit
sixteen-name tuple through the optional `pose_names` argument. Missing
animation atlases and insufficiently distinct locomotion/recovery cycles are
errors; the pipeline never invents placeholder frames. The breathing,
forward-walk and backward-walk loops are checked again after palette
quantization, requiring at least three distinct native indexed frames in each
four-frame loop. The source and quantized palettes must also retain at least
three opaque colors.
