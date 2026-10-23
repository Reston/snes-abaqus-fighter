# v0.21.0 four-button combat and native HUD
<!-- candidate-version: 0.21.0; rom-sha256: aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205 -->

The cartridge uses four attack face buttons: Y/X light/strong punches and
B/A light/strong kicks. L/R retain home and paused Training level controls.
Down+X uppercuts, toward+X throws, Down+A sweeps, Down+Y quick-casts a special,
and quarter-circle+Y/X casts the character special. A retains the close air
cross-up. The CPU, pause guide and keyboard documentation use these commands.

The floor shadow is one shallow contact ellipse using the same two mirrored
OAM pieces per fighter. Its Y 200 origin puts the dark center against the
feet while staying below low-wave fetches. The existing five-row HUD adds
gold nameplates, capped health, red low-health feedback, thin energy gauges,
a timer frame, closed diamond win medals and a bottom rule.

ROM SHA256 `aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205`, header `BEB8`.
Source freeze `72dd25e9b71c1db6973540eef2eddd380b8039ed`, tree `5a645d49b100b82260fe7b0f7ffc78c2b8d32ac0`.
The [design and controls note](FOUR-BUTTON-HUD.md),
[native comparison](FOUR-BUTTON-HUD-REVIEW.html),
[preservation record](four-button-hud-preservation.json) and
[verification record](four-button-hud-verification.json) retain the detail.

The six native suites pass 33,082 checks on this exact ROM: 2,594 gameplay,
15,182 roster, 3,760 presentation, 1,376 focused-input, 8,163 stage and 2,007
Training. The independent pinned bsnes2014 Accuracy smoke passes. The
controller-only focused proof passes 228 checks, covering all twelve fighters
on both ports, ignored shoulders, directional commands, floor shadows,
an earned round-win medal and low health. The 20 authoring guard tests pass
normally and under Python `-O`. Verification runs headlessly without audio
playback or emulated-memory writes.

Counts differ from v0.20.0 because the normal/air input inventory now has four
physical attack buttons. The 64-frame fighter art and native geometry checks
remain; the raw emulator input callback is unchanged.

All 1,276 RAM addresses, Fighter64/Wave16, TRACE0..122, actor streams, OBJ
slots, guide range and DMA budgets are retained. Of 219 tracked generated
assets, 216 retain their v0.20.0 bytes. Only ui_tiles.bin, ui_pal.bin and
effects.bin change. All twelve fighter records and palettes, portraits,
stages, ambient and audio are preserved; Damian's approved v5 art remains.

The [feedback record](review-feedback.json) retains the user's requests and
positive response, "much better", after this revision. Detailed controls and
gameplay/balance review, full listening, physical-controller, roster consent
and public-use gates remain open. `public_release_certified` remains false.

No new offline ZIP was made. Full matrix/replays, independent combat,
live-hour, audio and fresh-export evidence remains historical. The
[v0.19.0 package](RELEASE-v0.19.0.md) is the latest full offline checkpoint.
