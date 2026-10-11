"""A signed-distance sculpting kit for the House's statues (original work: no scans, no base meshes).

Shapes are recorded as clay: smooth unions (pressed on), smooth subtractions (chiselled out), smooth intersections
(trimmed). Nothing is evaluated until mesh(): a coarse pass finds the thin shell of space that holds the surface,
then only that shell is evaluated finely, in cubes, each polygonised with marching cubes and stitched. So a 13 m
Colossus can be carved at a few millimetres without a dense grid. Coordinates: Blender (z up), metres; figures
face -y and their right side is -x.
"""
import math, time
import numpy as np
from numba import njit, prange

# ------------------------------------------------------------------------------------------------ distance kernels
@njit(cache=True, fastmath=True)
def _smin(a, b, k):
    if k <= 0.0:
        return a if a < b else b
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25

@njit(cache=True, fastmath=True)
def _smax(a, b, k):
    if k <= 0.0:
        return a if a > b else b
    h = max(k - abs(a - b), 0.0) / k
    return max(a, b) + h * h * k * 0.25

@njit(cache=True, fastmath=True)
def _round_cone(px, py, pz, ax, ay, az, bx, by, bz, r1, r2):
    bax = bx - ax; bay = by - ay; baz = bz - az
    l2 = bax * bax + bay * bay + baz * baz
    if l2 < 1e-14:
        dx = px - ax; dy = py - ay; dz = pz - az
        return math.sqrt(dx * dx + dy * dy + dz * dz) - max(r1, r2)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pax = px - ax; pay = py - ay; paz = pz - az
    y = pax * bax + pay * bay + paz * baz
    z = y - l2
    qx = pax * l2 - bax * y; qy = pay * l2 - bay * y; qz = paz * l2 - baz * y
    x2 = qx * qx + qy * qy + qz * qz
    y2 = y * y * l2
    z2 = z * z * l2
    s = 1.0 if rr > 0 else (-1.0 if rr < 0 else 0.0)
    k = s * rr * rr * x2
    sz = 1.0 if z > 0 else (-1.0 if z < 0 else 0.0)
    sy = 1.0 if y > 0 else (-1.0 if y < 0 else 0.0)
    if sz * a2 * z2 > k:
        return math.sqrt(x2 + z2) * il2 - r2
    if sy * a2 * y2 < k:
        return math.sqrt(x2 + y2) * il2 - r1
    return (math.sqrt(max(x2 * a2 * il2, 0.0)) + y * rr) * il2 - r1

@njit(cache=True, fastmath=True)
def _ellipsoid(lx, ly, lz, rx, ry, rz):
    k0 = math.sqrt((lx / rx) ** 2 + (ly / ry) ** 2 + (lz / rz) ** 2)
    k1 = math.sqrt((lx / (rx * rx)) ** 2 + (ly / (ry * ry)) ** 2 + (lz / (rz * rz)) ** 2)
    if k1 < 1e-12:
        return -min(rx, min(ry, rz))
    return k0 * (k0 - 1.0) / k1

@njit(cache=True, fastmath=True)
def _round_box(lx, ly, lz, hx, hy, hz, r):
    qx = abs(lx) - hx + r; qy = abs(ly) - hy + r; qz = abs(lz) - hz + r
    ox = max(qx, 0.0); oy = max(qy, 0.0); oz = max(qz, 0.0)
    return math.sqrt(ox * ox + oy * oy + oz * oz) + min(max(qx, max(qy, qz)), 0.0) - r

@njit(cache=True, fastmath=True)
def _cyl(lx, ly, lz, r, h, rr):
    dx = math.sqrt(lx * lx + ly * ly) - r + rr
    dy = abs(lz) - h + rr
    return min(max(dx, dy), 0.0) + math.sqrt(max(dx, 0.0) ** 2 + max(dy, 0.0) ** 2) - rr

@njit(cache=True, fastmath=True)
def _torus(lx, ly, lz, R, r):
    q = math.sqrt(lx * lx + ly * ly) - R
    return math.sqrt(q * q + lz * lz) - r

@njit(cache=True, fastmath=True)
def _tri_slab(lx, ly, lz, ax, ay, bx, by, cx, cy, th):
    # a triangle in the local xy plane, extruded +-th in z (feathers, leaves, cloth panels), with rounded edges
    e0x = bx - ax; e0y = by - ay; e1x = cx - bx; e1y = cy - by; e2x = ax - cx; e2y = ay - cy
    v0x = lx - ax; v0y = ly - ay; v1x = lx - bx; v1y = ly - by; v2x = lx - cx; v2y = ly - cy
    t0 = min(max((v0x * e0x + v0y * e0y) / (e0x * e0x + e0y * e0y + 1e-20), 0.0), 1.0)
    t1 = min(max((v1x * e1x + v1y * e1y) / (e1x * e1x + e1y * e1y + 1e-20), 0.0), 1.0)
    t2 = min(max((v2x * e2x + v2y * e2y) / (e2x * e2x + e2y * e2y + 1e-20), 0.0), 1.0)
    d0 = (v0x - e0x * t0) ** 2 + (v0y - e0y * t0) ** 2
    d1 = (v1x - e1x * t1) ** 2 + (v1y - e1y * t1) ** 2
    d2 = (v2x - e2x * t2) ** 2 + (v2y - e2y * t2) ** 2
    s = 1.0 if (e0x * e2y - e0y * e2x) > 0 else -1.0
    c0 = s * (v0x * e0y - v0y * e0x); c1 = s * (v1x * e1y - v1y * e1x); c2 = s * (v2x * e2y - v2y * e2x)
    d2d = math.sqrt(min(d0, min(d1, d2)))
    inside = c0 <= 0 and c1 <= 0 and c2 <= 0
    if inside:
        d2d = -d2d
    # 2d distance combined with the slab thickness
    wx = d2d; wy = abs(lz) - th
    return min(max(wx, wy), 0.0) + math.sqrt(max(wx, 0.0) ** 2 + max(wy, 0.0) ** 2)

@njit(cache=True, fastmath=True)
def _radial(tab, prm, px, py, pz):
    # a surface of revolution with a free radius r(theta, z) and a wandering centre c(z), from a table:
    # rows from z_top down to z_bot, each [cx, cy, r_0 .. r_n-1]; then one row [0, 0, hem_0 .. hem_n-1] (the lower edge)
    off = int(prm[0]); nt = int(prm[1]); nzr = int(prm[2]); zt = prm[3]; zb = prm[4]; sl = prm[5]
    w = nt + 2
    fz = (zt - pz) / (zt - zb) * (nzr - 1)
    if fz < 0.0: fz = 0.0
    if fz > nzr - 1.0: fz = nzr - 1.0
    i0 = int(fz)
    if i0 >= nzr - 1: i0 = nzr - 2
    t = fz - i0
    a = off + i0 * w; b = off + (i0 + 1) * w
    cx = tab[a] * (1 - t) + tab[b] * t
    cy = tab[a + 1] * (1 - t) + tab[b + 1] * t
    dx = px - cx; dy = py - cy
    rho = math.sqrt(dx * dx + dy * dy)
    th = math.atan2(dy, dx)
    if th < 0.0: th += 2.0 * math.pi
    ft = th / (2.0 * math.pi) * nt
    j0 = int(ft) % nt; j1 = (j0 + 1) % nt; s = ft - int(ft)
    r = (tab[a + 2 + j0] * (1 - s) + tab[a + 2 + j1] * s) * (1 - t) + (tab[b + 2 + j0] * (1 - s) + tab[b + 2 + j1] * s) * t
    hrow = off + nzr * w
    zh = tab[hrow + 2 + j0] * (1 - s) + tab[hrow + 2 + j1] * s
    d = (rho - r) * sl
    e = zh - pz
    if e > d: d = e
    e = pz - zt
    if e > d: d = e
    return d

@njit(cache=True, fastmath=True)
def _prim(kind, prm, M, px, py, pz, tab):
    if kind == 6:
        return _radial(tab, prm, px, py, pz)
    if kind == 0:
        return _round_cone(px, py, pz, prm[0], prm[1], prm[2], prm[3], prm[4], prm[5], prm[6], prm[7])
    dx = px - M[0, 3]; dy = py - M[1, 3]; dz = pz - M[2, 3]
    lx = M[0, 0] * dx + M[1, 0] * dy + M[2, 0] * dz
    ly = M[0, 1] * dx + M[1, 1] * dy + M[2, 1] * dz
    lz = M[0, 2] * dx + M[1, 2] * dy + M[2, 2] * dz
    if kind == 1:
        return _ellipsoid(lx, ly, lz, prm[0], prm[1], prm[2])
    if kind == 2:
        return _round_box(lx, ly, lz, prm[0], prm[1], prm[2], prm[3])
    if kind == 3:
        return _cyl(lx, ly, lz, prm[0], prm[1], prm[2])
    if kind == 4:
        return _torus(lx, ly, lz, prm[0], prm[1])
    return _tri_slab(lx, ly, lz, prm[0], prm[1], prm[2], prm[3], prm[4], prm[5], prm[6])

@njit(parallel=True, cache=True, fastmath=True)
def _eval_pts(P, out, kinds, prms, Ms, los, his, ops, ks, sel, tab):
    for n in prange(P.shape[0]):
        px = P[n, 0]; py = P[n, 1]; pz = P[n, 2]
        v = 1e3
        for q in range(sel.shape[0]):
            s = sel[q]
            if px < los[s, 0] or px > his[s, 0] or py < los[s, 1] or py > his[s, 1] or pz < los[s, 2] or pz > his[s, 2]:
                continue
            d = _prim(kinds[s], prms[s], Ms[s], px, py, pz, tab)
            o = ops[s]
            if o == 0:
                v = _smin(v, d, ks[s])
            elif o == 1:
                v = _smax(v, -d, ks[s])
            else:
                v = _smax(v, d, ks[s])
        out[n] = v

@njit(parallel=True, cache=True, fastmath=True)
def _eval(F, ox, oy, oz, h, kinds, prms, Ms, los, his, ops, ks, sel, tab):
    nx, ny, nz = F.shape
    for i in prange(nx):
        px = ox + i * h
        for j in range(ny):
            py = oy + j * h
            for kk in range(nz):
                pz = oz + kk * h
                v = F[i, j, kk]
                for q in range(sel.shape[0]):
                    s = sel[q]
                    if px < los[s, 0] or px > his[s, 0] or py < los[s, 1] or py > his[s, 1] or pz < los[s, 2] or pz > his[s, 2]:
                        continue
                    d = _prim(kinds[s], prms[s], Ms[s], px, py, pz, tab)
                    o = ops[s]
                    if o == 0:
                        v = _smin(v, d, ks[s])
                    elif o == 1:
                        v = _smax(v, -d, ks[s])
                    else:
                        v = _smax(v, d, ks[s])
                F[i, j, kk] = v

# ------------------------------------------------------------------------------------------------ frames
def frame(z, x_hint=(1, 0, 0)):
    """3x3 rotation whose columns are (x, y, z): z along `z`, x as near to x_hint as possible."""
    z = np.asarray(z, float); z = z / (np.linalg.norm(z) + 1e-12)
    x = np.asarray(x_hint, float); x = x - z * np.dot(x, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.array([0, 1.0, 0]) - z * z[1]
    x /= np.linalg.norm(x); y = np.cross(z, x)
    return np.stack([x, y, z], 1)

def rot(axis, deg):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a); t = math.radians(deg)
    c, s = math.cos(t), math.sin(t); x, y, z = a; C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])

OPS = {'add': 0, 'cut': 1, 'keep': 2}

# ------------------------------------------------------------------------------------------------ the sculpt
class Sculpt:
    def __init__(self):
        self.kinds = []; self.prms = []; self.Ms = []; self.los = []; self.his = []; self.ops = []; self.ks = []
        self.disp = []          # (fn, band) surface displacements, applied after the shapes
        self.count = 0
        self.tab = [np.zeros(1)]; self.tab_n = 1

    def _rec(self, kind, prm, M, lo, hi, op, k):
        p = np.zeros(8); p[:len(prm)] = prm
        self.kinds.append(kind); self.prms.append(p); self.Ms.append(np.asarray(M, float))
        self.los.append(np.asarray(lo, float)); self.his.append(np.asarray(hi, float)); self.ops.append(OPS[op]); self.ks.append(float(k))
        self.count += 1

    @staticmethod
    def _M(c, R):
        M = np.eye(4); M[:3, :3] = R; M[:3, 3] = c; return M

    # ---- shapes
    def cone(self, a, b, r1, r2, k=0.01, op='add'):
        a = np.asarray(a, float); b = np.asarray(b, float); r = max(r1, r2) + k * 1.25
        self._rec(0, [*a, *b, r1, r2], np.eye(4), np.minimum(a, b) - r, np.maximum(a, b) + r, op, k)

    def ball(self, c, r, k=0.01, op='add'):
        self.cone(c, c, r, r, k, op)

    def chain(self, pts, radii, k=0.01, op='add'):
        for i in range(len(pts) - 1):
            self.cone(pts[i], pts[i + 1], radii[i], radii[i + 1], k, op)

    def ell(self, c, radii, R=np.eye(3), k=0.01, op='add'):
        c = np.asarray(c, float); r = max(radii) + k * 1.25
        if op == 'keep': r = 1e4                                  # an intersection trims everything, everywhere
        self._rec(1, list(radii), self._M(c, R), c - r, c + r, op, k)

    def box(self, c, half, R=np.eye(3), rnd=0.0, k=0.01, op='add'):
        c = np.asarray(c, float); r = float(np.linalg.norm(half)) + k * 1.25
        if op == 'keep': r = 1e4
        self._rec(2, [*half, rnd], self._M(c, R), c - r, c + r, op, k)

    def cyl(self, c, axis, radius, half_h, rnd=0.0, k=0.01, op='add'):
        c = np.asarray(c, float); r = math.hypot(radius, half_h) + k * 1.25
        self._rec(3, [radius, half_h, rnd], self._M(c, frame(axis)), c - r, c + r, op, k)

    def torus(self, c, axis, R_, r_, k=0.01, op='add', x_hint=(1, 0, 0)):
        c = np.asarray(c, float); r = R_ + r_ + k * 1.25
        self._rec(4, [R_, r_], self._M(c, frame(axis, x_hint)), c - r, c + r, op, k)

    def tri(self, a, b, c, th, k=0.005, op='add'):
        """a slab triangle (feather vanes, leaves, cloth flaps) through world points a, b, c, thickness 2*th."""
        a = np.asarray(a, float); b = np.asarray(b, float); c = np.asarray(c, float)
        ab = np.linalg.norm(b - a); n = np.cross(b - a, c - a); area2 = np.linalg.norm(n)
        if ab < 1e-6 or area2 < 1e-3 * max(ab, np.linalg.norm(c - a)) ** 2: return      # degenerate: nothing to carve
        x = (b - a) / ab; n /= area2; y = np.cross(n, x)
        R = np.stack([x, y, n], 1)
        L = lambda p: R.T @ (p - a)
        la, lb, lc = L(a), L(b), L(c)
        lo = np.minimum(np.minimum(a, b), c) - th - k; hi = np.maximum(np.maximum(a, b), c) + th + k
        self._rec(5, [la[0], la[1], lb[0], lb[1], lc[0], lc[1], th], self._M(a, R), lo, hi, op, k)

    def curve(self, pts, radii, k=0.01, op='add', n=None):
        """a tapering tube through a Catmull-Rom spline (locks of hair, folds, tails, fingers)."""
        pts = np.asarray(pts, float); radii = np.asarray(radii, float)
        if n is None:
            L = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
            n = int(min(80, max(4, L / max(radii.min(), 1e-4) / 1.5)))
        P = catmull(pts, n); R = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(radii)), radii)
        self.chain(P, R, k, op)

    def radial(self, centres, radii, hem, z_top, z_bot, k=0.01, op='add', slope=0.75):
        """a cloth-like surface of revolution: centres (nz, 2) and radii (nz, nt) on rows from z_top down to z_bot, and
        hem (nt,) the height of the lower edge at each angle (theta measured from +x toward +y)."""
        centres = np.asarray(centres, float); radii = np.asarray(radii, float); hem = np.asarray(hem, float)
        nz, nt = radii.shape
        rows = [np.concatenate([centres[i], radii[i]]) for i in range(nz)] + [np.concatenate([[0, 0], hem])]
        t = np.concatenate(rows); off = self.tab_n
        self.tab.append(t); self.tab_n += len(t)
        rmax = radii.max() + k * 1.25 + 0.01
        lo = np.array([centres[:, 0].min() - rmax, centres[:, 1].min() - rmax, min(z_bot, hem.min()) - k * 1.25])
        hi = np.array([centres[:, 0].max() + rmax, centres[:, 1].max() + rmax, z_top + k * 1.25])
        self._rec(6, [off, nt, nz, z_top, z_bot, slope], np.eye(4), lo, hi, op, k)

    def sample(self, P):
        """the field so far at points P (N, 3)."""
        kinds, prms, Ms, los, his, ops, ks = self._arrays()
        P = np.ascontiguousarray(P, float); out = np.empty(len(P))
        sel = np.arange(len(kinds), dtype=np.int64)
        _eval_pts(P, out, kinds, prms, Ms, los, his, ops, ks, sel, np.concatenate(self.tab))
        return out

    def displace(self, fn, band):
        """fn(points Nx3) -> offsets in metres (positive pushes out); applied to voxels within `band` of the surface."""
        self.disp.append((fn, band))

    # ---- evaluation
    def _arrays(self):
        return (np.array(self.kinds, np.int64), np.array(self.prms), np.array(self.Ms), np.array(self.los), np.array(self.his),
                np.array(self.ops, np.int64), np.array(self.ks))

    def field(self, lo, n, h):
        """dense field on a grid (for small things and the coarse pass)."""
        kinds, prms, Ms, los, his, ops, ks = self._arrays()
        lo = np.asarray(lo, float)
        hi = lo + (np.asarray(n) - 1) * h
        sel = np.where(np.all(his >= lo, 1) & np.all(los <= hi, 1))[0].astype(np.int64)
        F = np.full(tuple(n), 1e3, np.float32).astype(np.float64)
        _eval(F, lo[0], lo[1], lo[2], h, kinds, prms, Ms, los, his, ops, ks, sel, np.concatenate(self.tab))
        return F

    def bounds(self):
        los = np.array(self.los); his = np.array(self.his); add = np.array(self.ops) == 0
        return los[add].min(0), his[add].max(0)

    def mesh(self, h, smooth=4, target=None, chunk=40, coarse=None, verbose=True, region=None):
        """polygonise the surface at voxel size h (only inside region=(lo, hi) if given). Returns (V, F) in metres."""
        from skimage.measure import marching_cubes
        t0 = time.time()
        lo, hi = self.bounds(); lo = lo - 2 * h; hi = hi + 2 * h
        if region is not None: lo = np.maximum(lo, np.asarray(region[0], float)); hi = np.minimum(hi, np.asarray(region[1], float))
        kinds, prms, Ms, los, his, ops, ks = self._arrays()
        tab = np.concatenate(self.tab)
        csz = chunk * h                                     # chunk edge (m)
        hc = coarse or csz / 5
        nc = np.ceil((hi - lo) / hc).astype(int) + 2
        Fc = self.field(lo, nc, hc)
        # a chunk is worked only if the surface can pass through it: some coarse sample inside it lies within reach of
        # the surface (any surface point is within 0.87 coarse steps of a sample), or the field changes sign across it
        nchunk = np.ceil((hi - lo) / csz).astype(int)
        near = np.abs(Fc) < hc * 1.8
        V_all = []; F_all = []; nv = 0; active = 0
        for ci in range(nchunk[0]):
            for cj in range(nchunk[1]):
                for ck in range(nchunk[2]):
                    c0 = lo + np.array([ci, cj, ck]) * csz
                    g0 = np.floor((c0 - lo) / hc).astype(int); g1 = np.minimum(np.ceil((c0 + csz - lo) / hc).astype(int) + 1, nc)
                    blk = Fc[g0[0]:g1[0], g0[1]:g1[1], g0[2]:g1[2]]
                    if blk.size == 0: continue
                    if not (near[g0[0]:g1[0], g0[1]:g1[1], g0[2]:g1[2]].any() or (blk.min() < 0 < blk.max())): continue
                    c1 = c0 + chunk * h
                    sel = np.where(np.all(his >= c0 - h, 1) & np.all(los <= c1 + h, 1))[0].astype(np.int64)
                    if len(sel) == 0: continue
                    F = np.full((chunk + 1,) * 3, 1e3)
                    _eval(F, c0[0], c0[1], c0[2], h, kinds, prms, Ms, los, his, ops, ks, sel, tab)
                    if self.disp:
                        for fn, band in self.disp:
                            m = np.abs(F) < band
                            if m.any():
                                idx = np.argwhere(m); P = c0 + idx * h
                                F[m] -= fn(P)
                    if F.min() > 0 or F.max() < 0: continue
                    active += 1
                    v, f, _, _ = marching_cubes(F, 0.0, spacing=(h, h, h))
                    V_all.append(v + c0); F_all.append(f[:, [0, 2, 1]] + nv); nv += len(v)
        V = np.vstack(V_all); Fm = np.vstack(F_all)
        # stitch the chunks: weld vertices that sit on shared chunk faces
        key = np.round(V / (h * 1e-3)).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        V = V[first]; Fm = inv.ravel()[Fm]
        Fm = Fm[(Fm[:, 0] != Fm[:, 1]) & (Fm[:, 1] != Fm[:, 2]) & (Fm[:, 0] != Fm[:, 2])]
        if verbose: print(f'  sculpt: {self.count} shapes, {active} chunks, {len(Fm)} tris raw, {time.time() - t0:.1f}s')
        V, Fm = clean(V, Fm)
        if smooth: V = taubin(V, Fm, smooth)
        if target and len(Fm) > target:
            import fast_simplification
            V, Fm = fast_simplification.simplify(V.astype(np.float32), Fm.astype(np.int32), target_reduction=1 - target / len(Fm))
            V = np.asarray(V, float); Fm = np.asarray(Fm)
        if verbose: print(f'  mesh: {len(V)} verts, {len(Fm)} tris, {time.time() - t0:.1f}s')
        return V, Fm

# ------------------------------------------------------------------------------------------------ helpers
def catmull(P, n):
    P = np.asarray(P, float)
    if len(P) == 2: return np.linspace(P[0], P[1], n)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    seg = len(P) - 1; out = []
    for t in np.linspace(0, seg - 1e-9, n):
        i = int(t); u = t - i
        p0, p1, p2, p3 = Q[i], Q[i + 1], Q[i + 2], Q[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return np.array(out)

def clean(V, F):
    import trimesh
    m = trimesh.Trimesh(V, F, process=False)
    m.merge_vertices(); m.remove_unreferenced_vertices()
    cc = trimesh.graph.connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)))
    if len(cc) > 1:                                     # drop crumbs (tiny disconnected bits)
        sizes = np.array([len(c) for c in cc]); keep = np.concatenate([c for c in cc if len(c) > sizes.max() * 0.002])
        m.update_faces(np.isin(np.arange(len(m.faces)), keep)); m.remove_unreferenced_vertices()
    return np.asarray(m.vertices), np.asarray(m.faces)

def taubin(V, F, it, lam=0.5, mu=-0.53):
    import scipy.sparse as sp
    n = len(V)
    i = np.concatenate([F[:, 0], F[:, 1], F[:, 2], F[:, 1], F[:, 2], F[:, 0]])
    j = np.concatenate([F[:, 1], F[:, 2], F[:, 0], F[:, 0], F[:, 1], F[:, 2]])
    A = sp.coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)).tocsr(); A.data[:] = 1
    deg = np.asarray(A.sum(1)).ravel(); L = sp.diags(1 / np.maximum(deg, 1)) @ A
    V = V.copy()
    for _ in range(it):
        V = V + lam * (L @ V - V)
        V = V + mu * (L @ V - V)
    return V

def noise(P, scale, seed=0, octaves=3):
    """smooth deterministic 3D noise from sums of random sinusoids, roughly in [-1, 1]."""
    r = np.random.default_rng(seed); out = np.zeros(len(P))
    amp = 1.0; tot = 0
    for o in range(octaves):
        for _ in range(4):
            d = r.normal(size=3); d /= np.linalg.norm(d)
            out += amp * np.sin(P @ d * (scale * 2 ** o) * 2 * np.pi + r.uniform(0, 6.3))
            tot += amp
        amp *= 0.5
    return out / tot * 2.0
