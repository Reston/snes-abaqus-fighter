# v0.22.1 — nine approved improvements; stage 08 deferred
<!-- candidate-version: 0.22.1; rom-sha256: 52725899fa86b4ee3d3f3f022dae374c1ab4ff8777bdab4a7134640c34dc8727 -->

The user authorized merging features 01–07, 09 and 10 and requested that
feature 08 remain for further polish: “it looks bad the parallax background.”
This cartridge restores the original static camera, original ambient source
generator and all four stage-dynamics/ambient outputs byte-for-byte from v0.21.0.
Contact shake remains. No scanline parallax or round-winner stage reaction runs.
The 08 branch and worktree are retained for a separate polish pass.

ROM SHA256 `52725899fa86b4ee3d3f3f022dae374c1ab4ff8777bdab4a7134640c34dc8727`, header `8300`. All six native
suites pass **36,253 checks**, and matching pinned bsnes2014 Accuracy smoke
passes. See [verification](verification-v0.22.1.json) and
[preservation](expansion-preservation-v0.22.1.json).

The 219 generated files include 215 preserved files and four original-audio
extension outputs changed from v0.21.0. All fighter art, approved Damian v5,
portraits, stage masters, static stage tiles/maps/palettes and original scores
are retained. The unused 16-byte stage reservation stays in place to preserve
the other integrated RAM addresses. Fighter64/Wave16, TRACE0..122, existing
one-actor/DMA/OBJ/interface/audio bounds remain.

All nine other features remain: weighted animation, readable contacts, normal
balance, fighter gestures, Training tools, CPU personalities, supers, Arcade
dialogue/endings and resident announcements. Local 1v1 already exists as
**Local Versus**, using two independent SNES controller ports. Y/X punch and
B/A kick; fresh neutral Y+B spends the full 96 energy on a super.

Run [Play.cmd](../Play.cmd) for this main candidate. The user also requested
better walking for all twelve fighters and clearer local-1v1 discovery; those
are follow-up changes. Old v0.22.0 ten-feature proofs/captures and its review
gallery are historical and include the rejected parallax. No full new offline
archive, release-scale endurance/matrix, public-use approval or original-hardware
claim is made.
