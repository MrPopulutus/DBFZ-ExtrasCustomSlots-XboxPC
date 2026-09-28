import struct, pathlib, hashlib, zlib, json, sys

def read_pak(path, output=None):
    f=open(path,'rb'); f.seek(-44,2)
    magic,ver,offset,size,digest=struct.unpack('<IIQQ20s',f.read(44))
    assert magic==0x5a6f12e1,(path,hex(magic))
    assert ver in (3,4),ver
    f.seek(offset); index=f.read(size)
    assert hashlib.sha1(index).digest()==digest
    import io
    r=io.BytesIO(index)
    def string():
        n=struct.unpack('<i',r.read(4))[0]
        return r.read(n).rstrip(b'\0').decode() if n>=0 else r.read(-n*2).decode('utf-16-le').rstrip('\0')
    mount=string(); count=struct.unpack('<i',r.read(4))[0]; entries=[]
    for _ in range(count):
        name=string(); start=r.tell()
        pos,packed,raw,method=struct.unpack('<QQQI',r.read(28)); sha=r.read(20)
        blocks=[]
        if method:
            nb=struct.unpack('<I',r.read(4))[0]
            blocks=[struct.unpack('<QQ',r.read(16)) for _ in range(nb)]
        encrypted,blocksize=struct.unpack('<BI',r.read(5)); header=r.tell()-start
        e=dict(name=name,offset=pos,packed=packed,raw=raw,method=method,encrypted=encrypted,blocks=blocks,header=header)
        entries.append(e)
        if output:
            assert not encrypted
            if method:
                assert method==1
                chunks=[]
                for a,b in blocks:
                    f.seek(a); chunks.append(zlib.decompress(f.read(b-a)))
                data=b''.join(chunks)
            else:
                f.seek(pos+header); data=f.read(raw)
            assert len(data)==raw
            dest=pathlib.Path(output)/name
            assert dest.resolve().is_relative_to(pathlib.Path(output).resolve())
            dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    f.close()
    return dict(path=str(path),version=ver,mount=mount,entries=entries)

if __name__=='__main__':
    print(json.dumps(read_pak(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None),indent=2))
