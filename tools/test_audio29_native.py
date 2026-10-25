"""Exact callback replay for a bounded audio29 C performance change.

Independent CPU encounter script; both ROMs receive every recorded callback.
No repeated callback removal, state masking, WRAM writes or savestates.
The separate historical earned-ladder failure is never used as a passing case.
"""
from pathlib import Path
import argparse
import ctypes as C
import gzip
import hashlib
import json
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import test_audio29 as audio
from emulator import Emulator
from test_expansion_06_cpu_personality import p1_script
from test_training import core_identity
from v024_contracts import symbols


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(e):
    def raw(name, count):
        return C.string_at(e.ram+(e.syms[name] & 0x1ffff), count).hex()
    return {
        'frame': e.read('frame', 2), 'fighters': raw('fighters', 128),
        'waves': raw('waves', 32), 'trace': C.string_at(e.ram+0x1ff00, 246).hex(),
        'rng': raw('randomseed', 2),
        'cpu': ''.join(raw(n, 1) for n in ('cpuTick','difficulty','trainingDummy','mode')),
        'input': ''.join(raw(n, 2) for n in ('pad0','pad1','edge0','edge1')),
        'recoil': raw('rearKickRecoil', 1),
        'supers': ''.join(raw(n, 2) for n in ('superActive','superRequest','superPhase',
                         'superNext','superContactEnd','superWaveDamage','superWaveReach'))}


class Recorded(audio.Native):
    def __init__(self, rom, syms, folder):
        class ExplicitRom(Emulator):
            def __init__(self): super().__init__(rom)
        audio.Emulator = ExplicitRom
        super().__init__('snes9x', syms, folder)
        self.rows = []; self.compare = False

    def run(self, n=1, p1=(), p2=(), transition=False):
        for _ in range(n):
            super().run(1, p1=p1, p2=p2, transition=transition)
            self.rows.append({'keys': [list(p1),list(p2)], 'transition': transition,
                              'state': snapshot(self) if self.compare else None})
        return self.state()


def boot(e, fighter, cpu, difficulty, stage, local=False):
    e.run(120, transition=True)
    if difficulty != 1: e.tap('l' if difficulty == 0 else 'r')
    for _ in range(1 if local else 2): e.tap('down')
    e.tap('a', transition=True); e.wait(1)
    for _ in range(fighter): e.tap('right')
    e.tap('a', transition=True)
    port = 1 if local else 0
    for _ in range((cpu-e.read('selected2')) % 12): e.tap('right', port)
    e.tap('a', port, transition=True); e.wait(2)
    for _ in range(stage): e.tap('down')
    e.tap('a', transition=True); e.wait(3); e.run(180)
    if not local:
        e.tap('start'); e.tap('up'); e.tap('start')
        if e.read('trainingDummy') != 4: raise AssertionError('CPU menu route')
    if (e.state()['fighter_id1'],e.state()['fighter_id2']) != (fighter,cpu):
        raise AssertionError(('fighter menu route', e.state()))


def case(args, cpu, difficulty, local):
    fighter = (cpu+5) % 12; stage = cpu % 3
    old = Recorded(args.baseline_rom, symbols(args.baseline_symbols.read_text()), args.streams)
    try:
        boot(old, fighter, cpu, difficulty, stage, local)
        old.compare = True
        for tick in range(args.frames):
            s = old.state(); keys = p1_script(s, tick)
            # Fresh face-button chords, opposing directions and both buffers
            # supplement the unchanged independent 900-tick CPU encounter.
            if tick % 300 in (280,281): keys = ['y','b']
            if tick % 300 in (286,287): keys = ['left','right','down','up']
            second = (['left','x'] if tick % 70 < 3 else
                      ['down','a'] if tick % 70 in (30,31,32) else [])
            old.run(1, p1=keys, p2=second)
        # Both pads own a pause/resume sample without advancing simulation.
        old.tap('start', 1); old.tap('select', 1); old.tap('start', 1)
        try: baseline_health = {'status':'passed', **old.finish()}
        except AssertionError as error:
            # Negative control remains failed. Every physical callback and
            # snapshot is retained/replayed, including its stalled callback.
            baseline_health = {'status':'failed','error':repr(error),
                               'strict_callbacks':old.strict,'failures':old.failures}
        tape = old.rows
    finally: old.close()
    new = Recorded(args.rom, symbols(args.symbols.read_text()), args.streams)
    differences = []
    try:
        for tick, row in enumerate(tape):
            new.compare = row['state'] is not None
            new.run(1, p1=row['keys'][0], p2=row['keys'][1], transition=row['transition'])
            if row['state'] != new.rows[-1]['state']:
                differences.append({'callback':tick, 'baseline':row['state'],
                                    'candidate':new.rows[-1]['state']})
        candidate_health = new.finish()
        name = ('local' if local else 'cpu')+f'-{cpu}-{difficulty}.json.gz'
        stream = args.streams/name
        with gzip.GzipFile(filename=str(stream), mode='wb', mtime=0) as output:
            output.write(json.dumps({'baseline':tape,'candidate':new.rows}, separators=(',',':')).encode())
        trajectory = hashlib.sha256(json.dumps([r['state'] for r in tape if r['state'] is not None],
                                               separators=(',',':')).encode()).hexdigest()
        return {'status':'failed' if differences or baseline_health['status'] != 'passed' else 'passed',
                'cpu':cpu,'fighter':fighter,'difficulty':difficulty,
                'mode':'local' if local else 'training CPU', 'stage':stage,
                'callbacks_replayed':len(tape),'unmasked_snapshots':sum(r['state'] is not None for r in tape),
                'stream':stream.relative_to(ROOT).as_posix(),'stream_sha256':sha(stream),
                'trajectory_sha256':trajectory,'different_callbacks':len(differences),
                'differences':differences[:12], 'all_differences_retained_in_stream':True,
                'baseline_health':baseline_health,'candidate_health':candidate_health}
    finally: new.close()


def emitted(folder, function):
    assembly = (folder/'game.asm').read_text()
    body = assembly[assembly.index(function+':\n'):]; body = body[:body.index('.ENDS')]
    syms = symbols((folder/'abaqus-after-hours.sym').read_text())
    start = next(n for n in syms if n.startswith('SECTIONSTART_.'+function+'text'))
    return {'section_bytes':syms[start.replace('SECTIONSTART_','SECTIONEND_')]-syms[start],
            'locals':int(re.search(r'\.define __'+function+r'_locals (\d+)',assembly)[1]),
            'static_instruction_lines':sum(bool(re.match(r'^[a-z]{3}(?:\.[bwl])?(?: |$)',line)) for line in body.splitlines()),
            'indirect_field_instructions':sum('[tcc__' in line for line in body.splitlines()),
            'assembly_sha256':sha(folder/'game.asm')}


def structural(args):
    baseline = subprocess.check_output(['git','show',args.baseline_source_commit+':src/game.c'],
                                       cwd=ROOT,text=True)
    original = baseline
    header = (ROOT/'src/audio29_native.h').read_text()
    clean = lambda text: re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S))
    transformations = []
    for function,end,macro in (
        ('captureInput','void captureFightInputs(void)','AUDIO29_CAPTURE_AT'),
        ('controls','/* 816-tcc rebuilds generic far pointers','AUDIO29_CONTROLS_AT')):
        start = baseline.index('void '+function+'(u8 p,') if function == 'captureInput' else baseline.index('void controls(u8 p) {')
        stop = baseline.index(end,start)
        body = baseline[start:stop].split('\n',1)[1].rsplit('}',1)[0]
        body = re.sub(r'    Fighter \*f=&fighters\[p\];(?:Fighter \*enemy=&fighters\[1-p\];)?\n','',body)
        body = body.replace('fighters[1-p]','(E)').replace('enemy->','(E).').replace('f->','(F).')
        for a,b in [('superRequest[p]','superRequest[P]'),('captureSuper(p,','captureSuper(P,'),
                    ('discardFighterInput(f)','discardFighterInput(&(F))'),
                    ('actionForInput(p,','actionForInput(P,'),('combatProfiles[p]','combatProfiles[P]'),
                    ('startSuper(p)','startSuper(P)'),('p==1','P==1'),('attackStart(p,','attackStart(P,')]:
            body = body.replace(a,b)
        actual = header.split('#define '+macro+'(F,E,P) do {',1)[1].split('\n} while(0)',1)[0]
        actual = re.sub(r'\\(?:\n|$)','\n',actual)
        if clean(body) != clean(actual): raise AssertionError(('Non-mechanical C change',function))
        replacement = '#include "audio29_native.h"\n' if function == 'captureInput' else ''
        baseline = baseline[:start]+replacement+baseline[stop:]
        transformations.append({'function':function,'original_tests_calls_writes_order_exact':True,
                                'before':emitted(args.baseline_rom.parent,function),
                                'candidate':emitted(args.candidate_build,function)})
    if baseline != (ROOT/'src/game.c').read_text(): raise AssertionError('Other game.c changes')
    for name in ('cpu_personality.h','hardware.asm','trace.asm'):
        old = subprocess.check_output(['git','show',args.baseline_source_commit+':src/'+name],cwd=ROOT)
        if old.replace(b'\r\n',b'\n') != (ROOT/'src'/name).read_bytes().replace(b'\r\n',b'\n'):
            raise AssertionError(('Other native source changed',name))
    before = symbols(args.baseline_symbols.read_text()); after = symbols(args.symbols.read_text())
    ram = lambda v:v < 0x2000 or 0x7e0000 <= v < 0x800000
    a = {n:v for n,v in before.items() if ram(v)}; b = {n:v for n,v in after.items() if ram(v)}
    if a != b: raise AssertionError('RAM labels changed')
    return {'baseline_source_commit':args.baseline_source_commit,'prior_ram_labels_exact':len(a),
            'only_two_mechanical_function_replacements':True,'cpu_hardware_trace_exact':True,
            'transformations':transformations}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-rom',type=Path,required=True)
    p.add_argument('--baseline-symbols',type=Path,required=True)
    p.add_argument('--rom',type=Path,default=ROOT/'dist/abaqus-after-hours.sfc')
    p.add_argument('--symbols',type=Path,default=ROOT/'dist/abaqus-after-hours.sym')
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--streams',type=Path,required=True)
    p.add_argument('--frames',type=int,default=900)
    p.add_argument('--baseline-source-commit',default='0aa6c35e94682a7dff50e174822d71a05d234c94')
    p.add_argument('--candidate-build',type=Path,default=ROOT/'build/audio29-followup-final-afc7ff2c')
    args = p.parse_args(); args.streams = args.streams.resolve(); args.streams.mkdir(parents=True,exist_ok=True)
    report = {'status':'failed','baseline_rom_sha256':sha(args.baseline_rom),'rom_sha256':sha(args.rom),
              'harness_sha256':sha(__file__),'core':core_identity(),'host':audio.host_contract(),
              'scope':'bounded C performance equivalence; no combined certification',
              'callback_removal':0,'masked_state_fields':0,'emulated_memory_writes':0,
              'savestate_calls':0,'cases':[]}
    paths = [*ROOT.joinpath('src').glob('*'), *ROOT.joinpath('tools').glob('*.py')]
    inputs = {p.relative_to(ROOT).as_posix():sha(p) for p in paths if p.is_file()}
    report['inputs'] = inputs; started = time.monotonic()
    try:
        report['structural'] = structural(args)
        for difficulty in range(3):
            for cpu in range(12):
                report['cases'].append(case(args,cpu,difficulty,False))
        for cpu in (0,5,10): report['cases'].append(case(args,cpu,1,True))
        if any(sha(ROOT/path) != value for path,value in inputs.items()):
            raise AssertionError('Producer/harness changed during proof')
        report['status'] = 'passed' if all(c['status'] == 'passed' for c in report['cases']) else 'failed'
        report['candidate_strict_cadence_passed'] = True  # Each new.finish() raised on any failure.
        report['exact_callback_equivalent_cases'] = sum(c['status'] == 'passed' for c in report['cases'])
    except Exception as error:
        report['error'] = repr(error); raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started,3)
        args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':report['status'],'cases':len(report['cases']),
                      'unmasked_snapshots':sum(r['unmasked_snapshots'] for r in report['cases'])}))
    return int(report['status'] != 'passed')


if __name__ == '__main__': raise SystemExit(main())
