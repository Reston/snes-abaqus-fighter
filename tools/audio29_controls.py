"""Reproduce the separate legacy-runtime cadence / approved-ROM PCM controls.

Use explicit retained ROM/symbol files. Does not build or alter production.
Both probes are controller-only, headless and capture-only, like test_audio29.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import test_audio29 as audio
import test_compatibility as compat
from emulator import Emulator
from v024_contracts import symbols


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('legacy-runtime', 'accuracy-clock', 'candidate-champion'), required=True)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--captures', type=Path)
    args = parser.parse_args()
    rom = args.rom.resolve(); syms = symbols(args.symbols.read_text())
    folder = args.captures.resolve() if args.captures else ROOT/'build'/('audio29-control-'+args.mode)
    folder.mkdir(exist_ok=True, parents=True)
    class ExplicitRom(Emulator):
        def __init__(self): super().__init__(rom)
    audio.Emulator = ExplicitRom; compat.ROM_PATH = rom
    # Legacy cartridges have no audio29 telemetry; this is a host read shim,
    # never a cartridge memory write or a normalization of native cadence.
    if args.mode != 'candidate-champion': audio.Native.a = lambda self, index: 0
    core = 'accuracy' if args.mode == 'accuracy-clock' else 'snes9x'
    host = audio.Native(core, syms, folder)
    report = {'status': 'failed', 'mode': args.mode, 'rom_sha256': audio.sha(rom.read_bytes()),
              'harness_sha256': audio.sha(Path(__file__).read_bytes()),
              'audio_harness_sha256': audio.sha((ROOT/'tools/test_audio29.py').read_bytes()),
              'symbols_sha256': audio.sha(args.symbols.read_bytes()),
              'host': audio.host_contract(), 'controller_only': True,
              'emulated_memory_writes': 0, 'savestate_calls': 0, 'audio_device_opened': False}
    try:
        if args.mode != 'accuracy-clock':
            report['champion'] = audio.champion(host)
        else:
            host.run(120, transition=True); report['windows'] = []
            for _ in range(12):
                host.pcm.clear(); host.recording = True; host.run(240); host.recording = False
                expected = 240*host.exact_rate/host.fps
                report['windows'].append({'video_frames': 240, 'sample_frames': len(host.pcm)//4,
                                          'expected': expected, 'error_samples': len(host.pcm)/4-expected})
        report['health'] = host.finish(); report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error); report['strict_callbacks'] = host.strict
        report['failures'] = host.failures
    finally:
        host.close(); args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({'status': report['status'], 'mode': args.mode, 'rom_sha256': report['rom_sha256']}))
    return int(report['status'] != 'passed')


if __name__ == '__main__': raise SystemExit(main())
