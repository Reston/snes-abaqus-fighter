# v0.27.0 — classic arcade menus

An original slanted Abaqus logo, warm gold/charcoal menus and a world-map
selection backdrop follow the Street Fighter II direction chosen by the user.
The twelve existing portraits now form a six-by-two roster. P1/P2 badges have
their own row, including mirror matches. Up/Down moves one six-card row.
Arena landmark images retain their crops in matching warm panels.

[Native screens](REVIEW-v0.27.0.html) · [Verification](classic-menu-review.json)

All six native suites pass **49,209 current-ROM checks**. Both pinned cores
pass 74 focused menu states and 2,353 steady callbacks each, with no measured
SDK/cadence failures. The independent Accuracy smoke passes. A fresh committed export reproduces
the cartridge, 226 generated files and normalized symbols.
Authoring guards pass normally and under `-O`.

All fighter drawings, portraits, stage/audio data and 1,318 RAM addresses are
preserved. Thirteen generated menu/header outputs change; 213 stay exact.
Combat rules, hardware/trace assembly and the fixed ABI are unchanged.

Hover updates retain the fixed BG2 portrait map and transfer 2,560 portrait
bytes plus 980 UI bytes. Direct menu-frame writes remove the old cursor stall.
The title/roster artwork is code-authored from the project's original glyphs.
The decorative land silhouette uses public-domain Natural Earth geometry,
retained with a hash and source record in `assets/art/menu/classic-v1/`.
It assigns no nationalities or map locations to the fighters.

The older Training routes now use the six-column roster. Input fixtures hold
their measured spacing and guard between jump attempts; the same special,
range and cadence assertions remain. The Training HUD oracle also checks the
existing red/gold palette at HP <= 32. No combat policy changed for these tests.

Version: `0.27.0` · ROM `d5263c777cbb3a02ce438e07c1c425f2d39dd73d294cd4d2aa8c2cbc2da78e3d` · checksum `FA37`.
Source/test freeze: `4d7e8fe17f1a0a534bc06e3e059fc4c03cd556d0`.
[PR #24](https://github.com/Reston/snes-abaqus-fighter/pull/24) is an unmerged
playtest candidate stacked on the concise-help branch.
Human visual review remains pending; no new offline archive is claimed.
