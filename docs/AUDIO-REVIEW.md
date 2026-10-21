# v0.8.1 native audio review

This is supplemental audio evidence and listening material for the unchanged
v0.8.1 cartridge, SHA256
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`.
The six canonical suites and packaged game retain their existing identities.
This audit does not change the music, effects, mix, native code or ROM.

## Listening material

Extract [the audio review ZIP](../dist/Abaqus-After-Hours-v0.8.1-Audio-Review.zip).
It contains twelve native, signed-16 stereo WAV captures, a manifest with their
hashes and measured properties, and a short README. Nothing plays automatically.
The capture process opens no speaker device or emulator window.

Two complete runs of the same harness produced identical active cue files,
music files and ZIP bytes: **15,449,631 bytes**, SHA256
`5c66aeba230fded8e27507784a47fb72a918d1f854d57c7a983911a925871205`.
The separate [repeat report](audio-repeat-test-report.json) records that
comparison. This does not alter the checksum of the packaged game.

| Files | Purpose |
| --- | --- |
| `swing-control.wav`, `swing-active.wav` | Same music timeline, with a real distant normal attack only in the active take |
| `impact-control.wav`, `impact-active.wav` | Same normal attack and music timeline; only the closer active take makes contact |
| `special-control.wav`, `special-active.wav` | Actual projectile startup, recorded before the wave reaches the opponent |
| `round-confirm-control.wav`, `round-confirm-active.wav` | Title music with and without the real confirmation/scene transition |
| `music-title.wav` | Title score |
| `music-las-condes.wav` | Las Condes score |
| `music-el-castillo.wav` | El Castillo score |
| `music-la-oficina.wav` | La Oficina score |

The four music files last approximately one minute each. Cue pairs are short
comparisons. Start at a comfortable volume and keep the same playback gain for
both files in a pair. The differences are mixed PCM, including any interaction
with the music voices; these are not isolated source samples.

## What the automated audit establishes

[tools/test_audio.py](../tools/test_audio.py) loads the pinned Snes9x core and
drives the real cartridge with controller callbacks. It verifies the current
ROM/core identities and binds the music IT files to the exact-ROM
[fresh-source rebuild](fresh-build-test-report.json).

- Each cue's control take repeats bit-for-bit across cold boots. The active
  fixture must perform the intended action and produce a substantial PCM
  difference from its matched control. Both takes must remain non-silent.
- Every observed video frame has one 256x224 callback and complete stereo PCM.
  Total sample frames must agree with native AV timing within two PCM frames.
  Live/title TRACE cadence and scene identity are checked; a real scene load
  may retain old TRACE while forced blank runs, but audio/video cadence remains
  required.
- Every active/control cue and full music capture contains zero exact
  full-scale samples. Music contains no continuous near-zero stereo interval
  of 0.5 seconds or longer, including intervals crossing analysis boundaries.
- A long passage, approximately the nominal score length, repeats in actual
  PCM near the expected period. Both amplitude-envelope and zero-crossing
  correlations are required, with sample-time phase refinement. This is audio
  structure evidence, not direct SPC order-register telemetry.

| Score | Observed PCM repeat | Envelope correlation | Zero-crossing correlation |
| --- | --- | --- | --- |
| Title | 29.72285 s | 0.99955 | 0.96787 |
| Las Condes | 29.72285 s | 0.99947 | 0.96137 |
| El Castillo | 28.95581 s | 0.99936 | 0.96783 |
| La Oficina | 30.10637 s | 0.99945 | 0.96164 |

Captures span more than two measured repeat intervals. The source tracker
duration is only a search estimate; the table reports native PCM observations.
The authoritative details are in [audio-test-report.json](audio-test-report.json).

These checks do not establish a pleasing mix, a seamless-sounding loop,
freedom from short clicks/distortion, understandable cues on every device,
or human listening approval. Those judgments remain open in the
[public-release gates](PUBLIC-RELEASE.md). The playback API is documented by
[PVSnesLib's sound header](https://github.com/alekmaul/pvsneslib/blob/4.6.0/pvsneslib/include/snes/sound.h).

## Reproduce

From the project root, with the pinned tools and exact-ROM fresh-build report:

```powershell
& .\.tools\python\python.exe tools/test_audio.py
```

The script writes the report, WAVs under ignored `build/audio-review/`, and
the separate listening ZIP under ignored `dist/`. It does not rebuild or
replace the tested game package. This is an optional supplement to `Test.cmd`.

## Human listening record

The user requested a replay after not hearing the earlier material. An
explicitly requested Windows playback presented a 13.948-second preview at
the captures' original gain: title music from seconds 24-36, then the impact
and special captures, separated by 0.4 seconds of silence. The user replied:
**"I heard it; no issue noticed."** The playback device was not specified.
The [feedback record](review-feedback.json) pins the source archive, preview
hash, exact sample ranges and response. The original twelve WAVs and ZIP
remain unchanged.

This records a successful brief listening check. The four complete scores,
other cue classes and a busy live exchange still need listening review.
Record actual observations below; leave unreviewed items blank.

| Item | Listener observation |
| --- | --- |
| Listener, date, ROM and audio ZIP SHA256 | User; recorded 2026-10-21 UTC; same ROM/ZIP identified above |
| Playback device/software and gain setting | Device not specified; Windows default output; original capture gain and unchanged system volume |
| Swing/impact/special/confirmation distinction and timing | Brief title/impact/special preview heard with no issue reported; other cues unreviewed |
| Music remains clear through effects | No issue reported in the preview; busy live exchange unreviewed |
| Music balance, repetition and transitions | No issue reported in the title excerpt; full four-score listening unreviewed |
| Loop seam, clicks, harshness or pumping | |
| Comfortable level and clarity on the intended setup | |
| Blocking defect and reproduction, or requested mix change | |

No listening approval is inferred from the automated report or from downloading
the files.
