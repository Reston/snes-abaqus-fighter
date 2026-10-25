# Topic 5: original audio and native sound levels

Current combined release: [v0.29.0](RELEASE-v0.29.0.md) · [current verification](verification-v0.29.0.json). The implementation measurements below retain their isolated/historical scope.

This isolated feature targets `integration/six-improvements-v029`. The parent
owns combined verification, fresh export, final generated outputs and merge.
The cartridge remains the native 4 MiB NTSC FastROM LoROM game. No browser
code, combat rules, hardware/trace assembly, art or palettes change here.

## What to play

Pause with either pad's Start. The uploaded pause card says **PAUSED - Y
SOUND**. Y opens **Sound Levels**, native `pausePage = 4`. Up/Down selects
Music, Effects or Announcer; Left/Right chooses Off, Low, Medium or High.
Changes saturate at the ends. X previews the selected effects/announcer
channel. Music plays continuously at its selected level. Defaults are Medium
music and High effects/announcer. Preferences persist through matches,
Training resets, roster/title and music reloads, and reset on cold boot.

Select returns to the originating guide or ordinary pause. A/Start resumes;
B returns to roster. The existing Start > B > A > Select ownership remains.
Controls, Moves and Training keep pages 1/2/3 and their Select/Left/Right
routes. Y is available from each guide. Training X still changes the ordinary
paused dummy; the CPU's L/R difficulty route remains on ordinary pause. On
the sound page L retains music on/off, preserving the chosen level (or
restoring the last audible level after Off); R retains
the scenery comfort toggle. Opposite directions/shoulders across pads cancel.

All operations use SNES controller input, so this page is part of the same
ROM used by the browser player. No frontend memory writes or web changes
are needed. Actual browser launch/control mapping remains the automatic-start
topic and parent integration's verification responsibility.

## Music and feedback

Five original sixteen-bar arrangements replace the old scores:

| Scene | Arrangement | Tempo | Character |
| --- | --- | --- | --- |
| Menu | After Hours - Lobby | 114 | C-major glass-key call/answer, syncopated bass |
| Las Condes | Night Shift | 124 | D-minor reed lead, driving kick variation |
| El Castillo | Copper Steps | 108 | A-minor descending harmony and spacious melody |
| La Oficina | Deadline Funk | 120 | E-minor clipped keys, displaced bass and lead accents |
| Champion | Lights On | 112 | C-major rising fanfare, answering phrases and final resolution |

`assets/audio/audio29/scores.json` contains the authored notes, roots, rhythms
and instrument choices. `tools/audio29_assets.py` deterministically synthesizes
warm FM reed, rounded bass, dry kick, brush snare, closed hat and glass keys.
All scores share those six samples. Four music voices include an answering
harmony on the hat channel, retaining the original four-voice music bound.
No commercial melody/sample, download, TTS/API call or external service is used.

The thirteen resident cue slots keep all prior semantic numbers and add two:

| Slot | Meaning | Current sound |
| --- | --- | --- |
| 0 | swing | short shaped air swish |
| 1 | light contact | dry high crack with small pitched body |
| 2 | special | rising energy sweep |
| 3 | legacy confirmation | two-note bell |
| 4 | strong contact | lower, longer body impact |
| 5 | block | short inharmonic metal ring |
| 6/7/8 | Round/Fight/KO | retained project-authored Zira utterances |
| 9 | menu/round accent | short major chord |
| 10 | victory/result | rising tonic cadence |
| 11 | throw lift | shaped cloth/air pull |
| 12 | knockdown landing | low floor/body thump and short slap |

The old five IT scores, eleven-cue IT and old cue encoder are explicit
historical source assets under `assets/audio/history-v028/`; their provenance
records the approved v0.28 identity. Original Zira WAVs and their earlier
provenance stay untouched. Old generator functions remain historical code.

Music module gains are 0/24/48/72. Effect and voice gains independently use
0/5/10/14 out of 15, with quieter whiffs and menu accents. Speech ducks the
selected music gain to half and restores that gain, including zero. Muted
speech neither ducks nor suppresses contacts. Effects and speech mute only
their own future cue commands; a previously started short resident sample
finishes its bounded tail. No global stop command silences another channel.

## Native ownership and hooks

All new mutable bytes live in `v29AudioState[32]` at `$7F:05F8`; 12 are used:

| Bytes | Ownership |
| --- | --- |
| 0/1/2 | music/effects/announcer levels |
| 3/4 | sound cursor / cold-boot initialization stamp |
| 5/6 | reserved, untouched |
| 7/8/9/10 | last effect volpan/slot, command kind, wrapping command serial |
| 11 | originating pause page |
| 12 | cached master music gain, avoiding a per-combat-tick ROM lookup |
| 13 | last audible music level, restored by the legacy toggle after Off |
| 14..31 | reserved, untouched |

There are no new mutable definitions. Literal level names use explicit
branches: this compiler puts `const char[][]` into initialized WRAM. Both
hardware/trace assembly files, Fighter64/Wave16 and TRACE0..122 remain exact.

Small shared hooks are limited to:

- `src/audio_presentation.h`: per-channel filtering/gain and music target;
  retain existing intro/KO/result observers. Existing `audioCue`, `sound`,
  `soundImpact`, `audioAnnounce` APIs remain available to Bonus and Arenas.
- `src/knockdown.h`: emit slot 11 at accepted throw lift, slot 12 after actual
  floor impact. These event hooks avoid per-frame down-state polling. The
  final KO announcement still wins the frame's sound priority.
- `src/game.c`: paused Y routing, sound Select return, sound-page key dispatch
  and legacy music-toggle delegate.
- `src/pause_guide.h`: visible entry hint and the separate three-phase sound
  builder. It reuses existing guide glyphs, panel memory and DMA.
- `tools/audio_assets.py`: current cue delegate and thirteen-slot names;
  audio-only regeneration also writes current scores.
- `tools/make_assets.py`: invoke current scores after historical generation
  and validate thirteen resident effects.

Expected generated-output allowlist is exactly `music0.it` through
`music4.it`, `effects.it`, `soundbank.bnk`, `soundbank.asm`. No tracked
generated file or dist output belongs in this child PR. Parent regeneration
uses `tools/build.py` with the normal dependency graph, including
`audio29_assets.py` and all authored audio assets.

Bank 24 is **27,470 / 32,768 bytes**, leaving **5,298 bytes**. Thirteen
resident cues use **11,914 BRR bytes**. Each music module plus shared samples
and all cues ends at or below SPC `$587E`, leaving at least **42,882 bytes**.
There is no echo, streaming or spin/poll loop. The original assembly adapter
still transfers at most one ready three-byte FIFO record per frame. Runtime
cue/envelope writes remain mutually exclusive, at most one per tick.

No actor/OBJ/palette/tile allocation or transfer is added. The guide's single
1,472-byte range yields to the original maximum one 3,840-byte actor upload
per blank. No write targets the unsafe old ambient address `$3C00`.

## Focused verification

`tools/test_audio29.py` drives only controller callbacks and reads actual
WRAM/VRAM, PPU output and PCM on both pinned cores. It never opens an audio
device/window, writes emulated memory or uses save states. The report binds
ROM, source, harness/dependency hashes and captured media. Full scores plus
loop boundaries are measured; short native excerpts are retained for human
listening. Objective PCM measurements establish audibility, different
controller-triggered cues and gain/mute behavior, not a human quality verdict.

The final exact commands, counts, ROM and media are in
`docs/audio29-report.json`. Diagnostics remain under ignored `build/` and are
not pooled into the final record. The parent must rerun combined six-suite,
reproduction and browser proofs after integrating the other five topics.
Human listening and original-console/controller review remain unclaimed.

## Historical isolated integration blocker

The default eleven-win Negger Champion fixture encounters one strict SDK
stall at native frame 37312, Arcade opponent index 9, round 2, Negger versus
Cristobal, with both walking and no active speech. The native frame delta is
`[frame 0, VBlank 1, SDK lag 1]`; it is retained as a failure, not collapsed
or excluded. A control ROM using the legacy v0.28 audio runtime, the same
current score bank, and the current unchanged combat reproduces the exact
same frame/state failure. That control is ROM
`fa5e27d2e8f172ff5ea3cd570cd94eaed52a578f863439741fefd970b66517f5`.
This establishes that the new mixer is not the cause; it does not establish
that the exact approved v0.28 ROM follows the same long controller route.

The earned Champion arrangement is captured and technically audible, but its
complete long-ladder case remains **failed on cadence**. Both shorter core
audio cases retain strict native checks and pass independently. Parent must
resolve/reassess this shared timing blocker before claiming combined verified
merge. The legacy control and failing exact-candidate evidence are separate
from passing cases in `audio29-report.json`. No CPU or HUD trial is retained.

Accuracy exposes a fractional 32040.5 Hz AV rate and independent audio packet
phase. Twelve 240-frame windows on the exact approved ROM measure errors
from -12.28 to +11.72 stereo sample frames against nominal AV duration, with
zero native cadence failures. Its capture bound is one 64-frame packet,
less than an eighth of a video tick, while Snes9x retains its three-sample
bound. The core's [audio callback and retro_run flush](https://github.com/libretro/bsnes2014/blob/master/target-libretro/libretro.cpp)
provide the packet contract. Every native frame/VBlank/SDK/OBJ/FIFO assertion
remains unchanged; every PCM sample is retained. Captures store integer WAV
rate 32040 Hz, so their export time base rounds the fractional AV rate.

## Historical isolated delivery

Focused Snes9x and Accuracy each pass **225 checks / 20,209 strict callbacks** on ROM `240c194a09975158dfdc7d17b4569d171caba0e1caa4fa51dc9a80dea1c59360`, source freeze `8fffcf371246114fc63eb75dda05d6daf87aa8f8`. The separate earned-Champion route retains its one failed cadence callback and is not pooled into those passes. Parent must resolve the documented blocker before claiming full native cadence or combined verified merge.

Native excerpts: [menu](audio29/snes9x/menu.wav), [Las Condes](audio29/snes9x/stage0-music.wav), [El Castillo](audio29/snes9x/stage1-music.wav), [La Oficina](audio29/snes9x/stage2-music.wav), [earned Champion](audio29/champion/champion.wav). [Sound page](audio29/snes9x/05-sound-levels.png) is an actual native capture. Exact commands and all hashes are in [audio29-report.json](audio29-report.json).


## Current integration follow-up

The audio branch merged integration `1648122` and reviewed defense `99cdb4c`.
Current focused source/test freeze is `fcf6b1e7ac401d0bbc03d5d7b0594058a5b3be09`. ROM
`afc7ff2c883a5cb473df63e71e742abc7e7527b7bdeab6c42ea0fe94c05432b1` (checksum `4325`) includes Random, animated Arenas,
Auto and Defense alongside Audio; Bonus is still pending. The parent owns
final combined verification, reproduction and merge. Draft PR33 stays open.

The unchanged original earned Negger route reproduced frame 37312 on the
first merged context, ROM `4e5f7e11fb80055a6004a7c96f401a8dde5ec236cf6101d846bf415382a8a651`.
Its exact native/controller/RNG failure remains in
[the retained report](audio29-followup-original-failure.json).
Input-only, controls-only, modulo and diagnostic trials are retained separately.
The final fix changes only `captureInput` and `controls` to two direct actor
expansions in `src/audio29_native.h`. The original tests, calls and writes
remain in order, mechanically checked against the reviewed defense merge.
All 1,329 existing RAM labels remain exact, including reservations and markers.
CPU source, hardware/trace assembly and every generated asset remain exact
against that same current-audio control. No timing, decision or music change
is used. The original route then passes on the pre-defense context with only
these same two replacements: ROM
`40dd19d9bb8d031f4ae4d27032cefe4a863da2718c07d98d8696d1edadcc07c9`,
[full earned result](audio29-followup-original-route-fixed.json).

Emitted `captureInput` grows 2,803 to 3,090 bytes, locals shrink 28 to 16,
and indirect field instructions fall 77 to zero. `controls` grows 3,353 to
4,258 bytes, locals shrink 52 to 24, and indirect field instructions fall
81 to 16 (remaining profile accesses). Total ROM growth is 1,192 bytes;
142 static indirect field instructions disappear. Total instruction counts
include both actor branches, so they are not a per-call cycle measurement.
No direct scanline/cycle claim is made. Every native section remains within
one 32 KiB LoROM bank; the largest retained section is 30,720 bytes.

The unmodified historical throw policy hits its existing 10,000-step match
bound after Defense changes wake protection; that report is retained with
zero cadence failures up to its bound. A separate current policy guards
startup/active time, then approaches during visibly observed recovery.
The original policy stays callable. The current policy retains the same
10,000-step bound, maximum three attempts, eleven actual earned wins and all
native counters. It passes the complete Champion route on the current ROM.
The failed exploratory kick/super policy also remains a failed report.

Snes9x passes **254 checks / 52,606 strict callbacks**,
including the complete current earned Champion route. Accuracy passes
**224 checks / 20,209 strict callbacks**.
All five arrangements, all three arenas, actual contacts/announcements,
independent levels/mutes, duck restore, paired supers and rapid mixed contacts
retain the original sound and PCM assertions. Peak FIFO backlog is three bytes;
no candidate SDK lag, dropped callback, OBJ overflow or clipping is accepted.
`--combined` calls the parent's `v029_contracts.validate` for added arena assets;
it does not weaken audio or native assertions. The bank remains 27,470 bytes.
The native page/routes and generator output allowlist above remain unchanged;
the Defense `soundImpact(SOUND_GUARD)` hook stays exact.

The independent replay runs 39 cases (all twelve CPUs at three difficulties
plus three both-pad Local cases). All candidate cases pass strict cadence.
**38 cases / 37,050 snapshots** match
every unmasked Fighter128/Wave32 byte, all TRACE0..122, RNG, CPU, pads/edges,
recoil and super bytes at the identical physical callback. The unoptimized
control's separate stalls and resulting timestamp differences remain **failed**
in [the replay report](audio29-followup-native.json), including full paired
streams. That diagnostic command exits 1; it is never called an all-pass
equivalence suite. No callback is removed, aligned or collapsed, no field is
masked, and no baseline/candidate cadence allowance is added. The independent
structural check proves the two C templates retain the exact original operation
order; behavior equality across stalled physical callback timestamps remains
unclaimed. This limitation does not conceal a candidate cadence failure.

[Current Sound page](audio29-followup/snes9x/05-sound-levels.png),
[current menu music](audio29-followup/snes9x/menu.wav) and
[current earned Champion](audio29-followup/snes9x/champion.wav) are actual native
captures. Exact commands, hashes, counts, all negative controls and media are
bound in [audio29-report.json](audio29-report.json). The old aggregate is retained
byte-for-byte as [audio29-isolated-report.json](audio29-isolated-report.json).
The exact tested cartridge, symbols, manifest, assembly and all generated
outputs remain ignored under `build/audio29-followup-final-afc7ff2c`; tracked
generated/dist outputs are restored before the evidence commit.
Human listening, physical controllers, original hardware and final six-topic
combined verification remain separate from this focused delivery.
