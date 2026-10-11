"""vine-bloomer, part 2: ivy mantles. For each building piece, an offset shell over its real exterior roof and wall
faces that carries the Blender-rendered ivy texture (ivymat.py), with a coverage value per vertex (colour A) that the
IvyMat shader uses to thin the ivy leaf by leaf toward its edges. Two shells (4.5 cm and 10 cm out) give depth.

Every roof gets ~85% cover, outer walls ~70%, thicker from the waterline and cascading from the cornice; openings,
roof water channels and the undersides of things stay clear. Output: IvyMantle_<Piece>_<v>.bytes (+ _LOD1), Unity space.

    python3 gen/real/mantle.py [piece ...]
"""
import os, sys, math, json, zlib
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import ivy as IV

T = 1.5                     # texture tile (m)
MIN_AREA = 0.06             # skip small ornament faces (leaf curtains dress those)
UP = np.array([0, 1.0, 0])
EXCLUDE = ('Glass', 'Glass2', 'Water', 'Flow', 'Flame', 'Neon', 'Iron')
MAT = dict(shader='ivymat', albedo='IvyMat/IvyMat_Albedo.png', normal='IvyMat/IvyMat_Normal.png', mask='IvyMat/IvyMat_Mask.png',
           alpha='MASK', cutoff=0.5, translucency=0.7, smooth=0.75, doubleSided=False)

def nrm(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)

def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

class Noise:
    """smooth 3D noise from random sinusoids (~[-1, 1])."""
    def __init__(self, seed, scales=(6.0, 2.2, 0.9), weights=(1.0, 0.55, 0.3), k=10):
        r = np.random.default_rng(seed); self.terms = []
        for s, w in zip(scales, weights):
            D = nrm(r.normal(size=(k, 3))); ph = r.uniform(0, 2 * math.pi, k)
            self.terms.append((D * (2 * math.pi / s), ph, w))
        self.norm = sum(w for _, _, w in self.terms) * math.sqrt(k / 2)
    def __call__(self, P):
        out = np.zeros(len(P))
        for D, ph, w in self.terms:
            out += w * np.sin(P @ D.T + ph).sum(1)
        return out / self.norm * 1.6

def tri_faces(P, N, subs, keep):
    A = []; B = []; C = []; NA = []; NB = []; NC = []
    for nm, tri in subs.items():
        if any(nm == e or nm.endswith('_' + e) for e in EXCLUDE): continue
        a, b, c = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
        fn = np.cross(b - a, c - a); ar = np.linalg.norm(fn, axis=1) / 2; fn = fn / (2 * ar[:, None] + 1e-12)
        vn = N[tri[:, 0]] + N[tri[:, 1]] + N[tri[:, 2]]
        s = np.sign((fn * vn).sum(1)); s[s == 0] = 1; fn *= s[:, None]
        cen = (a + b + c) / 3
        m = (ar > MIN_AREA) & keep(cen, fn)
        flip = s < 0                                   # wind every kept face so its normal faces out
        b2 = np.where(flip[:, None], c, b); c2 = np.where(flip[:, None], b, c)
        nb2 = np.where(flip[:, None], N[tri[:, 2]], N[tri[:, 1]]); nc2 = np.where(flip[:, None], N[tri[:, 1]], N[tri[:, 2]])
        A.append(a[m]); B.append(b2[m]); C.append(c2[m])
        NA.append(N[tri[m, 0]]); NB.append(nb2[m]); NC.append(nc2[m])
    cat = lambda L: np.concatenate(L) if L else np.zeros((0, 3))
    return cat(A), cat(B), cat(C), nrm(cat(NA)), nrm(cat(NB)), nrm(cat(NC))

def subdivide(a, b, c, na, nb, nc, edge):
    """split each triangle by longest-edge bisection until every edge is shorter than `edge` (slivers along cornices
    stay cheap). Returns per-vertex positions, interpolated normals, faces and face normals."""
    Vs = []; Ns = []; Fs = []; FN = []; base = 0
    for i in range(len(a)):
        fn = nrm(np.cross(b[i] - a[i], c[i] - a[i]))
        stack = [((a[i], na[i]), (b[i], nb[i]), (c[i], nc[i]))]; out = []
        while stack:
            t = stack.pop()
            L = [np.linalg.norm(t[1][0] - t[0][0]), np.linalg.norm(t[2][0] - t[1][0]), np.linalg.norm(t[0][0] - t[2][0])]
            k = int(np.argmax(L))
            if L[k] <= edge or len(out) > 4000: out.append(t); continue
            p, q, r = t[k], t[(k + 1) % 3], t[(k + 2) % 3]
            m = ((p[0] + q[0]) / 2, nrm(p[1] + q[1]))
            stack.append((p, m, r)); stack.append((m, q, r))
        V = np.array([v[0] for t in out for v in t]); NN = np.array([v[1] for t in out for v in t])
        F = np.arange(len(V)).reshape(-1, 3)
        Vs.append(V); Ns.append(NN); Fs.append(F + base); FN.append(np.tile(fn, (len(F), 1))); base += len(V)
    return np.concatenate(Vs), nrm(np.concatenate(Ns)), np.concatenate(Fs), np.concatenate(FN)

def simplify(a, b, c, budget):
    """weld the kept faces into one surface and decimate it to `budget` triangles (fine ornament is left to the leaf
    curtains); smooth area-weighted normals let the mantle wrap round corners instead of cracking."""
    import fast_simplification
    P = np.concatenate([a, b, c]); n = len(a)
    key = np.round(P * 200).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
    V = np.zeros((len(uniq), 3)); np.add.at(V, inv, P); V /= np.bincount(inv, minlength=len(uniq))[:, None]
    F = np.stack([inv[:n], inv[n:2 * n], inv[2 * n:]], 1)
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    if len(F) > budget:
        V, F = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - budget / len(F))
        V = np.asarray(V, float); F = np.asarray(F)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    VN = np.zeros_like(V)
    for k in range(3): np.add.at(VN, F[:, k], fn)
    VN = nrm(VN)
    # keep each face's normal on the outer side of the original surface
    return V[F[:, 0]], V[F[:, 1]], V[F[:, 2]], VN[F[:, 0]], VN[F[:, 1]], VN[F[:, 2]]

def uvs(V, Nf_v, axis_mode, rot):
    """per-vertex UVs from the vertex's face orientation: roofs planar XZ, cardinal walls planar along the wall,
    curved walls cylindrical round the piece's vertical axis."""
    c, s = math.cos(rot), math.sin(rot)
    U = np.zeros((len(V), 2))
    horiz = np.abs(Nf_v[:, 1]) > 0.6
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    U[horiz, 0] = (x[horiz] * c - z[horiz] * s) / T; U[horiz, 1] = (x[horiz] * s + z[horiz] * c) / T
    wall = ~horiz
    nx, nz = Nf_v[:, 0], Nf_v[:, 2]
    card = wall & ((np.abs(nx) > 0.966) | (np.abs(nz) > 0.966) | (not axis_mode))
    along_x = np.abs(nz) >= np.abs(nx)
    U[card & along_x, 0] = x[card & along_x] * np.sign(nz[card & along_x] + 1e-9) / T
    U[card & ~along_x, 0] = -z[card & ~along_x] * np.sign(nx[card & ~along_x] + 1e-9) / T
    U[card, 1] = y[card] / T
    cyl = wall & ~card
    r = np.hypot(x[cyl], z[cyl]); th = np.arctan2(z[cyl], x[cyl])
    U[cyl, 0] = th * 8.0 / T; U[cyl, 1] = (y[cyl] + (12.0 - r)) / T
    return U

def cylinder(r, y0, y1, seg=48):
    """outward-facing cylinder faces (a synthetic surface over a richly ornamented drum)."""
    A = []; B = []; C = []
    for k in range(seg):
        t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        p00 = np.array([r * math.cos(t0), y0, r * math.sin(t0)]); p01 = np.array([r * math.cos(t1), y0, r * math.sin(t1)])
        p10 = p00 + [0, y1 - y0, 0]; p11 = p01 + [0, y1 - y0, 0]
        for (x, y, z) in ((p00, p10, p11), (p00, p11, p01)):
            fn = np.cross(y - x, z - x); out = np.array([x[0], 0, x[2]])
            if fn @ out < 0: y, z = z, y
            A.append(x); B.append(y); C.append(z)
    A, B, C = map(np.array, (A, B, C))
    n = lambda Q: nrm(Q * np.array([1, 0, 1]))
    return A, B, C, n(A), n(B), n(C)

def build(piece, keep, cover, seed, edge=2.4, offsets=(0.045, 0.10), axis_mode=False, water=None, budget=1800, extra=None):
    P, N, subs = IV.read_pms(piece)
    a, b, c, na, nb, nc = tri_faces(P, N, subs, keep)
    ex = extra() if extra is not None else None
    if not len(a): return None
    # decimate only the small ornament faces; big faces (and synthetic surfaces) go through untouched
    ar = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2; big = ar >= 0.5
    sm = simplify(a[~big], b[~big], c[~big], max(200, budget - int(big.sum()))) if (~big).any() else [np.zeros((0, 3))] * 6
    parts = [sm, (a[big], b[big], c[big], na[big], nb[big], nc[big])] + ([ex] if ex is not None else [])
    a, b, c, na, nb, nc = [np.concatenate([p_[i] for p_ in parts]) for i in range(6)]
    V, NV, F, FN = subdivide(a, b, c, na, nb, nc, edge)
    # per-vertex face normal (for UV choice and coverage rules)
    FNV = np.zeros_like(V); np.add.at(FNV, F[:, 0], FN); np.add.at(FNV, F[:, 1], FN); np.add.at(FNV, F[:, 2], FN); FNV = nrm(FNV)
    # how much surface surrounds each vertex (low next to openings and edges)
    # how much surface surrounds each vertex: sample the kept faces evenly (0.18 m) and count samples within 0.5 m;
    # a flat field gives ~pi r^2 / s^2, edges and openings much less
    sp = 0.18; r_ = np.random.default_rng(1)
    ar = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2
    cnt_ = np.maximum(1, np.round(ar / sp ** 2)).astype(int); ii = np.repeat(np.arange(len(a)), cnt_)
    u1 = np.sqrt(r_.random(len(ii))); u2 = r_.random(len(ii))
    S = a[ii] * (1 - u1)[:, None] + b[ii] * (u1 * (1 - u2))[:, None] + c[ii] * (u1 * u2)[:, None]
    cnt = cKDTree(S).query_ball_point(V, 0.5, return_length=True)
    dens = cnt / (math.pi * 0.25 / sp ** 2)
    rng = np.random.default_rng(seed); noise = Noise(seed)
    cov = cover(V, FNV, noise(V)) * smoothstep(0.35, 0.8, dens)
    if water is not None:
        cov *= ~water(V)
    cov = np.clip(cov, 0, 1)
    U = uvs(V, FNV, axis_mode, rng.uniform(0, 2 * math.pi))
    G = IV.Geo()
    for k, off in enumerate(offsets):
        cv = cov if k == 0 else np.clip((cov - 0.45) * 1.6, 0, 1) * smoothstep(-0.2, 0.4, noise(V * 1.7 + 11))
        keepF = (cv[F] > 0.08).any(1)
        if not keepF.any(): continue
        Fk = F[keepF]
        used = np.unique(Fk); remap = -np.ones(len(V), int); remap[used] = np.arange(len(used))
        Vk = V[used] + NV[used] * off
        Uk = U[used] + (np.array([0.37, 0.61]) if k else 0)
        C = np.zeros((len(used), 4), np.uint8)
        C[:, 0] = 200 if k == 0 else 255; C[:, 1] = C[:, 2] = 255; C[:, 3] = (cv[used] * 255).astype(np.uint8)
        G.add(Vk, NV[used], C, Uk, remap[Fk])
    return G

# ------------------------------------------------------------------------------------------- the pieces
def wall_cover(height, base=0.66):
    def f(V, Nf, n):
        y = V[:, 1]; up = Nf[:, 1] > 0.5
        c = base + 0.32 * n + 0.22 * smoothstep(4.0, 0.3, y) + 0.2 * smoothstep(height - 5, height, y) - 0.6 * smoothstep(0.35, 0.05, y)
        c = np.where(up, 0.88 + 0.25 * n, c)
        return c
    return f

def roof_cover(V, Nf, n):
    return 0.86 + 0.28 * n

PIECES = {}
def piece(name, mesh, keep, cover, variants=2, **kw):
    PIECES[name] = (mesh, keep, cover, variants, kw)

ext = lambda cen, fn: (fn[:, 2] > 0.3) | ((fn[:, 1] > 0.5) & (cen[:, 1] > 1.0))
for k in ('Window', 'Window_CutL', 'Window_CutR', 'Blind', 'Gallery', 'Gate', 'Tower', 'Cascade'):
    piece('Ext' + k, 'VestExt_' + k, ext, wall_cover(26.3), budget=1400, variants=1 if k in ('Gate', 'Tower', 'Cascade', 'Window_CutL', 'Window_CutR') else 2)
side_keep = lambda cen, fn: (fn[:, 2] > 0.3) & (cen[:, 2] > 11.5)
for k in ('Window', 'Window_CutL', 'Window_CutR', 'Blind', 'Open', 'Gate'):
    piece('Side' + k, 'Vest_Side' + k, side_keep, wall_cover(26.3), budget=900, variants=1 if k in ('Gate', 'Window_CutL', 'Window_CutR') else 2)
for g, X in (('Arcade', 7.0), ('Arcade_Win', 7.0), ('Nave', 10.32)):
    kg = (lambda X: lambda cen, fn: ((fn[:, 0] * np.sign(cen[:, 0]) > 0.3) & (np.abs(cen[:, 0]) > X - 0.5) & (cen[:, 1] > 0.2)) | ((fn[:, 1] > 0.5) & (cen[:, 1] > 13.0) & (np.abs(cen[:, 0]) > X - 1.0)))(X)
    piece('Gal' + g.replace('_', ''), g, kg, wall_cover(17.0), budget=1500, variants=2)
dome_keep = lambda cen, fn: (cen[:, 1] > 23.9) & ((fn[:, 1] > 0.45) | ((fn[:, [0, 2]] * cen[:, [0, 2]]).sum(1) > 0.2 * np.linalg.norm(cen[:, [0, 2]], axis=1)))
piece('Dome', 'Vest_Dome', dome_keep, lambda V, Nf, n: (0.84 + 0.3 * n) * (1 - 0.5 * smoothstep(33.5, 36.5, V[:, 1])), variants=3, axis_mode=True, budget=2600, extra=lambda: cylinder(10.95, 24.1, 29.8))
core_keep = lambda cen, fn: (cen[:, 1] > 23.5) & ((fn[:, 1] > 0.5) | (np.maximum(np.abs(cen[:, 0]), np.abs(cen[:, 2])) > 11.5))
piece('CoreTop', 'Vest_Core', core_keep, roof_cover, variants=1)
for g, X, ch in (('Arcade', 7.62, (3.62, 4.38)), ('Nave', 10.62, (7.92, 8.68))):
    keep_g = (lambda X: lambda cen, fn: ((fn[:, 0] * np.sign(cen[:, 0]) > 0.3) & (np.abs(cen[:, 0]) > X - 0.6)) | ((fn[:, 1] > 0.5) & (cen[:, 1] > 9.0)))(X)
    wat = (lambda ch: lambda V: (V[:, 0] > ch[0] - 0.35) & (V[:, 0] < ch[1] + 0.35) & (V[:, 1] > 12.0))(ch)
    piece(g, g + 'Ext', keep_g, wall_cover(17.0), variants=2, water=wat, budget=2600)
def hall_keep(X, Ln, H):
    return lambda cen, fn: (((fn[:, 0] * np.sign(cen[:, 0]) > 0.3) & (np.abs(cen[:, 0]) > X - 0.6)) |
                            ((fn[:, 2] < -0.3) & (cen[:, 2] < 0.6)) | ((fn[:, 2] > 0.3) & (cen[:, 2] > Ln - 0.6)) |
                            ((fn[:, 1] > 0.5) & (cen[:, 1] > H - 2.0)))
piece('SeaHall', 'SeaHall', hall_keep(11.55, 34.6, 34.5), wall_cover(34.5), variants=1, axis_mode=False)
piece('IsleHall', 'IsleHall', hall_keep(7.55, 22.6, 21.4), wall_cover(21.4), variants=1)

def main(only=None):
    man = json.load(open(IV.MANIFEST))
    total = {}
    for name, (mesh, keep, cover, variants, kw) in PIECES.items():
        if only and name not in only: continue
        for v in range(variants):
            out = f'IvyMantle_{name}_{v}'
            G = build(mesh, keep, cover, seed=zlib.crc32(f"{name}{v}".encode()) % 100000, **kw)
            if G is None: print('  nothing to mantle on', mesh); continue
            t0 = IV.write_pms2(out, [(f'IvyMantle_Mat', G)])
            kw1 = dict(kw, budget=max(300, kw.get('budget', 1800) // 4))
            G1 = build(mesh, keep, cover, seed=zlib.crc32(f"{name}{v}".encode()) % 100000, edge=6.0, offsets=(0.05,), **kw1)
            t1 = IV.write_pms2(out + '_LOD1', [(f'IvyMantle_Mat', G1)])
            man[out] = [dict(sub='IvyMantle_Mat', **MAT)]; man[out + '_LOD1'] = [dict(sub='IvyMantle_Mat', **MAT)]
            total[out] = (t0, t1)
    json.dump(man, open(IV.MANIFEST, 'w'), indent=1)
    print('mantles:', json.dumps(total))

if __name__ == '__main__':
    main(sys.argv[1:] or None)
