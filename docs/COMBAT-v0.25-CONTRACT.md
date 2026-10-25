# v0.25 pacing and floor revision

The user reported that approved v0.24 still felt too fast and rejected its
blank two-gray floor conversion. This revision starts at `8f028775` (v0.24
ROM `408cadfd…`, checksum `4857`). Main remains the approved baseline until
the new native candidate is verified and reviewed in one PR.

Combat keeps native NTSC video, 60 Hz controller sampling and ordinary audio
timing. There is no emulator slowdown, dropped logic frame or input throttle.
Ground travel and ordinary projectiles use approximately 75% of v0.24 speed.
Every normal gains windup and recovery; heavy and special commitments grow
further. Hit pauses become 7/10/5 ticks for light/strong/guard. The compiled
hit-stun table becomes `16 + floor(damage/3)`; guard stun becomes 11 ticks.
Damage, reach, meter costs, controls and four-button mappings stay unchanged.
The universal uppercut retains its quick defensive start and gains recovery;
the established throw clock stays responsive.

Lower gravity and proportional launch speeds lengthen jumps while keeping
their heights and nominal horizontal travel close to their approved values.
Supers gain readable preparation/recovery and slower travel. Rising pulse
gaps retain their established live clocks and capped linked recoil; longer
contact pauses slow their real-time beat without losing follow-up hits.
CPU neutral attack opportunities and recovery answers are less frequent.
These are deliberate balance changes, so old whole-state equality is not a
valid gameplay expectation. Unit native cadence and SDK/OBJ/SPC bounds remain
strict requirements.

Outdoor floors reuse the approved v0.23.1 material pixels. Office ground uses
the versioned built-in-imagegen strip and exact prompt/provenance in
`assets/art/stages/floor-v025/`. All prior masters remain retained.
Scenery and detailed ground share one 4bpp BG1 picture with a bounded ±8px
look. This removes the two-color BG3 apron and any moving-band seam.

BG1 tile graphics may use word `$0000..$37FF` (28 KiB); its 64x32 map stays at
`$3800..$3FFF`. BG3 is disabled. UI/portrait/guide `$4000..$5BFF`, actor pages
`$6000..$73FF`, effects `$7800..$7BFF`, all palettes outside the six stage
palettes, and all 1,318 prior RAM labels keep their existing allocations.
There is no live stage DMA/HDMA or added OBJ entry. The six old BG3 generated
files remain transparent compatibility records so the inventory stays 226.

All 64 fighter drawings, portraits, palettes, physical scales and contact
geometry stay exact. Only the hit-stun ROM lookup data changes in native
hardware assembly; its instructions and the trace ABI stay unchanged.
`tools/v025_contracts.py` independently compares committed baseline blobs,
generated inventory, all old source art, RAM symbols and compiled stun data.

Verification must bind the exact new ROM: both native cores for ground
geometry and freeze behavior, all twelve fighters/both ports for measured
pacing and super hit/guard sequences, all three CPU difficulties, the six
shared suites, authoring checks and a fresh source export. Before/after GIFs
are inspection approximations; the cartridge determines actual timing.
