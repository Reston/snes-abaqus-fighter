# v0.11.0 - Winner cards and reliable offline packaging
<!-- candidate-version: 0.11.0; rom-sha256: 1574bb4147605b3a0dd8d463b6403360a386c62334e1d5e29ea5654bd376baa7 -->

The result card now shows the match winner's existing 64x80 portrait, name,
quote and actual round score. Local Versus uses the neutral heading
`MATCH COMPLETE` for either winner. The A/Start prompt identifies the actual
next action: rematch, Arcade continue, next challenger or title after Office
Champion. B returns to character select.
Healthy timeout ties now read `TIME OVER` / `DRAW` from the first banner;
the `DOUBLE K.O.` caption is reserved for simultaneous knockouts before the clock expires.

This candidate includes the [v0.10.1 Lars and location-preview pass](POLISH-v0.10.1.md).
Its versioned art, exact prompts, native revision contract and retained
baseline are unchanged by this result-screen pass.

- Candidate: v0.11.0, 4,194,304-byte NTSC FastROM LoROM cartridge.
- ROM SHA256: `1574bb4147605b3a0dd8d463b6403360a386c62334e1d5e29ea5654bd376baa7`.
- Header checksum: `7CFE`.
- Cartridge source freeze: `68842a2b040fefc9070542fcf57284af5494e1dc`.
- Source tree: `b8e0eee67cdc0e8a92dee351bbf625959e38a9ec`.

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
The [preservation record](preservation-v0.11.0.json) verifies all 214 generated
assets plus hardware and trace assembly against that checkpoint, using exact
binary bytes and Git LF normalization for text.

## Verification and package status

All six native suites now pass on this exact ROM: 2,596 gameplay, 18,081
roster, 2,692 presentation, 1,030 focused input, 8,131 stage and 625 Training
checks, totaling **33,155**. The separate pinned bsnes2014 Accuracy smoke
matches. The clean committed-source rebuild reproduces the cartridge, all
214 generated assets and normalized symbols in 205.594 seconds. Native
endurance completes one live emulated hour in each of the three modes.

The full 288-case native matchup matrix, stage/policy/symmetry checks and
four deterministic replays pass. The independent bsnes combat run passes
48 cases of 600 frames. The [verification record](verification-v0.11.0.json)
collates these exact-cartridge gates; historical results are kept separately.

The Windows offline package includes the pinned Snes9x executable, cartridge,
player guide, exact QA reports and an embedded native-screen review gallery.
Extract the whole archive and run `Play.cmd`. The source checkout publishes
its archive checksum in `dist/release-sha256.txt`; the archive audit is
recorded separately in `docs/release-audit.json`.

Native result checks drive real controller inputs to P1 and P2 victories,
compare the winner portrait's exact VRAM bytes and actual PPU pixels, verify
opaque text and score digits, and follow the advertised Start rematch. The
gameplay suite also checks the actual champion title prompt before taking
that action.

The offline-package work checks pinned emulator identity, explicit native
evidence requirements even under optimized Python, complete file preflight,
and documentation paths for the extracted package. The source freeze above
is the committed cartridge input used by the isolated rebuild.

This remains an emulator-first technical candidate. Human gameplay/balance,
full listening, physical-controller sessions, likeness/consent and team/public
use review remain open. Original SNES/flash-cartridge support stays unverified.
`public_release_certified` remains false.
