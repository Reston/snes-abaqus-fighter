# v0.33.0 — Readable native faces for all twelve fighters
<!-- candidate-version: 0.33.0; identity: TECHNICALLY_VERIFIED_HUMAN_REVIEW_PENDING; rom-sha256: 64f7db0dea8b42be855abd836a8f7c9d2f249873a74116e4a0f06ee773631aad; source-freeze: fd4bee3acd8ef92d2437d1a9ead4125edb641a88 -->

All twelve in-game fighters now use native pixel-art faces with clearer eyes,
expressions, noses, mouths and jawlines across all **768 poses**. Six natural
skin values share each existing fifteen-colour actor palette with the retained
costume and hair colour families. Complete figures retain their physical
heights and pose roles; the original selection portraits stay byte-exact.

[Native before/after and walking review](NATIVE-FACES-v0.33.html) ·
[Artwork, exact prompts and scope](NATIVE-FACES-v0.33.md).

All six native suites pass **52,141 checks**. Focused
rendering checks cover all twelve fighters, both controller ports and both
pinned emulator cores: 48 cases,
35,280 strict callbacks, no health failures.
Independent Accuracy smoke, 23 authoring guards normally and under `-O`, five
web integrity tests and a fresh committed-source rebuild pass. The fresh build
reproduces all 237 assets, the ROM and normalized symbols. The stage suite is
counted once. [Exact verification](verification-v0.33.0.json).

The 116 non-fighter outputs remain exact. Changed outputs are the twelve model
previews, 96 sprite banks, twelve existing palettes and character manifest.
All 1,331 prior RAM/data labels and native rules remain; only version text and
pixel-derived contact rectangles differ. Stages, audio and slower pacing stay.

ROM `64f7db0dea8b42be855abd836a8f7c9d2f249873a74116e4a0f06ee773631aad` · checksum `5A59` · source `fd4bee3acd8ef92d2437d1a9ead4125edb641a88`.

Technical verification does not establish likeness acceptance. PR #36 remains
**draft and unmerged** for the user's native visual review. Public player is
still v0.30; no new offline package or physical-hardware claim.
