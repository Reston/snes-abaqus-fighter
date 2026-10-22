# v0.19.0 - practice controls and build identity
<!-- candidate-version: 0.19.0; rom-sha256: 945da11920112ca11fbc00acec2fc04a1d821209a7e7a920defe5a05c32005e7 -->

On Training's first PAUSED card with CPU selected, either controller's **L/R
shoulder buttons** cycle Easy/Normal/Hard. Holds change once; opposite held
shoulders cancel across ports. Start/B/A/Select and dummy directions retain
priority. Guide pages, scripted dummies and non-Training pause cards retain
their controls. Quick reset keeps the level, which also appears at home.
Resuming with a setting shoulder still held does not buffer a heavy attack.

The title shows **V0.19.0** at its lower right. The native label and manifest
share one source version definition. Build.cmd writes canonical LF generated
text after asset regeneration and reuse. Injecting CRLF into three cached
inputs restores their original bytes and reproduces the identical ROM.
Offline Markdown/license copies use LF without changing their source files
or notice wording; QA JSON and native binary entries remain byte-exact.

- ROM SHA256: `945da11920112ca11fbc00acec2fc04a1d821209a7e7a920defe5a05c32005e7`; checksum `05A4`.
- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- Source freeze: `003ab19b98f291fed67e7de457c1fc746d7ad2d8`.
- Source tree: `17854e74ac06042df3d9121747036a00a5034686`.
- Preservation baseline: `571181943892216d2fc98e63ae58c592cb1f19ab` (v0.18.0).

All 219 generated assets, 1,276 RAM addresses, protected hardware/trace ASM,
Fighter64/Wave16 and TRACE0..122 are preserved. CPU controls reuse the existing
difficulty and pause-direction local. The longer hint stays in banner row 13;
actor/OBJ/UI/ambient/SPC budgets remain. No AI decision, attack, damage or
recovery rule changes.

Focused controller cases cover both ports, wraps, holds, fresh/held opposites,
scope, priorities, frozen combat and home/reset persistence. The old v0.18.0
ROM rejects the new controller and title-label checks; the candidate passes.
The legacy-renderer negative and normal/optimized corrected checks prove
portable prose while retaining exact QA/native bytes.

All six native suites pass on this exact ROM: 2,596 gameplay, 18,084 roster, 3,344 presentation, 1,521 focused input, 8,163 stage, 2,007 Training,
totaling **35,715**. The Training proof retains twelve level-cycle cases, four holds, four
opposite pairs, four held-opposite cases, eight scope exclusions and five
priority routes, plus both non-Training modes. It checks frozen combat,
home/reset persistence and held-shoulder resume without an accidental attack.
The title glyph checks match the version from the build manifest.

The pinned bsnes2014 Accuracy smoke, 48-by-600-frame independent combat,
288-case native matrix, four deterministic replays and stage/policy/symmetry
checks pass. Each mode completes at least 216,356 live frames in one native
session. Training completes **216,356 CPU live frames** across all twelve
opponents. Cadence, native timing, ambient, PPU-overflow and SPC-FIFO failure
arrays are empty; stable FIGHT lag increments are zero in every mode.
Fresh committed export reproduces ROM, 219 assets and normalized symbols in
**471.844 seconds** from the recorded source freeze.

Focused menu, authoring, champion A/Start/B routes, technical audio, CPU
hit/whiff media and 72 all-roster cross-up practice cases pass on this ROM.
Current CPU Training card/clip and twelve practice clips accompany the native
gallery and 64-frame roster viewer. GIF playback timing is approximate.

The Windows archive includes pinned Snes9x, guides, exact QA/provenance and
native captures. Extract the whole ZIP and run Play.cmd. REVIEW.html opens on
CPU Training; filters show results and menus. Package checksum and technical
audit are published separately in dist/release-sha256.txt and
docs/release-audit.json. Packaging requires two identical final audited ZIPs.

The native review/practice/roster pages and version-tagged feedback export
remain. No new human feedback or approval is recorded. Human gameplay/balance,
full listening, physical-controller, likeness/consent and team/public-use
gates remain open. Original hardware is unverified;
`public_release_certified` remains false.
