# v0.10.1 Lars and location-preview polish candidate

This note preserves the art checkpoint at
`0708dea65c859786e8455da78bd58eb077135adf`. Its test results below identify
the historical v0.10.1 ROM. The current cartridge and verification status are
recorded in [RELEASE-v0.11.0.md](RELEASE-v0.11.0.md).

This review candidate addresses the two findings reported after playing
v0.10.0: Lars needed a closer likeness, and the location-selection pictures
were hard to understand. The exact responses are retained in
[review-feedback.json](review-feedback.json). The v0.10.0 Windows ZIP remains
the previous packaged snapshot; it does not contain these changes.

## Lars

Four new built-in imagegen masters revise the face and hair across all 64
poses. The public reference photograph is `assets/references/fighter-11.jpg`.
The design emphasizes fuller cheeks, a wider blunt jaw, a broader nose,
smaller eyes and dense dark hair with a curved forehead lock. The ice-blue
jacket, white shirt, navy trousers and dark shoes remain his costume.

The selected versioned sources are in
[`assets/art/characters/11-lars/`](../assets/art/characters/11-lars/):

- [atlas-v4.png](../assets/art/characters/11-lars/atlas-v4.png), frames 0-15,
  with [likeness-v4.json](../assets/art/characters/11-lars/likeness-v4.json).
- [animation-motion-v4.png](../assets/art/characters/11-lars/animation-motion-v4.png),
  frames 16-31, and
  [animation-actions-v4.png](../assets/art/characters/11-lars/animation-actions-v4.png),
  frames 32-47, with
  [animation-v4.json](../assets/art/characters/11-lars/animation-v4.json).
- [animation-airborne-v4.png](../assets/art/characters/11-lars/animation-airborne-v4.png),
  frames 48-63, with
  [animation-airborne-v4.json](../assets/art/characters/11-lars/animation-airborne-v4.json).

The three provenance JSON files contain the exact final prompt set, input
roles, generated source paths, source hashes and extraction results. The old
masters remain intact. A layout repair separates the ground-impact and
wake-up figures in the airborne sheet before native extraction.

The native revision contract pins all 64 indexed frames. Every atlas receives
one conversion to the original 328-pixel neutral source height; individual
poses are not fitted separately. Lars retains physical scale
`0.22560975609756098`, the 96x80 canvas, 94x77 safe area, baseline Y=78, eight
30,720-byte banks and his exact existing fifteen-color OBJ palette.

## Location previews

The v0.10.0 whole-scene thumbnails squeezed detailed 256x224 stages into
60x52 boxes using nearest-neighbor sampling. Fine texture became isolated
colored pixels, and floor space displaced the architecture.

The new 104x52 previews show each location's landmarks with BOX area filtering
before SNES palette conversion. Source and destination are both 2:1, so the
art is not stretched. Native source crops are:

| Location | Source crop | Visible landmarks |
| --- | --- | --- |
| Las Condes | `(0,32,256,160)` | Glass canopy, 140 sign and entrance |
| El Castillo | `(0,16,256,144)` | House, garden and patio gathering |
| La Oficina | `(0,24,256,152)` | Skyline, monitors and trading desks |

The existing three 240x56 cursor rows, input priorities and controls remain.
Only the static BG1 menu plate changes. The stage masters, combat scenes,
ambient phases, runtime transfers, C/ASM combat and audio remain unchanged.
See [MENU-DESIGN.md](MENU-DESIGN.md) for exact menu geometry.

## Verification

At the v0.10.1 checkpoint, `Build.cmd --assets` and `Test.cmd` exit 0. Its six native reports
point to ROM SHA256 `8f7def30d29c87a659d7fb623147cf726bab8f8c94a96a503738529aded15279`
(header `42AF`) and pass 32,205 checks: 2,595 gameplay, 18,081 roster, 1,756 presentation, 1,020 focused input, 8,131 stage, 622 Training.

The separate pinned bsnes2014 Accuracy smoke passes on the same SHA,
including 600/600 neutral cadence, all three ambient stages and the
synchronized low-wave check. [polish-test-summary.json](polish-test-summary.json)
records the exact-ROM results. The source provenance JSON files use LF
bytes so their pinned hashes survive a normal Git checkout. Rebuilding
after that normalization produces the identical ROM.

[polish-preservation-report.json](polish-preservation-report.json) verifies
192 retained files out of 217 compared files; the 25 changes are limited to Lars, the roster/arena
plates, generated metadata and the ROM/manifest. All twelve OBJ palettes,
the other eleven fighters and portraits, stages, ambient cells, UI glyphs,
title, effects and audio are unchanged. The complete native Lars art
review is in [lars-likeness-report.json](lars-likeness-report.json).

v0.10.1 was an unpackaged review candidate. The prior v0.10.0 matchup,
independent-combat, endurance, isolated committed rebuild and package
reports do not certify this new ROM. Human likeness, gameplay, controller,
full-listening and team/public-use review remain open. Original hardware
remains outside verified support. `public_release_certified` remains false.
