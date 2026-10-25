# Browser play on Cloudflare

**[Play Abaqus: After Hours](https://abaqus-after-hours.restonjd.workers.dev/)**

This adds a browser player around the existing native SNES cartridge. It uses
self-hosted EmulatorJS 4.2.3 and Snes9x. The game, combat speed, artwork and
`dist/abaqus-after-hours.sfc` are unchanged. Arcade, Training and local two-player
run on the player's device; remote multiplayer is not included.

## Try it locally on Windows

Run **`Web.cmd`**, then open **http://localhost:8787**. The cartridge loads automatically; your first key or tap enables sound.
The keyboard layout matches `Play.cmd`; the player's gamepad button configures
controllers. The controls panel includes both players and the four attack buttons.

The launcher prepares a checksum-pinned Node 24.22.1 inside `.tools/`, installs
the locked Wrangler dependency, and starts Cloudflare's local server. It does
not change the system's Node installation. Stop the server with Ctrl+C.
The project-local Python from `Build.cmd`, or an installed Python 3, is required.

| Command | Result |
| --- | --- |
| `Web.cmd` | Prepare the player and start the local server |
| `Web.cmd prepare` | Produce `build/cloudflare/site/` |
| `Web.cmd check` | Build and validate deployment without publishing |
| `Web.cmd login` | Sign into your Cloudflare account in the browser |
| `Web.cmd deploy` | Build and publish to your Cloudflare account |

## Publish

1. Create or sign into a Cloudflare account and select the Free plan.
2. Run `Web.cmd login` and approve Wrangler access in your browser.
3. Run `Web.cmd deploy`.
4. Wrangler prints the live `https://abaqus-after-hours.<your-subdomain>.workers.dev`
   address. If Cloudflare asks for an account subdomain, choose one in its dashboard.

No API token, account ID or password belongs in the repository. If the Worker
name already belongs to another application in your account, change `name` in
`wrangler.jsonc` before deploying. An owned custom domain can be added later.

For automatic updates, import `Reston/snes-abaqus-fighter` in Cloudflare
**Workers & Pages**, with repository root as the root directory:

| Setting | Value |
| --- | --- |
| Production branch | The branch containing this setup; `main` after merge |
| Build command | `npm run build` |
| Deploy command | `npx wrangler deploy` |

Cloudflare installs the locked npm dependencies. Node 22 or newer and Python 3
must be available on the build host. The native toolchain is not needed: the
web build verifies and copies the already-built cartridge from `dist/`.

## What is deployed

Only `build/cloudflare/site/`: the small HTML/CSS/JS page, native title capture,
4 MiB cartridge, required pinned SNES emulator files, release identity and license
notices. Emulator assets are downloaded at build time and verified against
`web/vendor-lock.json`; player visits use the self-hosted copies. A cached file
with a wrong hash fails the build. No runtime CDN, database or game server is
required. Static asset requests and storage are currently free under
[Cloudflare's static-asset pricing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/).

`wrangler.jsonc` contains no Worker script or server bindings. Missing files
return an actual 404, and `_headers` supplies the browser security headers.
The builder checks Cloudflare's 25 MiB per-file limit and verifies the ROM against
`dist/manifest.json`. `release.json` records the exact ROM and emulator hashes.
Rebuild this site after replacing the native cartridge with a new approved build.

Other systems can use `npm ci`, `npm run check:deploy`, `npx wrangler login`,
and `npm run deploy` with Node 22+ and Python 3 installed.

## Verification scope

This is browser hosting preparation, separate from the historical full Windows
offline archive. The native source, generated assets and cartridge are unchanged.
Browser smoke testing covers the real WebAssembly emulator, title/selection/live
combat, keyboard input for both local players, normal-speed frame progression,
responsive layout, HTTP paths, pinned dependencies and a Wrangler dry run.
Automated browser checks are muted; physical controllers and audible browser
listening still need a human check. The public player linked above uses the
current v0.29.0 cartridge; follow the Publish steps to host your own copy.
