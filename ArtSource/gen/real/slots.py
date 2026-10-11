"""Windows become plain slots: drop the glazing and the iron bars (submeshes Iron, Glass, Glass2) from the window
pieces, keeping every other submesh and the vertex data byte-for-byte. Works on PMS1 and PMS2.

    python3 gen/real/slots.py IN.bytes OUT.bytes
"""
import struct, sys
DROP = ('Iron', 'Glass', 'Glass2')

def strip(src, dst):
    with open(src, 'rb') as f:
        mg = f.read(4); nv, ns, fl = struct.unpack('<iii', f.read(12))
        per = 12 + 12 + 4 + (8 if mg == b'PMS2' else 0)
        body = f.read(nv * per)
        subs = []
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln); ni = struct.unpack('<i', f.read(4))[0]; idx = f.read(ni * 4)
            subs.append((nm, ni, idx))
    keep = [s for s in subs if s[0].decode().split('_')[-1] not in DROP and s[0].decode() not in DROP]
    with open(dst, 'wb') as f:
        f.write(mg); f.write(struct.pack('<iii', nv, len(keep), fl)); f.write(body)
        for nm, ni, idx in keep:
            f.write(struct.pack('<i', len(nm))); f.write(nm); f.write(struct.pack('<i', ni)); f.write(idx)
    print(f'{src.split("/")[-1]}: kept {[s[0].decode() for s in keep]}, dropped {[s[0].decode() for s in subs if s not in keep]}')

if __name__ == '__main__':
    strip(sys.argv[1], sys.argv[2])
