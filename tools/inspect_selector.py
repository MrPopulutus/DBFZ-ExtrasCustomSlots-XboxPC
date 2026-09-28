"""Read cooked selector widgets without modifying game assets."""
from pathlib import Path
import struct,json,sys
from build_char import names
ROOT=Path(__file__).resolve().parent

class Asset:
    def __init__(self,p):
        self.path=p;self.b=p.read_bytes();self.x=p.with_suffix('.uexp').read_bytes()
        b=self.b;self.names=[a[0] for a in names(b)]
        p=36+struct.unpack_from('<i',b,28)[0]
        ec,eo,ic,io=struct.unpack_from('<4i',b,p+16)
        self.imports=[];self.exports=[]
        for i in range(ic):
            off=io+28*i
            self.imports.append(dict(name=self.fn(b,off+20),outer=struct.unpack_from('<i',b,off+16)[0]))
        for i in range(ec):
            off=eo+104*i;cl,su,te,outer=struct.unpack_from('<4i',b,off)
            size,pos=struct.unpack_from('<qq',b,off+28)
            self.exports.append(dict(index=i+1,name=self.fn(b,off+16),cl=cl,outer=outer,size=size,pos=pos-len(b)))
        for e in self.exports:
            e['class']=self.ref(e['cl']);e['outername']=self.ref(e['outer'])
    def fn(self,b,o):
        i,n=struct.unpack_from('<ii',b,o);assert 0<=i<len(self.names),(i,o)
        return self.names[i]+('_'+str(n-1) if n else '')
    def ref(self,i):
        return self.imports[-i-1]['name'] if i<0 else self.exports[i-1]['name'] if i else 'null'
    def props(self,b,start=0):
        o=start;result=[]
        while o<len(b):
            begin=o;name=self.fn(b,o);o+=8
            if name=='None':return result,o
            ty=self.fn(b,o);o+=8;sz,idx=struct.unpack_from('<ii',b,o);o+=8;extra=None
            if ty=='StructProperty':extra=self.fn(b,o);o+=24
            elif ty=='BoolProperty':extra=b[o];o+=1
            elif ty in ('ByteProperty','EnumProperty','ArrayProperty','SetProperty'):extra=self.fn(b,o);o+=8
            elif ty=='MapProperty':extra=[self.fn(b,o),self.fn(b,o+8)];o+=16
            guid=b[o];o+=1
            if guid:o+=16
            assert sz>=0 and o+sz<=len(b),(name,ty,sz,o,len(b))
            value=b[o:o+sz];decoded=value.hex()
            if ty=='ObjectProperty' and sz==4:decoded=self.ref(struct.unpack('<i',value)[0])
            elif ty=='IntProperty' and sz==4:decoded=struct.unpack('<i',value)[0]
            elif ty=='FloatProperty' and sz==4:decoded=struct.unpack('<f',value)[0]
            elif ty=='NameProperty' and sz==8:decoded=self.fn(value,0)
            elif ty=='StructProperty':
                if extra in ('Vector2D','Margin','LinearColor'):decoded=list(struct.unpack('<'+'f'*(sz//4),value))
                else:
                    try:decoded=self.props(value)[0]
                    except (AssertionError,IndexError,struct.error):pass
            result.append(dict(name=name,type=ty,extra=extra,value=decoded,offset=o,size=sz,tag=begin))
            o+=sz
        return result,o
    def dump(self):
        for e in self.exports:
            try:e['props'],e['props_end']=self.props(self.x[e['pos']:e['pos']+e['size']])
            except Exception as ex:e['error']=str(ex)
        return dict(path=str(self.path),names=self.names,imports=self.imports,exports=self.exports)

if __name__=='__main__':
    out=ROOT/'selector-analysis';out.mkdir(exist_ok=True)
    folder=ROOT.parent/'base-assets/RED/Content/UI/CharaSelect_S3'
    for name in ['BP_CharaSelect_Main','BP_All_Frame','CS_ChoiceBG_Main','CS_ChoiceBG_1P','CS_ChoiceBG_2P','3D_CS_ChoiceBG_Main']:
        a=Asset(folder/(name+'.uasset'));d=a.dump()
        (out/(name+'.json')).write_text(json.dumps(d,indent=2),encoding='utf8')
        print(name,'exports',len(a.exports),'errors',sum('error' in x for x in a.exports))
        print('names:',', '.join(n for n in a.names if any(s in n.lower() for s in ['help','guide','characterimage','charaid','charaimage','portrait','banner','gks','image_','choicebg'])))
