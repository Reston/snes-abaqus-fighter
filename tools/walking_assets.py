"""Import coordinated full-body walking poses; rejected v1 sources stay historical."""
import hashlib
import json
from PIL import Image

PHASES=('left-contact','left-recoil','right-pass','right-extension',
        'right-contact','right-recoil','left-pass','left-extension')

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def apply_walking(root,fighter,slug,indices,metadata,colors,preview,extract,standing_height):
    manifest_path=root/'assets/art/walking-v2.json'
    require(manifest_path.is_file(),'Missing full-body walking manifest')
    manifest=json.loads(manifest_path.read_bytes());rows=manifest.get('fighters',[])
    require(manifest.get('schema')==2 and manifest.get('scope')=='coordinated-full-body' and
            len(rows)==12 and {row.get('id') for row in rows}==set(range(12)),
            'Walking manifest must cover twelve individual full-body cycles')
    row=next(row for row in rows if row['id']==fighter)
    require(row['slug']==f'{fighter:02d}-{slug}','Walking fighter identity mismatch')
    provenance=root/row['provenance']
    require(sha(provenance)==row['provenance_sha256'],'Walking provenance changed: '+slug)
    record=json.loads(provenance.read_bytes());source=root/record['source']
    require(source.parent==root/f'assets/art/characters/{fighter:02d}-{slug}',
            'Walking source escapes individual fighter directory')
    require(record['fighter_id']==fighter and sha(source)==record['sha256'],'Walking master changed: '+slug)
    require(sha(root/record['reference'])==record['reference_sha256'],'Walking reference changed: '+slug)
    packed=bytearray()
    for r,g,b in [(0,0,0)]+colors:
        packed.extend(((r>>3)|((g>>3)<<5)|((b>>3)<<10)).to_bytes(2,'little'))
    require(hashlib.sha256(packed).hexdigest()==record['palette_sha256'],'Walking palette changed: '+slug)
    require(record['native_frame_range']==[20,27] and record['scope']=='coordinated-full-body',
            'Walking edit scope changed')
    figures,details=extract(source,pose_names=PHASES,expected_count=8)
    # One isotropic conversion for the whole body and whole cycle. No waist
    # splice or fixed upper-body overlay. Sole anchoring retains natural bob.
    scale=standing_height/max(fig.height for fig in figures)
    base_native64=hashlib.sha256(''.join(hashlib.sha256(bytes(ids)).hexdigest() for ids in indices).encode()).hexdigest()
    quantizer=Image.new('P',(1,1))
    quantizer.putpalette(sum((list(c) for c in colors),[])+list(colors[-1])*241)
    for phase,(figure,detail) in enumerate(zip(figures,details)):
        n=20+phase
        size=(max(1,round(figure.width*scale)),max(1,round(figure.height*scale)))
        require(size[0]<=94 and size[1]<=77,'Walking silhouette exceeds native bounds: '+slug)
        resized=figure.resize(size,Image.Resampling.NEAREST)
        frame=Image.new('RGBA',(96,80))
        frame.alpha_composite(resized,((96-size[0])//2,78-size[1]))
        indexed=frame.convert('RGB').quantize(palette=quantizer,dither=Image.Dither.NONE)
        ids=[min(c,14)+1 if a else 0 for c,a in zip(indexed.get_flattened_data(),frame.getchannel('A').get_flattened_data())]
        require(ids!=indices[n],'Walking revision does not change pose: '+slug)
        raster=Image.new('RGBA',(96,80));raster.putdata([colors[c-1]+(255,) if c else (0,0,0,0) for c in ids])
        box=raster.getchannel('A').getbbox()
        require(box is not None and box[0]>0 and box[2]<96 and box[3]==78,
                'Walking frame clips or loses floor contact: '+slug)
        require(all(any(ids[y*96:(y+1)*96]) for y in range(box[1],box[3])),
                'Walking silhouette has a disconnected horizontal body seam: '+slug)
        indices[n]=ids;preview.paste(raster,(n*96,0))
        digest=hashlib.sha256(bytes(ids)).hexdigest()
        metadata[n].update(pose='walk-'+PHASES[phase],source_kind='walking-v2',
            previous_source_file=metadata[n]['source_file'],source_file=record['source'],
            previous_source_normalization=metadata[n]['source_scale'],
            source_scale=scale/metadata[n]['physical_scale'],source_normalization=scale/metadata[n]['physical_scale'],
            sourcefile=record['source'],source_sha256=record['sha256'],source_hash=record['sha256'],
            sourcehash=record['sha256'],pixels_sha256=digest,native_hash=digest,hash=digest,
            native_box=list(box),nativebox=list(box),native_size=[box[2]-box[0],box[3]-box[1]],
            effective_width=box[2]-box[0],effective_height=box[3]-box[1],
            walking_conversion_scale=scale,walking_scope='coordinated-full-body',walking_source_box=detail['source_box'])
    require(len({bytes(indices[n]) for n in range(20,28)})==8,'Walking cycle must retain eight distinct native poses: '+slug)
    return {'provenance':row['provenance'],'source':record['source'],'sha256':record['sha256'],
            'frame_range':[20,27],'scope':'coordinated-full-body','conversion_scale':scale,
            'base_identity_native64_sha256':base_native64,
            'final_native64_sha256':hashlib.sha256(''.join(hashlib.sha256(bytes(ids)).hexdigest() for ids in indices).encode()).hexdigest(),
            'native_frame_sha256':[metadata[n]['native_hash'] for n in range(20,28)]}
