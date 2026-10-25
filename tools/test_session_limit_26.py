"""Earn 200 real local matches and verify both session counters saturate at 99."""
import hashlib, json, subprocess, sys, time
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'tools'))
import test_local_session_26 as t
from candidate_sources import snapshot
from play_flow_media import inventory
from test_champion import host_contract

def main():
    start = time.monotonic()
    sources = snapshot(root)
    m = json.loads((root / 'dist/manifest.json').read_bytes())
    checks = []
    rows = []

    def require(ok, label, details=None):
        checks.append({'check': label, 'passed': bool(ok), 'details': details})
        if not ok:
            raise RuntimeError((label, details))
    r = {'status': 'failed', 'version': m['version'], 'rom_sha256': m['sha256'], 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, cwd=root).strip(), 'source_sha256': sources, 'native_execution': True, 'primary_verification_counts_pooled': False, 'host_contract': host_contract(), 'controller_only': True, 'memory_writes': False, 'save_states': False, 'producer_path': 'tools/test_session_limit_26.py', 'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'matches': rows, 'checks': checks, 'native_health': t.native.HEALTH}
    old = t.inputs.Emulator
    t.inputs.Emulator = lambda **kwargs: t.native.Rig(False)
    try:
        e = t.inputs.boot(1, fighter=0, fighter2=0)
    finally:
        t.inputs.Emulator = old
    try:
        require(hashlib.sha256((root / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() == m['sha256'], 'the real cartridge matches its manifest')
        require(hashlib.sha256((root / '.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest().lower() == t.native.EXPECTED_NATIVE_CORE['dll_sha256'].lower(), 'the expanded native core matches its pin')
        require(t.score(e) == (0, 0), 'the actual local session starts at zero')
        expected = [0, 0]
        for index in range(200):
            winner = int(index >= 100)
            prior = tuple(expected)
            callbacks = t.earn(e, winner, prior)
            expected[winner] = min(99, expected[winner] + 1)
            require(t.score(e) == tuple(expected), 'only the winning session counter increments and both saturate at 99', [index + 1, winner, list(t.score(e))])
            t.presentation.verify_opaque_text_rows(e, [(19, 15, f'P1 {expected[0]:02} - {expected[1]:02} P2')], 'earned boundary session score')
            require(all((x['passed'] for x in t.presentation.checks)), 'native PPU shows the exact two-digit score')
            e.run(24)
            require(t.score(e) == tuple(expected), 'waiting never counts an extra match')
            require(not t.native.HEALTH['failures'] and all((x['passed'] for x in t.native.CHECKS)), 'all original strict callback predicates pass')
            require(e.host.audio_peak < 32767, 'long local sessions retain unclipped native PCM')
            rows.append({'match': index + 1, 'winner': winner, 'score': list(expected), 'earned_callbacks': callbacks, 'native_checks': len(t.native.CHECKS)})
            t.native.CHECKS.clear()
            t.presentation.checks.clear()
            e.host.pcm.clear()
            if index == 99:
                e.frame.save(root / 'docs/screenshots/play-flow-v026/local-session-cap-p1.png')
            if index == 199:
                e.frame.save(root / 'docs/screenshots/play-flow-v026/local-session-cap-both.png')
            if index < 199:
                t.inputs.press(e, 'a' if index % 2 else 'start', index % 2)
                e.run(30)
                s = t.inputs.trace(e)
                require(t.inputs.native_screen(e) == 3 and s['wins1'] == s['wins2'] == 0 and (t.score(e) == tuple(expected)), 'either-pad rematch retains only session score')
            if index % 10 == 9:
                print(json.dumps({'matches': index + 1, 'score': expected}), flush=True)
        require(t.score(e) == (99, 99), 'both real earned counters reach and retain 99')
        t.inputs.press(e, 'b', 1)
        e.run(35)
        require(t.inputs.native_screen(e) == 1 and t.score(e) == (0, 0), 'leaving the session resets both saturated scores')
        require(snapshot(root) == sources, 'supplemental producer runs on fixed source bytes')
        r['native_assertions'] = sum((x['native_checks'] for x in rows))
        r['captures'] = inventory(root, 'session-limit')
        r['status'] = 'passed'
    except Exception as error:
        r['error'] = repr(error)
        raise
    finally:
        e.close()
        r['elapsed_seconds'] = round(time.monotonic() - start, 3)
        r['check_count'] = len(checks)
        (root / 'docs/play-flow-v026-session-limit-report.json').write_text(json.dumps(r, indent=2) + '\n')
        print(json.dumps({k: r[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)
if __name__ == '__main__':
    main()
