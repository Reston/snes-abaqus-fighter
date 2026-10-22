# v0.15.0 - Close cross-ups and practice help
<!-- candidate-version: 0.15.0; rom-sha256: 2c447156b7c1f12d94e1c76dde3423928ad026933076c952806abda7d6281d44 -->

A close airborne medium kick can now connect after crossing behind the
opponent. Its short rear reach is sixteen pixels plus the ten-pixel body
half-width. Front reach, move timing, damage and the other directional attacks
retain their existing rules. High guard follows the defender's new away
direction after a crossing; low guard loses to an airborne kick.

Recoil and impact effects follow the actual contact side. A private direction
latch survives landing and simultaneous trades. It reuses the previously unused
flash byte, preserving WRAM storage and existing symbol addresses. Projectiles
and delayed throw damage retain their original hurt path. The Controls pause
page teaches the cross-up within its existing 1,472-byte, three-tick panel.

The package gate also binds the collated verification record's current version,
ROM, source freeze and six-suite counts to the individual native reports.

- Cartridge: 4,194,304-byte NTSC FastROM LoROM.
- ROM SHA256: `2c447156b7c1f12d94e1c76dde3423928ad026933076c952806abda7d6281d44`.
- Header checksum: `2491`.
- Cartridge source freeze: `e406ac17af1c25a64c7be547e7d0857880c18599`.
- Source tree: `78493ed80bfd259deb228e7a8ca20580fef4f267`.

## Native preservation

All 219 generated art/audio/UI assets match verified v0.14.0. Hardware/trace
assembly, Fighter64/Wave16, TRACE[0..122], actor/OBJ transfers, stage ambient
and SPC budgets remain. The [preservation report](preservation-v0.15.0.json)
recomputes approved baseline/freeze Git objects; no asset differences are allowed.
Champion art/music scopes remain in [CHAMPION-ENDING.md](CHAMPION-ENDING.md)
and [CHAMPION-AUDIO.md](CHAMPION-AUDIO.md).

## Verification and package status

All six native suites pass on this exact ROM: 2,596
gameplay, 18,084 roster, 3,337
presentation, 1,410 focused input, 8,163
stage and 1,446 Training checks, totaling **35,036**.
Thirty new controller cases cover both cross-up directions, old/new/low guard,
short rear reach, longer front reach, other air normals, grounded backward
whiffs, simultaneous trades, wall clamps, sparks, hitstop and recoil through
landing. The paused Controls cue is checked in all three modes.

The pinned bsnes2014 Accuracy smoke and 48-by-600-frame independent combat run
match. The 288-case native matrix, four deterministic replays and stage/policy/
symmetry checks pass. Those existing policy traces match v0.14.0; the new
cross-up routes are exercised separately by the focused controller cases.
All three modes complete 216,356 live frames with empty
cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure arrays.

The isolated source rebuild reproduces the ROM, all 219 generated assets and
normalized symbols in 448.641 seconds, from source commit
`e406ac17af1c25a64c7be547e7d0857880c18599` and tree
`78493ed80bfd259deb228e7a8ca20580fef4f267`. Three eleven-opponent controller ladders prove
champion A/Start to title and B to fighter select. Focused audio passes
1,792 capture-only checks across four cues and five scores, with
native repeat structure and earned scene/title transitions. An identified
fixture exercises cues over victory music. The optional WAV archive is separate
and identified by the [listening record](audio-listening-v0.15.0.json).

[Menu evidence](menu-footer-report.json) retains 4,650 checks, 69 paired
native states, fifty controller routes and fourteen final footer images. Its
baseline blobs, current core/helpers, actual preserved PNG/VRAM and footer
glyph comparisons are independently recomputed. [Authoring evidence](authoring-guards-report.json)
passes 19 mutation checks in normal Python and 19 in python -O, bound to frozen
production inputs and committed producer dependencies. The [verification
record](verification-v0.15.0.json) collates the complete current technical gates.
Packaging also compares that record's identity, source freeze and native totals
with its individual reports.

The [cross-up review record](crossup-review.json) retains two controller-driven
native clips, including takeoff, crossing, contact and landing in both directions.
Their GIF playback timing is an inspection approximation. Packaging verifies
their dimensions, decoded pixels and retained durations against the recorded
callback-frame hashes, together with current-ROM, core and producer identity.

The Windows package contains pinned Snes9x, player guides, exact QA/provenance,
champion/menu captures, cross-up clips and offline review pages. Extract the
whole ZIP and run Play.cmd. REVIEW.html includes both clips and the native
Controls cue alongside gameplay/presentation views;
ROSTER-REVIEW.html offers twelve generated 64-frame fighter strips with facing
and frame inspection. Its fixed-rate sweep is an art review aid. Retained
captures support human review; they are recorded emulator evidence and package
validation does not replay their execution. The archive checksum is published
separately in dist/release-sha256.txt and its audit in docs/release-audit.json.

The new cross-up needs human gameplay and balance feedback. Full listening,
physical controllers, likeness/consent and team/public-use approval remain open.
Original SNES/flash-cartridge support is unverified; public_release_certified
remains false. Historical records retain their own version and ROM identity.
