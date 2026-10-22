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

Before replacing generated output, `prepare_roster()` loads the immutable
`assets/art/roster-baseline-v0.8.json` and verifies its pinned SHA-256. It
compares all 64 old indexed-pixel hashes, the exact OBJ palette bytes and the
uniform physical scale for every fighter. A changed source, native frame,
palette ordering or scale is a hard failure; the generated manifest is never
used as its own baseline.

## Reviewed art revisions

An intentional likeness revision is an explicit, per-fighter contract. The
registered slots are fighter 00 (Damian's photo likeness), fighter 09
(Reston's short buzz cut) and fighter 11 (Lars's v0.10.1 photo likeness).
Each resolver requires its exact reviewed contract
SHA-256 in `tools/fighter_assets.py`. There is no command-line bypass. All other fighters
reject versioned alternate masters and must continue to match the complete
64-frame baseline.

Damian's v0.9 revision explicitly pins `normalization_policy: neutral-height`
and the original upright source height of 311 pixels. Each complete new atlas
uses one reviewed conversion to those source units before the unchanged native
physical scale is applied. The exact four factors and all resulting native
hashes are pinned in his contract; the resolver verifies each factor against
the original and replacement neutral anchors. This corrects different raster
sizes in regenerated sheets without fitting individual poses. Reston's v4
contract continues to use its original baseline conversions.

The adjacent `native-revision.json` contract uses this schema:

```json
{
  "schema": 1,
  "fighter_id": 9,
  "slug": "reston",
  "baseline": {
    "file": "assets/art/roster-baseline-v0.8.json",
    "sha256": "<pinned baseline SHA-256>"
  },
  "old_sources": {
    "legacy": {"file": ".../atlas.png", "sha256": "..."},
    "motion": {"file": ".../animation-motion.png", "sha256": "..."},
    "actions": {"file": ".../animation-actions.png", "sha256": "..."},
    "airborne": {"file": ".../animation-airborne.png", "sha256": "..."},
    "airborne_metadata": {"file": ".../animation-airborne.json", "sha256": "..."}
  },
  "new_sources": {
    "legacy": {"file": ".../atlas-v4.png", "sha256": "..."},
    "motion": {"file": ".../animation-motion-v4.png", "sha256": "..."},
    "actions": {"file": ".../animation-actions-v4.png", "sha256": "..."},
    "airborne": {"file": ".../animation-airborne-v4.png", "sha256": "..."},
    "airborne_metadata": {"file": ".../animation-airborne-v4.json", "sha256": "..."}
  },
  "provenance_files": [
    {"file": ".../likeness-v4.json", "sha256": "..."},
    {"file": ".../animation-v4.json", "sha256": "..."},
    {"file": ".../animation-airborne-v4.json", "sha256": "..."}
  ],
  "source_normalization": {
    "legacy": 1.0,
    "motion": "<old manifest source scale>",
    "actions": "<old manifest source scale>",
    "airborne": "<old manifest source scale>"
  },
  "old_native": {
    "frame_hashes": ["<64 ordered SHA-256 values>"],
    "frame_hashes_sha256": "<SHA of concatenated ASCII hashes>",
    "palette_hex": "<exact 32-byte SNES palette>",
    "palette_sha256": "...",
    "uniform_scale": "<old scale>",
    "physical_scale": "<old scale>"
  },
  "expected_native": {
    "frame_hashes": ["<64 reviewed indexed-frame SHA-256 values>"],
    "frame_hashes_sha256": "<SHA of concatenated ASCII hashes>",
    "palette_hex": "<unchanged baseline palette>",
    "palette_sha256": "...",
    "uniform_scale": "<locked old scale>",
    "physical_scale": "<locked old scale>"
  }
}
```

Each indexed frame hash covers one 96×80 (7,680-byte) plane. The summary hash
covers the 64 frame hashes in order. The encoded eight banks remain 245,760
bytes; the revision guard does not re-encode them to establish approval.
The contract must match the immutable old sources and old native block, and
the generated replacement must match its reviewed expected block. Previews,
portraits and the manifest are held in memory until all twelve fighters pass,
then published together. `provenance_files` is exactly the three same-folder
JSON records `likeness-v4.json`, `animation-v4.json` and
`animation-airborne-v4.json`; each path and SHA-256 is checked before any
replacement atlas is extracted, so the full prompt/provenance set cannot drift
independently of the approved source hash.

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
