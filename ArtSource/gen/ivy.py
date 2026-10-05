"""Ivy: climbing and cascading English ivy grown on the House's own geometry.

Growth follows the adhesion/gravity model of Luft's IvyGenerator. Each strand steps forward and is pulled onto
the nearest surface (a KD-tree over area-sampled triangles of the real module meshes). Climbers drift upward and
cascades drift downward. Strands branch now and then, and fall under gravity when they lose contact. Hanging
curtains are free strands that sway down from rims and beams.

Leaves are real scanned English-ivy leaves (ambientCG LeafSet017 + LeafSet029, CC0) packed into one atlas with
their tips pointing up. Stems are tapered tubes. Output is PMS2 meshes in Unity space plus Materials.json entries.
Per-leaf vertex colours carry AO (R) and an age/variety tint (G, B, A) used by the Foliage shader."""
import os, sys, json, math, struct, numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
MESH = os.path.join(ROOT, 'out', 'Meshes'); IMP = os.path.join(ROOT, 'out', 'Imported'); DATA = os.path.join(ROOT, 'out', 'Data')
MANIFEST = os.path.join(DATA, 'Materials.json')
ACG = os.path.join(ROOT, 'assets', 'ambientcg')
UP = np.array([0, 1.0, 0]); DOWN = -UP

def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v

def rodrigues(v, k, a):
    k = norm(k)
    return v * math.cos(a) + np.cross(k, v) * math.sin(a) + k * (k @ v) * (1 - math.cos(a))

def euler(x=0, y=0, z=0):
    """Unity Quaternion.Euler(x, y, z) as a matrix (z, then x, then y)."""
    x, y, z = map(math.radians, (x, y, z))
    Rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz

def read_pms(name):
    with open(os.path.join(MESH, name + '.bytes'), 'rb') as f:
        mg = f.read(4); nv, ns, fl = struct.unpack('<iii', f.read(12))
        P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3).astype(np.float64)
        N = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3).astype(np.float64)
        f.read(nv * 4)
        if mg == b'PMS2': f.read(nv * 8)
        subs = {}
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln).decode()
            ni = struct.unpack('<i', f.read(4))[0]; subs[nm] = np.frombuffer(f.read(ni * 4), '<i4').reshape(-1, 3)
    return P, N, subs

# ------------------------------------------------------------------ leaf atlas
def build_atlas():
    d = os.path.join(IMP, 'Ivy'); os.makedirs(d, exist_ok=True)
    W = H = 1024
    def load(set_, rot):
        base = os.path.join(ACG, f'{set_}_2K-JPG', f'{set_}_2K-JPG')
        col = Image.open(base + '_Color.jpg').convert('RGB').resize((W, H), Image.LANCZOS)
        op = Image.open(base + '_Opacity.jpg').convert('L').resize((W, H), Image.LANCZOS)
        nm = Image.open(base + '_NormalGL.jpg').convert('RGB').resize((W, H), Image.LANCZOS)
        rough = Image.open(base + '_Roughness.jpg').convert('L').resize((W, H), Image.LANCZOS)
        if rot:
            col, op, nm, rough = [im.transpose(Image.ROTATE_90) for im in (col, op, nm, rough)]
            a = np.asarray(nm, np.uint8).copy()          # tangent-space normal rotates with the image: (x, y) -> (-y, x)
            r, g = a[..., 0].copy(), a[..., 1].copy()
            a[..., 0] = 255 - g; a[..., 1] = r; nm = Image.fromarray(a)
        return col, op, nm, rough
    parts = [load('LeafSet017', False), load('LeafSet029', True)]
    col = Image.new('RGB', (2 * W, H)); op = Image.new('L', (2 * W, H)); nm = Image.new('RGB', (2 * W, H)); ro = Image.new('L', (2 * W, H))
    for i, (c, o, n, r) in enumerate(parts):
        col.paste(c, (i * W, 0)); op.paste(o, (i * W, 0)); nm.paste(n, (i * W, 0)); ro.paste(r, (i * W, 0))
    c = np.asarray(col, np.float32); a = np.asarray(op, np.float32) / 255
    # deepen the pale scanned leaves toward a glossy dark ivy green (veins stay light)
    lum = c.mean(-1, keepdims=True)
    c = c * 0.62 + lum * np.array([0.10, 0.30, 0.06]) * 1.0
    # bleed leaf colour into the transparent background so mips have no white halos
    solid = a > 0.5
    idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
    c = c[idx[0], idx[1]]
    rgba = np.concatenate([np.clip(c, 0, 255), (a * 255)[..., None]], -1).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(os.path.join(d, 'Ivy_Albedo.png'))
    nm.save(os.path.join(d, 'Ivy_Normal.png'))
    r = np.asarray(ro, np.float32) / 255
    mask = np.stack([np.clip(1.05 - r, 0, 1), np.ones_like(r), np.zeros_like(r), np.ones_like(r)], -1)
    Image.fromarray((mask * 255).astype(np.uint8), 'RGBA').save(os.path.join(d, 'Ivy_Mask.png'))
    # leaf rectangles (connected components of the opacity), in UV space with v up
    small = np.asarray(op.resize((512, 256)), np.float32) / 255 > 0.4
    lab, n = ndimage.label(small)
    rects = []
    for sl in ndimage.find_objects(lab):
        y0, y1 = sl[0].start, sl[0].stop; x0, x1 = sl[1].start, sl[1].stop
        if (y1 - y0) > 30 and (x1 - x0) > 30:
            rects.append([(x0 - 1) / 512, 1 - (y1 + 1) / 256, (x1 + 1) / 512, 1 - (y0 - 1) / 256])
    print('ivy atlas leaves', len(rects))
    return rects

# ------------------------------------------------------------------ surfaces
class Surface:
    def __init__(self, spacing=0.05, seed=0):
        self.P = []; self.N = []; self.sp = spacing; self.r = np.random.default_rng(seed)

    def add_mesh(self, name, R=np.eye(3), t=(0, 0, 0), s=1.0, keep=None, exclude=('Glass', 'Glass2', 'Water', 'Flame', 'Flow')):
        P, N, subs = read_pms(name)
        Pw = (P * s) @ R.T + np.asarray(t, float)
        Nw = N @ R.T
        for nm, tri in subs.items():
            if any(nm == e or nm.endswith('_' + e) for e in exclude): continue
            a, b, c = Pw[tri[:, 0]], Pw[tri[:, 1]], Pw[tri[:, 2]]
            fn = np.cross(b - a, c - a); ar = np.linalg.norm(fn, axis=1) / 2
            fn = fn / (2 * ar[:, None] + 1e-12)
            vn = Nw[tri[:, 0]] + Nw[tri[:, 1]] + Nw[tri[:, 2]]
            sgn = np.sign((fn * vn).sum(1)); sgn[sgn == 0] = 1; fn = fn * sgn[:, None]
            cen = (a + b + c) / 3
            m = ar > 1e-7
            if keep is not None: m &= keep(cen, fn)
            self._sample(a[m], b[m], c[m], fn[m], ar[m])
        return self

    def add_plane(self, y, x0, x1, z0, z1):
        xs = np.arange(x0, x1, self.sp); zs = np.arange(z0, z1, self.sp)
        X, Z = np.meshgrid(xs, zs)
        pts = np.stack([X.ravel(), np.full(X.size, float(y)), Z.ravel()], 1)
        self.P.append(pts); self.N.append(np.tile(UP, (len(pts), 1)))
        return self

    def _sample(self, a, b, c, n, ar):
        if not len(a): return
        cnt = np.maximum(1, np.round(ar / self.sp ** 2)).astype(np.int64)
        idx = np.repeat(np.arange(len(a)), cnt)
        r1 = self.r.random(len(idx)); r2 = self.r.random(len(idx))
        s1 = np.sqrt(r1)
        pts = a[idx] * (1 - s1)[:, None] + b[idx] * (s1 * (1 - r2))[:, None] + c[idx] * (s1 * r2)[:, None]
        self.P.append(pts); self.N.append(n[idx])

    def build(self):
        self.P = np.concatenate(self.P); self.N = np.concatenate(self.N)
        self.tree = cKDTree(self.P)
        print('  surface samples', len(self.P), flush=True)
        return self

    def near(self, p):
        d, i = self.tree.query(p)
        return self.P[i], self.N[i], d

# ------------------------------------------------------------------ growth
def grow(S, seeds, rng, *, step=0.06, offset=0.035, adhere=0.45, w_prev=0.6, w_up=0.35, w_rand=0.45, w_adh=1.6,
         w_grav=1.4, max_float=0.6, branch_p=0.035, length=(5, 11), budget=300.0, max_strands=900, bounds=None):
    strands = []
    queue = [(np.asarray(p, float), norm(np.asarray(d, float)), rng.uniform(*length), 0) for p, d in seeds]
    total = 0.0
    while queue and total < budget and len(strands) < max_strands:
        p, d, L, gen = queue.pop(0)
        q, n, dist = S.near(p)
        pts = [p.copy()]; nrs = [n if dist < adhere else -d]; att = [dist < adhere]
        floating = 0.0; ln = 0.0
        while ln < L:
            q, n, dist = S.near(p)
            rnd = rng.normal(size=3)
            if dist < adhere:
                floating = 0.0
                t_up = UP - n * (UP @ n)
                t_rnd = rnd - n * (rnd @ n)
                dn = d * w_prev + t_up * w_up + norm(t_rnd) * w_rand + (q + n * offset - p) * w_adh
            else:
                floating += step
                if floating > max_float: break
                dn = d * 0.7 + DOWN * w_grav * min(1.0, floating / 0.3) + rnd * 0.15
            d = norm(dn)
            pn = p + d * step
            q2, n2, d2 = S.near(pn)
            sd = (pn - q2) @ n2
            if d2 < 0.5 and sd < offset * 0.6:
                pn = pn + n2 * (offset - sd)
            if bounds is not None and not bounds(pn): break
            ln += float(np.linalg.norm(pn - p)); p = pn
            pts.append(p.copy()); nrs.append(n2 if d2 < adhere else -d); att.append(d2 < adhere)
            if rng.random() < branch_p and len(strands) + len(queue) < max_strands:
                nn = n2 if d2 < adhere else UP
                bd = rodrigues(d, nn, rng.choice([-1, 1]) * rng.uniform(0.6, 1.5))
                queue.append((p.copy(), bd, max(0.4, (L - ln) * rng.uniform(0.35, 0.85)), gen + 1))
        if len(pts) > 4:
            strands.append(dict(p=np.array(pts), n=np.array(nrs), att=np.array(att), gen=gen))
            total += ln
    print(f'  grew {len(strands)} strands, {total:.0f} m', flush=True)
    return strands

def hang(anchors, rng, *, length=(2, 6), face=None, step=0.08, sway=0.25, branch=0.25):
    """Free-hanging strands. anchors: list of points; face: unit vector the leaves favour (or None = all round)."""
    strands = []
    for a in anchors:
        L = rng.uniform(*length)
        n = int(L / step)
        ph = rng.uniform(0, 6.3, 3); amp = rng.uniform(0.3, 1.0) * sway
        out = face if face is not None else norm(np.array([rng.normal(), 0, rng.normal()]))
        pts = []; nrs = []
        for k in range(n + 1):
            t = k * step
            off = np.array([math.sin(t * 0.9 + ph[0]) * amp * min(1, t / 2), 0, math.sin(t * 0.7 + ph[1]) * amp * min(1, t / 2)])
            pts.append(np.asarray(a, float) + np.array([0, -t, 0]) + off + out * 0.05 * min(1, t))
            nrs.append(out)
        strands.append(dict(p=np.array(pts), n=np.array(nrs), att=np.zeros(len(pts), bool), gen=1, hang=True))
        # side tendrils
        if rng.random() < branch:
            k0 = rng.integers(len(pts) // 4, max(len(pts) // 4 + 1, len(pts) // 2))
            L2 = L - k0 * step
            m = int(L2 * rng.uniform(0.4, 0.8) / step)
            if m > 4:
                b = pts[k0]; dx = norm(np.array([rng.normal(), 0, rng.normal()])) * 0.4
                pts2 = [b + dx * min(1, k * step / 0.6) + np.array([0, -k * step, 0]) for k in range(m)]
                strands.append(dict(p=np.array(pts2), n=np.array([out] * m), att=np.zeros(m, bool), gen=2, hang=True))
    return strands

# ------------------------------------------------------------------ geometry
class Geo:
    def __init__(self):
        self.V = []; self.N = []; self.C = []; self.U = []; self.F = []; self.n = 0
    def add(self, V, N, C, U, F):
        F = np.asarray(F, np.int64)
        V = np.asarray(V, float); N = np.asarray(N, float)
        # Unity front-face winding: cross(b - a, c - a) along the vertex normal
        a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        fn = np.cross(b - a, c - a)
        flip = (fn * (N[F[:, 0]] + N[F[:, 1]] + N[F[:, 2]])).sum(1) < 0
        F[flip] = F[flip][:, [0, 2, 1]]
        self.V.append(V); self.N.append(N); self.C.append(np.asarray(C)); self.U.append(np.asarray(U, float)); self.F.append(F + self.n)
        self.n += len(V)
    def arrays(self):
        if not self.V: return None
        return (np.concatenate(self.V), np.concatenate(self.N), np.concatenate(self.C), np.concatenate(self.U), np.concatenate(self.F))

def resample(P, every):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]
    if cum[-1] < every: return P[[0, -1]], np.array([0, cum[-1]]), np.array([0, len(P) - 1])
    s = np.arange(0, cum[-1], every); s = np.r_[s, cum[-1]]
    idx = np.clip(np.searchsorted(cum, s, side='right') - 1, 0, len(P) - 2)
    f = ((s - cum[idx]) / np.maximum(seg[idx], 1e-9))[:, None]
    return P[idx] * (1 - f) + P[idx + 1] * f, s, idx

def stems(G, strands, rng, offset=0.035, max_gen=2, every=0.22):
    for s in strands:
        if s['gen'] > max_gen: continue
        P, N = s['p'], s['n']
        Q, cum, idx = resample(P, every)
        if len(Q) < 2: continue
        Ltot = cum[-1]
        r_root = {0: 0.026, 1: 0.012}.get(s['gen'], 0.007) * (0.5 if s.get('hang') else 1.0)
        r_tip = 0.0035
        V = []; NN = []; U = []
        for k, q in enumerate(Q):
            n = norm(N[min(idx[k], len(N) - 1)])
            tg = norm(Q[min(k + 1, len(Q) - 1)] - Q[max(k - 1, 0)])
            r = r_tip + (r_root - r_tip) * ((Ltot - cum[k]) / max(Ltot, 0.5)) ** 0.9
            c = q - n * (offset - r) if s['att'][min(idx[k], len(N) - 1)] else q
            b = norm(np.cross(tg, n)); u = norm(np.cross(b, tg))
            for j in range(3):
                a = j * 2 * math.pi / 3
                dv = b * math.cos(a) + u * math.sin(a)
                V.append(c + dv * r); NN.append(dv); U.append((j / 3 * 0.25, cum[k] / 0.6))
        F = []
        for k in range(len(Q) - 1):
            for j in range(3):
                a = k * 3 + j; b2 = k * 3 + (j + 1) % 3
                F += [(a, b2, b2 + 3), (a, b2 + 3, a + 3)]
        C = np.tile([200, 255, 255, 255], (len(V), 1))
        G.add(V, NN, C, U, F)

def leaves(strands, rng, rects, *, every=0.055, density=0.95, size=(0.09, 0.18), offset=0.035, face_bias=None):
    cent = []; recs = []
    for s in strands:
        P, N = s['p'], s['n']
        Q, cum, idx = resample(P, every)
        Ltot = cum[-1]; side = 1
        for k in range(1, len(Q)):
            if rng.random() > density: continue
            side = -side
            i = min(idx[k], len(N) - 1)
            n = norm(N[i]); q = Q[k]
            tg = norm(Q[min(k + 1, len(Q) - 1)] - Q[k - 1])
            sv = norm(np.cross(n, tg)) * side
            age = 1 - cum[k] / max(Ltot, 0.1)                     # 1 near the root, 0 at the tip
            maturity = age * (1.0 if s['gen'] == 0 else 0.7)
            sz = rng.uniform(*size) * (0.55 + 0.6 * maturity)
            hang_ = s.get('hang', False)
            if hang_:
                fb = face_bias if face_bias is not None else n
                ln = norm(fb * 0.8 + rng.normal(size=3) * 0.6 + UP * 0.2)
                want = DOWN * 0.9 + sv * 0.6 + rng.normal(size=3) * 0.5
            else:
                ln = norm(n + UP * 0.2 + rng.normal(size=3) * 0.32)
                want = DOWN * 0.65 + sv * 0.9 + tg * 0.25 + rng.normal(size=3) * 0.45
            tip = want - ln * (want @ ln)
            if np.linalg.norm(tip) < 1e-3: tip = norm(np.cross(ln, sv))
            tip = norm(tip)
            right = norm(np.cross(ln, tip))
            base = q + sv * 0.015 + ln * rng.uniform(0.01, 0.035) + (n * 0.0 if hang_ else -n * (offset - 0.02))
            rect = rects[rng.integers(len(rects))]
            asp = (rect[2] - rect[0]) * 2048 / ((rect[3] - rect[1]) * 1024)
            h = sz; w = sz * asp
            fold = 0.16 * sz; droop = rng.uniform(0.05, 0.18) * h
            um = (rect[0] + rect[2]) / 2
            V = [base - right * w / 2, base + ln * fold, base + right * w / 2,
                 base + tip * h - right * w / 2 - ln * droop, base + tip * h + ln * fold - ln * droop, base + tip * h + right * w / 2 - ln * droop]
            Uv = [(rect[0], rect[1]), (um, rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (um, rect[3]), (rect[2], rect[3])]
            NN = [norm(ln - right * 0.35), ln, norm(ln + right * 0.35), norm(ln - right * 0.35 + tip * 0.2), norm(ln + tip * 0.2), norm(ln + right * 0.35 + tip * 0.2)]
            F = [(0, 1, 4), (0, 4, 3), (1, 2, 5), (1, 5, 4)]
            # tint: old leaves deep green, young tips bright lime; a few bronze leaves
            if rng.random() < 0.03: tint = (1.0, 0.62, 0.42)
            else:
                y = 1 - maturity
                tint = (0.78 + 0.22 * y, 0.86 + 0.14 * y, 0.78 + 0.08 * y)
            tint = tuple(np.clip(np.array(tint) * rng.uniform(0.9, 1.05), 0, 1))
            recs.append((V, NN, Uv, F, tint)); cent.append(base + tip * h * 0.5)
    if not recs: return []
    cent = np.array(cent); tr = cKDTree(cent)
    cnt = np.array([len(x) for x in tr.query_ball_point(cent, 0.14)])
    out = []
    for (V, NN, Uv, F, tint), c, ce in zip(recs, cnt, cent):
        ao = float(np.clip(1.08 - 0.045 * c, 0.5, 1.0))
        C = np.tile([int(ao * 255), int(tint[0] * 255), int(tint[1] * 255), int(tint[2] * 255)], (6, 1))
        out.append((np.array(V), NN, C, Uv, F, ce))
    return out

def emit_leaves(G, recs, keep=1.0, grow_=1.0, rng=None):
    for (V, NN, C, Uv, F, ce) in recs:
        if keep < 1.0 and rng.random() > keep: continue
        G.add(ce + (V - ce) * grow_ if grow_ != 1.0 else V, NN, C, Uv, F)

def write_pms2(name, groups):
    """groups: [(sub_name, Geo)] -> one PMS2 file."""
    arrs = [(nm, g.arrays()) for nm, g in groups]
    arrs = [(nm, a) for nm, a in arrs if a is not None]
    P = []; N = []; C = []; U = []; subs = []; base = 0
    for nm, (V, NN, CC, UU, F) in arrs:
        P.append(V); N.append(NN); C.append(CC); U.append(UU); subs.append((nm, (F + base).ravel())); base += len(V)
    P = np.concatenate(P).astype('<f4'); N = np.concatenate(N); N = (N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)).astype('<f4')
    C = np.concatenate(C).astype(np.uint8); U = np.concatenate(U).astype('<f4')
    with open(os.path.join(MESH, name + '.bytes'), 'wb') as f:
        f.write(b'PMS2'); f.write(struct.pack('<iii', len(P), len(subs), 1))
        f.write(P.tobytes()); f.write(N.tobytes()); f.write(C.tobytes()); f.write(U.tobytes())
        for nm, idx in subs:
            bn = nm.encode(); f.write(struct.pack('<i', len(bn))); f.write(bn)
            f.write(struct.pack('<i', len(idx))); f.write(idx.astype('<i4').tobytes())
    tris = sum(len(i) for _, i in subs) // 3
    print(f'{name}: {len(P)} verts, {tris} tris, bounds {P.min(0).round(1)} {P.max(0).round(1)}', flush=True)
    return tris

LEAF = dict(shader='foliage', albedo='Ivy/Ivy_Albedo.png', normal='Ivy/Ivy_Normal.png', mask='Ivy/Ivy_Mask.png', alpha='MASK',
            wind=0.18, windScale=40, translucency=0.9, vertexTint=1, smooth=0.6, cutoff=0.42)
LEAF_HANG = dict(LEAF, wind=0.7, windScale=6)
STEM = dict(shader='prop', albedo='Palm/PalmBark_Albedo.png', normal='Palm/PalmBark_Normal.png', alpha='OPAQUE', tint=[0.42, 0.36, 0.3], smooth=0.15)

def export(name, strands, rng, rects, man, hanging=False, lod=True, **leafkw):
    recs = leaves(strands, rng, rects, **leafkw)
    GL = Geo(); GS = Geo()
    emit_leaves(GL, recs); stems(GS, strands, rng)
    write_pms2(name, [(f'{name}_Leaf', GL), (f'{name}_Stem', GS)])
    entries = [dict(sub=f'{name}_Leaf', **(LEAF_HANG if hanging else LEAF)), dict(sub=f'{name}_Stem', **STEM)]
    man[name] = entries
    if lod:   # distant version: a third of the leaves, enlarged to keep the silhouette, trunk stems only
        GL = Geo(); GS = Geo()
        emit_leaves(GL, recs, keep=0.33, grow_=1.55, rng=rng); stems(GS, strands, rng, max_gen=0, every=0.5)
        write_pms2(name + '_LOD1', [(f'{name}_Leaf', GL), (f'{name}_Stem', GS)])
        man[name + '_LOD1'] = entries
    print(f'  {len(recs)} leaves', flush=True)

# ------------------------------------------------------------------ the ivy set
def column_ivy(rng, rects, man, name, reach):
    S = Surface(0.04, 1).add_mesh('Column').build()
    seeds = []
    for k in range(rng.integers(3, 5)):
        a = rng.uniform(0, 2 * math.pi)
        seeds.append(((math.cos(a) * 0.66, 0.15, math.sin(a) * 0.66), (-math.cos(a) * 0.2, 1, -math.sin(a) * 0.2)))
    st = grow(S, seeds, rng, length=(reach * 0.5, reach), budget=reach * 14, w_up=0.38, branch_p=0.07,
              bounds=lambda p: p[1] < 10.45 and abs(p[0]) < 1.5 and abs(p[2]) < 1.5)
    export(name, st, rng, rects, man)

def wall_ivy(rng, rects, man, name, mesh, keep, climb_seeds, cascade_seeds, bounds, budget=(420, 300), leaf_size=(0.09, 0.19)):
    S = Surface(0.05, 2).add_mesh(mesh, keep=keep).build()
    st = grow(S, climb_seeds, rng, length=(6, 15), budget=budget[0], w_up=0.28, w_rand=0.62, branch_p=0.075, max_strands=2000, bounds=bounds)
    st += grow(S, cascade_seeds, rng, length=(3, 11), budget=budget[1], w_up=-0.5, w_rand=0.6, branch_p=0.07, max_float=0.9, max_strands=2000, bounds=bounds)
    export(name, st, rng, rects, man, size=leaf_size)

def main():
    rng = np.random.default_rng(2024)
    rects = build_atlas()
    man = json.load(open(MANIFEST))
    R = lambda a, b: rng.uniform(a, b)

    # columns (ruin + selected nave columns)
    column_ivy(rng, rects, man, 'Ivy_Column_0', 9.5)
    column_ivy(rng, rects, man, 'Ivy_Column_1', 5.0)

    # vestibule blind side, exterior face (z = 12, normal +z)
    ext = lambda c, n: c[:, 2] > 11.4
    bnd = lambda p: p[2] > 9.0 and abs(p[0]) < 12.1 and 0.25 < p[1] < 24.6
    for i in range(2):
        cx = R(-6, 6)
        climb = [((float(np.clip(cx + rng.normal() * 3.5, -11, 11)), 0.4, 12.04), (0, 1, 0)) for _ in range(9)]
        casc = [((float(np.clip(-cx + rng.normal() * 4, -11, 11)), 23.6, 12.04), (0, -1, 0)) for _ in range(8)]
        wall_ivy(rng, rects, man, f'Ivy_VestBlind_{i}', 'Vest_SideBlind', ext, climb, casc, bnd)
    # vestibule window side, exterior: keep clear of the glass
    climb = [((s * R(5, 11), 0.4, 12.04), (0, 1, 0)) for s in (-1, 1, -1, 1, 1, -1, 1, -1)]
    casc = [((s * R(3.5, 11), 23.6, 12.04), (0, -1, 0)) for s in (-1, 1, -1, 1, -1, 1, -1, 1)]
    wall_ivy(rng, rects, man, 'Ivy_VestWindow', 'Vest_SideWindow', ext, climb, casc, bnd)
    # vestibule inner faces: ivy that came in through the lunette and cascades down the marble
    inner = lambda c, n: c[:, 2] < 10.4
    bnd_in = lambda p: p[2] < 10.6 and abs(p[0]) < 9.8 and 0.3 < p[1] < 21
    for nm, mesh, lo in (('Ivy_VestInnerBlind', 'Vest_SideBlind', 2.0), ('Ivy_VestInnerOpen', 'Vest_SideOpen', 12.4)):
        S = Surface(0.05, 3).add_mesh(mesh, keep=inner).build()
        seeds = [((R(-3.2, 3.2), R(15.6, 17.5), 9.97), (R(-0.5, 0.5), -1, -0.3)) for _ in range(9)]
        b = (lambda lo_: (lambda p: p[2] < 10.6 and abs(p[0]) < 9.8 and lo_ < p[1] < 21))(lo)
        st = grow(S, seeds, rng, length=(4, 12), budget=170, w_up=-0.6, w_rand=0.6, branch_p=0.07, max_float=1.2, bounds=b)
        export(nm, st, rng, rects, man, size=(0.07, 0.13))
    # arcade with windows: exterior +x face (x = 7)
    ext_a = lambda c, n: c[:, 0] > 6.3
    bnd_a = lambda p: p[0] > 5.5 and abs(p[2]) < 18.1 and 0.25 < p[1] < 16.0
    climb = [((7.04, 0.4, R(-17, 17)), (0, 1, 0)) for _ in range(10)]
    casc = [((7.04, 15.2, R(-17, 17)), (0, -1, 0)) for _ in range(10)]
    wall_ivy(rng, rects, man, 'Ivy_ArcadeWin', 'Arcade_Win', ext_a, climb, casc, bnd_a, budget=(480, 320))
    # stair tower: climbing from the waterline up three faces
    ext_t = lambda c, n: (np.abs(c[:, 0]) > 4.6) | (c[:, 2] > 9.6)
    bnd_t = lambda p: (abs(p[0]) > 4.5 or p[2] > 9.5) and -0.5 < p[2] < 10.6 and abs(p[0]) < 5.6 and 0.25 < p[1] < 27.2
    climb = [((5.04, 0.4, R(1, 9)), (0, 1, 0)) for _ in range(3)] + [((-5.04, 0.4, R(1, 9)), (0, 1, 0)) for _ in range(3)] + [((R(-4, 4), 0.4, 10.04), (0, 1, 0)) for _ in range(3)]
    S = Surface(0.05, 4).add_mesh('StairTower', keep=ext_t).build()
    st = grow(S, climb, rng, length=(6, 18), budget=520, w_up=0.33, w_rand=0.6, branch_p=0.07, max_strands=2000, bounds=bnd_t)
    export('Ivy_Tower', st, rng, rects, man)
    # aqueduct: climbing the piers, cascading off the channel walls (local frame; channel top y = 18)
    S = Surface(0.05, 5).add_mesh('Aqueduct').build()
    L = float(read_pms('Aqueduct')[0][:, 2].max())
    climb = [((s * 1.54, 0.9, R(1, L - 1)), (0, 1, 0)) for s in (-1, 1, -1, 1, -1, 1)]
    casc = [((s * 1.69, 17.7, R(1, L - 1)), (0, -1, 0)) for s in (-1, 1, -1, 1, -1, 1, 1, -1, 1)]
    bnd_q = lambda p: abs(p[0]) < 2.2 and -0.5 < p[2] < L + 0.3 and 0.7 < p[1] < 18.3
    st = grow(S, climb, rng, length=(5, 14), budget=300, w_up=0.33, w_rand=0.6, branch_p=0.07, max_strands=2000, bounds=bnd_q)
    st += grow(S, casc, rng, length=(3, 10), budget=300, w_up=-0.5, w_rand=0.6, branch_p=0.07, max_float=0.9, max_strands=2000, bounds=bnd_q)
    export('Ivy_Aqueduct', st, rng, rects, man)
    # ruin: standing columns + beams (fallen columns lying across the tops) -> climbing + hanging
    import ruin
    S = Surface(0.045, 6)
    for (x, z) in ruin.COLUMNS: S.add_mesh('Column', t=(x, ruin.BASE_Y, z))
    for b in ruin.BEAMS: S.add_mesh('Column', R=euler(*b['e']), t=b['p'])
    S.build()
    seeds = []
    for (x, z) in ruin.COLUMNS:
        for k in range(4):
            a = rng.uniform(0, 2 * math.pi)
            seeds.append(((x + math.cos(a) * 0.62, ruin.BASE_Y + 0.5, z + math.sin(a) * 0.62), (0, 1, 0)))
    st = grow(S, seeds, rng, length=(8, 18), budget=1000, w_up=0.4, w_rand=0.55, branch_p=0.065, max_strands=3000,
              bounds=lambda p: -0.2 < p[1] < 14.5 and abs(p[0]) < 13 and abs(p[2]) < 8)
    anchors = []
    for b in ruin.BEAMS:
        d = euler(*b['e']) @ UP; p0 = np.asarray(b['p'])
        for k in range(30):
            t = rng.uniform(0.5, 10.1)
            anchors.append(p0 + d * t + np.array([rng.normal() * 0.15, -0.5, rng.normal() * 0.15]))
    hs = hang(anchors, rng, length=(2.0, 7.5), face=None, sway=0.2)
    hs = [h for h in hs if h['p'][:, 1].min() > 2.6]
    export('Ivy_Ruin', st + hs, rng, rects, man)
    # hanging curtains: oculus ring (r 3.05) and straight rims (3 m and 8 m)
    anchors = []
    for c0 in (R(0, 6.3), R(0, 6.3), R(0, 6.3)):
        for k in range(34):
            a = c0 + rng.normal() * 0.5
            anchors.append((math.cos(a) * 3.05, 0.0, math.sin(a) * 3.05))
    hs = hang(anchors, rng, length=(1.5, 8.0), sway=0.15)
    export('Ivy_HangRing', hs, rng, rects, man, hanging=True, density=0.95)
    for nm, w, ln, cnt in (('Ivy_HangLine_S', 3.0, (1.0, 4.5), 30), ('Ivy_HangLine_L', 8.0, (2.0, 9.0), 70)):
        anchors = [(R(-w / 2, w / 2), 0.0, R(-0.05, 0.05)) for _ in range(cnt)]
        hs = hang(anchors, rng, length=ln, face=np.array([0, 0, -1.0]), sway=0.2)
        export(nm, hs, rng, rects, man, hanging=True, face_bias=np.array([0, 0, -1.0]))
    json.dump(man, open(MANIFEST, 'w'), indent=1)
    print('ivy done')

if __name__ == '__main__':
    main()
