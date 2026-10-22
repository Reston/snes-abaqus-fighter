"""Bundle already verified focused PCM captures for later human listening."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import package
import test_audio as audio


def main():
    source = ROOT/'docs/champion-audio-report.json'
    report = json.loads(source.read_bytes())
    manifest = json.loads((ROOT/'dist/manifest.json').read_bytes())
    package.validate_champion_audio(report, ROOT, manifest)
    core = audio.core_identity()
    if core['dll_sha256'] != report['core_sha256']:
        raise RuntimeError('Focused capture core identity differs from pinned listening pack core')
    listening = dict(report, version=manifest['version'], core=core, cues=report['production_cues'])
    archive = audio.make_listening_pack(listening)
    record = {'version':manifest['version'], 'rom_sha256':manifest['sha256'],
              'status':'passed', 'scope':'Verified capture archive for later human listening; no playback or listening approval.',
              'human_listening_approved':False,
              'source_report':source.relative_to(ROOT).as_posix(),
              'source_report_sha256':audio.digest(source.read_bytes()),
              'archive':archive, 'scores':list(report['music']),
              'cue_pairs':list(report['production_cues']), 'checks':audio.checks}
    target = ROOT/f"docs/audio-listening-v{manifest['version']}.json"
    target.write_bytes((json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps(record['archive']))


if __name__ == '__main__':
    main()
