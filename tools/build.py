"""Reproducible native SNES build using PVSnesLib 4.6.0."""
from pathlib import Path
import hashlib, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
SDK = Path(os.environ.get('PVSNESLIB_HOME', ROOT/'.tools/sdk/pvsneslib')).resolve()
BUILD = ROOT/'build'
BUILD.mkdir(exist_ok=True)
os.chdir(ROOT)

def run(*args):
    args = [str(x) for x in args]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        raise SystemExit(r.returncode)
    if 'warning' in r.stderr.lower(): print(r.stderr)

if '--assets' in sys.argv or not (ROOT/'assets/generated/data.asm').exists():
    run(sys.executable, ROOT/'tools/make_assets.py')

template = (SDK/'devkitsnes/include/hdr.asm.in').read_text()
values = dict(HIROMDEF='', FASTROMDEF='.DEFINE FASTROM 1', ROMTITLE='ABAQUS AFTER HOURS',
              CARTRIDGETYPE='00', ROMSIZE='0A', SRAMSIZE='00', COUNTRY='01',
              LICENSEECODE='00', VERSION='00', ROMBANKS='32', ROMBANKSIZE='8000',
              ROMMODE='LOROM', ROMSPEED='FASTROM')
for key,value in values.items(): template = template.replace('@'+key+'@', value)
(ROOT/'build/hdr.asm').write_text(template)
binary = SDK/'devkitsnes/bin'
tool = SDK/'devkitsnes/tools'
includes = ['-I'+str(SDK/'pvsneslib/include'), '-I'+str(SDK/'devkitsnes/include'), '-I'+str(ROOT/'build'), '-I'+str(ROOT/'assets/generated')]
for unit in ['game']:
    run(binary/'816-tcc.exe', *includes, '-Wall','-c',ROOT/f'src/{unit}.c','-F','-o',BUILD/f'{unit}.ps')
    run(tool/'816-opt.exe','-i',BUILD/f'{unit}.ps','-o',BUILD/f'{unit}.asm')
    run(binary/'wla-65816.exe','-I',BUILD,'-d','-s','-x','-o',BUILD/f'{unit}.obj',BUILD/f'{unit}.asm')
for name,path in [('header', BUILD/'hdr.asm'), ('hardware',ROOT/'src/hardware.asm'), ('assets',ROOT/'assets/generated/data.asm'), ('soundbank',ROOT/'assets/generated/soundbank.asm')]:
    run(binary/'wla-65816.exe','-I',BUILD,'-d','-s','-x','-o',BUILD/f'{name}.obj',path)
lib = SDK/'pvsneslib/lib/LoROM_FastROM'
objects = [BUILD/'header.obj',BUILD/'game.obj',BUILD/'hardware.obj',BUILD/'assets.obj',BUILD/'soundbank.obj'] + sorted(lib.glob('*.obj'))
(BUILD/'linkfile').write_text('[objects]\n'+'\n'.join(str(p).replace('\\','/') for p in objects)+'\n')
rom = ROOT/'dist/abaqus-after-hours.sfc'
run(binary/'wlalink.exe','-d','-s','-A','-c','-L',lib,BUILD/'linkfile',rom)
data = rom.read_bytes()
assert len(data)==1024*1024, 'Expected 1 MiB LoROM'
assert data[0x7fd5] == 0x30, 'Expected FastROM LoROM header'
checksum = int.from_bytes(data[0x7fde:0x7fe0],'little')
assert checksum == (sum(data)&65535), 'ROM checksum mismatch'
manifest = {'title':'Abaqus: After Hours','version':'0.2.0','rom':rom.name,'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest(),'checksum':f'{checksum:04X}',
            'toolchain':'PVSnesLib 4.6.0 / 816-tcc / WLA-DX','mapping':'1 MiB FastROM LoROM','region':'NTSC 60 Hz'}
(ROOT/'dist/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built',rom.name, len(data),'bytes; SHA256',manifest['sha256'])
