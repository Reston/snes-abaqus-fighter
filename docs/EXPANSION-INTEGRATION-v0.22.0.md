# How the ten improvements share the cartridge

The [combined release note](RELEASE-v0.22.0.md) identifies the tested ROM and
links all ten merged feature PRs. The
[verification record](expansion-v0.22.0-verification.json) binds the native
reports to that cartridge and the committed source. This note explains the
integration decisions a reviewer needs to preserve.

## Contact, animation and sound

Each contact selects one light, strong or guard effect, one hitstop duration
(4/6/3 ticks), and one sound cue. A stronger simultaneous contact retains the
shared effect slot and its sound. Fighter intro/victory accents borrow that
slot only when no actual impact owns it. No extra effect OBJ is allocated.

Weighted sequencing and fighter gestures select from the approved 64 poses.
Landing holds are visual and yield to real input. Super animation uses the
same actor streams. The renderer still uploads at most one 3,840-byte actor
per vblank; the 320-byte HUD, guide and Training footer yield to that upload.

Stage HDMA adds the same horizontal impact offset to all three scenery bands;
the floor remains fixed apart from the contact shake. The ordinary ambient
clock freezes during round end. A separate bounded winner clock publishes the
celebration after the KO work, then returns to neutral. A KO can retain a final
hitstop value because round-end simulation takes priority; that retained value
does not block the separate celebration. Live hitstop and pause still freeze
ordinary ambient work.

The resident audio engine owns the single queued contact cue, speech ducking
and restore. Attack starts retain their original cue. All five original
scores and four original resident BRR sources remain intact; the new resident
effects and spoken announcements fit the existing soundbank bank.

## Four buttons, supers and practice

Y/X and B/A retain their punch/kick roles. Supers use both fresh Y+B edges on
one neutral, grounded, full-gauge sample. Their rejected chord does not become
an ordinary attack, and the CPU uses the same command path after defense.
Normal/Hard commitments are sampled and fallible. No opponent input or future
outcome enters the personality policy.

Training counts actual damage from normal and super contacts. Its normal-to-
special drill and `SP!` cue distinguish an ordinary paid special from a super.
History samples the cleaned P1 signature, ignores menu controls and preserves
separate taps. Snapshot, individual token construction and row publication
use separate service samples. Status formatting keeps immutable labels cached
and uses bounded decimal subtraction instead of software division.

## Keeping a native tick within budget

Combined contact, CPU and display work needed shorter execution paths. The
CPU caches its unsigned frame phase and profile values, uses fixed fighter
indices, and evaluates pure range/chance guards before expensive modulo work.
It retains its random-call order, decisions and fallible priorities.

No-op super and Training helper calls are guarded before far-pointer setup.
The ordinary unblocked P1 damage observer uses the caller's finished HP scratch
word for its bounded total. A fixed-victim knockdown adapter applies the same
stores after `applyHitReaction` has already cleared action and input fields;
linked throw victims retain the original release path. The adapter explicitly
clears `connected`, which a simultaneous trade can set again.

The live `DOWN_FLIGHT` renderer specializes the existing pose/state/frame
selection and capped animation clock. Intro, round-end and all other states
use their normal paths. This preserves the visible sequence while avoiding
the full state scans on the heaviest contact sample. The animation comparison
control retains this shared renderer branch; only its sequencer function uses
the old timing. Its proof therefore compares non-animation state under that
explicit control scope.

These changes add no further mutable storage. The
[preservation record](expansion-preservation-v0.22.0.json) independently checks
the 219-file inventory, eight permitted generated changes, protected source
art, 1,271 unchanged prior RAM labels and five documented metadata/libc moves.
Fighter64/Wave16, TRACE0..122 and the native hardware/trace assembly remain
unchanged. The final six suites and ten focused proofs retain strict live
cadence, transfer, OBJ and SPC assertions with all features enabled.
