"""Select the current native stage oracle without weakening legacy coverage."""
import hashlib
import json
from pathlib import Path


def depth_manifest(root):
    root=Path(root);path=root/'assets/generated/stage-depth.json'
    if not path.is_file():return None
    value=json.loads(path.read_bytes())
    integrated=value.get('revision')=='detailed-color-floor-v025' and value.get('floor_plane')=='BG1'
    bg1={'gfx_word':[0,0x37ff if integrated else 0x2fff],'map_word':[0x3800,0x3fff],'map_size':[64,32],'bpp':4}
    bg3=({'enabled':False,'map_word':[0x5c00,0x5fff],'map_size':[32,32],'bpp':2} if integrated else
         {'gfx_word':[0x3000,0x37ff],'map_word':[0x5c00,0x5fff],'map_size':[32,32],'bpp':2})
    if (value.get('schema')!=1 or value.get('scope')!='stage-depth-v1' or
            value.get('hdma_mask')!=0 or value.get('live_dma_bytes')!=0 or value.get('obj_entries')!=0 or
            value.get('bg1')!=bg1 or value.get('bg3')!=bg3):
        raise ValueError('Unknown stage-depth allocation; update the native oracle explicitly')
    stages=value.get('stages',[])
    if [row.get('id') for row in stages]!=[0,1,2]:raise ValueError('Incomplete stage-depth roster')
    for stage in stages:
        if stage.get('ambient_enabled') is not False:raise ValueError('Legacy ambient must remain disabled for the wide map')
        for name,record in stage['outputs'].items():
            source=root/'assets/generated'/name
            if source.parent!=root/'assets/generated':raise ValueError('Invalid stage output path')
            raw=source.read_bytes()
            if len(raw)!=record['bytes'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:
                raise ValueError('Stage payload differs from the native allocation record: '+name)
    return value
