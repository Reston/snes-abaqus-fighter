"""Import bounded eight-phase walking legs without replacing approved faces."""
import hashlib
import json
from pathlib import Path
from PIL import Image

PHASES=('left-contact','left-recoil','right-pass','right-extension',
        'right-contact','right-recoil','left-pass','left-extension')
HAND_BOUNDS={0:(20,43,27,51),2:(33,43,45,51),4:(27,43,40,55),
             6:(23,42,38,54),7:(17,42,45,54),8:(31,42,51,54),
             9:(33,43,46,54),11:(20,42,37,59)}

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def hand_pixels(old,colors,fighter):
    """Retain low hands/belt accents inside their approved native regions.

    The bounded regions exclude the legs/feet. Keep original skin/accent
    pixels and their one-pixel ink edge rather than extending a flat crop.
    """
    if fighter not in HAND_BOUNDS:return set()
    warm={i+1 for i,(r,g,b) in enumerate(colors) if r>=128 and r>g+18 and g>b+6 and g*2>=r}
    left,top,right,bottom=HAND_BOUNDS[fighter]
    seen={y*96+x for y in range(top,bottom) for x in range(left,right) if old[y*96+x] in warm}
    protected=set()
    for i in seen:
        if i<46*96:continue
        x,y=i%96,i//96
        for yy in range(max(47,y-1),min(61,y+2)):
            for xx in range(max(0,x-1),min(96,x+2)):
                n=yy*96+xx
                if old[n]:protected.add(n)
    return protected

def apply_walking(root,fighter,slug,indices,metadata,colors,preview,extract,standing_height):
    manifest_path=root/'assets/art/walking-v1.json'
    if not manifest_path.is_file():return None
    manifest=json.loads(manifest_path.read_bytes())
    rows=manifest.get('fighters',[])
    require(manifest.get('schema')==1 and len(rows)==12 and
            {row.get('id') for row in rows}==set(range(12)),'Walking manifest must cover twelve individual fighters')
    row=next(row for row in rows if row['id']==fighter)
    require(row['slug']==f'{fighter:02d}-{slug}','Walking fighter identity mismatch')
    provenance=root/row['provenance']
    require(sha(provenance)==row['provenance_sha256'],'Walking provenance changed: '+slug)
    record=json.loads(provenance.read_bytes())
    source=root/record['source']
    require(source.parent==root/f'assets/art/characters/{fighter:02d}-{slug}', 'Walking source escapes individual fighter directory')
    require(record['fighter_id']==fighter and sha(source)==record['sha256'],'Walking master changed: '+slug)
    require(sha(root/record['reference'])==record['reference_sha256'],'Walking reference changed: '+slug)
    # Check the palette computed from the locked original masters, allowing
    # complete regeneration even when no previous generated palette exists.
    packed=bytearray()
    for r,g,b in [(0,0,0)]+colors:
        packed.extend(((r>>3)|((g>>3)<<5)|((b>>3)<<10)).to_bytes(2,'little'))
    require(hashlib.sha256(packed).hexdigest()==record['palette_sha256'],'Walking palette changed: '+slug)
    require(record['native_frame_range']==[20,27] and record['preserved_upper_rows']==[0,47], 'Walking edit scope changed')
    figures,details=extract(source,pose_names=PHASES,expected_count=8)
    # One shared conversion across the entire cycle. The existing upper body
    # retains its exact native pixels; every supporting sole meets baseline78.
    target_height=round(standing_height/2)
    scale=target_height/max(fig.height for fig in figures)
    base_native64=hashlib.sha256(''.join(hashlib.sha256(bytes(ids)).hexdigest() for ids in indices).encode()).hexdigest()
    quantizer=Image.new('P',(1,1))
    quantizer.putpalette(sum((list(c) for c in colors),[])+list(colors[-1])*241)
    for phase,(figure,detail) in enumerate(zip(figures,details)):
        n=20+phase;old=indices[n][:]
        size=(max(1,round(figure.width*scale)),max(1,round(figure.height*scale)))
        require(size[0]<=94 and size[1]<=77,'Walking silhouette exceeds native bounds: '+slug)
        # Anchor by the waist, not the varying foot-span bounding-box center.
        alpha=figure.getchannel('A')
        waist=alpha.crop((0,0,figure.width,max(1,figure.height//12))).getbbox()
        require(waist is not None,'Walking master has no waist: '+slug)
        waist_x=(waist[0]+waist[2])*scale/2
        resized=figure.resize(size,Image.Resampling.NEAREST)
        frame=Image.new('RGBA',(96,80))
        frame.alpha_composite(resized,(round(48-waist_x),78-size[1]))
        indexed=frame.convert('RGB').quantize(palette=quantizer,dither=Image.Dither.NONE)
        ids=[min(c,14)+1 if a else 0 for c,a in zip(indexed.get_flattened_data(),frame.getchannel('A').get_flattened_data())]
        ids[:47*96]=old[:47*96]
        hands=hand_pixels(old,colors,fighter)
        for pixel in hands:ids[pixel]=old[pixel]
        require(ids!=old,'Walking revision does not change the legs: '+slug)
        raster=Image.new('RGBA',(96,80));raster.putdata([colors[c-1]+(255,) if c else (0,0,0,0) for c in ids])
        box=raster.getchannel('A').getbbox()
        require(box is not None and box[0]>0 and box[2]<96 and box[3]==78,'Walking frame clips or loses floor contact: '+slug)
        indices[n]=ids;preview.paste(raster,(n*96,0))
        digest=hashlib.sha256(bytes(ids)).hexdigest()
        metadata[n].update(pose='walk-'+PHASES[phase],source_kind='walking-v1',
            previous_source_file=metadata[n]['source_file'],source_file=record['source'],
            previous_source_normalization=metadata[n]['source_scale'],
            source_scale=scale/metadata[n]['physical_scale'],source_normalization=scale/metadata[n]['physical_scale'],
            sourcefile=record['source'],source_sha256=record['sha256'],source_hash=record['sha256'],
            sourcehash=record['sha256'],pixels_sha256=digest,native_hash=digest,hash=digest,
            native_box=list(box),nativebox=list(box),native_size=[box[2]-box[0],box[3]-box[1]],
            effective_width=box[2]-box[0],effective_height=box[3]-box[1],
            walking_conversion_scale=scale,preserved_upper_rows=47,preserved_hand_pixels=len(hands),walking_source_box=detail['source_box'])
    require(len({bytes(indices[n]) for n in range(20,28)})==8,'Walking cycle must retain eight distinct native poses: '+slug)
    return {'provenance':row['provenance'],'source':record['source'],'sha256':record['sha256'],
            'frame_range':[20,27],'preserved_upper_rows':47,'conversion_scale':scale,
            'preserved_hand_policy':'original low-hand/waist accent pixels and one-pixel ink rim in bounded native regions',
            'base_identity_native64_sha256':base_native64,
            'final_native64_sha256':hashlib.sha256(''.join(hashlib.sha256(bytes(ids)).hexdigest() for ids in indices).encode()).hexdigest(),
            'native_frame_sha256':[metadata[n]['native_hash'] for n in range(20,28)]}
