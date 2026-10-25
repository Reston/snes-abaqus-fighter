# Restore the accepted defense evidence

Current accepted scope: [../../defense29-combined-report.json](../../defense29-combined-report.json).
Its SHA256 remains `34665dcb4bf46db49e5a047dd7fe0bf11ef722f028f68d052787103dcc06cf26`.
The [manifest](manifest.json) maps reported ignored/absolute paths to these committed
copies. No field or byte in any original report was rewritten.

The accepted coverage is the completed32 defense +16 CPU +32 KO functional prefix,
plus24 ordinary and24 unteched-throw pairs against the current defense-disabled
reference. The supplement passed234,149 checks in100 seconds. The old-reference
full run still failed: its first tuple differed in absolute frame605/604, and the
complete pair also differed in energy and cached oldFrame bytes. The historical
failed report is preserved as `historical-functional-prefix-failed-report.json`.
`docs/defense29-report.json` is left byte-exact in that failed historical state;
use the combined report for the accepted current result. Do not rerun the eight-minute
functional prefix merely to reproduce the supplemental comparisons.

## Reconstruct the isolated inputs

Use final candidate checkout `4c35ee89d6269662269481ffafff0166a905c775`, current ROM
`7e93c7f233ac557f0f5687e952f0ece9ab9c0e54e3c108d04dd0b39c7d26afa0`, the pinned
project Python/SDK/cores, and the native source freeze
`cb61690501d0688050a453aabcdd6993bc6dcb49`. Keep the candidate checkout untouched.

Reconstruct `build/v029/defense-reference-cb616905/workspace/` from the original
raw source/input hashes in `reference-provenance.json`. Most inputs are committed
at the source freeze. Preserve recorded LF/CRLF bytes, not just text contents.
The three older helper copies under `helpers/` preserve the exact imported bytes;
the used trace/boot/spacing definitions were also checked against the final freeze.
Copy all237 generated outputs plus `soundbank.h`; the byte-exact matching cache
stamp is published as `asset-cache-v1.json` and restores to the isolated `build/`.
Restore that stamp before the native build; restore the runner/fixture afterward.
The `.tools` junction targets the canonical shared cache read-only; never run setup,
downloads or replacements there.

Apply `defense-disabled-native.patch` only in that isolated source, preserving
line endings. The provenance binds the original and resulting native file hashes.
Only `src/game.c` and `src/cpu_personality.h` change. Retain all other features,
optimized audio/input code, defense reset/reservation and simultaneous tech.
Build only that workspace with the exact command below. Require asset reuse,
reference ROM `c54a9774fe4f036535369099ebd815742a3325bee59290adf9c0d70403dc9d79`,
checksum `0D46`, all1329 RAM labels exact and all237+1 asset bytes unchanged.

```powershell
Set-Location -LiteralPath D:/snes-abaqus-fighter
[System.Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity = 12
$defensePython = (Resolve-Path -LiteralPath D:/snes-abaqus-fighter/.tools/python/python.exe).Path
& $defensePython D:/snes-abaqus-fighter/build/v029/defense-reference-cb616905/workspace/tools/run_background.py --log D:/snes-abaqus-fighter/build/v029/defense-reference-cb616905/reference-build.log -- $defensePython D:/snes-abaqus-fighter/build/v029/defense-reference-cb616905/workspace/tools/build.py
```

After building the reference, restore the executed runner/fixture and archived
reports to their original ignored paths. Feed this block to the canonical embedded
Python (`D:/snes-abaqus-fighter/.tools/python/python.exe -`); it copies only below
`build/` and checks every published byte hash. It does not execute a proof:

```python
from pathlib import Path
import hashlib, json
root = Path('D:/snes-abaqus-fighter')
manifest = json.loads((root/'docs/evidence/v029-defense/manifest.json').read_bytes())
for item in manifest['restore_to_ignored_paths']:
    source = root/item['committed_copy']
    target = root/item['restore_path']
    assert target.resolve().is_relative_to((root/'build').resolve())
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item['sha256']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
```

`test_defense29-explicit-rom.py.txt` is the exact executed fixture after the approved
`explicit-rom-fixture.patch`; restoring it replaces the need to apply that patch
again. The runner is QA data as `.py.txt` until explicitly restored below ignored
`build/`. No executable file is installed in root `tools/`.

## Exact passing supplemental command

Run only after the candidate/helper inputs are frozen and the required reference
ROM is verified. The wrapper enforces BelowNormal, CPUs2/3 and silent/headless hosts.
Its output streams stay under the isolated workspace, preserving the fixture's
existing path invariant. The root historical report and current combined report
are never output targets of this command.

```powershell
Set-Location -LiteralPath D:/snes-abaqus-fighter
[System.Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity = 12
$env:PYTHONDONTWRITEBYTECODE = '1'
$defensePython = (Resolve-Path -LiteralPath D:/snes-abaqus-fighter/.tools/python/python.exe).Path
& $defensePython D:/snes-abaqus-fighter/build/v029/defense-reference-cb616905/workspace/tools/run_background.py --log D:/snes-abaqus-fighter/build/v029/defense-current-reference-equivalence.log -- $defensePython D:/snes-abaqus-fighter/build/v029/defense-reference-cb616905/run_equivalence.py --workspace D:/snes-abaqus-fighter/build/v029/defense-reference-cb616905/workspace --candidate-root D:/snes-abaqus-fighter --prefix-report D:/snes-abaqus-fighter/build/v029/defense-failed-cb616905/docs/defense29-report.json --report D:/snes-abaqus-fighter/build/v029/defense-current-reference-equivalence.json
```

This command preserves full unmasked equality, including absolute frame, energy,
oldFrame and padding. All native cadence/SDK/PCM/FIFO/OBJ/actor assertions remain.
On any genuine difference, preserve the failed report and stop; do not normalize,
shift callbacks, mask fields or adjust quiet frames. The original routing failure
is retained separately and is excluded from the passing48-pair result.

The large compressed controller streams remain in ignored storage, with their
exact hashes and locations in the raw reports. The ten native captures are already
under `docs/screenshots/defense29/`. The manifest links these existing repository
artifacts; it does not claim the ignored stream binaries are embedded here.
