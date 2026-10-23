# Expansion 02: readable native contacts

> Combined v0.22.0: this note retains the original feature-branch design and
> isolated measurements. The linked focused report and native captures are
> regenerated for the combined cartridge. Use the [combined release note](RELEASE-v0.22.0.md)
> and [verification record](expansion-v0.22.0-verification.json) for current
> identity, coverage and integration contracts.

Feature branch: `t3/impact-spark-polish`, based on integration commit `610537d`.
The isolated native candidate is a 4 MiB NTSC FastROM LoROM built with the pinned
PVSnesLib 4.6.0 toolchain. Its SHA256 is
`75745e5a96438666747322910205ad8bf2db7bfd9cb6c6bef163bd40bc811e98`.
The ROM, symbols and manifest are local build products, intentionally absent from
the feature commit. Version identity remains owned by the integration branch.

## Behavior

- Y/B light contacts use a compact amber diamond followed by separated flecks,
  four simulation ticks of hitstop and one pixel of horizontal camera response.
- X/A and other strong contacts use a larger cream/gold burst, split rays and
  embers, six ticks of hitstop and the restrained horizontal sequence
  `+2, 0, -1, 0, +1, 0` pixels, mirrored for the opposite contact direction.
- Blocks show an expanding hollow cyan brace, three ticks of hitstop and no
  camera shake. Low contacts stay at the legs; crouched high contacts move down
  to the crouching torso. There is no screen-wide flash or palette change.
- The spark retains its contact direction throughout hitstop. Its age, position
  and phase freeze with combat. Pause also freezes feedback and the camera.
  Ordinary Training Select resets the effect and shake.
- A simultaneous strong/light trade keeps the strong contact's spark, direction
  and six-tick freeze regardless of player port. Both ordinary damage/recoil
  results still resolve. Equal-class trades retain the previous last-contact
  ownership. Detached projectiles and delayed throw damage count as strong.

Damage, reach, startup, active/recovery profiles, guard stun, energy and command
rules are unchanged. This branch changes only hitstop and cosmetic feedback.

## Native contracts and hooks

`src/impact_presentation.h` uses the existing effect state. `fxType` low two bits
are `0` strong, `1` guard and `2` light; bit 7 latches contact direction. Existing
throw/landing/clash assignments of `0/1` remain valid. There is no new mutable
state, Fighter/Wave field or TRACE word. All baseline RAM/direct-page symbols,
including linker markers, retain their addresses.

The only generated asset change is `assets/generated/effects.bin`, still 2,048
bytes at VRAM `$7800-$7BFF`. Strong sparks retain OBJ cells 384/386/388/390;
guard retains 416/418. Light uses the formerly blank cells 426/428. The palette,
high/low projectile pixels and shadow pixels are byte-identical to the base.
The existing two-piece shadows remain at Y 200 with tile 430. Approved fighter
art, physical scale, palettes, portraits, stage assets and audio are untouched.

There is still exactly one 16x16 impact OBJ, at OAM byte 276 (entry 69).
Native captures exposed a pre-existing visibility issue: even a priority-3 OBJ
loses sprite overlap to earlier OAM entries. Low sparks could disappear under a
fighter. After the existing NMI OAM upload and ordinary vblank transfers,
`publishImpactPriority()` writes `$2102/$2103` to start priority at entry 69
while the spark is visible. Quiet combat and menus restore entry zero. This
adds two register writes, zero DMA bytes and zero OBJ entries. Relative ordering
of the fighters and their shadows stays the same. Waves also precede actors
during a spark. The focused proof checks the complete spark's actual PPU pixels,
including low hits, on both Snes9x and bsnes2014 Accuracy.

The hardware reference for restoring the first sprite after OAM transfer is
[SNESdev's PPU memory documentation](https://snes.nesdev.org/wiki/Reading_and_writing_PPU_memory).
The pinned SDK's `include/snes/sprite.h` documents `$2102/$2103` and their
priority-rotation bits. The one-actor-per-vblank transfer path is unchanged.

The small `game.c` hooks are:

- Include the module after existing global declarations.
- Pass snapshotted `m0/m1` as the appended `impactAction` argument to
  `hurtWithRecoil`. This survives the opposing trade cancel. The `hurt` wrapper
  passes special action 7 for projectiles/delayed throws.
- Start feedback inside `hurtWithRecoil`, then use `drawImpact()` in `drawFight`.
- Publish OBJ priority after vblank transfers and use `impactScroll()` for the
  horizontal BG1 offset. Its vertical baseline remains 511.

## Parent integration notes

Audio10 exports `AUDIO_PRESENTATION_H`, `soundImpact`, `SOUND_LIGHT`,
`SOUND_STRONG` and `SOUND_GUARD`. The guarded contact hook already calls that API
once and falls back to the original `sound(1)` when Audio10 is absent. Retain
this single hook when resolving Audio10's overlapping `soundContact(blocked,
a->action)` change; do not keep both calls. The snapshotted action correctly
classifies canceled trade actions and detached waves. No audio assets or sound
implementation are changed here.

Stage08 should compose the horizontal `impactScroll()` value with its BG1 base
scroll, modulo 512, and preserve pause behavior. Keep `publishImpactPriority()`
after the NMI OAM transfer. Other features reading `fxType` must mask the low
two bits rather than treating the byte as a boolean.

Feature03 retains all damage/profile ownership. Shared tests that hard-code
five-tick real-hit hitstop need the new light=4/strong=6 expectation. The parent
owns those suite changes and the combined-ROM regressions. Supers can use the
strong default for actions other than 1/4. No main branch, release package,
shared suite report or release-readiness claim is changed by this feature.

## Focused evidence

Run silently with the canonical Python after building the native ROM:

```powershell
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/build.py
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/test_expansion_02_impact.py
```

`docs/expansion-02-report.json` identifies the exact tested ROM. The driver uses
only real controller input for boot, selection, approach, strikes, guards,
jumps, projectiles, trades, pause and reset. It reads native video, VRAM, OAM,
symbols and telemetry; it never writes WRAM, loads a save state, opens a GUI or
plays audio.

The final candidate passes 1,930 focused checks. Peak observed fetch is 34 tiles
within the 34-tile limit; every sampled STAT77 overflow mask is clear. Each
sustained session advances exactly 600 native ticks in 600 video frames. The
paired low-wave fixture observes thirteen two-wave frames on each stage. All
1,280 baseline RAM/direct-page symbols including linker markers match. Linked
ROM section coverage is 3,259,054 bytes with 935,250 bytes unallocated; every
section fits its 32 KiB bank. The largest changed routine, `hurtWithRecoil`, is
2,232 linked bytes. A second ordinary build reproduces the same cartridge hash.

The proof covers 72 contact cases (twelve cases, both ports, all three stages),
every authored phase in actual video, eight detached high/low wave hit/block
cases, equal/mixed trades and both-port pause/reset. Three sustained 600-frame
contact sessions check exact native cadence. Three synchronized low-wave cases
check coexistence/clash/floor fetch safety. Twelve independent Accuracy-core
contact cases verify full spark visibility and the same freeze/camera behavior.
Snapshots and short native capture clips are under
`docs/screenshots/expansion-02/`; GIF timing is a viewing approximation.

The report records exact OBJ fetch peaks and actual STAT77, bank allocation and
linked native function sizes. This is bounded feature evidence, not a full
endurance run, six-suite result, hardware validation or release certification.
Human feel review and the combined-feature integration remain with the parent.
