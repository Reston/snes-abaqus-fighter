"""Collate one frozen cartridge's play-flow, native and reproduction evidence."""
import argparse
import ast
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from collate_pacing_floor_25 import SIX, count
from collate_combat_24 import failure_arrays, media_files
from release_evidence import EXPECTED_NATIVE_CORE, EXPECTED_INDEPENDENT_CORE
from v026_contracts import validate, canonical, BASE as INHERITED_BASE
from candidate_sources import snapshot as source_snapshot
from test_compatibility import CORE_PATH as INDEPENDENT_CORE_PATH
from play_flow_media import inventory as media_inventory
from play_flow_counterfactual import validate as validate_reference
from test_play_flow_long_26 import current_coverage as hour_coverage, compare_streams as compare_hour_streams
import math

INHERITED = {p: f'play-flow-v026-{p}-report.json' for p in ('pacing', 'supers', 'cpu', 'stage')}
PARTS = ('results', 'training', 'meter', 'arenas', 'arcade', 'manual', 'rounds',
         'feedback', 'previews', 'repeat', 'music', 'confirm', 'normal-guide', 'throw',
         'best', 'session', 'roster', 'motion', 'build', 'native-build', 'native-suite', 'launcher', 'stress', 'long-session', 'session-limit')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def read(name):
    report = json.loads((ROOT / name).read_bytes())
    require(isinstance(report, dict), 'Report must be an object: ' + name)
    return report


def rows_equal(rows, keys, inventory, label):
    require(isinstance(rows, list) and [tuple(r[k] for k in keys) for r in rows] == inventory,
            label + ' has incomplete or reordered coverage')
    require(all(r.get('passed', True) is True for r in rows), label + ' contains a failed case')


def feature_coverage(part, report):
    result = report.get('result')
    cases = report.get('cases')
    if part in ('training', 'meter', 'arcade', 'manual', 'rounds', 'feedback', 'music', 'confirm',
                'normal-guide', 'throw', 'best', 'session', 'roster', 'motion'):
        health = report.get('native_health', result.get('native_health') if isinstance(result, dict) else None)
        require(isinstance(health, dict) and health.get('callbacks', health.get('measured_callbacks', 0)) > 0 and
                isinstance(health.get('failures'), list) and not health['failures'] and
                0 <= health.get('max_spc_backlog', 255) <= 6, 'Native health inventory differs: ' + part)
    if part == 'results':
        routes = [r for r in result if 'route' in r]
        require(len(routes) == 20 and {r['winner'] for r in routes} == {0, 1}, 'Both result winners need all ten routes')
    elif part == 'training':
        rows_equal(result['cases'], ('fighter', 'port', 'challenge'),
                   list(itertools.product(range(12), range(2), (1, 2, 0))), part)
        require(all(r['dummy'] == {0: 6, 1: 4, 2: 0}[r['challenge']] for r in result['cases']), 'Drill partners differ')
    elif part in ('meter', 'manual'):
        rows_equal(result['cases'], ('fighter',), [(f,) for f in range(12)], part)
        if part == 'meter':
            require(all(r['ports'] == [0, 1] and r['thresholds'] == [95, 96, 0] for r in result['cases']), 'Natural meter threshold coverage differs')
        else:
            require(all(r['normal_actions'] == [1, 3, 4, 5] and r['special_and_super'] and r['reset_retains_manual'] for r in result['cases']), 'Manual practice lacks actual commands/reset')
    elif part == 'arenas':
        require(len(result) == 10 and {r['port'] for r in result if 'port' in r} == {0, 1}, 'Local arena routes differ')
    elif part == 'arcade':
        rows_equal(result['ladder'], ('shift', 'opponent'), [(s + 1, (s + 5) % 12) for s in range(11)], part)
        require(result['ladder'][-1].get('champion') is True, 'Eleventh Arcade victory is not recorded')
    elif part == 'rounds':
        rows_equal(result['cases'], ('fighter', 'winner_port'), list(itertools.product(range(12), range(2))), part)
    elif part in ('feedback', 'throw'):
        axes = ('punish-punch', 'punish-kick', 'counter', 'idle-hit', 'guard') if part == 'feedback' else (True, False)
        key = 'scenario' if part == 'feedback' else 'tech'
        rows_equal([r['after'] for r in cases], ('fighter', 'port', key),
                   list(itertools.product(range(12), range(2), axes)), part)
        require(all(r['exact_unmasked_equality'] is True and r['before']['unmasked_stream_sha256' if part == 'feedback' else 'unmasked_sha256'] == r['after']['unmasked_stream_sha256' if part == 'feedback' else 'unmasked_sha256'] for r in cases), 'Whole-state equality differs: ' + part)
    elif part == 'confirm':
        require(len(cases) == 39 and sum(r['independent'] for r in cases) == 3, 'Confirm proof needs both real links and late guard for all twelve fighters')
        for fighter in range(12):
            subset = [r for r in cases if not r['independent'] and r['fighter'] == fighter]
            require(len(subset) == 3 and {r.get('route') for r in subset if 'route' in r} == {'y->x', 'b->a'} and
                    sum(r.get('late_follow_up') == 'blocked' for r in subset) == 1, 'Missing actual confirm/late block')
    elif part == 'normal-guide':
        rows_equal(cases, ('independent', 'fighter'), list(itertools.product((False, True), range(12))), part)
        require(all(len(r['native_ground_actions']) == 8 for r in cases), 'Normal guide lacks both ports actual ground clocks')
    elif part in ('best', 'session'):
        expected = [(False, f) for f in range(12)] + [(True, f) for f in ((0, 5, 11) if part == 'best' else (0,))]
        rows_equal(cases, ('independent', 'fighter'), expected, part)
        if part == 'best':
            require(all(r['best_hits'] == 2 and r['best_damage'] > r['single_damage'] and
                        r['reset_before_publication'] and r['guide_retry_retains_best'] and r['new_session_clears_best'] for r in cases),
                    'Session best lacks actual record/retry/reset coverage')
        else:
            require(all([m['winner'] for m in r['matches']] == [0, 1, 0] and
                        [m['score'] for m in r['matches']] == [[1, 0], [1, 1], [2, 1]] for r in cases),
                    'Session score lacks actual alternating rematches')
    elif part == 'motion':
        rows_equal(cases, ('independent', 'stage', 'still'), list(itertools.product((False, True), range(3), (False, True))), part)
        require(len(report['comparisons']) == 6 and all(r['observable_equality'] is True and
                (r['exact_unmasked_equality'] is True if not r['independent'] else r['exact_unmasked_equality'] is None)
                for r in report['comparisons']) and report['accuracy_byte_equivalence_claimed'] is False,
                'Motion comparison makes an incomplete or incorrect equality claim')
    elif part == 'roster':
        rows_equal(cases, ('independent',), [(False,), (True,)], part)
        for row in cases:
            rows_equal(row['roster'], ('player', 'fighter'), list(itertools.product(range(2), range(12))), 'roster hints')
    elif part in ('music', 'repeat'):
        require(len(cases) == 2, 'Both pinned cores required: ' + part)
    elif part == 'previews':
        require(len(cases) == 6, 'All three native arenas need both cores')
    elif part == 'build':
        require(report.get('cartridge_reproduced') is True and report.get('stage_encoder_calls') == [0, 1, 2] and
                len(report.get('generated_files', {})) == 226 and report.get('rejected_snapshot_mutations') ==
                ['workspace', 'palette', 'source', 'missing-stage'] and report.get('generation_failure_preserved_live_assets') is True,
                'One-pass build reproduction/guard coverage differs')
        for key, producer in (('publication_guard_runs', 'test_asset_transaction.py'), ('cache_guard_runs', 'test_asset_cache.py')):
            runs = report.get(key, [])
            parsed = ast.parse((ROOT / 'tools' / producer).read_text())
            expected = sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_') for cls in parsed.body if isinstance(cls, ast.ClassDef) for n in cls.body)
            require(len(runs) == 2 and {r['optimized'] for r in runs} == {False, True} and
                    all(r['exit_code'] == 0 and r['tests'] == expected and r['output'].rstrip().endswith('OK') for r in runs),
                    producer + ' lacks both interpreter-mode proofs')
        require(report.get('ordinary_build_reused_assets') is True, 'The ordinary build did not prove asset reuse')
    elif part == 'native-build':
        require(report.get('cartridge_reproduced') is True and report.get('identical_outputs_not_replaced') is True and
                len(report.get('builds', [])) == 2 and all(r['exit_code'] == 0 for r in report['builds']), 'Native publication/reproduction proof differs')
        runs = report.get('native_artifact_guard_runs', [])
        parsed = ast.parse((ROOT / 'tools/test_native_artifacts.py').read_text())
        expected = sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_') for cls in parsed.body if isinstance(cls, ast.ClassDef) for n in cls.body)
        require(len(runs) == 2 and {r['optimized'] for r in runs} == {False, True} and
                all(r['exit_code'] == 0 and r['tests'] == expected and r['output'].rstrip().endswith('OK') for r in runs), 'Native publication fault proofs differ')
        for name, digest in report['published_files'].items():
            require(sha((ROOT / 'dist' / name).read_bytes()) == digest, 'Published native file changed: ' + name)
    elif part == 'native-suite':
        require(report.get('native_execution') is True and report.get('exit_code') == 0 and
                set(report.get('suite_reports', {})) == set(SIX), 'Canonical six-program execution is incomplete')
        for key, producer in (('source_guard_runs', 'test_candidate_sources.py'), ('media_guard_runs', 'test_play_flow_media.py'),
                              ('collation_guard_runs', 'test_play_flow_collation.py'), ('counterfactual_guard_runs', 'test_play_flow_counterfactual.py'), ('long_session_guard_runs', 'test_long_session_guards.py'), ('verification_runner_guard_runs', 'test_verification_runner_guards.py')):
            parsed = ast.parse((ROOT / 'tools' / producer).read_text())
            expected = sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_') for cls in parsed.body if isinstance(cls, ast.ClassDef) for n in cls.body)
            runs = report.get(key, [])
            require(len(runs) == 2 and {r['optimized'] for r in runs} == {False, True} and
                    all(r['exit_code'] == 0 and r['tests'] == expected and r['output'].rstrip().endswith('OK') for r in runs),
                    'Source/media/collation guards lack both interpreter modes: ' + producer)
    elif part == 'launcher':
        rows_equal(cases, ('scenario',), [(s,) for s in ('valid', 'wrong-sha', 'stale-version', 'truncated-rom', 'missing-manifest', 'malformed-manifest')], part)
        require(report.get('gui_opened') is False and report.get('setup_invoked') is False and
                [r['accepted'] for r in cases] == [True, False, False, False, False, False], 'Launcher validation scope differs')
    elif part == 'session-limit':
        matches=report['matches']
        require(len(matches)==200 and report['native_health']['callbacks']>0 and not report['native_health']['failures'] and report['native_health']['max_spc_backlog']<=6, 'Session limit lacks real native coverage')
        for index,row in enumerate(matches):
            score=[min(99,index+1),0] if index<100 else [99,min(99,index-99)]
            require(row['match']==index+1 and row['winner']==int(index>=100) and row['score']==score and row['earned_callbacks']>0 and row['native_checks']>0, 'Session saturation route/count differs')
        require(report['native_assertions']==sum(row['native_checks'] for row in matches), 'Session saturation native assertion count differs')
    elif part == 'long-session':
        rows_equal(cases, ('mode',), [(0,), (1,), (2,)], part)
        require(report['diagnostic'] is False, 'Long-session summary is partial')
        for row in cases:
            proof=row['native']
            require(proof['rom_sha256']==report['rom_sha256'] and proof['core']==report['core'] and row['legacy_six_button_champion_completeness_claimed'] is False, 'Continuous hour native identity/scope differs')
            require(hour_coverage(row['mode'],proof,math.ceil(proof['video_fps']*3600))==row['coverage'], 'Continuous hour current coverage differs')
            require(all(event['before_native']==event['after_trace']==event['after_native']==1 and 0<=event['neutral_callbacks']<=32 for event in row['roster_publication_waits']), 'Continuous hour route wait escapes its native roster transition')
        row=cases[0];baseline=read(row['baseline_reference']['path'])
        require(sha((ROOT/row['baseline_reference']['path']).read_bytes())==row['baseline_reference']['sha256'] and baseline['rom_sha256']==row['baseline_reference']['rom_sha256'], 'Original rare-lag reference differs')
        candidate=ROOT/row['stream']['path'];require(candidate.resolve().is_relative_to(ROOT/'build') and sha(candidate.read_bytes())==row['stream']['sha256'], 'Current complete unmasked hour stream changed')
        require(compare_hour_streams(ROOT/baseline['stream_path'],candidate)==row['comparison'] and row['comparison']['compared_logical_frames']>=200000, 'Full hour unmasked gameplay comparison differs')
    elif part == 'stress':
        rows_equal(cases, ('fighter', 'stage', 'phase', 'approach_port', 'spacing'),
                   list(itertools.product(range(12), range(3), range(3), range(2), ('wide', 'close'))), part)
        require(report.get('diagnostic') is False and report.get('candidate_collapsed_callbacks') == 0 and
                report.get('baseline_byte_equivalence_claimed') is False, 'Stress proof has incomplete or normalized scope')
        require(all(r.get('status') == 'passed' and not r.get('failures') and r['sdk_lag_increments'] == 0 and
                    r['max_changed_actor_bytes'] <= 3840 and r['peak_spc_backlog'] <= 6 and
                    r['pcm_samples'] > 0 and 0 < r['pcm_peak'] < 32767 and r['callbacks'] > 0 for r in cases), 'Current stress case failed native health')
        require(report['callbacks'] == sum(r['callbacks'] for r in cases), 'Stress callback count differs')
        for row in cases:
            path = (ROOT / row['retained_stream']).resolve()
            require(path.is_relative_to(ROOT / 'build') and path.is_file() and sha(path.read_bytes()) == row['stream_sha256'], 'Stress source stream differs')


def validate_record(report, name, rom, sources):
    require(report.get('status') == 'passed' and report.get('version') == '0.26.0' and report.get('rom_sha256') == rom,
            'Stale, failed or wrong-version evidence: ' + name)
    failure_arrays(report, name)
    require(report.get('source_sha256') == sources, 'Producer/runtime dependency inventory differs: ' + name)
    if name in ('play-flow-v026-build-report.json', 'play-flow-v026-native-build-report.json', 'play-flow-v026-launcher-report.json'):
        require(report.get('host_only') is True and report.get('native_execution') is False, 'Build proof must identify its host-only scope')
    else:
        require(report.get('controller_only') is True and report.get('memory_writes') is False and report.get('save_states') is False,
                'Read-only native controller contract differs: ' + name)
    for key in ('native_failed_checks', 'accuracy_native_failed_checks'):
        require(not report.get(key), 'Native assertion failures in ' + name)
    for key in ('native_checks',):
        if isinstance(report.get(key), list):
            require(all(r.get('passed') is True for r in report[key]), 'Failed native assertions in ' + name)
    return len(report['cases']) if name == 'play-flow-v026-stress-report.json' else count(report)


def collect(source_ref):
    manifest = read('dist/manifest.json')
    rom = sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes())
    require(manifest['version'] == '0.26.0' and manifest['sha256'] == rom and manifest['bytes'] == 4194304,
            'Wrong current native cartridge')
    freeze = git('rev-parse', source_ref + '^{commit}').decode().strip()
    git('merge-base', '--is-ancestor', freeze, 'HEAD')
    require(read('dist/manifest.json') == json.loads(git('show', freeze + ':dist/manifest.json')) and
            sha(git('show', freeze + ':dist/abaqus-after-hours.sfc')) == rom, 'Frozen cartridge differs')
    changed = git('diff', '--name-only', freeze, '--', 'src', 'tools', 'assets', 'dist', 'Build.cmd', 'Test.cmd', 'Play.cmd').decode().splitlines()
    extra = git('ls-files', '--others', '--exclude-standard', 'src', 'tools', 'assets', 'dist').decode().splitlines()
    require(not changed and not extra, 'Runtime/producers changed after freeze: ' + str(changed + extra))
    tree = git('rev-parse', freeze + '^{tree}').decode().strip()
    sources = source_snapshot(ROOT)
    for name, digest in sources.items():
        require(sha(canonical(name, git('show', freeze + ':' + name))) == digest, 'Frozen source bytes differ: ' + name)
    require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).lower() == EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
            'Actual Snes9x core differs from the pin')
    require(sha(Path(INDEPENDENT_CORE_PATH).read_bytes()).lower() == EXPECTED_INDEPENDENT_CORE['dll_sha256'].lower(),
            'Actual independent Accuracy core differs from the pin')
    preservation = validate(ROOT)
    evidence, media, features = {}, {}, {}
    names = (*SIX, *INHERITED.values(), *(f'play-flow-v026-{p}-report.json' for p in PARTS),
             'compatibility-test-report.json', 'fresh-build-test-report.json', 'authoring-guards-report.json')
    for name in names:
        path = 'docs/' + name
        report = read(path)
        require(report.get('rom_sha256', report.get('rom', {}).get('sha256')) == rom, 'Stale exact-ROM evidence: ' + name)
        require(report.get('status', 'passed' if name == 'test-report.json' else None) == 'passed', 'Failed evidence: ' + name)
        failure_arrays(report, name)
        total = count(report) if name in (*SIX, *INHERITED.values()) else None
        if name in INHERITED.values():
            require(report['source_commit'] == freeze and report['diagnostic'] is False and report['selected_fighters'] == list(range(12)), 'Incomplete inherited pacing proof')
            require(report['source_sha256'] == sources, 'Inherited runtime/producer inventory differs')
            require(report['preservation'] == preservation['inherited_v025_contract'], 'Inherited preservation differs')
        if name.startswith('play-flow-v026-') and name not in INHERITED.values():
            part = name[len('play-flow-v026-'):-len('-report.json')]
            total = validate_record(report, name, rom, sources)
            feature_coverage(part, report)
            if part in ('feedback', 'throw'):
                require(report['counterfactual']['source_commit'] == freeze, 'Counterfactual freeze differs')
                validate_reference(ROOT, report['counterfactual'])
            if part != 'stress':
                require(report.get('captures') == media_inventory(ROOT, part), 'Current capture inventory/bytes differ: ' + part)
            features[part] = total
        if name == 'compatibility-test-report.json':
            require(report['pinned_core'] is True and report['checks']['cadence']['passed'] is True and
                    report['core']['dll_sha256'].lower() == EXPECTED_INDEPENDENT_CORE['dll_sha256'], 'Independent smoke/pin differs')
        if name == 'fresh-build-test-report.json':
            require(report['source_commit'] == freeze and report['source_tree'] == tree and report['rebuilt_rom_sha256'] == rom and
                    report['generated_assets_verified'] == 226 and report['symbols_equal_after_source_path_normalization'] is True,
                    'Fresh source export does not reproduce the native cartridge')
            require(len(report['generated_assets']) == 226, 'Fresh output inventory differs')
            for row in report['generated_assets']:
                require(sha(canonical(row['file'], (ROOT / row['file']).read_bytes())) == row['sha256'], 'Fresh asset differs: ' + row['file'])
        if name == 'authoring-guards-report.json':
            require(report['source_commit'] == freeze, 'Authoring source freeze differs')
            parsed = ast.parse((ROOT / 'tools/test_authoring_guards.py').read_text(encoding='utf-8'))
            tests = sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_') for cls in parsed.body if isinstance(cls, ast.ClassDef) for n in cls.body)
            require(len(report['runs']) == 2 and {r['optimized'] for r in report['runs']} == {False, True} and
                    all(r['exit_code'] == 0 and r['tests'] == tests and r['output'].rstrip().endswith('OK') for r in report['runs']),
                    'Authoring mutations lack both interpreter modes')
        media_files(report, media)
        evidence[name] = {'path': path, 'sha256': sha((ROOT / path).read_bytes()), 'checks': total}
    shared = read('docs/stage-test-report.json')
    native = read('docs/play-flow-v026-native-suite-report.json')
    require(native.get('source_commit') == freeze, 'Six-suite execution commit differs')
    for name in SIX:
        require(native['suite_reports'][name]['sha256'] == evidence[name]['sha256'] and
                native['suite_reports'][name]['checks'] == evidence[name]['checks'], 'Canonical suite report binding differs: ' + name)
    require(native['native_six_suite_checks'] == sum(evidence[n]['checks'] for n in SIX), 'Canonical native suite total differs')
    require(shared.get('shared_native_execution') is True and shared['focused_report'] == 'docs/' + INHERITED['stage'] and
            shared['focused_report_sha256'] == evidence[INHERITED['stage']]['sha256'], 'Shared/focused stage execution differs')
    pacing = read('docs/' + INHERITED['pacing'])['result']
    require([(r['after']['fighter'], r['after']['port']) for r in pacing] == list(itertools.product(range(12), range(2))) and
            all(r['crossing']['crossed_airborne'] and r['crossing']['landed'] for r in pacing), 'Incomplete inherited pacing/crossing proof')
    supers = read('docs/' + INHERITED['supers'])['result']
    require([(r['fighter'], r['port'], r['guard']) for r in supers] == list(itertools.product(range(12), range(2), (False, True))),
            'Incomplete inherited super hit/guard proof')
    cpu = read('docs/' + INHERITED['cpu'])['result']
    for phase in ('before', 'after'):
        require([(r['cpu'], r['difficulty']) for r in cpu[phase]] == list(itertools.product(range(12), range(3))), 'Incomplete inherited CPU difficulty proof')
    require(len(cpu['hard_replays']) == 12 and cpu['pressure']['after'] < cpu['pressure']['before'], 'Inherited pressure/replay proof differs')
    for directory in ('docs/screenshots/play-flow-v026', 'docs/audio/play-flow-v026'):
        for path in sorted((ROOT / directory).iterdir()):
            if path.is_file():
                media[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    historical = 'docs/screenshots/play-flow-v026/before-arena-0.png'
    require(sha((ROOT / historical).read_bytes()) == sha(git('show', INHERITED_BASE + ':docs/screenshots/arena-0.png')),
            'Historical v0.25 picker reference differs from its committed source')
    result = {'status': 'passed', 'version': manifest['version'], 'rom_sha256': rom, 'checksum': manifest['checksum'],
              'scope': 'Native slower-combat and play-flow review candidate; no offline package',
              'source_commit': freeze, 'source_tree': tree, 'source_sha256': sources,
              'native_six_suite_checks': sum(evidence[n]['checks'] for n in SIX),
              'inherited_focused_checks': {part: evidence[name]['checks'] for part, name in INHERITED.items()},
              'play_flow_checks': features, 'shared_stage_and_focused_execution': True,
              'preservation': preservation, 'evidence': evidence, 'review_media_sha256': media,
              'human_playtest_approved': None, 'public_release_certified': False, 'full_offline_package_regenerated': False}
    (ROOT / 'docs/verification-v0.26.0.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps({k: result[k] for k in ('status', 'rom_sha256', 'native_six_suite_checks', 'play_flow_checks')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-freeze', required=True)
    collect(parser.parse_args().source_freeze)
