"""Move Werezaru's cosmetics to EXG while retaining EX's gameplay registries."""
import os
import pathlib, re, json, shutil, hashlib, struct
from build_char import entries_data, names, make_conv, rename_path, convert_uasset, convert_uexp, write_pak
root=pathlib.Path(os.environ.get('DBFZ_WORK', pathlib.Path(__file__).resolve().parent))
source=pathlib.Path(os.environ.get('DBFZ_WEREZARU', 'C:/EDIT-ME/Unverum/Mods/Dragon Ball FighterZ/Sonic x Dragon Ball FighterZ Vol.3 - Werezaru Goku/WerezaruGoku/WerezaruGoku.pak'))
installed=pathlib.Path(os.environ.get('DBFZ_EXG_DIR', os.environ.get('DBFZ_GAME', 'D:/Games/Dragon Ball FighterZ') + '/RED/Content/Paks/~mods'))  # folder with DBFZX_EXG.pak
out={};report={'hash_mismatch':[],'skipped':[],'files':[]}
baseconv=make_conv('DGF','EXG')
def conv(s):
    s=baseconv(s)
    s=re.sub(r'(?i)(_)(DGF)$',r'\1EXG',s) if '/UI/' in s or (not s.startswith('/') and s.startswith(('cp_chara_','vs_chara_','CS_CharacterImage_'))) else s
    s=s.replace('/UI/CharaSelect_S3/tex/CS_CIcon45','/UI/CharaSelect_S3/EXG/CS_CIcon45')
    return s
for n,get in entries_data(source):
    if n.startswith('RED/Content/Chara/DGF/'):
        if '/ParticleData.' in n or '/EffectData.' in n:
            report['skipped'].append(n);continue
        nn=rename_path(n,'DGF','EXG')
    elif n.startswith('RED/Content/UI/'):
        nn=re.sub(r'_DGF(?=\.)','_EXG',n)
        nn=nn.replace('/CharaSelect_S3/tex/CS_CIcon45','/CharaSelect_S3/EXG/CS_CIcon45')
        assert nn!=n,n
    else:
        report['skipped'].append(n);continue
    b=get()
    if n.endswith('.uasset'): b=convert_uasset(b,conv,report,n)
    elif n.endswith('.uexp'): b=convert_uexp(b,'DGF','EXG')
    assert '/Chara/DGF/' not in nn and '/Chara/GKD/' not in nn
    out[nn]=b
assert not report['hash_mismatch']
# Validate EXG package imports, respecting numbered FNames.
available={n.lower():get for n,get in entries_data(installed/'DBFZX_EXG.pak')}
available.update({n.lower():lambda b=b:b for n,b in out.items()})
missing=[]
for n,b in out.items():
    if not n.endswith('.uasset'):continue
    ns=[s for s,*_ in names(b)]
    p=32+struct.unpack_from('<i',b,28)[0]+4
    count,off=struct.unpack_from('<ii',b,p+24)
    for i in range(count):
        idx,num=struct.unpack_from('<ii',b,off+28*i+20)
        s=ns[idx]+('_'+str(num-1) if num else '')
        if s.lower().startswith('/game/chara/exg/'):
            key=('RED/Content/'+s[6:]+'.uasset').lower()
            if key not in available:missing.append([n,s])
    assert not any('/chara/dgf/' in s.lower() for s in ns),n
    if '/UI/' in n:
        ec,eo=struct.unpack_from('<ii',b,p+16)
        idx,num=struct.unpack_from('<ii',b,eo+16)
        assert ec==1 and num==0 and ns[idx]==pathlib.PurePosixPath(n).stem,(n,ns[idx])
report['missing_exg_imports']=missing
assert not missing,missing
assert not any('/Common/Data/' in n or '/ParticleData.' in n or '/EffectData.' in n for n in out)
dest=root/'paks/werezaru-exg';dest.mkdir(exist_ok=True)
pak=dest/'zzWerezaruEXG_P.pak'
write_pak(pak,sorted(out.items()))
assert {n:get() for n,get in entries_data(pak)}==out
shutil.copy2(pathlib.Path(os.environ.get('DBFZ_SIG', str(source.with_suffix('.sig')))),pak.with_suffix('.sig'))
report['files']=[{'path':n,'sha256':hashlib.sha256(b).hexdigest()} for n,b in out.items()]
(dest/'conversion-report.json').write_text(json.dumps(report,indent=2))
print('Validated:',len(out),'files;',len(report['skipped']),'excluded; missing EXG imports:',len(missing))
print(pak)
