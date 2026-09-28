"""Repair added object imports omitted from cooked dependency lists.

Scoped to single-export RED material/animation lists in SBG, GRN and GKG.
Preserves export payloads, names, existing dependency ordering and originals.
Header/dependency layout checked against UAssetAPI UAsset.cs and Export.cs.
"""
import os
import pathlib, struct, json, hashlib, shutil
from build_char import entries_data, names, write_pak
root=pathlib.Path(__file__).resolve().parent
CLASSES={'REDPawnMaterials','REDMeshMaterialSet','REDAnimSet'}

def repair(b, x):
    ns=[v[0] for v in names(b)]
    p=32+struct.unpack_from('<i',b,28)[0]+4
    namecount,nameoff=struct.unpack_from('<ii',b,p)
    ec,eo,ic,io=struct.unpack_from('<iiii',b,p+16)
    if ec != 1: return b, None
    cls=struct.unpack_from('<i',b,eo)[0]
    if cls>=0: return b,None
    def fn(off):
        idx,num=struct.unpack_from('<ii',b,off)
        return ns[idx]+('_'+str(num-1) if num else '')
    classname=fn(io+(-cls-1)*28+20)
    if classname not in CLASSES: return b,None
    # UE4.17 summary ends with BulkDataStart, WorldTile, empty chunk IDs, dependencies.
    assert struct.unpack_from('<ii',b,nameoff-16)==(0,0)
    count,offset=struct.unpack_from('<ii',b,nameoff-8)
    assert offset+count*4==len(b)
    assert struct.unpack_from('<i',b,24)[0]==len(b)
    first,sbs,cbs,sbc,cbc=struct.unpack_from('<5i',b,eo+84)
    assert first==0 and sbs+cbs+sbc+cbc==count
    deps=list(struct.unpack_from('<'+str(count)+'i',b,offset))
    imports=[]
    for i in range(ic):
        o=io+i*28
        outer=struct.unpack_from('<i',b,o+16)[0]
        imports.append((fn(o+20),outer))
    def full(i):
        name,outer=imports[-i-1]
        return full(outer)+'.'+name if outer<0 else name
    added=[-i-1 for i,(name,outer) in enumerate(imports)
           if outer<0 and full(-i-1).startswith('/Game/') and -i-1 not in deps]
    if not added: return b,None
    # Do not change payload or introduce bulk data handling into this narrow repair.
    size,pos=struct.unpack_from('<qq',b,eo+28)
    assert pos==len(b) and size==len(x)-4
    bulk=struct.unpack_from('<q',b,nameoff-24)[0]
    assert bulk==len(b)+len(x)-4, (bulk,len(b),len(x))
    nd=deps[:sbs+cbs]+added+deps[sbs+cbs:]
    new=bytearray(b[:offset]+struct.pack('<'+str(len(nd))+'i',*nd))
    delta=len(new)-len(b)
    struct.pack_into('<i',new,24,len(new))
    struct.pack_into('<i',new,nameoff-8,len(nd))
    struct.pack_into('<q',new,nameoff-24,bulk+delta)
    struct.pack_into('<q',new,eo+36,pos+delta)
    struct.pack_into('<i',new,eo+92,cbs+len(added))
    # Layout/integrity assertions: payload starts exactly at new header end.
    assert struct.unpack_from('<q',new,eo+36)[0]==len(new)
    assert list(names(new))==list(names(b))
    info=dict(classname=classname,added=[full(i) for i in added],old_size=len(b),new_size=len(new))
    return bytes(new),info

def main(codes=('SBG', 'GRN', 'GKG')):
    out=[]; report=[]
    for code in codes:
        src=root/f'paks/chars/DBFZX_{code}.pak'
        files={n.lower():(n,get) for n,get in entries_data(src)}
        for key,(n,get) in files.items():
            if not n.endswith('.uasset'): continue
            if code in ('SBG', 'GKG') and '/Material/Color' not in n: continue
            if code=='GRN' and not n.endswith('/Animation/Default/Body/AS_Body.uasset'): continue
            xe=files.get(key[:-7]+'.uexp')
            if not xe: continue
            b=get(); x=xe[1]()
            new,info=repair(b,x)
            if info:
                for dependency in info['added']:
                    package,obj=dependency.split('.',1)
                    target=files['red/content/'+package[6:].lower()+'.uasset'][1]()
                    targetnames=[v[0] for v in names(target)]
                    tp=32+struct.unpack_from('<i',target,28)[0]+4
                    tc,to=struct.unpack_from('<ii',target,tp+16)
                    exports=[]
                    for ti in range(tc):
                        idx,num=struct.unpack_from('<ii',target,to+104*ti+16)
                        exports.append(targetnames[idx]+('_'+str(num-1) if num else ''))
                    assert obj.lower() in [e.lower() for e in exports], dependency
                info.update(path=n,source_sha256=hashlib.sha256(b).hexdigest())
                report.append(info);out.extend([(n,new),(xe[0],x)])
                same,again=repair(new,x)
                assert same==new and again is None
    dst=root/'paks/fixes';dst.mkdir(exist_ok=True)
    (dst/'preload-repair-report.json').write_text(json.dumps(report,indent=2))
    write_pak(dst/'zzDBFZSlotsPreloadFix.pak',sorted(out))
    recovered={n:get() for n,get in entries_data(dst/'zzDBFZSlotsPreloadFix.pak')}
    assert recovered==dict(out)
    sig=pathlib.Path(os.environ.get('DBFZ_SIG', os.environ.get('DBFZ_GAME', 'D:/Games/Dragon Ball FighterZ') + '/RED/Content/Paks/~mods/DBFZX_SBG.sig'))
    shutil.copy2(sig,dst/'zzDBFZSlotsPreloadFix.sig')
    print('Repaired assets',len(report),'new dependencies',sum(len(i['added']) for i in report))
    for i in report:
        print(i['path'],len(i['added']))

if __name__=='__main__':main()
