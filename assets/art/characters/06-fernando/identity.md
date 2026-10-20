# Fernando Pérez

Fernando is the grounded veteran silhouette in the character-specific art pass.
The teal open field jacket, rolled sleeves, white collar, and sturdy charcoal
trousers give him a clear cool-color read. His broad torso, planted stance, and
compact guard should make him feel anchored and hard to push around while the
large hands and expressive face keep attacks readable at SNES size.

The face and hair in likeness v2 are cartoon design cues derived from
`assets/references/fighter-06.jpg`: a broad round-oval adult face with full
cheeks and a soft chin, dense black natural side-parted hair with modest lift,
thick dark brows, soft normal eyes, and a friendly calm mouth. The face is
clean-shaven or has only the gentlest tiny stubble. The atlas is original game
art and depicts a fictional fighter, not a realistic employee portrait or
assigned real-world role.

Readability targets:

- teal/cyan jacket ramp with bright rolled cuffs and white collar;
- stocky broad-shouldered torso, sturdy legs, charcoal trousers, and dark shoes;
- deep navy contour and approximately fifteen usable material colors;
- compact right-facing guard with a consistent feet baseline;
- distinct connected silhouettes and transparent gaps between all sixteen cells;
- enlarged fists, face, and shoes for low-resolution play.

Pose order is row-major: idle guard, forward walk, backward walk, crouch guard;
tucked jump, straight jab, cross punch, high side kick; low sweep, raised
block, hurt recoil, victory; two-hand energy cast with no projectile, rising
uppercut, horizontal KO with head to the left, forward shoulder lunge.

The likeness v2 master was selected from a built-in imagegen edit of the prior
atlas using `assets/references/fighter-06.jpg` as a face-and-hair reference
only. A second built-in edit repaired a vertical component merge between the
raised-block and rising-uppercut cells. The selected master is an RGBA 4x4
atlas (1217x1293) and passes the shared component extractor at alpha threshold
200 with all 16 poses intact.
