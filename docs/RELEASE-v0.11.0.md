# v0.11.0 - Winner cards and reliable offline packaging
<!-- candidate-version: 0.11.0; rom-sha256: 77615cb93f9f7c572c66b23f4a078acb87c1a8ab925667ead42a84d1a880e629 -->

The result card now shows the match winner's existing 64x80 portrait, name,
quote and actual round score. Local Versus uses the neutral heading
`MATCH COMPLETE` for either winner. The A/Start prompt identifies the actual
next action: rematch, Arcade continue, next challenger or title after Office
Champion. B returns to character select.

This candidate includes the [v0.10.1 Lars and location-preview pass](POLISH-v0.10.1.md).
Its versioned art, exact prompts, native revision contract and retained
baseline are unchanged by this result-screen pass.

- Candidate: v0.11.0, 4,194,304-byte NTSC FastROM LoROM cartridge.
- ROM SHA256: `77615cb93f9f7c572c66b23f4a078acb87c1a8ab925667ead42a84d1a880e629`.
- Header checksum: `5AFE`.
- Source freeze: pending completion of the current source changes.

## Native contracts

The winner portrait uses the existing BG2 tile block at VRAM word `$4A00`
and palette 1, loaded while the screen is blanked. No new per-frame transfer,
OBJ usage, palette bank, trace field or Fighter/Wave layout is introduced.
The wake-input fix discards directional command stages during the six-tick
wake state. Previously, directions entered while getting up could cause a
later fresh punch to spend energy on a special. Fresh wake attack/jump edges
and complete post-recovery quarter-circle motions remain supported. Both
player ports have controller-driven regressions for this case.

All twelve fighter banks, stage masters, ambient cells and audio remain
unchanged from the v0.10.1 checkpoint. The normal pause card now includes
Start in its resume hint, matching the existing controls.

## Verification and package status

Candidate verification is in progress. Do not use the historical v0.10.1
six-suite results or v0.10.0 release-scale results as evidence for this ROM.
No v0.11.0 Windows package has been produced yet.

Native result checks drive real controller inputs to P1 and P2 victories,
compare the winner portrait's exact VRAM bytes and actual PPU pixels, verify
opaque text and score digits, and follow the advertised Start rematch. The
gameplay suite also checks the actual champion title prompt before taking
that action.

The offline-package work checks pinned emulator identity, explicit native
evidence requirements even under optimized Python, complete file preflight,
and documentation paths for the extracted package. Full release evidence and
archive results will be recorded after the candidate source is committed.

This remains an emulator-first technical candidate. Human gameplay/balance,
full listening, physical-controller sessions, likeness/consent and team/public
use review remain open. Original SNES/flash-cartridge support stays unverified.
`public_release_certified` remains false.
