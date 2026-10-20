# Cristian Valdés

Cristian is the tall defensive counter silhouette in the character-specific art
pass. The slate navy sleeveless sweater vest over pale rolled sleeves gives him
a strong readable two-tone design. His upright posture, long reach, disciplined
guard, and composed expression distinguish him from the other roster fighters.

This likeness revision keeps the existing body and every animation pose intact
while refining only the head and hair. The face now follows the supplied
reference's broad round-square geometry: fuller cheeks, a rounded substantial
chin, thick dark brows, calm narrower eyes, a broader nose, a clean-shaven jaw,
and a neutral friendly confident mouth. The hair is short, dense, near-black,
and naturally brushed forward with a restrained front shape rather than a spiky
anime silhouette.

Readability targets:

- slate/navy vest ramp with pale rolled sleeves and collar;
- tall lean upright silhouette, dark tailored trousers, and dark shoes;
- deep navy contour and approximately fifteen usable material colors;
- long connected reach in the jab, cross, kick, and shoulder lunge;
- right-facing poses with a consistent feet baseline and transparent gaps;
- enlarged hands, face, and shoes for low-resolution play;
- broad soft cartoon face, dense black hair, thick brows and clean-shaven jaw.

Pose order is row-major: idle guard, forward walk, backward walk, crouch guard;
tucked jump, straight jab, cross punch, high side kick; low sweep, raised
block, hurt recoil, victory; two-hand energy cast with no projectile, rising
uppercut, horizontal KO with head to the left, forward shoulder lunge.

The replacement atlas was produced with the built-in image generation edit
workflow using `atlas.png` as the edit target and
`assets/references/fighter-07.jpg` as the identity reference. Validation with
`fighter_assets.extract_atlas(..., alpha_threshold=200)` found sixteen large
connected silhouettes and a genuinely transparent RGBA background.
