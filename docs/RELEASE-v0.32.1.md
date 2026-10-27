# v0.32.1 — In-game faces, original selection portraits
<!-- candidate-version: 0.32.1; identity: TECHNICALLY_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: 1dc456430a706fd0e6ac3a4d25bc0455b1cf9e034599d15e581962202dda628b; source-freeze: dfb7ef1dd032e5ca6765d6b0776f09f417898fe6 -->

The face work belongs on Ivo, Fernando and Cristian's fighting models. The
mistaken v0.32 photo-head selection portraits are removed. All selection
portraits and roster artwork return exactly to their pre-change v0.31 bytes.

The photo-referenced in-game drawings remain across all 64 poses per fighter.
Their sprite banks and contact geometry are byte-identical to v0.32. The other
nine fighters, palettes, physical heights, combat rules, stages and audio remain.
The full standing preview continues to use the fighter's actual model.

[Actual in-game model comparison](IN-GAME-FACES-v0.32.1.html) ·
[Scope and source art](IN-GAME-FACES-v0.32.1.md).

All six native suites pass **50,605 checks**. Both-core,
both-port portrait and combat checks pass 8,820
strict callbacks, with no health failures. Accuracy smoke, 21 authoring guards
normally and under -O, five static web build tests and fresh reproduction of
the ROM, all 237 generated assets and normalized symbols pass. Stage execution
is counted once. [Exact verification](verification-v0.32.1.json).

ROM `1dc456430a706fd0e6ac3a4d25bc0455b1cf9e034599d15e581962202dda628b` · checksum `1A4C` · source `dfb7ef1dd032e5ca6765d6b0776f09f417898fe6`.

PR #36 remains unmerged for native likeness review. The public player remains
v0.30; no new offline package or physical-hardware claim.
