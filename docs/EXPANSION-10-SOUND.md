# Expansion 10: resident sound presentation

> Combined v0.22.0: this note retains the original feature-branch design and
> isolated measurements. The linked focused report and native captures are
> regenerated for the combined cartridge. Use the [combined release note](RELEASE-v0.22.0.md)
> and [verification record](expansion-v0.22.0-verification.json) for current
> identity, coverage and integration contracts.

This feature extends the native PVSnesLib/SNESMod sound path. The game still
boots as a 4 MiB NTSC FastROM LoROM cartridge. The original five scores, four
original synthesized cues and all visual assets remain retained. This is a
focused feature candidate, not the combined ten-feature or release evidence.

## Behavior and integration

Light contacts retain the original dry impact. Strong contacts add a lower,
longer body and guard contacts use a short metallic ring. Menu confirmations
and round openings use an original rising C-major chord. The existing arena
score fades in after a scene load, ducks during speech and returns to its
normal level. A short original tonic cadence follows a round and accompanies
the result card. The original fifth Champion score is preserved.

The announcer says **Round**, **Fight**, and **K O** using real synthesized
speech. Round plays at intro 104, Fight at intro 50, and K O on the first
round-end tick after actual zero HP. Healthy timeouts receive the cadence
without a false KO announcement. Pause/resume does not replay a frozen intro
milestone. No gameplay input, attack timing, hitstop or camera rule changes.

`src/audio_presentation.h` supplies the small integration API:

| API | Contract |
| --- | --- |
| `soundImpact(kind)` | `SOUND_LIGHT=0`, `SOUND_STRONG=1`, `SOUND_GUARD=2`; feature 02 may call this with its contact classification. |
| `soundContact(blocked, action)` | Standalone contact adapter: guard wins; actions 1/4 are light; other actions are strong. |
| `sound(n)` | Retains the existing swing/impact/special/confirm call interface. |
| `audioPresentationTick()` | Once before `processResidentAudioReady`; resolves announcements, cues and music envelope. |
| `audioSceneLoaded()` | Called after the existing screen-off score/effect load; starts the fade-in. |

The only combat hook changes the existing `sound(1)` contact call to
`soundContact(blocked,a->action)`. If feature 02 calls `soundImpact` itself,
the parent should use that call instead of the adapter, avoiding duplicate
classification. No feature 02 visuals or hitstop tuning are included here.

Eight initialized state bytes are defined by
`src/audio_presentation_state.h`, included after the existing definitions.
They append at `$7F:0448..044F` in this isolated candidate. Every existing
game and SDK variable keeps its address; only the two data-extent labels
grow by eight. Fighter64, Wave16 and TRACE 0..122 are untouched. The combined
candidate must audit its own final addresses.

## Resident slots and budgets

| Slot | Content |
| --- | --- |
| 0..3 | Exact original swing, light impact, special and legacy confirm BRR sources |
| 4 | Original synthesized strong impact |
| 5 | Original synthesized guard ring |
| 6..8 | Spoken Round, Fight and K O |
| 9 | Original menu/round chord |
| 10 | Original victory cadence |

All eleven slots load only during the existing screen-off music replacement.
There is no per-hit BRR transfer, streaming allocation, echo allocation or
additional hardware voice reservation. The original four-voice scores remain
unchanged. The bank occupies 28,822 of 32,768 bytes in LoROM bank 24, leaving
3,946 bytes. Resident BRR consumes 11,296 SPC bytes; the budget validator checks
every score plus all eleven effects against 64 KiB SPC RAM.

The scheduler queues at most one three-byte SPC command per video tick. Cue
and volume writes are mutually exclusive. Announcements suppress lower-priority
cues while the utterance settles. Envelope changes occur at most once every
four ticks, with no busy wait. `processResidentAudioReady` is unchanged: one
ready FIFO record, no polling or retry. Actor uploads, OBJ entries, palettes,
guide transfers, ambient cells and the SPC FIFO format are unchanged.

## Original synthesis and provenance

`tools/synthesize_announcements.ps1` exports the project-authored strings
`Round!`, `Fight!`, `K O!` through Windows
`System.Speech.Synthesis.SpeechSynthesizer`, using **Microsoft Zira Desktop**,
English US, rate 3 and volume 100. It writes mono signed16 16 kHz WAV directly
to disk and never selects a speaker output. No API key, paid service,
commercial game sample, commercial soundtrack or recorded human voice is used.
The raw exports and exact settings/hashes are retained in
`assets/audio/announcements/`, including `provenance.json`.

`tools/audio_assets.py` low-pass filters and downsamples the exports to 8 kHz,
trims only outer silence with lead/tail padding, normalizes to a signed16 peak
of 16,000 and applies a three-millisecond outer taper. The retained spoken words
last 0.37025, 0.359625 and 0.33425 seconds respectively. They are encoded as IT
samples and converted to native BRR with the pinned SMConv. Strong/guard sounds
and both musical cadences use original deterministic procedural oscillators,
envelopes and locally seeded noise.

The synthesis code follows the project license. Microsoft owns the installed
system voice; no voice engine, voice model or phoneme database is redistributed.
Only newly exported project utterance PCM is retained. This provenance records
the source rather than claiming ownership of the operating-system voice or
certifying public distribution rights. The project's human listening and
public-use review gates remain separate.

Audio-only regeneration, without touching fighter/stage generation:

```powershell
D:\snes-abaqus-fighter\.tools\python\python.exe tools/audio_assets.py
D:\snes-abaqus-fighter\.tools\python\python.exe tools/build.py
```

The ordinary full asset generator also uses the same expansion function after
generating the original scores/cues. It preserves the original RNG sequence.
The budget validator derives resident count from the effects-first module and
rejects more than sixteen slots, bank spill, echo allocation or SPC overflow.

## Focused evidence

Run the capture-only test with the background launcher:

```powershell
D:\snes-abaqus-fighter\.tools\python\python.exe tools/run_background.py --log build/audio10-test.log -- D:\snes-abaqus-fighter\.tools\python\python.exe tools/test_expansion_10_audio.py
```

The authoritative focused result is `docs/expansion-10-report.json` and its
WAVs are under `docs/expansion-10-audio/`. All gameplay uses actual controllers:
menu confirmations, all three arena intros, neutral light/strong contacts,
guarded contact, two real KO rounds and a Versus result. Additional simultaneous
two-controller combat exercises all three stages. The host reads native
telemetry and linker symbols but never writes WRAM or loads a savestate.

A separately built control cartridge changes only the eleven effect volume
bytes. It executes identical gameplay, music envelopes and SPC effect commands.
Production-minus-control PCM exposes the actual decoded cues over a matched
music timeline. Native speech is correlated against the retained spoken source
with a strict 0.80 threshold; arbitrary beeps cannot satisfy this waveform
identity check. The mixed clips retain the actual score/cue balance. The KO
WAV is a continuous six-second excerpt; the complete controller run is checked.

Checks cover cue identity, real damage/guard outcomes, cold-boot determinism,
music duck/restore, full PCM retention, silence, clipping, FIFO backlog,
one-tick native fight cadence and native OBJ overflow flags. Forced-blank scene
loading is recorded separately from live-fight cadence. The test does not
overwrite any shared six-suite report, claim an independent-core smoke, or
substitute for human listening. The parent owns combined-ROM tests and final
release decisions.

The final isolated candidate is ROM SHA256
`1910bff59f1248e36d728b30f41dfa9a9990f6161238e6ca328d3b6c56f9e1d5`,
header checksum `F17F`. Its focused report passes **159 checks**, including
2,700 simultaneous-combat frames across three arenas. Maximum observed FIFO
backlog is six bytes, with no live cadence failures, native OBJ overflow or
mixed PCM clipping. Spoken-source correlations exceed 0.91. Each live music
module plus all resident cues leaves at least 43,414 SPC bytes free. The seven
feature/compatibility C routines occupy 1,791 ROM bytes; the report also lists
the existing 1,675-byte SNESMod support section separately by name.

Audio-only regeneration reproduces `effects.it` and `soundbank.bnk` exactly,
and rebuilding reproduces this ROM hash. The existing authoring mutation suite
also passes 20 tests normally and 20 under `python -O`. These are focused
results; no six-suite total, full release-scale evidence or listening approval
is claimed.
