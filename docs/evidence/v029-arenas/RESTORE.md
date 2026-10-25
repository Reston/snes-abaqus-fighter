# Restore the captured arena proof

These are captured QA files, not new production code. Every .py.txt, .h.txt,
.sym.txt, patch, log and JSON payload preserves its original bytes.
The manifest gives original absolute execution paths, sizes, SHA256 hashes
and an explicit file_alias_map. The failed report restores to its ignored
historical path, never over the current passed report.

The producer is 4c35ee89d6269662269481ffafff0166a905c775. Native source/assets
remain cb61690501d0688050a453aabcdd6993bc6dcb49. Only the approved one-line
arena tick return differs in the reference; all other five features,
237 generated outputs and 1,329 mutable addresses remain identical.

## Historical reconstruction prerequisites

These preparation instructions were not executed during this delivery.
Exact replay uses a clean, inactive historical checkout at
D:/snes-abaqus-fighter with HEAD at the producer commit above. Retain this
delivery's docs/evidence/v029-arenas/, Accuracy report and native media:
required_delivery_files_for_wrapper lists the exact delivery paths/hashes.

The unchanged wrapper also binds 34 ignored historical release ZIPs
(404,453,268 bytes) in the original frozen dist inventory. Restore their
original bytes from the retained archive cache; the manifest lists each
path/hash under required_external_ignored_release_archives. Pinned Python,
Pillow, SDK and core caches remain external prerequisites. No guard is
removed for a fresh checkout. This is captured proof source/provenance,
not a self-contained toolchain or historical release archive package.

For an isolated reference reconstruction, export source without changing
ROOT source:

~~~powershell
Set-Location -LiteralPath 'D:/snes-abaqus-fighter'
$taskReference='D:/snes-abaqus-fighter-arena-cf-cb61690-7e942e57'
New-Item -ItemType Directory -Path 'D:/snes-abaqus-fighter/build/v029' -Force | Out-Null
New-Item -ItemType Directory -Path $taskReference -Force | Out-Null
git -C 'D:/snes-abaqus-fighter' archive --format=tar --output='D:/snes-abaqus-fighter/build/v029/arena-reference-source.tar' cb61690501d0688050a453aabcdd6993bc6dcb49 src tools web assets dist
tar -xf 'D:/snes-abaqus-fighter/build/v029/arena-reference-source.tar' -C $taskReference
if (-not (Test-Path -LiteralPath "$taskReference/.tools")) {
    cmd /c mklink /J 'D:\snes-abaqus-fighter-arena-cf-cb61690-7e942e57\.tools' 'D:\snes-abaqus-fighter\.tools'
}
~~~

Restore captured ignored inputs using the alias map below. It refuses to
overwrite different existing bytes. Captured native manifest/symbol outputs
are comparison values and are not copied into an unbuilt reference. ROOT
tools are verified against their captures, never replaced.

~~~powershell
$taskRoot='D:/snes-abaqus-fighter'
$taskManifest=Get-Content -LiteralPath "$taskRoot/docs/evidence/v029-arenas/manifest.json" -Raw | ConvertFrom-Json
foreach ($entry in $taskManifest.file_alias_map) {
    $from=Join-Path $taskRoot $entry.published_path
    if ((Get-FileHash -LiteralPath $from -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Capture differs: $from" }
    if ($entry.restore_policy -eq 'verify_frozen_source_only') {
        if ((Get-FileHash -LiteralPath $entry.original_execution_path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Frozen source differs: $($entry.original_execution_path)" }
        continue
    }
    if ($entry.restore_policy -eq 'verify_reference_source_only') { continue }
    if ($entry.published_path -match '/reference-(manifest\.json|symbols\.sym\.txt)$') { continue }
    $to=$entry.restore_to_original_path
    if (Test-Path -LiteralPath $to) {
        if ((Get-FileHash -LiteralPath $to -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Target differs: $to" }
    } else {
        New-Item -ItemType Directory -Path (Split-Path -Parent $to) -Force | Out-Null
        Copy-Item -LiteralPath $from -Destination $to
    }
}
~~~

Apply only the approved line to the isolated reference. This also restores
audited LF/CRLF representations: every resulting source/asset byte must match
the captured export, accommodating Git checkout line-ending settings.

~~~powershell
$env:PYTHONDONTWRITEBYTECODE='1'
@'
from pathlib import Path
import hashlib,json
r=Path('D:/snes-abaqus-fighter-arena-cf-cb61690-7e942e57')
a=json.loads((r/'build/arena-counterfactual-source-audit.json').read_bytes())
p=r/'src/arena_life29.h';raw=p.read_bytes().replace(b'\r\n',b'\n')
line=b'    return; /* Counterfactual only: keep the arena upload unarmed. */\n'
if line not in raw:
    needle=b'    v29ArenaState[12]=0;\n'
    assert raw.count(needle)==1
    raw=raw.replace(needle,needle+line)
p.write_bytes(raw)
for rel,digest in a['reference_producer_inputs'].items():
    if rel.startswith('dist/'): continue
    p=r/rel;raw=p.read_bytes();lf=raw.replace(b'\r\n',b'\n')
    match=next((v for v in (raw,lf,lf.replace(b'\n',b'\r\n'))
                if hashlib.sha256(v).hexdigest()==digest),None)
    assert match is not None,rel
    if match!=raw: p.write_bytes(match)
print('Exact audited isolated source bytes restored')
'@ | & 'D:/snes-abaqus-fighter/.tools/python/python.exe' -
~~~

## Exact executed commands

Both commands exited 0; the reference build reused unchanged generated
assets. No setup/download/shared cache replacement occurred. All complete
argv, including retained Accuracy and failed v0.28 commands, are in manifest.

~~~powershell
Set-Location -LiteralPath 'D:/snes-abaqus-fighter'
$env:PYTHONDONTWRITEBYTECODE='1'
$p=[System.Diagnostics.Process]::GetCurrentProcess()
$p.ProcessorAffinity=[IntPtr]12288
$p.PriorityClass='BelowNormal'
& 'D:/snes-abaqus-fighter/.tools/python/python.exe' 'D:/snes-abaqus-fighter/tools/run_background.py' --log 'D:/snes-abaqus-fighter-arena-cf-cb61690-7e942e57/build/arena-counterfactual-build.log' -- 'D:/snes-abaqus-fighter/.tools/python/python.exe' 'D:/snes-abaqus-fighter-arena-cf-cb61690-7e942e57/tools/build.py'
& 'D:/snes-abaqus-fighter/.tools/python/python.exe' 'D:/snes-abaqus-fighter/tools/run_background.py' --log 'D:/snes-abaqus-fighter/build/v029/arena-current-snes9x-final.log' -- 'D:/snes-abaqus-fighter/.tools/python/python.exe' 'D:/snes-abaqus-fighter/build/v029/run_arenas_current_source.py'
~~~

Before replay, compare the rebuilt reference ROM/symbols with the manifest:
ROM ed0d22e6bfbec35cc728458bedc84917be53c55582d6cdfaf9e00e3d52843fa2;
symbols 2595d0ace16f90f239b891ad6f3dba2d2d3cf4de1df27a1f34e8b1409fa57358.
The unchanged wrapper validates all captured reference provenance and
retained failure/Accuracy inputs before native replay.

The accepted Snes9x result is 265,621 checks, three full native cases and
three replays: 8,201 controller callbacks plus three initial states compare
all 414 unmasked gameplay bytes, including absolute TRACE2. Both ROMs retain
strict native health. Candidate arena transfers total 1,358; reference
transfers total zero and its pool stays phase0. Native Rig/arena_case/trace/
game/health code is imported unchanged. A read-only Python return observer
retains exact first-divergence bytes. There is no masking, rebasing, memory
write, save state, callback collapse or quiet-frame waiver.

Accuracy retains its original cb61690-producer-bound 117,158-check pass on
the same current ROM. The historical v0.28 comparison remains FAILED at
initial TRACE2, 691 versus 690; its exact report/log/diagnostic/native captures
are preserved here. This delivery ran no native jobs and changed neither
passed current report.
