"""Statue processing: orient scans to Unity space (Y up, facing +Z), scale to real size, decimate to
LOD0/LOD1, bake ambient occlusion into vertex colours with Cycles, export .bytes (Unity space)."""
import os, sys, numpy as np, trimesh, fast_simplification, struct, bpy, math

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
OUT = os.path.join(HERE, '..', 'out', 'Meshes')
os.makedirs(OUT, exist_ok=True)

# mapping from scan coords to Unity coords (proper rotations only)
ZUP_FRONT_POSY = lambda v: np.stack([-v[:, 0], v[:, 2], v[:, 1]], 1)
ZUP_FRONT_NEGY = lambda v: np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)
YUP = lambda v: v
YUP_FRONT_POSX = lambda v: np.stack([-v[:, 2], v[:, 1], v[:, 0]], 1)   # turn +x to face +z

# name, source, mapping, height (m), registry role (book statue it stands in for)
STATUES = [
    ('Statue_WingedFigure', 'lucy', ZUP_FRONT_POSY, 2.3),
    ('Statue_SeatedSage', 'happy', YUP, 1.7),
    ('Statue_Head', 'igea', YUP, 0.75),
    ('Statue_Horse', 'horse', lambda v: ZUP_FRONT_POSY(v), 2.1),
    ('Statue_Dragon', 'xyzrgb_dragon', YUP, 1.5),
    ('Statue_Queen', 'nefertiti', ZUP_FRONT_NEGY, 0.85),
    ('Statue_Child', 'bimba', YUP, 0.7),
    ('Statue_Hare', 'stanford-bunny', YUP, 0.9),
    ('Statue_Beast', 'armadillo', YUP, 2.0),
]
LODS = [('', 16000), ('_LOD1', 3000)]

def ao_bake(V, F):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
    # Unity (x,y,z) -> Blender (x,z,y) with winding flip for the bake
    Vb = V[:, [0, 2, 1]]; Fb = F[:, [0, 2, 1]]
    me = bpy.data.meshes.new('s'); me.from_pydata(Vb.tolist(), [], Fb.tolist()); me.shade_smooth()
    ob = bpy.data.objects.new('s', me); sc.collection.objects.link(ob)
    # ground plane so the base darkens like it sits on a plinth
    gp = bpy.data.meshes.new('g'); s = 5
    zmin = Vb[:, 2].min()
    gp.from_pydata([(-s, -s, zmin), (s, -s, zmin), (s, s, zmin), (-s, s, zmin)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new('g', gp); sc.collection.objects.link(g)
    m = bpy.data.materials.new('m'); m.use_nodes = True; me.materials.append(m)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    me.color_attributes.active_color = ca
    sc.render.bake.target = 'VERTEX_COLORS'
    sc.world = bpy.data.worlds.new('w')
    for o in sc.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='AO')
    buf = np.empty(len(me.vertices) * 4, np.float32); ca.data.foreach_get('color', buf)
    return buf.reshape(-1, 4)[:, 0]

def write_bytes(name, V, F, N, AO):
    C8 = np.zeros((len(V), 4), np.uint8)
    a = np.clip(AO, 0, 1)
    C8[:, 0] = C8[:, 1] = C8[:, 2] = (a * 255).astype(np.uint8); C8[:, 3] = 255
    idx = F.astype('<i4').ravel()
    with open(os.path.join(OUT, name + '.bytes'), 'wb') as f:
        f.write(b'PMS1'); f.write(struct.pack('<iii', len(V), 1, 0))
        f.write(V.astype('<f4').tobytes()); f.write(N.astype('<f4').tobytes()); f.write(C8.tobytes())
        b = b'Statue'; f.write(struct.pack('<i', len(b))); f.write(b)
        f.write(struct.pack('<i', len(idx))); f.write(idx.tobytes())

if __name__ == '__main__':
    only = sys.argv[1:]
    for name, src, mp, height in STATUES:
        if only and name not in only: continue
        t = trimesh.load(os.path.join(SRC, src + '.obj'), process=False)
        V = mp(np.asarray(t.vertices, float)); F = np.asarray(t.faces)
        V[:, 0] *= -1  # RH -> LH (Unity): mirror X, winding flipped below
        # mapping may be a reflection for safety-check: ensure outward normals keep orientation
        V -= [ (V[:, 0].max() + V[:, 0].min()) / 2, V[:, 1].min(), (V[:, 2].max() + V[:, 2].min()) / 2 ]
        V *= height / (V[:, 1].max())
        # Unity is left-handed: flip winding once for the handedness change
        F = F[:, [0, 2, 1]]
        for suffix, target in LODS:
            ratio = 1 - min(1.0, target / len(F))
            if ratio > 0:
                Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=ratio)
            else:
                Vs, Fs = V.astype(np.float32), F.astype(np.int32)
            m = trimesh.Trimesh(Vs, Fs, process=True)
            trimesh.repair.fix_normals(m) if suffix == '_LOD1' and False else None
            Vs, Fs = np.asarray(m.vertices), np.asarray(m.faces)
            # left-handed: trimesh normals computed right-handed -> negate for display in Unity
            N = -np.asarray(m.vertex_normals)
            if suffix == '':
                ao = ao_bake(Vs, Fs)
                ao = 0.25 + 0.75 * ao
                np.save(os.path.join(OUT, name + '_ao.npy'), np.c_[Vs, ao])
            else:
                ref = np.load(os.path.join(OUT, name + '_ao.npy'))
                from scipy.spatial import cKDTree
                ao = ref[cKDTree(ref[:, :3]).query(Vs)[1], 3]
            write_bytes(name + suffix, Vs, Fs, N, ao)
            print(name + suffix, len(Vs), len(Fs), 'ao range', float(ao.min()), float(ao.max()), flush=True)
    print('statues done')
