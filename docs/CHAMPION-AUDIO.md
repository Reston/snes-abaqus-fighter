# Office Champion victory score
<!-- candidate-version: 0.16.0; rom-sha256: feb73416224a7bbe6317f0c8a2b88abc403383c5017e151e1e6e2a8c3478cebd -->

The combined v0.16.0 cartridge is SHA256
`feb73416224a7bbe6317f0c8a2b88abc403383c5017e151e1e6e2a8c3478cebd`, checksum `FA49`,
source freeze `c5b64914b35af11897210701a2394a540a20a6b6`. It retains the original
v0.13 champion score without changing generated audio bytes.
The [release note](RELEASE-v0.16.0.md) records full candidate status.
Current-ROM focused evidence passes 1,792 capture-only checks.
The victory capture spans 72.580462 seconds, peak 2366/32,768,
RMS 387.7968, no clipped samples and longest near-zero interval
0.114388 seconds. Its native repeat spans
34.900375 seconds; amplitude/zero-crossing
correlations are 0.999392/0.978390.

## Composition and source

[The authoring helper](../tools/victory_music.py) composes sixteen 4/4 bars at
112 BPM and tracker speed 6, using four 64-row patterns. Its rising C-G-C-E
fanfare develops fifth/octave calls over C, F, A minor, D minor and G. The
closing phrase resolves F-D minor-G-C, softening the voices before the repeat.
The ideal tracker cycle is 34.285714 seconds; native SPC timing is measured
separately by the PCM proof.

The arrangement is original project code. It uses the title score's exact
five synthesized instruments and sample waves: Night Lead, Glass Bass, Kick,
Snare and Hat. Music occupies four SPC voices. No RNG values are consumed.
[Asset generation](../tools/make_assets.py) writes the new
[8,393-byte tracker module](../assets/generated/music4.it) after the original
four scores and effects. These encoder/module links require the source checkout
and are labeled source-only in the offline copy.

## Native scope and budget

Only the earned champion branch calls `music(4)`, during its screen-off
transition. Ordinary results keep arena music; title/roster actions restore
title music. C rejects score indices above 4 and compile checks pin the
effects-first module IDs. There is no new live per-frame task, trace field,
native struct, actor transfer or OBJ allocation.

The soundbank is 19,330 bytes, within one 32 KiB LoROM bank, with 13,438 bytes
free. All fifteen BRR source records and existing effects/music payloads
0..4 are preserved. The victory module uses 2,234 resident data bytes plus
1,928 music BRR bytes; the four resident effects add 1,944 bytes. The combined
6,106-byte SPC load starts at `$1A00`, ends at `$31DA` exclusive and leaves
52,774 bytes above it. Echo and streaming allocation remain zero. The helper
computes these values from actual binary tables, including word rounding,
and rejects invalid pointers, lengths, counts or overflow with explicit errors.

[Preservation](preservation-v0.16.0.json) records all 219 generated files
unchanged from verified v0.14.0. The v0.13 feature added the victory IT and
extended the soundbank; this candidate retains their exact bytes, the original
four scores, effects, native BRR/module payloads and every art asset. Source-input
provenance includes the original victory authoring helper and strengthened guards.

## Focused technical evidence

[The focused report](champion-audio-report.json) records the production ROM,
host/core/harness hashes, source preservation, soundbank budget and every check.
The probe captures all four resident cues and all five scores as signed-16
stereo PCM. It measures peaks, RMS, clipping, near-silence and a full passage's
repeat using amplitude and zero-crossing correlation. Separate controller-only
eleven-opponent ladders earn the ending, check ordinary results keep arena
music, and prove A/Start restore title music. The final scene load also checks
the existing six-byte SPC FIFO budget and drain.

The trophy scene offers no attacks. A separately identified test-only ROM
selects the victory module for all score loads so real-controller swing,
impact, special and confirmation cues can be compared against repeated control
boots. Its sole C literal substitution, fixture source/ROM hashes and capture
metrics are recorded separately. This fixture is distinct from the cartridge
being delivered; it uses no emulated-memory writes or save states.

All runs are headless at BELOW_NORMAL priority on the last two logical CPUs,
with no GUI or audio device. Report capture paths under build/champion-audio
refer to ignored source-checkout WAVs and fixture outputs; the offline archive
bundles exact JSON evidence and this guide, not those source captures.
The separate [listening archive record](audio-listening-v0.16.0.json) identifies
an optional WAV review ZIP created from these verified captures. It contains
all five scores and matched control/active cue pairs; it is separate from the
Windows game package and has not been played or approved by a human.
These are capture-only technical checks. Human full listening, gameplay,
controllers, likeness/consent and public-use approval remain open. Original
SNES/flash-cartridge support is unverified; `public_release_certified` is false.
