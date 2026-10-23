# Project instructions

This is a native SNES fighting game. The authoritative deliverable is
`dist/abaqus-after-hours.sfc`, built with PVSnesLib 4.6.0 from C and 65816
assembly. The current integration targets a 4 MiB NTSC FastROM LoROM image
across 128 banks.
Preserve the native emulator requirement when extending the project.

- The active integration is **v0.22.0, all ten improvements combined**, on
  `integration/ten-improvements-v022`. Feature PRs #2..11 are merged into it;
  [final PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1) awaits
  one human playtest before merge; combined automated verification passes. Main remains
  v0.21.0. Run `Play.cmd` from the integration checkout to play the candidate.
  ROM SHA256 `d4fddaf609a0c29f45353a8d9e22fe1131fc3380838d9c0073d3255474cdf8af`, header `EA9D`.
  Source freeze `b149cdf2d9e25560f61d09a0f49e71ce6fea7042`, tree `f58da040001f57a12c55b3ce92bde66041164b71`.
  All six native suites pass 36,253 exact-ROM checks; matching pinned
  independent smoke, all ten focused proofs, normal/optimized authoring
  guards and a fresh committed-source export pass. The export reproduces
  the ROM, all 219 generated assets and normalized symbols. Current evidence
  is docs/expansion-v0.22.0-verification.json. Keep isolated measurements historical.
  All ten behaviors are present: animation weight, light/strong/guard contacts,
  normal balance, individual intro/victory gestures, Training tools, CPU
  personalities, twelve supers, stage depth/ambient reactions, Arcade story
  and resident audio/announcements. Y/X punches and B/A kicks remain; a fresh
  neutral Y+B chord costs all 96 energy. Normal/Hard CPUs may fallibly use the
  same super command after incoming-wave and ordinary attack defense.
  Training page 3 adds input history, combo damage, ordinary-special `SP!` and
  three drills. The ordinary pause dummy/CPU shoulder controls, opposing-input
  cancellation, Start > B > A > Select and live P1 Select reset remain.
  All twelve fighter sets/portraits/scales, including approved Damian v5,
  original masters, static stage art and five original scores are preserved.
  The 219-file generated inventory permits only eight changes: effects.bin,
  effects.it, soundbank.asm/.bnk, stage-dynamics.json and stage0/1/2_ambient.bin.
  Of 1,276 prior RAM labels, 1,271 keep their addresses; five metadata/libc
  labels move by the documented 32/331 bytes. Fighter64/Wave16, TRACE0..122
  and native hardware/trace assembly retain their ABI. Use
  `tools/expansion_contracts.py` and docs/DEVELOPMENT.md for the combined
  allocations, HDMA, shared effect OBJ, footer/guide and resident-audio bounds;
  exact-ROM preservation, bank and transfer checks pass.
  No v0.22.0 offline ZIP, full release-scale evidence or human approval exists.
  v0.19.0 remains the latest full offline archive; public_release_certified is
  false. Human balance, listening, controllers, consent/public-use and original
  hardware gates remain open. See docs/RELEASE-v0.22.0.md and
  docs/expansion-review-v0.22.0.json. Keep older identities below historical.

- The previous candidate, retained on main, is **v0.21.0 four-button combat and HUD polish**.
  ROM SHA256 `aad68e7d0563df905e9136c0c7d26bac70b5fbaa1ab6c347e94e1208094ea205`, header `BEB8`.
  Source freeze `72dd25e9b71c1db6973540eef2eddd380b8039ed`, tree `5a645d49b100b82260fe7b0f7ffc78c2b8d32ac0`.
  Y/X are light/strong punch; B/A light/strong kick. Down+X uppercut,
  toward+X close throw, Down+A sweep, Down+Y quick special and QCF+Y/X.
  Only face buttons attack; L/R retain home/paused CPU Training level controls.
  The CPU uses these commands too. Guide and keyboard help match the layout.
  The shadow uses the same two 16x16 entries per actor at Y 200, meeting under
  the feet and staying below the low waves' fetch rectangle. The five-row HUD
  adds gold names, framed health, red low-HP feedback, thin energy, diamond
  round-win medals and a bottom rule within the same 320-byte transfer.
  All 219 generated files remain; 216 match v0.20.0. Only ui_tiles.bin,
  ui_pal.bin and effects.bin change. All twelve fighter sets, portraits,
  stages, ambient and audio are preserved, including approved Damian v5.
  All 1,276 RAM addresses, Fighter64/Wave16, TRACE0..122, actor, guide and
  transfer budgets remain. Six native suites pass 33,082 exact-ROM checks;
  the matching independent smoke and 228-check focused proof pass.
  The latest full offline archive remains v0.19.0; no v0.21 package or
  regenerated full release-scale evidence exists. The user responded "much
  better" to this revision; detailed controls/gameplay review remains open.
  See docs/RELEASE-v0.21.0.md.

- The approved historical **v0.20.0 Damian likeness candidate**. ROM SHA256
  `6b3544fa09e37a3f70c4eaecf5565718abc467962610ec1ce0437fc023d9f501`, header `3F2A`.
  The explicit new user request supersedes Damian's historical v4 appearance
  pin. Four imagegen v5 atlases use the additional photo; the current exact
  contract pin is `b6b94f879ed72b1eb0e84e100076f6cb80fddd990c162bc0361f1cd7da4631fc`.
  The native source freeze is commit `c83cf5e`; see
  [the likeness review note](docs/DAMIAN-LIKENESS-v5.md). All six suites pass
  35,715 checks and the matching independent smoke passes. There is no v0.20
  offline package or regenerated full release evidence. The user approved the
  revised likeness with "ok good" after the comparison review on 2026-10-22.
  Team/subject consent and public-use approval remain separate open gates.
  Preserve the retained v4 contract and all old source art.
  Other eleven fighters, Damian's OBJ palette and physical scale, all 1,276
  RAM addresses and native C/assembly behavior are unchanged.

- The previous full release checkpoint is **v0.19.0 practice controls**.
  ROM SHA256 `945da11920112ca11fbc00acec2fc04a1d821209a7e7a920defe5a05c32005e7`, header `05A4`,
  source freeze `003ab19b98f291fed67e7de457c1fc746d7ad2d8`, tree `17854e74ac06042df3d9121747036a00a5034686`.
  Paused CPU Training accepts both ports' L/R shoulders to change the existing
  home difficulty. Held opposites cancel; Start/B/A/Select, guide and dummy
  priorities remain. src/version.h drives title and manifest identity.
  Build canonicalizes generated text on regeneration and reuse. All 219
  generated assets, 1,276 RAM addresses, Fighter64/Wave16, TRACE0..122 and
  existing transfer/audio contracts are preserved.
  All six native suites pass 35,715 exact-ROM checks. Matching smoke, full
  matrix/replays, independent combat and three native live hours pass. Training
  completes 216,356 CPU live frames across all twelve opponents. Fresh
  export reproduces ROM, 219 assets and symbols in 471.844
  seconds. The Windows archive passes 9,299 technical audit
  checks. Two final packages are identical: 22,904,626 bytes, SHA256
  `b518ddf6eb6e20bfed1e55758aebb61fa2cca0462b5918412eb0837dc5eb1b07`. Human/public-use gates remain open.
  See docs/RELEASE-v0.19.0.md.

- The previous verified offline checkpoint is **v0.18.0 CPU Training level readout**.
  ROM SHA256 `fbf24853bef53f8d7be59c85363ba7496d8ee35da803f0368fc9cbea5ce3c4bb`, header `A299`,
  source freeze `8a7a6fc78c2160aac23de2a2f32ea927016853d0`, tree `9d78764a6f40c5fe3661b0b2f6fb8469d9f0a25f`.
  Training's CPU PAUSED card names Easy/Normal/Hard from the home setting.
  The four-entry label array, 219 generated assets, 1,276 RAM addresses,
  Fighter64/Wave16, TRACE0..122 and existing DMA/audio contracts are preserved.
  All six native suites pass 35,512 exact-ROM checks. Matching smoke, full
  matrix/replays, independent combat and three native live hours pass. Training
  completes 216,356 CPU live frames across all twelve opponents. Fresh
  export reproduces ROM, 219 assets and symbols in 568.453
  seconds. The Windows archive passes 9,103 technical audit
  checks. Two final packages are identical: 22,897,834 bytes, SHA256
  `42d25616285e9275e527bb412529da21575671d38cbe239b99b2ba9e69a7d153`. Human/public-use gates remain open.
  See docs/RELEASE-v0.18.0.md.

- The historical verified checkpoint is the **v0.17.0 CPU Training candidate**.
  ROM SHA256 `cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe`, header `5EAF`,
  source freeze `5fcd5cb28f4cf2453cb3310fbab0d6947d7afd9a`, tree `5e3ef5c5f4be06fbd0bad8a37ef215a449f1c2a1`.
  Training choice 4 uses existing home-difficulty AI; choices 0..3 and the
  default Stand remain. Health recovery, clock 99 and P1 Select reset persist.
  P2 gameplay input stays ignored. All 219 generated assets and 1,276 existing
  WRAM/direct-page symbol addresses match v0.16.0. Fighter64/Wave16,
  TRACE0..122, actor/OBJ/UI/ambient/SPC contracts remain.
  Training recovery uses a low-bit timer prefilter, direct fighter accesses
  and one HUD refresh. The HUD skips unchanged fields and caches each fighter
  pointer locally. Hit/update/animation paths avoid repeated reads and an
  empty-link call. HP recovery conditions remain. Its full live hour must
  cover every CPU.
  All six native suites pass 35,506 exact-ROM checks. Matching smoke, matrix/
  replays, independent combat and three native live-hour sessions pass. Training
  completes 216,356 live CPU frames. Fresh export reproduces the ROM, 219
  assets and normalized symbols in 498.672 seconds. The Windows archive passes
  9,097 technical audit checks. Two final packages are identical:
  22,899,854 bytes, SHA256 `1955e7c735978943f7ca409dff9bf1f853012490e502b60a51c9fe47eb211213`.
  Native CPU Training card/clip, anti-air clips and all-roster practice are bundled. Human gameplay/balance, listening, controllers, likeness/
  consent and public-use gates remain open; public_release_certified is false.
  See docs/RELEASE-v0.17.0.md.

- The historical verified checkpoint is the **v0.16.0 CPU anti-air candidate**.
  ROM SHA256 `feb73416224a7bbe6317f0c8a2b88abc403383c5017e151e1e6e2a8c3478cebd`, header `FA49`,
  cartridge source freeze `c5b64914b35af11897210701a2394a540a20a6b6`, tree `82c5128473b62ee0d9fd40394485f9b400242d5b`.
  Normal/Hard use bounded sampled universal uppercuts against visible near
  jump-ins, with ordinary startup and fallible commitments. Easy retains its
  prior behavior; wave/attack defense and signature-special priorities remain.
  All 219 generated assets match v0.15.0. WRAM, Fighter64/Wave16, TRACE0..122,
  controls, actor/OBJ/UI/ambient/audio contracts remain unchanged.
  All six native suites pass 35,147 exact-ROM checks. Matching pinned smoke,
  matrix/replays, independent combat and three uninterrupted native live-hour
  sessions pass. Fresh committed export reproduces ROM, 219 assets and symbols
  in 348.547 seconds. The Windows archive passes 8,729
  technical audit checks. Two final packages are identical: 21,689,220 bytes,
  SHA256 `e8736a6f9a786fd7e9b66e639e7ba220928cd36411159da4b0ba59db08426679`.
  Native CPU hit/whiff clips and twelve-fighter practice are bundled. Human gameplay/balance, listening, controllers, likeness/
  consent and public-use gates remain open; public_release_certified is false.
  See docs/RELEASE-v0.16.0.md.

- The historical offline checkpoint is the **v0.15.0 close cross-up/practice candidate**.
  ROM SHA256 `2c447156b7c1f12d94e1c76dde3423928ad026933076c952806abda7d6281d44`, header `2491`,
  source freeze `e406ac17af1c25a64c7be547e7d0857880c18599`, tree `78493ed80bfd259deb228e7a8ca20580fef4f267`.
  Only airborne medium kick action 5 reaches behind its locked facing, within
  16px plus the 10px body half-width. Existing timing/damage/front reach and
  other directional moves remain. Contact-side recoil survives landing and
  trades in the previously unused flash byte; no WRAM storage or trace/ABI
  changes. Controls teaches the cross-up at row 22 of the existing pause panel.
  All 219 generated assets match verified v0.14.0. All six native suites pass
  35,036 checks on this exact ROM. Pinned smoke, full matrix/replays, independent
  combat and three native live-hour sessions pass. The isolated rebuild reproduces
  ROM, assets and symbols in 448.641 seconds. Focused menu and authoring
  evidence matches the current ROM/source freeze. The Windows package passes
  8,707 technical audit checks. Two consecutive final ZIPs are identical at
  14,747,425 bytes, SHA256
  `481d5fb0968c1ba44ffee1e46ed1009736d45f45fa0e79c415478d370661ba62`.
  The offline review includes two native moving cross-up clips and the new
  Controls cue; GIF playback timing is an inspection approximation.
  Human gameplay/balance, listening, controllers, likeness/consent and public-use
  gates remain open; public_release_certified remains false.
  See docs/RELEASE-v0.15.0.md.

- The historical offline checkpoint is the **v0.14.0 menu/motion-help/authoring candidate**.
  ROM SHA256 `3de317b43f72bea76cfc2f1a1ebd5c67dd57913b8d9fddfb50a7a846a02ddeaa`, header `D1E2`,
  source freeze `d534af0132440c0de3e1cb5a33a62301026449af`, tree `2dd5e2c1b6b4a64f7aa5fbb61bc69e8f522cd3cd`.
  Roster/arena hints show A/Start. The arena uses an existing opaque native
  footer at rows 26..27; all scene/cursor pixels above 208 are preserved.
  Specials adds the per-step twelve-tick motion hint inside the existing
  three-tick, 1,472-byte guide panel. Existing controls and timing are retained.
  Authoring guards are explicit raises under normal/optimized Python. All 219
  generated assets match verified v0.13.0, including fighters, stages and audio.
  All six native suites pass 34,683 checks on this exact ROM. Matching pinned
  smoke, full matchup/replays, independent combat and three native live-hour
  sessions pass. Fresh committed source reproduces 219 assets, ROM and symbols
  in 419.844 seconds. Focused menu proof covers 69 paired native
  states, fifty controller routes and fourteen final footer images, with
  4,650 checks. Authoring mutation checks pass 19/19 under normal/-O Python.
  The Windows package passes 8,698 technical audit checks. Two consecutive
  final ZIPs are identical at 13,479,437 bytes, SHA256
  `dd880e6b5b068e0172b92cdad8a52011938df0d0f6adbc1b528d64ce3f9e6339`.
  Human gates remain open; public_release_certified remains false.
  See docs/RELEASE-v0.14.0.md; older evidence below is historical.

- The preserved offline checkpoint is the **v0.13.0 champion music/pause/build candidate**.
  ROM SHA256 `eefa712718d52aa536258773596e78cee3f4cfc83b1cd4144e3de1110d2273b4`, header `B2CC`,
  source freeze `9e4b4a6e837bd3c91bba81f9781dab1cecbb79c8`, tree `c7f5aeda2c1873ef6450138bbdea1389d58a71e9`.
  Start owns a paused Training sample even with simultaneous Select from either
  controller. The earned champion scene loads a fifth original score; the four
  original scores and resident BRR/native module payloads are preserved.
  An ordinary build regenerates assets when any required generated header is absent.
  There are 219 generated files; two soundbank outputs change and music4.it is
  added relative to v0.12.0. Native ABI, actor, ambient and art budgets remain.
  All six native suites pass 34,193 checks on this exact ROM. Matching
  independent smoke, full matrix/replays, bounded independent combat, three
  native live-hour sessions and a fresh committed-source rebuild pass.
  The rebuild reproduces 219 assets and symbols in 298.656 seconds.
  Focused champion audio passes 1,792 capture-only checks.
  The Windows package passes 8,401 audit checks. Two consecutive
  final ZIPs are identical at 8,533,050 bytes, SHA256
  `c054e656ac840be746e785f11ea49325b67e7eea8a6586ddbb17e92b5fbbb174`. Human gates remain open.
  See docs/RELEASE-v0.13.0.md; older evidence below is historical.

- The preserved offline checkpoint is the **v0.12.0 Training/ending candidate**.
  ROM SHA256 `33502fba12bf2cf02e6244174449c678ad1dd704afc754e7819f815489c6fa83`, header `222B`,
  source freeze `9134d4307037a935e1de31f08efd405409ac8ef7`.
  Training adds a DUMMY roster step supporting arbitrary and mirror opponents.
  The eleventh Arcade victory loads a static original trophy scene, retaining
  the portrait page, six scene palettes and existing title/roster actions.
  The generated asset count is 218; existing binary assets are preserved.
  All six native suites pass 33,509 checks on the exact current ROM.
  Matching bsnes smoke, full native matrix, independent bounded combat, three
  native live-hour sessions and fresh-source rebuild pass. The rebuild
  reproduces all 218 assets and symbols in 126.672 seconds. The Windows
  package passes 7,709 audit checks. Consecutive archives are identical at
  7,114,333 bytes, SHA256
  `04de3ba2ececd5b31e2c1aca8a2f367765351f49aeaa196b8b9245f7b8d35818`.
  Human gates remain open.
  A controller-only probe found that paused Training Start+Select also resets
  the round; Start alone preserves it. The fix is isolated for the next
  integration. The frozen v0.12 package explicitly records this known issue.

- The preserved offline checkpoint is the **v0.11.0 result/input/package polish candidate**.
  It carries the v0.10.1 art checkpoint below and adds winner portraits,
  truthful result prompts, a complete normal-pause resume hint, discarded
  wake-only motion commands and a truthful healthy-timeout DRAW banner.
  Source freeze `68842a2b040fefc9070542fcf57284af5494e1dc` builds ROM SHA256
  `1574bb4147605b3a0dd8d463b6403360a386c62334e1d5e29ea5654bd376baa7`,
  header `7CFE`. All six native reports match and pass 33,155 checks; the
  separate pinned bsnes smoke, isolated source rebuild and three native
  live-hour sessions also match. The full native matchup matrix and bounded
  independent-combat evidence pass. The Windows offline archive passes 7,549
  audit checks; two consecutive builds are identical at 6,874,448 bytes,
  SHA256 `157112e2f4b1008a4cd112dadbf33664286cc1f57581e606d994a59bf554a278`.
  See `docs/RELEASE-v0.11.0.md`. Human gates and hardware support remain open.

- The preserved **v0.10.1 unpackaged art checkpoint** is commit
  `0708dea65c859786e8455da78bd58eb077135adf`,
  ROM SHA256 `8f7def30d29c87a659d7fb623147cf726bab8f8c94a96a503738529aded15279`,
  header `42AF`. `Build.cmd --assets` and `Test.cmd` exit 0; all six reports
  match this SHA and pass 32,205 checks, and the separate pinned bsnes smoke
  matches. See `docs/POLISH-v0.10.1.md`, `docs/polish-test-summary.json` and
  `docs/polish-preservation-report.json`. The user reported that Lars needed
  a closer likeness and the location pictures were unclear; exact responses
  and pending replacement review are in `docs/review-feedback.json`.
  Lars (ID 11) is a new, explicitly reviewed exception to the earlier
  ten-fighter baseline: four versioned v4 atlases and three exact-prompt JSON
  records live in `assets/art/characters/11-lars/`, with the airborne spacing
  repair input retained under `source-v4/`. His LF-normalized
  `native-revision.json` is pinned at SHA256
  `3413da731ed37a650b081fc49a03fa800c0be7c94ed04aca7747f640e3d01b27`;
  its native64 summary is
  `e9b4da3d6734e0d340c4ce9690c0109e977fc56c6308b065b6f7400f03c258c7`.
  His original palette and physical scale remain fixed; the other eleven
  fighter sets, including approved Damian and Reston, are unchanged. Arena
  previews are 104x52 filtered landmark crops at x18..121, retaining the
  240x56 native cursor rows. The pass preserves 192 of 217 compared files;
  its 25 changes are limited to Lars, select/arena plates, generated metadata
  and ROM/manifest. Stage masters, ambient cells, C/ASM combat, transfer
  budgets, trace ABI and audio are unchanged. No new package or source freeze
  was created; the extended v0.10.0 evidence and package below are historical
  for this ROM. Human likeness/consent and the other public-release gates
  remain open; `public_release_certified` remains false.

- The user selected **emulators first; hardware support stays unverified** for
  the first public release. Original SNES/flash-cartridge validation is future
  work outside that support scope. Human gameplay, physical-controller,
  full-listening, likeness/consent and team/public-use reviews remain required.
  Record actual responses in `docs/review-feedback.json`; the user reported
  four live v0.8.1 presentation defects (clipped selection faces, a Damian
  likeness mismatch, an ugly arena picker and stage bleed through HUD/result
  lettering), and heard a brief audio replay with no issue noticed. Full combat
  playtesting and the other human gates remain open.

- The latest packaged historical technical snapshot is the v0.10.0 cartoon-stage
  candidate, source-frozen for
  review at commit `8536bb6956212952c17302a62cc6c1de7e12a65d`, tree
  `d524d3f960600dc5c9ff83578ac73675f9798735`; its ROM is SHA256
  `a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445`, header
  checksum `BE19`. Native PPU review accepted all three stage scenes and the
  arena picker; focused presentation, stage and menu probes pass. `Test.cmd`
  exits 0 with all six reports matching this SHA: 2,595 gameplay, 18,081
  roster, 1,756 presentation, 1,020 focused-input, 8,131 stage and 622
  Training checks (32,205 total). Fresh committed export validation passes 214
  assets and symbols in 62.031 seconds. The [stage pass note](docs/STAGE-CARTOON-v2.md)
  and [preservation report](docs/cartoon-preservation-report.json) record the
  source/art details. The candidate adds three versioned original
  built-in-imagegen stage masters and adapts the existing feature-driven
  ambient art to the candidate palette and map. It also carries bounded
  menu-only correctness polish: cleaned directional edges, both-pad navigation
  only for the P2 roster case, Start > B > A priority and immediate return
  after Back. Active combat, Fighter/Wave ABI, fighters, portraits, audio,
  existing four-phase 256-byte ambient cells and `TRACE[115..118]` remain
  unchanged. Endurance passes all three modes at 216,356 live frames each at
  60.098811862348406 FPS, with native wraps 4/4/3, peak SPC backlog 6 and
  empty cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure
  arrays. The technical audio report passes 1,262/1,262 capture-only checks:
  all four cues and four scores are unclipped, the four music captures run
  60.899688-63.079432 seconds, and no near-zero interval reaches 0.5 seconds
  (longest near-silence 0.075499-0.078652 seconds). Its separate listening
  pack is 15,447,456 bytes with SHA256
  `5afec27e3022f87580e21991beb6785b9366dfb9bf16bf2abb45a08400309c70`.
  The 288-by-600 matchup/stage/policy/replay/symmetry run with four replays
  across all three stages, pinned bsnes smoke at 600/600 plus the independent
  28,800-frame run, and `validate_release_evidence` all pass on this SHA.
  The historical [v0.10.0 Windows package](dist/Abaqus-After-Hours-v0.10.0-Windows.zip)
  is available and `tools/audit_release.py` passes 7,472 checks against it.
  Two consecutive final packaging runs produce identical 6,592,864-byte ZIPs,
  SHA256 `8402f8be6f4c928e5b56cf22955d990c8bb6c4e2107262d489d2b3fc84036a99`.
  Human listening, gameplay, physical-controller, likeness/consent and
  team/public-use review gates remain open, and `public_release_certified`
  remains false.

- The historical v0.9.0 native presentation
  pass. Its corrected source freeze is commit
  `76f0a08a7562800df01507db83c6877745c3bdcf`, tree
  `f37852da57a42d2d6819374db5d23278d12587a5`; the ROM is SHA256
  `bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639`, header
  checksum `6D41`. C text-tile selection changes to opaque glyphs; native
  assembly, controls, combat, audio, trace offsets, memory layout and
  Fighter/Wave contracts remain unchanged. `Test.cmd`
  exits 0 with all six reports on that SHA: 2,595 gameplay, 18,081 roster,
  1,756 presentation, 997 focused-input, 8,131 stage and 622 Training checks
  (32,182 total). Fresh committed export validation reproduces the ROM,
  manifest, 214 assets and symbols in 75.078 seconds. The 288-by-600 native
  matchup/stage/policy/replay/symmetry checks pass; the pinned bsnes smoke and
  bounded 48-by-600 run pass; native endurance passes 216,356 live frames in
  each of three modes; and `validate_release_evidence` passes. The native all64
  review accepts the corrected Damian set. The historical [v0.9.0 Windows package](dist/Abaqus-After-Hours-v0.9.0-Windows.zip)
  is available and `tools/audit_release.py` passes 7,471 checks against it.
  Two consecutive packages are identical: 6,578,152 bytes, SHA256
  `8203ffab8d27b4205e25ebfcc2e74e09f5af199641b281a925a9b981c4d1f97e`.
  Public-release certification remains false.

- The historical v0.8.1 technical snapshot has source freeze
  commit `fe05e5fd1391a1db20f1b66f1e9f6e699445e77a`, tree
  `46e1af160ffb8ab6cb768e3d9deec1352d77ae83`; the ROM is SHA256
  `76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`, header
  checksum `A358`. Native C/ASM, controls, gameplay and audio are unchanged.
  `Test.cmd` exits 0 with all six reports on that SHA: 2,595 gameplay, 18,081
  roster, 215 presentation, 997 focused-input, 8,131 stage and 622 Training
  checks (30,641 total). Fresh committed export validation reproduces the ROM,
  manifest, 214 assets and symbols in 76.344 seconds. The 288-by-600 native
  matchup, stage, policy, replay and symmetry checks pass; the pinned bsnes
  smoke matches this SHA with 600/600 cadence and healthy PPU/PCM/ambient
  freeze, and its bounded 48-by-600 run passes. Native endurance passes 216,356
  live frames in each of three modes at 60.0988118623 FPS, wraps 4/4/3, peak
  SPC six, zero stable FIGHT lag and empty failure arrays. `validate_release_evidence`
  passes. The historical v0.8.1 offline package and its 7,471-check audit pass;
  the v0.8.0 package is historical. Full64 native visual review accepted
  Reston's v4 art for integration, but human likeness/consent, balance, full
  listening, controller and branding gates remain open. These results are
  historical evidence and do not identify a later candidate.

- v0.8.0 adds a pause overlay with Normal, Controls and Specials pages. Select
  cycles the pages, and Left/Right toggles the guide pages. Start resumes
  first; otherwise B returns to the roster, A resumes and Select cycles pages.
  The Controls page keeps the original glyph
  set and the Specials page names both live fighters, their specials and family
  types, including the true 12-tick quarter-circle motion and 32-energy cost.
  Training pause Up/Down cycles Stand, Guard High, Guard Low and Jump; guard
  holds relative back without retreat, and the Jump dummy automatically jumps
  again after landing. Live Select resets the round while preserving the dummy choice and
  returning a new match to Stand. Pause camera shake is frozen and a pause
  after contact settles the actual HP bar on the first quiet paused tick.

- The guide uses opaque original glyphs 256-383 in VRAM `$5000-$57FF`; the
  selected portrait remains at `$4A00`. Its rows 5-27 publish as a 1,472-byte
  staged panel over three paused ticks and yield to actor DMA. `drawGuideWord`
  and the native full-clear UI path are part of the hardware contract. The
  Fighter/Wave layout and native fighter contracts are unchanged. Stable trace offsets
  `0..118` remain unchanged; v0.8 appends `TRACE[119]` pause page,
  `[120]` guide build stage, `[121]` Training dummy mode and `[122]` guide dirty.

- Read `docs/DEVELOPMENT.md` before changing memory layout or hardware transfers.
- Build with `Build.cmd`; regenerate assets with `Build.cmd --assets`.
- Run `Test.cmd` after gameplay, graphics-transfer, audio, menu, presentation or
  progression changes. It runs the actual ROM in Snes9x and records the tested
  ROM hash for the gameplay, roster, presentation, focused-input, stage and
  Training suites.
- Run automated verification silently and headlessly. The libretro test host
  may capture audio for assertions, but must not play it through the speakers.
  The user has also authorized muted live emulator review now that they are
  no longer playing another fullscreen game. Keep GUI review muted and separate
  from the reproducible headless suites. Default to preserving foreground focus
  during future automated work.
- Do not report emulator pass counts or release readiness until all six current
  native ROM reports point to the exact same ROM SHA256:
  `docs/test-report.json`, `docs/character-test-report.json`,
  `docs/presentation-test-report.json`, `docs/input-test-report.json`,
  `docs/stage-test-report.json` and `docs/training-test-report.json`. The
  package gate also requires `docs/compatibility-test-report.json` to pass
  against that same SHA. The compatibility report is a separate pinned
  bsnes2014 Accuracy smoke, not part of the six-suite `Test.cmd` batch. The
  historical v0.9.0 reports all match the corrected SHA and record 32,182
  passed checks; the pinned compatibility report is also matched. The historical
  v0.9.0 package and audit pass 7,471 technical checks. The v0.8.1 reports,
  package and audit are historical evidence.
- The v0.6 fast path caches actor-bank and per-action timing selection, uses the
  compile-checked `Fighter` stride 64 and `Wave` stride 16 layouts, and caches
  unchanged OAM/shadow work by integer position and facing. Native health and
  energy bars keep their glyph formulas; impact HUD and empty-banner clears are
  serviced through hitstop, while interface DMA yields to an actor upload.
  Interface feedback may therefore lag one to three video frames while hitstop
  keeps combat state frozen.
- `src/trace.asm` writes read-only telemetry directly at stable `TRACE[0..113]`
  offsets and ambient stores `TRACE[115..118]`; `main` samples post-wait PPU
  `STAT77` into `TRACE[114]` before DMA. Any native `Fighter` or `Wave` struct
  layout change requires an assembly-offset audit and a matching trace-contract
  update; offsets `0..113` remain the Fighter/Wave ABI.
- Keep the one-actor-per-vblank transfer budget, 32 KiB LoROM bank boundaries,
  OBJ scanline limits and reserved palette banks in mind.
- The v0.6 renderer uses thirty 16x16 sprites per actor at OAM byte 0 and 128,
  with 3,840-byte pose streams in actor pages `$6000-$69FF` and `$6A00-$73FF`.
  Keep the 96x80 canvas, 94x77 safe area, native feet baseline at height 78
  and one uniform physical scale per fighter across all 64 frames. The native
  review strip is 6,144x80 RGBA. Eight contiguous 30,720-byte banks
  (`fighterXX` and `fighterXXb` through `fighterXXh`) hold each fighter's
  native data; each fighter uses one shared fifteen-color OBJ palette.
- The v0.8 pause guide uses original opaque glyphs 256-383 in VRAM
  `$5000-$57FF`, before the BG2 map at `$5800`; the selected portrait remains
  at `$4A00-$4EFF`. Keep its 1,472-byte rows 5-27 panel within the three-tick
  paused DMA path and yield to actor uploads.
- v0.7 stage ambient work uses BG1 tile indices 960-967 at VRAM `$3C00-$3C7F`:
  four 256-byte phases provide eight dynamic 4bpp tiles while the original
  stage graphics, map and palette masters remain unchanged. Ambient uploads
  yield to actor and interface DMA and advance only during live combat; intro,
  pause, hitstop and round-end states freeze them. The stage effects use no
  additional OBJ budget.
- Each fighter has legacy frames 0-15, motion/transition frames 16-31, action
  frames 32-47 and the v0.6 airborne/throw/knockdown range 48-63. Preserve the
  original 48-frame hashes and palette bytes for the ten baseline fighters. The
  approved Damian (ID 00) and Reston (ID 09) revisions pin their exact native
  64-frame contracts: Damian
  `00f90a6765904c546284832d399c1a5ec581f08fed64a7f7bedc6d9df985e261` and
  Reston `7fe74ce9c1d771203191606d8f9ea05398eebb2507f7ab7dc538c766c274bfda`.
- Keep twelve individual illustrated fighter masters and their identities,
  palettes and costumes separate. The v0.6 animation pass adds twelve new
  built-in-imagegen `animation-airborne.png` atlases while leaving all twelve
  identity masters unchanged. The approved v0.9.0 sources update Damian's
  corrected 64-frame set, and the historical v0.8.1 sources update Reston's
  complete 64-frame set and portrait to the v4 short-buzz-cap sources
  (`atlas-v4.png`, `animation-motion-v4.png`, `animation-actions-v4.png` and
  `animation-airborne-v4.png`); the original v3 sources remain retained. Keep
  Damian's v4 provenance and `native-revision.json` plus Reston's three v4
  provenance JSON files with the art; retain the earlier motion/action metadata
  and the v0.8.0 baseline banks for the other ten fighters.
- The v0.5 presentation uses three independent stage PNGs described by
  `assets/art/stages/stages.json`, plus original home/select/arena menu art
  under `assets/art/menu/`. Keep `assets/art/menu/prompts.json` with the source
  prompt set and keep menu lettering on the original project glyphs. The menu
  direction is minimal royal navy, white and gold with one cursor and one large
  selected portrait. v0.8 adds pause Controls/Specials guide pages without
  changing the menu grid or portrait contract.
- The v0.10.0 stage candidate uses versioned masters
  `00-las-condes-cartoon-v2.png`, `01-castillo-cartoon-v2.png` and
  `02-oficina-cartoon-v2.png`, each with an adjacent exact-basename JSON
  provenance file and raw source under `assets/art/stages/source-v2/`.
  `assets/art/stages/stages.json` is the selected schema-2 manifest and
  `stages-v0.4.json` remains the prior manifest history. `tools/stage_sources.py`
  validates path, hash, RGB 1024x896, exact 4x-native dimensions and at most
  90 colors; `tools/stage_cartoon.py`
  carries the existing feature ambient work into the new palette/map. Preserve
  the existing four-phase 256-byte, eight-cell budget. The candidate ambient
  change counts by phase are Las Condes `[0,20,20,20]`, El Castillo
  `[0,18,18,18]` and La Oficina `[0,6,6,6]`; the office keeps one 3-pixel
  monitor segment per monitor at `y114` while protecting the monitor digits.
  The [stage pass note](docs/STAGE-CARTOON-v2.md) and
  [cartoon preservation report](docs/cartoon-preservation-report.json) record
  the 192 generated files retained from v0.9, including fighter 64-frame banks,
  palettes, portraits, UI, audio, title and select assets.
- Keep original art masters and prompts in the repository. Do not import
  commercial game ROMs, Capcom sprites, or commercial game audio.
- Preserve future scope for art review, balance tuning, stage parallax, human
  playtesting and real-console/flash-cartridge verification; do not imply those
  roadmap items are complete. The v0.8.0 verified snapshot remains the
  historical evidence baseline. Reston's v4 art and Damian's corrected v4 art
  are accepted for native integration by the full64 visual review, while actual
  human likeness and consent review remains future work. The historical v0.9.0
  evidence above is tied to its exact ROM; v0.10.0 public-release gates remain
  unverified.
- Do not commit `.tools/`, emulator saves, build intermediates or release ZIPs.
- Rebuild the offline package with `tools/package.py` only after all six native
  suites and the matching compatibility smoke pass against the exact current
  ROM. It also requires the current full matchup matrix, bounded independent
  combat, three native live-hour sessions and isolated source rebuild through
  `tools/release_evidence.py`. Run `tools/audit_release.py` on the result.
  The v0.7.1 offline archive and its 6,153-check audit are historical. The
  historical v0.8.0 package passes 7,471 technical audit checks. The current
  historical v0.8.1 package also passes 7,471 technical audit checks. Keep third-party
  license notices intact. Two consecutive v0.8.1 packaging runs produce identical
  6,546,645-byte ZIPs, SHA256
  `04d951c3abef278afada5a666f9eec8a04d140650354bd82506e750e2849e0b6`.
  Historical v0.8.0 packaging produced identical ZIP bytes:
  6,546,551 bytes, SHA256
  `44f92c041563badc1a6b903e859ad4dd5258b5bd85f6d253cdf74b5c06641869`.
