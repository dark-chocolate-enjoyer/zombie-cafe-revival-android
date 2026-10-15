import struct,sys
data=bytearray(open(sys.argv[1],'rb').read()); new=int(sys.argv[3])
pos=8; resmap=[]; hits=[]
while pos<len(data):
    t,h,sz=struct.unpack_from('<HHI',data,pos)
    if t==0x0180: resmap=list(struct.unpack_from('<%dI'%((sz-8)//4),data,pos+8))
    if t==0x0102:
        ac=struct.unpack_from('<H',data,pos+28)[0]; start=pos+36
        for k in range(ac):
            a=start+20*k; name=struct.unpack_from('<I',data,a+4)[0]
            if name<len(resmap) and resmap[name] in (0x01010270,0x0101020c):
                dt=data[a+15]; val=struct.unpack_from('<I',data,a+16)[0]
                print(hex(resmap[name]),'type',hex(dt),'val',val,'at',hex(a+16))
                if resmap[name]==0x01010270: hits.append(a)
    pos+=sz
assert len(hits)==1
a=hits[0]; assert data[a+15]==0x10
struct.pack_into('<I',data,a+16,new)
open(sys.argv[2],'wb').write(data); print('targetSdk ->',new)
