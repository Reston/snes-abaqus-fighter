# v0.27.1 — office menu backdrop

The world maps are replaced by a gold duotone of the game's authored office:
windows, Santiago skyline and trading desks. The title uses a quieter crop
behind the logo. The roster layout, original portraits and controls remain.

[Native screens](REVIEW-v0.27.1.html) · [Verification](office-menu-review.json) · [PR #24](https://github.com/Reston/snes-abaqus-fighter/pull/24)

Presentation and Training pass **6,642 exact-ROM checks**. Both pinned
cores pass 74 menu states each, including comparisons of the rendered office
pixels, with zero steady-menu cadence/SDK failures. Normal/optimized authoring
guards pass 20/20. Fresh source reproduces the ROM, all 226 assets and symbols.
The prior v0.27.0 six-suite results are historical for this new cartridge.

Relative to v0.27.0, 217 of 226 generated files remain exact. The nine
changes are title/select plates and their size header. Gameplay C/ASM,
fighter/portrait/stage/audio assets and all 1,318 RAM addresses are preserved.
The rejected map data remains retained as history and is no longer rendered.

ROM `c6682d3da92ae7ae41f80e62580163c169b4017cb81c83abcdbc611f8b1d7000` · checksum `3C43`.
Source/test freeze: `2e6f947a43d148b44f8b7528769bfef1865ed85f`. Visual review and merge remain pending.
No new offline package is claimed.
