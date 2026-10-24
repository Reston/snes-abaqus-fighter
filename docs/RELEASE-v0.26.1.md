# v0.26.1 — shorter game text

Menus, results and pause guides use shorter labels. Training drops repeated
explanations and gives each drill a brief instruction. The edited prompts
contain **43% fewer characters**; controls and gameplay rules stay the same.

Try **Training → Start → Select three times**. See the
[native before/after screens](REVIEW-v0.26.1.html).

Verification: **6,606 presentation and Training checks passed**. Additional
Snes9x/bsnes Accuracy captures retain strict native cadence, OBJ and audio
checks. The source audit permits only UI string literals and the version;
all 226 generated assets and 1,318 RAM addresses remain exact.

[Focused evidence](concise-text-review.json) binds the cartridge, reports and
screenshots. Source snapshot: `3feabef37f45a96e1ab7a82eea5d5af9159132cd`.

This is a small follow-up to [v0.26.0](RELEASE-v0.26.0.md). Its full six-suite
result remains historical; v0.26.1 claims the focused checks above. Human
review and merge approval remain pending. No new offline package is included.
