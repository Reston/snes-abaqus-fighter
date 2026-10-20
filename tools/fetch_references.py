"""Fetch only public portrait references explicitly supplied by the user."""
import json
from pathlib import Path
from urllib.request import urlopen, Request
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
items = json.loads((ROOT/'assets/references/team.json').read_text(encoding='utf-8')) + json.loads((ROOT/'assets/references/wealth.json').read_text(encoding='utf-8'))
names = ['Damián Gelerstein','Ivo Kovacevic','Cristóbal Mackenzie','José Ignacio Villarroel','Gonzalo Reyes','David Ponce','Fernando Pérez','Cristián Valdés','Ignacio Madariaga','José David Ordoñez','Roxana Espínola','Rodrigo Lártiga']
sheet = Image.new('RGB',(600,450),'#162235')
for n,name in enumerate(names):
    item = next(x for x in items if x['alt']==name)
    dest = ROOT/f'assets/references/fighter-{n:02}.jpg'
    if not dest.exists():
        with urlopen(Request(item['src'].replace('w=800','w=400'),headers={'User-Agent':'AbaqusAfterHours/0.1'})) as response:
            dest.write_bytes(response.read())
    img = Image.open(dest).convert('RGB')
    img = ImageOps.fit(img,(140,120),centering=(.5,.22))
    x,y = (n%4)*150,(n//4)*150
    sheet.paste(img,(x,y))
    ImageDraw.Draw(sheet).text((x+2,y+124),name,fill='white')
sheet.save(ROOT/'assets/references/contact-sheet.png')
print('Downloaded 12 public portraits; created contact-sheet.png')
