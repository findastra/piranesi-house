"""Export a sculpted statue to the House's mesh format (PMS1, Unity space), with LODs and baked ambient occlusion.

Blender (z up, figure facing -y, right-handed) -> Unity (y up, facing +z, left-handed): a proper rotation to y-up
facing +z, then the usual mirror of x with flipped winding. U = (-x, z, -y)."""
import os, sys, struct
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MESH = os.path.join(HERE, '..', '..', 'out', 'Meshes')
sys.path.insert(0, os.path.join(HERE, '..'))

def to_unity(P): return np.stack([-P[:, 0], P[:, 2], -P[:, 1]], 1)

def vnormals(V, F):
    n = np.zeros_like(V)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    for k in range(3): np.add.at(n, F[:, k], fn)
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)

def write_pms1(name, P, N, C, subs):
    with open(os.path.join(MESH, name + '.bytes'), 'wb') as f:
        f.write(b'PMS1'); f.write(struct.pack('<iii', len(P), len(subs), 0))
        f.write(np.asarray(P, '<f4').tobytes()); f.write(np.asarray(N, '<f4').tobytes()); f.write(np.asarray(C, np.uint8).tobytes())
        for nm, idx in subs:
            b = nm.encode(); f.write(struct.pack('<i', len(b))); f.write(b)
            idx = np.asarray(idx, '<i4').ravel(); f.write(struct.pack('<i', len(idx))); f.write(idx.tobytes())

def decimate(V, F, target):
    if len(F) <= target: return V, F
    import fast_simplification
    V2, F2 = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - target / len(F))
    return np.asarray(V2, float), np.asarray(F2)

def export_statue(name, V, F, origin, scale, lods=(('', 200000), ('_LOD1', 40000)), sub='Statue', ao=True, ao_floor=0.3):
    """V, F: Blender-space mesh (human scale). origin: Blender point that becomes the statue's base centre.
    scale: multiplier to final size. Writes <name>.bytes and LODs. Returns the transform (Blender point -> Unity)."""
    xf = lambda P: to_unity((np.asarray(P, float) - origin) * scale)
    AO0 = None; V0u = None
    for suffix, target in lods:
        Vd, Fd = decimate(V, F, target)
        Nb = vnormals(Vd, Fd)
        Vu = xf(Vd); Nu = to_unity(Nb); Fu = Fd[:, [0, 2, 1]]
        C = np.full((len(Vu), 4), 255, np.uint8)
        if ao:
            if AO0 is None:
                import statues as ST
                a = ST.ao_bake(Vu, Fu)
                AO0 = ao_floor + (1 - ao_floor) * np.clip(a, 0, 1); V0u = Vu
                a_ = AO0
            else:
                from scipy.spatial import cKDTree
                _, idx = cKDTree(V0u).query(Vu); a_ = AO0[idx]
            C[:, 0] = C[:, 1] = C[:, 2] = (np.clip(a_, 0, 1) * 255).astype(np.uint8)
        write_pms1(name + suffix, Vu, Nu, C, [(sub, Fu)])
        print(f'  {name + suffix}: {len(Vu)} verts, {len(Fu)} tris, size {np.ptp(Vu, axis=0).round(2)}')
    return xf
