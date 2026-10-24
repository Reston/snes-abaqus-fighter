"""Read-only checks for the native selection actor, shared by UI proofs."""
import ctypes as C
from functools import lru_cache
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

@lru_cache(maxsize=12)
def poses(fighter):
    result={}
    for bank,suffix in enumerate(('', 'b','c','d','e','f','g','h')):
        raw=(ROOT/f'assets/generated/fighter{fighter:02}{suffix}.bin').read_bytes()
        for index in range(8):result[raw[index*3840:(index+1)*3840]]=bank*8+index
    return result

def uploaded_pose(host,fighter):
    pointer=host.core.retro_get_memory_data(3)
    raw=C.string_at(pointer,host.core.retro_get_memory_size(3))
    payload=b''.join(raw[0xc000+row*512:0xc000+row*512+384] for row in range(10))
    return poses(fighter).get(payload)

@lru_cache(maxsize=256)
def expected_crop(fighter,pose):
    with Image.open(ROOT/'assets/generated/select.png') as image:
        background=image.convert('RGB').point(lambda v:(v>>3)*255//31).crop((2,24,98,104))
    with Image.open(ROOT/f'assets/generated/fighter{fighter:02}.png') as image:
        actor=image.crop((pose*96,0,(pose+1)*96,80)).convert('RGBA')
        actor=actor.point(lambda v:(v>>3)*255//31)
    background.paste(actor,(0,0),actor.getchannel('A'))
    return background

def verify_preview(host,fighter):
    pose=uploaded_pose(host,fighter)
    if pose is None:raise AssertionError(('selection VRAM is not an approved full-body pose',fighter))
    expected=expected_crop(fighter,pose)
    actual=host.frame.crop((2,24,98,104)).convert('RGB')
    maximum=max(abs(a-b) for p,q in zip(actual.get_flattened_data(),expected.get_flattened_data()) for a,b in zip(p,q))
    if maximum>3:raise AssertionError(('native full-body preview pixels differ',fighter,pose,maximum))
    return {'fighter':fighter,'pose':pose,'canvas':[96,80],'origin':[2,24],'max_channel_delta':maximum}
