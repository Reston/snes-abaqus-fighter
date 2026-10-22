# Damián “Damian” Gelerstein

This is the game-fiction identity sheet for roster slot 00. The source portrait at `assets/references/fighter-00.jpg` is an appearance reference only; it is not shipped as game art. The fighter is rendered as an original cartoon sprite character.

## Appearance and outfit

- Shaved scalp with close stubble, a long oval face, dark fairly straight brows,
  hooded eyes, a prominent long nose with a rounded tip, a narrow natural mouth,
  tapered jaw and short facial stubble. Neutral poses use a small relaxed smile.
  Keep the nose and stubble readable; avoid a broad toothy grin, a baby-smooth
  face, a full beard or a square military jaw.
- Compact, broad-shouldered veteran silhouette with a low center of gravity and oversized readable hands.
- Cobalt rolled-sleeve blazer over an open white collar shirt, navy trousers, black shoes, warm peach skin, and a deep navy contour.
- The cobalt jacket, white collar, bald head, and compact stance are the primary recognition cues at SNES fighting distance.

## Likeness revision

The current v5 review candidate uses the additional user-supplied photo at
`assets/references/fighter-00-v5.png` for the facial structure and stubble.
The four versioned v5 atlases retain the cobalt costume and the existing 64
pose roles. Exact prompts, inputs and output hashes are retained in
`likeness-v5.json`, `animation-v5.json` and `animation-airborne-v5.json`.
The previous selected contract is retained as `native-revision-v4.json`,
along with all v4 source images and provenance. Agent review accepted the
native framing and readability. The user accepted the revised likeness with
"ok good" after the comparison review on 2026-10-22; see
`docs/review-feedback.json`. Team/subject consent and public-use approval
remain separate open gates.

The historical v2 likeness pass uses `assets/references/fighter-00.jpg` only as a broad
identity reference. It keeps the original fictional cartoon fighter, cobalt
costume, body, and all sixteen pose silhouettes while refining the head cues
across every cell. The selected source was generated with the built-in imagegen
edit workflow and is recorded in `likeness-v2.json`.

## Readability notes

The atlas uses a limited cel-shaded palette with a dark outline and two to four value steps per material. The jacket stays bright cobalt in every pose so the character remains distinct from the emerald-jacketed Ivo. Large hands, strong shoulders, the white collar, and the bald head are exaggerated for a roughly 64×80-pixel in-game reduction. There are no logos, lettering, weapons, effects, or background elements.

## Atlas layout

`atlas.png` is an original transparent 4×4 sheet. Poses are row-major: idle guard; front walking step; back walking step; low crouch guard; knees-tucked jump; extended jab; cross punch; high side kick; low sweep; raised block; hurt recoil; victory; two-hand energy cast with no projectile; rising uppercut; horizontal KO with head left; forward shoulder lunge.
