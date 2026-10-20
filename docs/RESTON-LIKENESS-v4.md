# Reston v4 likeness review

Reston's v0.8.1 revision adds a fuller, very short dark buzz cap over the crown
and temples while retaining his mature high forehead, beard and costume. All
64 frames passed native-size visual review for integration. Human likeness
feedback and public-use approval remain pending.

## Saved art and full prompts

Mode: **built-in imagegen edits**, with transparent RGBA output. Original v3
masters remain intact in the same folder.

| Frame range | Selected source | Full prompt and provenance |
| --- | --- | --- |
| 0-15 | [atlas-v4.png](../assets/art/characters/09-reston/atlas-v4.png) | [likeness-v4.json](../assets/art/characters/09-reston/likeness-v4.json) |
| 16-31 | [animation-motion-v4.png](../assets/art/characters/09-reston/animation-motion-v4.png) | [animation-v4.json](../assets/art/characters/09-reston/animation-v4.json) |
| 32-47 | [animation-actions-v4.png](../assets/art/characters/09-reston/animation-actions-v4.png) | [animation-v4.json](../assets/art/characters/09-reston/animation-v4.json) |
| 48-63 | [animation-airborne-v4.png](../assets/art/characters/09-reston/animation-airborne-v4.png) | [animation-airborne-v4.json](../assets/art/characters/09-reston/animation-airborne-v4.json) |

## Native output

The [6,144x80 review strip](../assets/generated/fighter09.png) and
[portrait](../assets/generated/portrait09-large.png) are deterministic native
asset conversions. The following images come from the actual v0.8.1 ROM PPU:

- [Player 1](screenshots/likeness/reston-v4-p1.png) and
  [Player 2](screenshots/likeness/reston-v4-p2.png), with loaded IDs and hashes
  recorded in [capture metadata](screenshots/likeness/captures.json).
- [Selected portrait](screenshots/presentation/select-09.png).
- [Idle](screenshots/characters/09-idle-animation.gif),
  [walk](screenshots/characters/09-walk-animation.gif),
  [attacks](screenshots/characters/09-attack-animation.gif),
  [air punch](screenshots/characters/09-p1-air-y.gif),
  [air kick](screenshots/characters/09-p1-air-b.gif) and
  [throws](screenshots/characters/09-p1-throw-sequence.gif).

The [preservation report](reston-likeness-report.json) checks the immutable
baseline against generated output: the other eleven fighters retain identical
native bank bytes; all twelve palettes and physical scales are unchanged.
Reston retains scale `0.2280130293159609`, the existing source-normalization
factors and exact palette bytes. His reviewed 64-frame hashes are pinned by
[native-revision.json](../assets/art/characters/09-reston/native-revision.json).
The [pipeline contract](ANIMATION-PIPELINE.md) describes the validation rules.

The six canonical suites and expanded technical gates identify ROM SHA256
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`.
See [v0.8.1 release notes](RELEASE-v0.8.1.md) for their scope.
