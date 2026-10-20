# Rodrigo “Lars” Lártiga

Lars is a tall, long-limbed, disciplined adult fighter with dense wavy near-black hair, a forward side-swept fringe, strong brows, and a composed serious expression based on `assets/references/fighter-11.jpg`. His bespoke costume uses an ice-blue tailored open jacket with rolled sleeves over a light shirt, navy trousers, and practical dark shoes.

The atlas is an original transparent 4×4 SNES-era cartoon sprite sheet. All figures face right and use the row-major pose contract consumed by the character-art extraction pass:

1. idle guard; front walk; back walk; low crouch guard
2. tucked jump; extended jab; crosspunch; high sidekick
3. low sweep; raised block; hurt recoil; victory
4. two-hand energy cast with no projectile; rising uppercut; horizontal lying KO with head to the left; forward shoulder lunge

The face likeness revision uses a broad full oval / softly square adult face with fuller cheeks, a blunt rounded jaw, broad straight nose, thick dark brows, calm serious eyes, and a clean-shaven chin. His identity landmark is dense wavy near-black hair with a forward side-swept fringe and one curved lock falling onto the forehead; this head shape is repeated across all sixteen poses instead of the previous small angular generic male head.

The visual target is chunky 1993 arcade pixel art with navy contours, hard-edged cel shading, a limited material palette, readable exaggerated hands and faces, and generous transparent spacing between cells. The character is deliberately a new design and does not use commercial game sprites, logos, or copied animation.

Likeness v2 was produced with the built-in imagegen editor using `assets/references/fighter-11.jpg` as the identity reference and the prior Lars atlas as the edit target. The selected replacement is `atlas.png`; `tools.fighter_assets.extract_atlas` at alpha threshold 200 verifies sixteen separate RGBA figures (SHA-256 `16eb9059e3809047d95b5d4af0e2bfeaf4577ea5d17fa50a100f5590062a3cc5`).
