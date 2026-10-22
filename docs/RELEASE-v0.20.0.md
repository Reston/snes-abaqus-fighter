# v0.20.0 Damian likeness candidate
<!-- candidate-version: 0.20.0; rom-sha256: 6b3544fa09e37a3f70c4eaecf5565718abc467962610ec1ce0437fc023d9f501 -->

The source cartridge now includes Damian's revised face across all 64 native
poses and both portraits. The additional supplied photo guides a longer nose,
darker brows, narrower mouth and short stubble; the blue game costume remains.
The user answered "ok good" after reviewing the photo, previous and revised
faces, native portraits and game captures on 2026-10-22. The exact question
and response are retained in [review-feedback.json](review-feedback.json).

The ROM is SHA256 `6b3544fa09e37a3f70c4eaecf5565718abc467962610ec1ce0437fc023d9f501`, header checksum `3F2A`.
Its cartridge source freeze is `c83cf5ece118fe6c2454a0eaa55a6a20aaecd72b`,
tree `459a6eaa21b3bcb8d10d14662006c9dc65c31b96`. The integration and approval
documentation preserve that tested cartridge. See the
[art/provenance note](DAMIAN-LIKENESS-v5.md),
[comparison page](DAMIAN-REVIEW-v5.html),
[silent motion review](DAMIAN-MOTION-v5.html) and
[focused verification record](damian-v5-verification.json).

All six native suites on this exact ROM pass 35,715 checks: 2,596 gameplay,
18,084 roster, 3,344 presentation, 1,521 input, 8,163 stage and 2,007 Training.
The separate pinned bsnes2014 Accuracy smoke also passes. The 20 authoring
guard tests pass normally and under Python `-O`. Ordinary and regenerated
asset builds reproduce the same cartridge.

The preservation record compares with v0.19.0: 200 of 219 generated files,
all eleven other fighter records and all 1,276 RAM addresses are preserved.
The 19 intended changes are Damian art, portraits, the selection plate and
generated metadata. Damian's OBJ palette, uniform scale, canvas and feet
baseline remain fixed. C/assembly behavior is unchanged; the software version
literal changes to 0.20.0. Earlier v4 masters and the v4 contract are retained.

This candidate has no new offline ZIP. Full release-scale matrix/replays,
independent combat, endurance, technical audio and isolated fresh-export
evidence have not been regenerated for this ROM. The
[v0.19.0 checkpoint](RELEASE-v0.19.0.md) remains the latest fully verified
offline package. Existing versioned galleries and extended reports identify
their original cartridges.

The user's response accepts this likeness revision. Human gameplay/balance,
full listening, physical controllers, remaining roster likeness review,
team/subject consent and public-use approval remain open.
`public_release_certified` remains false; original hardware is unverified.
