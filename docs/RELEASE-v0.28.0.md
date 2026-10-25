# v0.28.0 — full-body roster preview

The selected fighter now stands at native 96×80 size with the original four
breathing poses. A/Start plays two signature poses and a victory pose over
18 ticks (0.3 seconds) before advancing. Held confirm advances one step.
The small portraits, office backdrop, P1/P2, Training and mirrors remain.

[Native animations](REVIEW-v0.28.0.html) · [Verification](menu-preview-review.json)

Both pinned cores pass all twelve fighters in Arcade, local P1/P2 and Training:
36 sessions each, including exact VRAM poses, rendered body pixels, held
confirm, Back and live fight handoff. 49,286 focused checks pass with
zero cadence/SDK/OBJ failures. Presentation/Training pass another 6,455.
Normal/-O guards pass 20/20. Fresh source reproduces the ROM, 226 outputs
and symbols. Older six-suite results retain their historical ROM identities.

The preview reuses actor0's OBJ/VRAM page and original palettes/art. Hover UI
(972 bytes) and pose uploads (3,840 + 32 palette bytes) use separate blanks.
All 1,316 existing variable/data labels keep their addresses; two allocation
end/size markers grow by five bytes. Five menu bytes append after audio state.
221/226 generated outputs stay exact; only select art and its size header
change. Fighter/Wave/TRACE ABI, hardware assembly, combat and pacing remain.
GIFs sample every three callbacks; GIF timing is an inspection approximation.

ROM `09eaa47ddc12d419e259f1330eb225f1e56f75d42efdd2faf5c27063f8f2357c` · checksum `ECEB`.
Source/test freeze `16e9989497fa7f7bf16271d59555a13b57caeac4`. User accepted this revision with “ok let's go with this one”. PRs #21–25
are merged into main. [Integration record](integration-v0.28.0.json).
No new offline package is claimed.
