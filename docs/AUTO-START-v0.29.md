# Topic 3: automatic browser launch

Current combined release: [v0.29.0](RELEASE-v0.29.0.md) · [current verification](verification-v0.29.0.json). The implementation measurements below retain their isolated/historical scope.

The redundant confirmation was the browser's **Play game** overlay. Native
v0.28 already advanced automatically after arena confirmation: Arcade displays
its six-second story, then the existing 110-tick intro; Local and Training enter
that intro directly. This feature retains those native paths and proves them
with no further controller input. It changes no native source or art.

The browser now downloads and boots the native title on page load. Mode,
fighter, second player/dummy and arena remain deliberate choices. The status
explains loading and automatic fight progression. The player exposes an error
and **Try again** for loading failures, including a 90-second startup timeout.
Retry reloads the page and repeats automatic boot. A missing release manifest
also exposes retry; browsers without WebAssembly retain the ROM download route.

Video starts muted. The first trusted key, pointer or touch gesture resumes the
pinned EmulatorJS Web Audio context and enables volume without consuming the
game input. A separate **Enable sound** button supports controller users whose
gamepad activity does not grant browser user activation. Modifier/navigation
keys do not unexpectedly enable audio. Once enabled, the normal emulator mute
and volume controls own sound. Saved emulator settings are disabled so an old
saved volume cannot bypass silent boot. No music, samples or native mix changes
belong to this feature.

Automatic boot bypasses the old start button's touch detection. Touch-capable
devices therefore receive visible virtual controls directly. EmulatorJS's
startup toolbar is closed in the game-start callback: its mobile panel covered
the native Start control. Its menu icon remains available for controller
assignment, mute, restart and fullscreen.

The pinned gamepad handler's initial constructor poll precedes its connected
listener. Already-connected controllers could therefore remain unassigned.
The start callback applies its normal first-free-player policy to the first
two ports for pads found at boot. Later hotplug still belongs to EmulatorJS;
the player control menu can change assignments.

## Native and integration contract

- Native hooks: none. `src/game.c`, story, intro, pause, hardware/trace assembly,
  all other native producers and all 226 generated files are unchanged from
  integration base `29fee8343ceaa47c9c74921494142c2c02a1198f`.
- `v29AutoState[8]` is unused. Added native WRAM, code, OBJ, VRAM, palette,
  actor/UI/background DMA, SPC resources and RNG consumption: zero.
- The existing one-3840-byte-actor-per-vblank budget remains. No transfer is
  added to `$3C00` or elsewhere. Slower combat, detailed floors and every fighter
  drawing remain the base implementation.
- Generator hooks/output allowlist: none; no generated or `dist` file is part
  of the PR. The exact tested ROM, symbols, manifest and generated directory are
  retained under ignored `build/auto29-candidate/` before restoring tracked
  outputs.
- Browser hooks are confined to `web/player.js`, `web/index.html` and the
  existing singular `web/style.css`. Audio integration should retain the zero
  initial browser volume and first-interaction unlock, and apply its mix after
  unlock. The native audio page is independent.
- The parent's random-selection hooks and five other topics are outside this
  proof. No combined verification, final merge or hosted-production acceptance
  is claimed.

## Reproduction and proof

The tested isolated cartridge is **4 MiB FastROM LoROM**, checksum **DB0C**,
SHA-256 `46108c5e955733820f92c8baab4088a0f054e2b4986fb5d8093c1352e1023738`.
This is the integration contract base's cartridge with v0.29 identity/state
reservations; the browser feature adds no native changes. Implementation/harness
freeze is `9afc7ed` (the native proof's recorded source commit is `875478f`;
the intervening commit only adjusts the browser observation harness).

| Focused proof | Sessions/scenarios | Passed checks | Published-scene callbacks |
| --- | ---: | ---: | ---: |
| Pinned Snes9x 1.63 | 9 | 9,486 | 2,610 |
| Pinned bsnes2014 Accuracy | 9 | 9,486 | 2,610 |
| Actual EmulatorJS 4.2.3 WASM / headless Edge | 7 | 386 | native host owns strict cadence |

The web build boundary regression also passes all four tests. These counts
belong only to topic 3 and are not combined release-suite evidence. Native JSON
reports are canonicalized to LF for repository publication; assertions and all
recorded source/core/media hashes are unchanged.

Focused harness SHA-256:

- `tools/test_auto29.py`: `f20ef65c71c4477b3b2cd28e80349bdc0ed2feb36d4f2ffd2c6ec84adf62541c`
- `tools/test_auto29_web.mjs`: `a2d3d33f1b4f6d7a0d671dad1b3b967fa7d3584ab2662701c4da02c5046d9a70`

Use the project Python and set the wrapper's affinity before the background
launcher. All heavy commands used logical processors 6/7 (mask 192) and inherited
below-normal priority. Native proofs open no window or audio device; the
headless browser mutes speaker output. For example:

```powershell
$taskProc = Get-Process -Id $PID
$taskProc.ProcessorAffinity = 192
$taskPython = (Resolve-Path .tools/python/python.exe).Path
$taskNode = (Resolve-Path .tools/node/node-v24.22.1-win-x64/node.exe).Path
& $taskPython tools/run_background.py --log build/auto29-build.log -- $taskPython tools/build.py
& $taskPython tools/run_background.py --log build/auto29-snes9x.log -- $taskPython tools/test_auto29.py --core snes9x --report docs/auto29-snes9x.json
& $taskPython tools/run_background.py --log build/auto29-accuracy.log -- $taskPython tools/test_auto29.py --core accuracy --report docs/auto29-accuracy.json
& $taskPython tools/run_background.py --log build/auto29-web-build.log -- $taskPython tools/build_web.py
# Run this fixture in another background command, then the browser proof:
& $taskPython tools/run_background.py --log build/auto29-fixture.log -- $taskPython tools/test_auto29.py --serve 8794
& $taskPython tools/run_background.py --log build/auto29-browser.log -- $taskNode tools/test_auto29_web.mjs
& $taskPython tools/run_background.py --log build/auto29-web-build-tests.log -- $taskPython tools/test_web_build.py
```

The fixture's `/fault-loader/` and `/fault-rom/` each fail one real asset request
with HTTP 503, then serve the unchanged production bundle on retry. Restart the
fixture before repeating a complete browser proof. `AUTO29_URL` and
`AUTO29_BROWSER` can select another local fixture and browser executable. The
browser harness uses the existing cached Playwright Core 1.58.2 and installed
Edge, headlessly with speaker output muted; it installs or replaces nothing.
The final run used a fresh fixture on port 8795 and
`$env:AUTO29_URL = 'http://127.0.0.1:8795'`; otherwise its commands match above.

Native coverage is nine sessions per pinned core: all three modes crossed with
all three arenas, selected fighters 0/4/8, A and Start arena confirmation,
including P2 arena ownership in Local, and pause/resume from either port. It
checks both actual native pad samples remain zero after arena confirmation;
neither story skip nor another Start is sent. It checks the native story timer
passes 350, 180, 1 and 0, and intro passes 109, 50 and 0. Cold title/fighter/arena
waiting and the second deliberate fighter choice are retained.

Strict one-tick/one-vblank/zero-SDK-lag and OBJ overflow checks start when the
native trace publishes the fight scene. `beginMatch` sets the raw screen byte
before its forced-blank asset load; using that byte as a cadence-ready signal
was an initial harness error. The full no-input interval includes the load.
Expected arena-to-combat durations are 497 callbacks in Arcade and 136 in
Local/Training. This documents existing behavior, not a newly added countdown.

Browser coverage runs the actual pinned SNES WASM: automatic title rendering,
all three keyboard mode/arena routes, no-input dialogue/intro progression,
Start pause/resume, visible touch Start with a real held touch event, a standard
Gamepad API fixture, silent initial gains, first-gesture audio unlock, and real
loader/ROM failure plus retry. Native WRAM/trace reads are observation only;
there are no save states or emulated writes. The browser reads `pad0`/`pad1`
using the tested symbol file; `raw_keys2` includes CPU commands and is not a
physical-input assertion.
The first trace published by `beginMatch` can still contain the arena-confirm
sample taken before its forced-blank load. The browser observes the next
native frame/input poll without sending anything, then requires both physical
pad samples to remain zero. The native host likewise checks release after the
first publication; the no-input interval includes the entire load in both.

T3 preview was used first and reproduced `started:false`, zero canvases and
“Ready. Click Play game to begin.” Both snapshot attempts returned
`Preview automation snapshot timed out after 15000ms.` Its hidden canvas stayed
at 300x150/frame zero even after starting. The cached headless browser provided
actual rendered WASM screenshots and controller proof. Initial diagnostic
failures remain under ignored build: raw-screen cadence gating, capture-path
normalization, the mobile toolbar interception and CPU-vs-pad observation.

Exact results, source/harness/dependency hashes and screenshot hashes are in
`auto29-report.json`, the two native reports and `auto29-browser-report.json`.
Screenshots are under `docs/screenshots/auto29/`. Physical controllers,
Safari/iOS autoplay policy, original hardware, combined six-suite integration
and the final live deployment remain parent/human checks.

## Hosting coordination

Read-only local checks confirmed package pin **Wrangler 4.152.0**:
`wrangler.js --version` returned `4.152.0`, and
`wrangler.js preview --help` exited 0 with
“Create a Preview deployment of the current Worker [open beta]”. Thus
`npx wrangler preview` is valid for this pin; changing it solely because it
looks obsolete is unsupported by local evidence.

Current [Cloudflare Builds configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
also lists that command as the default Preview command, after the build step
(`npm run build` for this repository). Its
[Preview setup guide](https://developers.cloudflare.com/workers/previews/get-started/)
mentions one-time setup for an existing Worker using Workers Builds. The
documented alternative `npx wrangler versions upload` creates a Worker version
and Version URL instead of a Preview; that is a different deployment workflow,
not an asserted fix. No account settings, secrets, credentials or Wrangler
configuration were changed. The parent's reported PR preview build failure is
unresolved because detailed authenticated logs are unavailable; local dry-run
success and the existing main live player do not establish PR preview success.
