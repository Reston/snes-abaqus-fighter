# Simultaneous-contact diagnostic

This supplemental controller-only probe checks busy combat callbacks on the
current native cartridge. It does not replace the six suites, compatibility
smoke, extended combat or uninterrupted live-hour gates. Its output stays in
ignored `build/`; it is outside the offline package's release evidence.

The v0.17.0 run passed on ROM SHA256
`cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe`:

| Pattern | Mirror/stage cases | Required observation |
| --- | ---: | --- |
| Down+L uppercuts | 36 | Both players hit and enter knockdown together |
| Down+R sweeps | 36 | Both players hit and enter knockdown together |
| Down+X specials | 36 | Same-frame damage to both players |
| Projectile/groundwave clashes | 21 | Both live waves disappear without damage |

The 129 sequential cases measured 154,800 live frames, 1,071 simultaneous
contacts, 936 simultaneous double knockdowns and 84 wave clashes. All 78
double KOs repeated the same round, restored both fighters and awarded no
win. Every case observed at least four starts of its requested move from
each player. Wave-clash cases kept both fighters at full health.

The unchanged endurance checker examined every measured callback. Cadence,
native timing, ambient, PPU overflow and SPC FIFO failure totals were all
zero. These are focused technical observations; human gameplay, balance,
listening, controller and likeness reviews remain open.

The host used the pinned Snes9x libretro core, no GUI or audio device,
controller input only, read-only telemetry and no save states. Each case
closed its core before the next boot. The worker inherited Below Normal
priority and logical processors 14/15 from the background runner.

Rush mirrors start 61..64 pixels apart because both fighters advance during
startup. The initial point-blank Cote setup produced no contacts and was
correctly rejected as missing coverage; it exposed no timing failure.
The corrected spacing preserves the requirement for real simultaneous hits.

Run from the source root after building the cartridge and preparing tools:

```powershell
New-Item -ItemType Directory -Path build -Force | Out-Null
Copy-Item tools/run_background.py build/run_background.py
& '.tools/python/python.exe' build/run_background.py --log build/contact-budget.log -- cmd /d /c '.tools\python\python.exe tools\test_contact_budget.py --report build\contact-budget.json'
```

Use `--fighter 0..11`, `--stage 0..2` and `--pattern uppercut`, `sweep`,
`special-contact` or `wave-clash` for a smaller reproduction. Wave clashes
require a projectile/groundwave fighter. Each case defaults to 1,200 live
frames and requires at least two actual contacts or clashes.

The full retained source-only report is `build/contact-patterns-v17.json`,
SHA256 `3b9fd37a4abce3c0d661058a1c1fa404524c4ec8428e691f50a0771fe3fb1dde`.
Its harness hash is
`fab4f20277e6ba5edefeebb84891309888fe58a1e599cf32735dab74a44ccfb1`;
it records current ROM/core identities, per-case results, contact telemetry
and imported harness hashes. Rerunning the tool produces a fresh report.
