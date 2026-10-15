import zipfile,sys
a=zipfile.ZipFile(sys.argv[1]); b=zipfile.ZipFile(sys.argv[2])
A={i.filename:i for i in a.infolist()}; B={i.filename:i for i in b.infolist()}
for n in sorted(set(A)|set(B)):
    if n not in A: print("ADDED  ",n,B[n].file_size)
    elif n not in B: print("REMOVED",n,A[n].file_size)
    elif A[n].CRC!=B[n].CRC: print("CHANGED",n,A[n].file_size,"->",B[n].file_size)
