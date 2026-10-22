# Office Champion victory score

This bounded child change starts from `8f51915e060dc4a9d47139767f607ef2f26fe4b8`
(v0.12.0 ROM `33502fba12bf2cf02e6244174449c678ad1dd704afc754e7819f815489c6fa83`,
checksum `222B`). It adds an original score for the earned Office Champion
trophy scene. It does not establish a source freeze or release certification.

The child ROM is `82a0162a94e2f9e928412c3748ec82adc126eab13c6a7e224f7fcad03a5bd704`,
checksum `AA1A`, still 4,194,304 bytes, NTSC FastROM LoROM, version 0.12.0.
Two consecutive local `tools/build.py --assets` builds reproduce that hash.
The supplemental `champion-audio-rebuild-report.json` records the second-build
comparison, all fifteen exact native BRR source hashes and a controller-driven
Training selection/reset smoke (P1 fighter 11, independently selected dummy 2).
Its complete small supplemental harness is embedded in that JSON for replay;
this is a local rebuild, not the parent's isolated source-rebuild release gate.

## Composition and provenance

`tools/victory_music.py` authors sixteen 4/4 bars at 112 BPM, tracker speed 6,
four rows per beat: four 64-row patterns, nominal cycle 34.285714 seconds.
The first four bars announce a rising C–G–C–E fanfare and answer it downward;
the middle phrases develop fifth/octave calls over C, F, A minor, D minor
and G. The last four bars soften the lead, bass and drums and resolve
F–D minor–G–C before returning to the opening. The final tonic drops through
C–G–C while a quiet bass pulse keeps the resolution audible.

The melody/rhythm/harmonic arrangement was composed as original project code.
It does not import a recording, commercial tune, external instrument or MIDI.
The lead's fifth/octave language develops the project's existing title motif.
All five instruments and sample waves are copied directly from the generated
title IT: Night Lead, Glass Bass, Kick, Snare and Hat, including the existing
short melodic decay envelopes. Music still occupies four SPC voices. The new
helper consumes no RNG values and runs after the original four music ITs and
effects IT have been written.

The authored source is the helper plus `tools/make_assets.py`; its native
tracker output is `assets/generated/music4.it` (8,393 bytes). Exact original
IT/SFX source hashes, signed-8 cue sample hashes, resident BRR hashes, native
module preservation and harness hashes are in `champion-audio-report.json`.
The existing four IT scores, effects IT, four SFX binaries and the native
effects/music payloads for module IDs 0–4 are byte-identical to the parent.
The new score also uses the title's five exact sample byte streams.

## Native scope and budgets

The screen-off `showResult` Champion branch calls `music(4)` before the existing
round cue. Ordinary result cards keep their current arena score. Existing
`showTitle`/`showSelect` calls restore title music. No new per-frame task,
timer, trace field, native struct, live DMA, actor/OBJ allocation or backend
change is introduced. The combined Training opponent selection code remains
unchanged. `music()` rejects indices above 4; compile-time checks pin every
effects-first module ID (`MOD_EFFECTS=0`, `MOD_MUSIC0..4=1..5`).

The soundbank remains one dedicated LoROM bank, bank 24. It grows from 17,082
to 19,330 bytes (+2,248), leaving 13,438 bytes in that bank. All fifteen BRR
source identities remain unchanged: the new module references the title's
existing sources 4–8 and adds no sample storage. The new module has 2,234
resident data bytes and 1,928 music BRR bytes. All four resident effects require
1,944 additional bytes. Starting at SPC `$1A00`, the 6,106-byte combined load
ends at `$31DA` exclusive, leaving 52,774 bytes above it. Echo and streaming
allocations remain zero. This accounting includes word-rounded transfers.

`soundbank_budget()` reads SMConv's actual binary tables, source lengths and
module word counts and raises explicit errors for invalid module/source
counts, out-of-bank pointers, nonzero echo or SPC overflow. The composition
writer separately checks tracker sample/event/length bounds. These checks do
not disappear under Python optimization.

The investigated pinned sources were `.tools/it2spc.cpp` (`Bank::Export`,
`Module::Export`, `Source::Export`, `$1A00` pointer base) and
`.tools/snesmod.asm` (`spcLoad`, `spcLoadEffect`, word-sized transfers), alongside
the SDK sound API. Existing C still loads music, reloads all four resident
effects, and uses the existing queued/coalesced effect path.

There are exactly 219 generated files, up from 218. Only `soundbank.asm` and
`soundbank.bnk` change among the old generated files; `music4.it` is added.
The other 216 files are preserved (text compared after LF normalization,
binary assets byte-for-byte). All fighter/stage/UI art, source masters and
prompts remain intact. `release_evidence.GENERATED_ASSET_COUNT` is 219 and
`tools/victory_music.py` is included in source-input provenance.

## Focused verification

Run `tools/test_champion_audio.py` with the pinned Python/core in a hidden
background process at BELOW_NORMAL priority, affinity 14/15 (or the last two
logical CPUs). It writes only `docs/champion-audio-report.json` and ignored
`build/champion-audio` captures/fixture outputs. It uses no audio device,
frontend window, save states or emulated-memory writes. The test verifies its
actual host priority and affinity.

The production-ROM probe captures the original cues and all five scores,
measures signed-16 stereo PCM peaks/RMS/clipping/near-silence, and correlates a
full score-length passage against its next cycle using both amplitude envelope
and zero-crossing structure. It earns the ending by defeating all eleven other
fighters using the existing real-controller Arcade policy. It checks an
ordinary result retains arena music, captures the final arena-to-victory load
and SPC FIFO drain, and captures both A and Start exits restoring title music.

The focused capture run completed successfully on the child ROM in 173.453
seconds. The victory capture spans 72.580462 seconds, with peak 2,366/32,768,
RMS 388.0889, zero clipped samples and a longest near-zero interval of
0.114451 seconds. Its observed native repeat is 34.900375 seconds (SPC tempo
quantization differs from ideal IT timing); the full-passage amplitude and
zero-crossing correlations are 0.999323 and 0.978883. Both exceed the existing
0.96/0.85 thresholds. All four original score captures also remain unclipped
and retain their measured repeat structure.

The final arena-to-Champion capture has no clipping and a longest near-zero
interval of 0.185144 seconds. A and Start exits restore `musicIndex=0`, remain
unclipped, and have maximum near-zero intervals of 0.201841 and 0.200562
seconds. These bounded load intervals remain below the existing 0.5-second
dropout limit. The Champion load's SPC FIFO stays within the existing six-byte
budget and drains to zero.

The earned trophy screen does not offer attacks. To exercise every resident
cue against the new score, the probe also compiles an explicitly identified
test-only ROM under `build/champion-audio-fixture`. Its sole C substitution is
`spcLoad(MOD_MUSIC0+index)` to `spcLoad(MOD_MUSIC4)`. Controller-driven cold-boot
control/repeat/active comparisons then exercise actual swing, impact, special
and confirmation cues. This fixture is not the deliverable ROM; its source
change and ROM hash are recorded separately. Mixed PCM differences include
music-voice interaction and are not isolated source samples.

All four fixture cue comparisons are deterministic on repeated control boots,
produce measurable mixed-PCM changes, and remain unclipped. Delta RMS values
are swing 170.2050, impact 190.2286, special 366.7099 and confirmation 206.6321;
the highest active mixed peak is 3,008/32,768. The production ROM retains its
Champion-only music mapping throughout this proof. All cue captures under the
victory score have near-zero intervals shorter than 0.092 seconds.

These are capture-only technical checks, not a listening judgment. The child
does not run the whole six-suite batch, compatibility/matrix/endurance/fresh
source release gates, or packaging. Canonical root native/evidence reports are
preserved at their parent revisions. Parent integration must run its gates
against its next exact source freeze, including the independent pause fix.
Human listening/gameplay/controller/consent/public-use reviews and hardware
support remain outside this focused evidence.
