# v0.6.0 - air attacks, throws and recovery

This development milestone expands all twelve fighters to 64 original frames
in the 4 MiB native SNES cartridge. Each fighter adds dedicated air punches,
air kicks, thrower and victim drawings, knockdown, get-up and wake guard.
The original 48 native frames and fifteen-color palette bytes are preserved.
One physical scale applies across all 64 frames on the existing 96x80 canvas.

Throws now have separate attacker/victim ownership, six live lift ticks and
ballistic release. Damage applies once on ground impact. A projectile that
interrupts the thrower during lift releases the victim safely and cancels the
pending throw damage. Mutual throws tech; active throws beat normals and
active direct specials beat throws.

Heavy sweeps, uppercuts and rising specials cause bounded knockdown. Floor,
get-up and wake take 18, 10 and 6 live ticks. Downed fighters cannot act or be
hit again. New inputs in the final six wake ticks can buffer a command; earlier
inputs are discarded. Four free ticks of contact invulnerability follow wake.
Pause and hitstop freeze these states and their timers. Training heals only
after hit/down recovery and invulnerability finish, and Select resets the state.

Air normals use visible anticipation, extension and recovery drawings. Landing
ends the air action before contact resolution. Source prompts, reference roles,
hashes and built-in ImageGen provenance accompany every new airborne atlas.

The native hot paths cache actor banks, attack timings and unchanged sprite
geometry. Health/energy bars and read-only telemetry use bounded assembly
routines. Impact UI work is spread across frozen hitstop ticks, and interface
DMA waits for a blank without an actor transfer. The four original sound cues
are preloaded into SPC memory; combat triggers playback without streaming BRR
sample bytes. Same-frame cues use a single prioritized sound command. Music
source files and the original cue amplitudes are preserved.

Holding back during a real hit reaction cannot turn a true combo into chip
damage. Guard stun still permits continued blocking, so a held-back block
string remains protected.

## Verification

All four native suites pass against the same 4,194,304-byte cartridge:

`0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`

| Suite | Passing checks |
| --- | ---: |
| Gameplay and progression | 2,595 |
| Roster, native VRAM/OAM and animation | 18,085 |
| Menus, portraits, stages and results | 215 |
| Input, contact, recovery, audio and cadence | 604 |
| Total | 21,499 |

Verification uses real controller input and read-only native telemetry, PPU
frames and captured SPC samples in the official Snes9x 1.63 libretro core.
Automated runs are silent and headless. The transition, two-controller air and
trade, and confirmed-combo stress cases retain 600 simulation ticks per 600
emulated video frames. Reports and native captures are retained under `docs/`.
Regenerating all native assets with `Build.cmd --assets` and relinking after the
canonical batch produced the identical cartridge SHA above.
Two package runs with identical inputs also produced identical ZIP bytes;
the technical package audit passes 199 checks. The development archive contains
the tested ROM, Snes9x, control defaults, reports, guides and license notices.

The input suite includes mirrored throw escape, tech and delayed impact,
projectile interruption of a throw, bounded down/wake recovery, close-range
re-hit rejection, pause/input-buffer behavior, and held-back hit/guard strings.
These automated results do not certify the public-release gates in
[PUBLIC-RELEASE.md](PUBLIC-RELEASE.md). Independent-engine and endurance checks,
CPU improvements, human balance/motion/listening sessions, controller/hardware
validation and public-use approval remain open.
