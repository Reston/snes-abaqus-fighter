# v0.12.0 candidate - Training opponent selection
<!-- candidate-version: 0.12.0; rom-sha256: 45dae37c358a71e8ffb8d1b9fec3a60a1d0d95e516bdd6e314d0bef995f24b91 -->

This draft builds on parent commit `68842a2b040fefc9070542fcf57284af5494e1dc`.
Training now lets the player choose an arbitrary opponent or mirror match.
Confirm PLAYER 1 to open the existing second roster step, headed `DUMMY`.
Its initial cursor remains the next roster entry. Confirm the dummy to choose
an arena; B returns to PLAYER 1 without confirming again in the same sample.
P1 can operate both roster steps, and the DUMMY step also accepts P2 input.

The existing four-by-three grid, one cursor, large portrait, directional
neutralization and Start > B > A priorities are preserved. Arcade and Local
Versus keep their existing routes. Live Training input, dummy behaviors,
combat, AI, balance, Fighter64/Wave16 layouts, trace offsets 0..122, hardware
transfers, native art, palettes, audio and the generated assets are unchanged.
Live Select reset keeps the chosen fighters and dummy behavior; a new match
starts with Stand behavior.

## Verification status

`Build.cmd` succeeds without asset regeneration in the isolated worktree.
The 4,194,304-byte NTSC FastROM LoROM candidate has SHA256
`45dae37c358a71e8ffb8d1b9fec3a60a1d0d95e516bdd6e314d0bef995f24b91`
and header checksum `B3F1`. Focused headless native checks pass for the DUMMY
heading and portrait, first-confirm roster step, nonadjacent and mirror
opponents, combined-button Back/confirm priority, both-pad navigation/SOCD,
reset preservation and new-match Stand behavior. Existing dummy contact,
port-two inertness, reset-after-damage, pause cadence and menu regressions
also pass. Updated ordinary/stress input and character boot routes, plus a
bounded uninterrupted endurance-host boot and roster return, load the requested
fighters through native controller input. The focused report is retained only
under ignored `build/focused-training-v012.json`; it is not six-suite release
evidence. All jobs remain headless and silent, below normal priority on logical
processors 14/15.

All six native suites on one exact ROM SHA, matching compatibility smoke,
extended evidence, preservation review, isolated source rebuild and packaging
remain pending integration. Historical reports do not verify this candidate.
No v0.12.0 package or source freeze has been produced.

Human gameplay/balance, full listening, physical-controller, likeness/consent
and team/public-use review remain open. Original SNES/flash-cartridge support
stays unverified; this remains an emulator-first candidate with
`public_release_certified=false`.
