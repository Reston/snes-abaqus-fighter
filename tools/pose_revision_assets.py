"""Apply disjoint, versioned whole-body combat pose revisions after identity pins."""
import hashlib
import json
from PIL import Image

SCOPES={
    'attack-v1':set((5,6,7,8,9,10,12,13,15,*range(32,46),47)),
    'jump-v1':set((29,30,31,*range(49,56))),
    'super-v1':{1,2,4},
}

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def apply_pose_revision(root,fighter,slug,indices,metadata,colors,preview,extract,standing_height,scope):
    index_path=root/f'assets/art/{scope}.json'
    if not index_path.is_file():return None
    index=json.loads(index_path.read_bytes());rows=index.get('fighters',[])
    require(index.get('schema')==1 and index.get('scope')==scope and len(rows)==12 and
            {row.get('id') for row in rows}==set(range(12)),scope+': incomplete roster')
    row=next(row for row in rows if row['id']==fighter)
    require(row['slug']==f'{fighter:02d}-{slug}',scope+': wrong fighter')
    provenance=root/row['provenance']
    require(sha(provenance)==row['provenance_sha256'],scope+': provenance hash differs')
    record=json.loads(provenance.read_bytes())
    require(record.get('scope')==scope and record.get('fighter_id')==fighter,scope+': wrong record scope')
    require(sha(root/record['reference'])==record['reference_sha256'],scope+': reference changed')
    packed=bytearray()
    for r,g,b in [(0,0,0)]+colors:packed.extend(((r>>3)|((g>>3)<<5)|((b>>3)<<10)).to_bytes(2,'little'))
    require(hashlib.sha256(packed).hexdigest()==record['palette_sha256'],scope+': palette changed')
    groups=[];targets=[]
    for source in record['sources']:
        path=root/source['file']
        require(path.parent==root/f'assets/art/characters/{fighter:02d}-{slug}',scope+': source escapes fighter directory')
        require(sha(path)==source['sha256'],scope+': source hash differs')
        require(source['count'] in (8,16) and len(source['poses'])==len(source['frames'])==source['count'],scope+': invalid pose mapping')
        figures,details=extract(path,pose_names=source['poses'],expected_count=source['count'])
        groups.append((source,figures,details));targets.extend(n for n in source['frames'] if n is not None)
    require(len(targets)==len(set(targets)) and set(targets)==SCOPES[scope],scope+': target ownership differs')
    anchor=record['anchor'];neutral=groups[anchor['source']][1][anchor['pose']]
    target=record.get('height_target',standing_height)
    require(isinstance(target,(int,float)) and target==standing_height,scope+': standing height must remain exact')
    scale=target/neutral.height
    quantizer=Image.new('P',(1,1));quantizer.putpalette(sum((list(c) for c in colors),[])+list(colors[-1])*241)
    for source,figures,details in groups:
        for figure,detail,n in zip(figures,details,source['frames']):
            if n is None:continue
            size=(max(1,round(figure.width*scale)),max(1,round(figure.height*scale)))
            require(size[0]<=94 and size[1]<=77,f'{scope}/{slug}/{n}: exceeds fixed canvas at shared scale: {size}')
            frame=Image.new('RGBA',(96,80));resized=figure.resize(size,Image.Resampling.NEAREST)
            frame.alpha_composite(resized,((96-size[0])//2,78-size[1]))
            indexed=frame.convert('RGB').quantize(palette=quantizer,dither=Image.Dither.NONE)
            ids=[min(c,14)+1 if a else 0 for c,a in zip(indexed.get_flattened_data(),frame.getchannel('A').get_flattened_data())]
            raster=Image.new('RGBA',(96,80));raster.putdata([colors[c-1]+(255,) if c else (0,0,0,0) for c in ids])
            box=raster.getchannel('A').getbbox()
            require(box is not None and box[0]>0 and box[2]<96 and box[3]==78,scope+': clipped pose or incorrect baseline')
            digest=hashlib.sha256(bytes(ids)).hexdigest();indices[n]=ids;preview.paste(raster,(n*96,0))
            metadata[n].update(pose=detail['pose'],source_kind=scope,source_file=source['file'],sourcefile=source['file'],
                source_sha256=source['sha256'],source_hash=source['sha256'],sourcehash=source['sha256'],
                source_scale=scale/metadata[n]['physical_scale'],source_normalization=scale/metadata[n]['physical_scale'],
                pixels_sha256=digest,native_hash=digest,hash=digest,native_box=list(box),nativebox=list(box),
                native_size=[box[2]-box[0],box[3]-box[1]],effective_width=box[2]-box[0],effective_height=box[3]-box[1],
                revision_scope=scope,conversion_scale=scale,revision_source_box=detail['source_box'])
    return {'scope':scope,'provenance':row['provenance'],'provenance_sha256':row['provenance_sha256'],
            'frame_ids':sorted(targets),'conversion_scale':scale,
            'native_frame_sha256':{str(n):metadata[n]['native_hash'] for n in sorted(targets)}}
