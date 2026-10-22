"""Record the current champion's actual linked blocks after its clean rebuild."""
from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools'))
from package import champion_native_budget
manifest=json.loads((root/'dist/manifest.json').read_text())
record=champion_native_budget(root,manifest)
(root/'docs/champion-native-budget.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({'rom_sha256':record['rom_sha256'],'blocks':record['blocks']}))
