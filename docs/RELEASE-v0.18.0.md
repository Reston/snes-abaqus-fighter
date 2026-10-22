# v0.18.0 - CPU Training level readout
<!-- candidate-version: 0.18.0; rom-sha256: fbf24853bef53f8d7be59c85363ba7496d8ee35da803f0368fc9cbea5ce3c4bb -->

CPU Training's first PAUSED card names **Easy**, **Normal** or **Hard** beside
the behavior. Set difficulty with L/R at home. The readout survives quick
reset and guide cycling; other dummy labels clear it when selected. This
adds no control, AI, damage, timing or recovery rule.

- ROM SHA256: `fbf24853bef53f8d7be59c85363ba7496d8ee35da803f0368fc9cbea5ce3c4bb`; checksum `A299`.
- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- Source freeze: `8a7a6fc78c2160aac23de2a2f32ea927016853d0`.
- Source tree: `9d78764a6f40c5fe3661b0b2f6fb8469d9f0a25f`.

The change uses three ROM literals and the existing banner rebuild/transfer.
The four-entry initialized label array keeps its WRAM footprint. All 219
generated assets and 1,276 existing RAM addresses match v0.17.0. Fighter64,
Wave16, TRACE0..122, protected hardware/trace ASM, actor/OBJ/UI/ambient and
SPC contracts remain. Preservation baseline: `83e9123ad1702261ea8a78e73249b776e839616d`; no asset changes
or additions are allowed.

Focused controller cases read the actual PPU glyph map at all three levels,
after reset and guide cycling, and while cycling all five dummy labels.
The updated label check rejects v0.17.0's unsuffixed CPU label and passes the
new cartridge. The ordinary Stand opening, ignored P2 Training gameplay,
both-port pause controls, health recovery and 99 clock remain.

All six native suites pass on this exact ROM: 2,596 gameplay, 18,084 roster, 3,337 presentation, 1,521 focused input, 8,163 stage, 1,811 Training,
totaling **35,512**. The added Training checks read all three difficulty
labels and verify them again after quick reset and pause-guide cycling.
Five-choice navigation, shorter dummy labels, both controllers, SOCD/chord
priorities, real CPU play and gated recovery retain their existing coverage.

The pinned bsnes2014 Accuracy smoke, 48-by-600-frame independent combat,
288-case native matrix, four deterministic replays and stage/policy/symmetry
checks pass. Each mode completes at least 216,356 live frames in one native
session. Training completes **216,356 CPU live frames** across all twelve
opponents. Cadence, native timing, ambient, PPU-overflow and SPC-FIFO failure
arrays are empty; stable FIGHT lag increments are zero in every mode.
Fresh committed export reproduces ROM, 219 assets and normalized symbols in
**568.453 seconds** from the recorded source freeze.

Focused menu, authoring, champion A/Start/B routes, technical audio, CPU
hit/whiff media and 72 all-roster cross-up practice cases pass on this ROM.
Current CPU Training card/clip and twelve practice clips accompany the native
gallery and 64-frame roster viewer. GIF playback timing is approximate.

The Windows archive includes pinned Snes9x, guides, exact QA/provenance and
native captures. Extract the whole ZIP and run Play.cmd. REVIEW.html opens on
CPU Training; filters show results and menus. Package checksum and technical
audit are published separately in dist/release-sha256.txt and
docs/release-audit.json. Packaging requires two identical final audited ZIPs.

The review gallery retains local feedback export tagged with the current
version and ROM hash. No new human feedback or approval is recorded.
It inserts encoded captures after text substitution, so a valid image payload
containing a placeholder token keeps its original bytes. A synthetic PNG
reproduces the earlier failure and passes with the corrected expansion order.
Human gameplay/balance, full listening, physical-controller, likeness/consent
and team/public-use gates remain open. Original hardware is unverified and
`public_release_certified` remains false.
