"""Small mesh-building kit for the hand-made props: grids, fans and triangle lists with UVs and materials, built
into a Blender object and exported to the House's PMS2 format (with an optional LOD1), plus texture helpers."""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import assets as AS            # noqa: E402  (bpy, export_pms2, paths)
import bpy                     # noqa: E402

OUTI = AS.OUTI

def nrm(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)

def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

class Mesh:
    def __init__(self):
        self.V = []; self.UV = []; self.F = []; self.M = []; self.mats = []; self.n = 0
    def mat(self, name):
        if name not in self.mats: self.mats.append(name)
        return self.mats.index(name)
    def grid(self, P, UV, m, flip=False, wrap=False):
        """P: (nu, nv, 3), UV: (nu, nv, 2) -> quads between neighbours (wrap closes the u direction)."""
        P = np.asarray(P, float); UV = np.asarray(UV, float)
        nu, nv = P.shape[:2]
        base = self.n
        self.V.append(P.reshape(-1, 3)); self.UV.append(UV.reshape(-1, 2)); self.n += nu * nv
        mi = self.mat(m)
        idx = lambda i, j: base + (i % nu) * nv + j
        for i in range(nu if wrap else nu - 1):
            for j in range(nv - 1):
                q = (idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1))
                self.F.append(q[::-1] if flip else q); self.M.append(mi)
    def tris(self, P, UV, F, m, flip=False):
        base = self.n
        self.V.append(np.asarray(P, float)); self.UV.append(np.asarray(UV, float)); self.n += len(P)
        mi = self.mat(m)
        for f in F:
            f = tuple(base + int(i) for i in f)
            self.F.append(f[::-1] if flip else f); self.M.append(mi)
    def merge(self, other, xf=None):
        base = self.n
        P = np.concatenate(other.V); UV = np.concatenate(other.UV)
        if xf is not None: P = xf(P)
        self.V.append(P); self.UV.append(UV); self.n += len(P)
        remap = [self.mat(m) for m in other.mats]
        for f, mi in zip(other.F, other.M):
            self.F.append(tuple(base + i for i in f)); self.M.append(remap[mi])
    def ntris(self):
        return sum(len(f) - 2 for f in self.F)
    def build(self, name, fresh=True):
        if fresh: bpy.ops.wm.read_factory_settings(use_empty=True)
        V = np.concatenate(self.V); UV = np.concatenate(self.UV)
        me = bpy.data.meshes.new(name)
        me.from_pydata(V.tolist(), [], [list(f) for f in self.F])
        uvl = me.uv_layers.new(name='UVMap')
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
        uvl.data.foreach_set('uv', UV[lv].astype(np.float32).ravel())
        for m in self.mats: me.materials.append(bpy.data.materials.new(m))
        me.polygons.foreach_set('material_index', np.array(self.M, np.int32))
        me.shade_smooth()
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        return ob

def xform(P, R=None, t=(0, 0, 0), s=1.0):
    P = np.asarray(P, float) * s
    if R is not None: P = P @ np.asarray(R).T
    return P + np.asarray(t, float)

def rotz(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])

def export(M, name, mats, man, lod1=None):
    """export mesh M as <name> (and lod1 as <name>_LOD1 with the same submesh names); mats: {mat: manifest dict}."""
    ob = M.build(name)
    AS.export_pms2(ob, name, [f'{name}_{m}' for m in M.mats])
    man[name] = [dict(sub=f'{name}_{m}', **mats[m]) for m in M.mats]
    print(f'  {name}: {M.ntris()} tris, mats {M.mats}', flush=True)
    if lod1 is not None:
        ob = lod1.build(name + '_LOD1')
        AS.export_pms2(ob, name + '_LOD1', [f'{name}_{m}' for m in lod1.mats])
        man[name + '_LOD1'] = [dict(sub=f'{name}_{m}', **mats[m]) for m in lod1.mats]
        print(f'  {name}_LOD1: {lod1.ntris()} tris', flush=True)
    elif name + '_LOD1' in man:
        del man[name + '_LOD1']
        p = os.path.join(AS.OUTM, name + '_LOD1.bytes')
        if os.path.exists(p): os.remove(p)

def load_manifest():
    return json.load(open(AS.MANIFEST)) if os.path.exists(AS.MANIFEST) else {}

def save_manifest(man):
    json.dump(man, open(AS.MANIFEST, 'w'), indent=1)

# ------------------------------------------------------------------------------------------- texture helpers
def save_rgb(a, path, alpha=None):
    a = np.clip(np.asarray(a, float), 0, 1)
    if alpha is not None:
        a = np.concatenate([a, np.clip(alpha, 0, 1)[..., None]], -1); mode = 'RGBA'
    else: mode = 'RGB'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8), mode).save(path)

def normal_from_height(h, strength):
    """GL tangent-space normal map from a height field (rows = v downward in the image, so flip y)."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny = -dx * strength, dy * strength
    nz = np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5

def mask(smooth, ao=None, metal=None):
    s = np.asarray(smooth, float)
    ao = np.ones_like(s) if ao is None else ao
    metal = np.zeros_like(s) if metal is None else metal
    return np.stack([s, ao, metal], -1)

def fbm(shape, scales, seed, weights=None):
    """sum of blurred white noise at several scales (pixels), normalised to ~[-1, 1]; tileable."""
    from scipy.ndimage import gaussian_filter
    r = np.random.default_rng(seed)
    out = np.zeros(shape)
    weights = weights or [1.0] * len(scales)
    for sc, w in zip(scales, weights):
        n = gaussian_filter(r.standard_normal(shape), sc, mode='wrap')
        out += w * n / (n.std() + 1e-9)
    return out / sum(weights)
