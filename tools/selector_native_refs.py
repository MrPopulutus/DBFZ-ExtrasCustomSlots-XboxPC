import os
from pathlib import Path
import sys,re,struct,bisect,json
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'validation-tools'))
import pefile,capstone,numpy as np
pe=pefile.PE(os.environ.get('DBFZ_GAME', 'D:/Games/Dragon Ball FighterZ') + '/RED/Binaries/Win64/DRAGON_BALL_FighterZ.exe',fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
img=pe.get_memory_mapped_image()
funcs=sorted((e.struct.BeginAddress,e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION)
starts=[x[0] for x in funcs]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
def fun(p):
 i=bisect.bisect_right(starts,p)-1
 return funcs[i] if i>=0 and p<funcs[i][1] else None
def show(p,end=None):
 f=fun(p) if end is None else (p,end)
 if f:
  for ins in md.disasm(img[f[0]:f[1]],f[0]):
   note=''
   for op in ins.operands:
    if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
     t=ins.address+ins.size+op.mem.disp
     note+=f' ; @{t:x}'
     if 0<=t<len(img)-4 and ins.mnemonic in ('movss','addss','mulss','subss','divss','comiss'):note+=f' float={struct.unpack_from("<f",img,t)[0]}'
   print(f'{ins.address:x}: {ins.mnemonic} {ins.op_str}{note}')
def refs(target):
 out=[]
 # Locate signed RIP offsets, then validate containing instruction boundaries.
 for s in pe.sections:
  if not s.Characteristics&0x20000000:continue
  lo=s.VirtualAddress;seg=img[lo:lo+s.Misc_VirtualSize]
  for align in range(4):
   n=(len(seg)-align)//4
   vals=np.frombuffer(seg,dtype='<i4',count=n,offset=align).astype(np.int64)
   pos=np.arange(n)*4+lo+align
   candidates=pos[np.isin(pos+4+vals,[target,target-1,target-2,target-4])]
   for p in candidates:
    f=fun(int(p))
    if not f:continue
    for ins in md.disasm(img[f[0]:f[1]],f[0]):
     if ins.address<=p<ins.address+ins.size:
      if any(op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP and ins.address+ins.size+op.mem.disp==target for op in ins.operands):out.append((ins.address,f[0],ins.mnemonic+' '+ins.op_str))
      break
 return sorted(set(out))
def callers(target):
 out=[]
 for s in pe.sections:
  if not s.Characteristics&0x20000000:continue
  lo=s.VirtualAddress;seg=img[lo:lo+s.Misc_VirtualSize]
  for m in re.finditer(b'[\xe8\xe9]',seg):
   p=m.start()
   if p+5<=len(seg) and p+lo+5+struct.unpack_from('<i',seg,p+1)[0]==target:out.append(p+lo)
 return out
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--strings':
  for text in sys.argv[2:]:
   for enc in ['ascii','utf-16-le']:
    for m in re.finditer(re.escape(text.encode(enc)),img):print(text,hex(m.start()),refs(m.start()))
 elif len(sys.argv)>1:
  show(int(sys.argv[1],16),int(sys.argv[2],16) if len(sys.argv)>2 else None)
 else:
  for word in ['CS_CharacterImage_', 'SetBGCharaTexture1P','SetBGCharaTexture2P','SetBGCharaTexOffsetToCPP','REDWidgetCharaSelect_Root_S3','KeyGuide','HelpText','KeyHelp']:
   needle=word.encode('utf-16-le'); hits=[m.start() for m in re.finditer(re.escape(needle),img)]
   print(word, [hex(x) for x in hits])
   for p in hits:print('refs',refs(p))
