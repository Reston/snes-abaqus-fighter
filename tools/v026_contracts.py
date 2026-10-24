"""Preserve the slower v0.25 game while adding bounded v0.26 play-flow tools."""
import json
from pathlib import Path
import re

from v025_contracts import canonical, git, require, sha, validate as inherited_contract

BASE = '7ba40c106000b2b2eb916f6b35d47065334dd4c7'
BASE_ROM = 'f0223f8240e2338ec57674b465a93cc5b0145a6210b5d5933706bac7277168a2'
GENERATED_CHANGES = {'assets/generated/assets.h'} | {
    'assets/generated/arenas' + suffix for suffix in ('.png', '_tiles.bin', '_map.bin', '_pal.bin')}
PROTECTED = ('characters.h', 'pacing_recoil.h', 'super_moves.h', 'contact_geometry.h',
             'animation_weight.h', 'animation_banks.h', 'fighter_personality.h',
             'impact_presentation.h', 'audio_presentation_state.h', 'hardware.asm', 'trace.asm')
FUNCTIONS = ('attackStartup', 'attackActive', 'attackRecovery', 'attackDamage', 'attackReach',
             'rng', 'attackStart', 'actionForInput', 'captureInput', 'updateFighter', 'canHit',
             'combat', 'poseFor', 'drawFighter', 'drawFight', 'traceProfiles')


def function_source(source, name):
    pattern = r'(?m)^(?:\w+\s+)+\**' + re.escape(name) + r'\([^;{]*\)\s*\{'
    start = re.search(pattern, source)
    require(start is not None, 'Protected function missing', name)
    clean = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                   lambda match: ' ' * len(match[0]), source, flags=re.S)
    depth = 1
    index = start.end()
    while depth and index < len(clean):
        depth += (clean[index] == '{') - (clean[index] == '}')
        index += 1
    require(depth == 0, 'Unclosed protected function', name)
    return source[start.start():index]


def validate(root):
    root = Path(root)
    prior = inherited_contract(root, allow_arena_previews=True)
    git(root, 'merge-base', '--is-ancestor', BASE, 'HEAD')
    manifest = json.loads(git(root, 'show', BASE + ':dist/manifest.json'))
    require(manifest['version'] == '0.25.0' and manifest['sha256'] == BASE_ROM,
            'The inherited slower-game baseline identity differs')
    names = git(root, 'ls-tree', '-r', '--name-only', BASE, '--', 'assets/generated').decode().splitlines()
    changed = []
    for name in names:
        if canonical(name, (root / name).read_bytes()) != canonical(name, git(root, 'show', BASE + ':' + name)):
            changed.append(name)
    require(set(changed) <= GENERATED_CHANGES, 'v0.26 changed protected stage/fighter/audio payloads', changed)
    require(len(names) == 226, 'v0.26 baseline generated inventory differs')
    protected = {}
    for name in PROTECTED:
        path = 'src/' + name
        raw = canonical(path, (root / path).read_bytes())
        require(raw == canonical(path, git(root, 'show', BASE + ':' + path)),
                'v0.25 timing, animation, contact or native hardware source changed', path)
        protected[path] = sha(raw)
    current = canonical('game.c', (root / 'src/game.c').read_bytes()).decode('utf-8')
    before = canonical('game.c', git(root, 'show', BASE + ':src/game.c')).decode('utf-8')
    functions = {}
    for name in FUNCTIONS:
        raw = function_source(current, name)
        require(raw == function_source(before, name), 'v0.25 combat/input/render function changed', name)
        functions[name] = sha(raw.encode())
    for name, allowed_line in (
            ('controls', '\n        if(trainingDummy==6)return;'),
            ('captureFightInputs', '\n    else if(mode==2 && trainingDummy==5)second=pad1;')):
        raw = function_source(current, name)
        require(raw.count(allowed_line) == 1 and raw.replace(allowed_line, '') == function_source(before, name),
                'Practice input change escapes its explicit manual/recovery-guard branch', name)
        functions[name] = sha(raw.encode())
    cpu = canonical('cpu.h', (root / 'src/cpu_personality.h').read_bytes())
    # The only CPU dispatch addition sends new non-CPU practice dummies to
    # trainingKeys. The actual ordinary AI policy stays exactly v0.25.
    cpu = cpu.replace(b'if(mode==2 && trainingDummy!=4)return trainingKeys();',
                      b'if(mode==2 && trainingDummy<4)return trainingKeys();')
    require(cpu == canonical('cpu.h', git(root, 'show', BASE + ':src/cpu_personality.h')),
            'Ordinary CPU policy changed outside explicit practice dispatch')
    stage = canonical('stage.h', (root / 'src/stage_depth.h').read_bytes()).decode('utf-8')
    old_stage = canonical('stage.h', git(root, 'show', BASE + ':src/stage_depth.h')).decode('utf-8')
    for name in ('stageDepthLoad', 'stageDepthTrack', 'stageDepthAmbientReady'):
        require(function_source(stage, name) == function_source(old_stage, name),
                'Connected stage loading/camera policy changed', name)
    return {'baseline_commit': BASE, 'baseline_rom_sha256': BASE_ROM,
            'generated_count': len(names), 'changed_generated': changed,
            'preserved_generated': len(names) - len(changed),
            'protected_source_sha256': protected, 'protected_function_sha256': functions,
            'ordinary_cpu_policy_preserved': True, 'inherited_v025_contract': prior}
