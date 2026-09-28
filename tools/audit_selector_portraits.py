import os
from pathlib import Path
import struct,json,hashlib
from build_char import entries_data,names
ROOT=Path(__file__).resolve().parent
rows=[]
for pak in Path(os.environ.get('DBFZ_GAME', 'D:/Games/Dragon Ball FighterZ') + '/RED/Content/Paks/~mods').glob('*.pak'):
 for n,get in entries_data(pak):
  if 'CS_CharacterImage_' not in n or not n.endswith('.uasset'):continue
  b=get();ns=list(names(b));p=36+struct.unpack_from('<i',b,28)[0]
  ec,eo=struct.unpack_from('<ii',b,p+16)
  exp=[ns[struct.unpack_from('<i',b,eo+104*i+16)[0]][0] for i in range(ec)]
  row=dict(pak=pak.name,path=n,exports=exp,packages=[a[0] for a in ns if a[0].startswith('/Game/')])
  rows.append(row);print(pak.name,n.rsplit('/',1)[-1],exp)
(ROOT/'selector-analysis/portraits.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
