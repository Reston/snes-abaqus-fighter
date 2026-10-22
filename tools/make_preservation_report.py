"""Compare a frozen candidate with its approved generated-asset checkpoint."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from preservation import build_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref', required=True)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--allow-changed', nargs='*', default=[])
    parser.add_argument('--allow-added', nargs='*', default=[])
    args = parser.parse_args()
    report = build_report(ROOT, args.base_ref, args.source_ref,
                          args.allow_changed, args.allow_added)
    output = (json.dumps(report, indent=2)+'\n').encode()
    (ROOT/f"docs/preservation-v{report['version']}.json").write_bytes(output)
    (ROOT/'docs/champion-preservation-report.json').write_bytes(output)
    print(json.dumps({key: value for key, value in report.items() if key not in ('files', 'added')}))


if __name__ == '__main__':
    main()
