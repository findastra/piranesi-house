"""House v3 kit, part 2 (redlines 1): hall fountains + the Trevi wall fountain, the open marble tower with its inner
marble slide, the sea hall, isle halls, the ruin's arches / block seats / drum table / shards / paths, eroded sea gates
and broken stairs, gold plaques, floating docks, new sand bars and the extended seabed.

Same conventions as kit3.py (Blender space, Z up; PMS1 stone + PMS2 water/props). Run: python3 gen/kit3b.py [name ...]"""
import os, sys, json, math, numpy as np
from math import pi, sin, cos, sqrt, atan2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import (K, AS, NA, bpy, reset, apply, mesh, prism_xz, prism_xy, recalc, cyl, arch_outline, ring_band, baluster,
                  balustrade_x, urn, half_column, dentils, finish, rot_z, MAN, EXTRA, FLOW, LOD)
import islands as IS

rng = np.random.default_rng(3031)
POOL = dict(shader='pool', alpha='BLEND')

def uv_export(B, name, mats):
    ob = B.build(name)
    subs = [f'{name}_{m}' for m in B.mats]
    AS.export_pms2(ob, name, subs)
    MAN[name] = [dict(sub=f'{name}_{m}', **mats[m]) for m in B.mats]

# =====================================================================================================
# helpers: rocks, worn blocks, sweeps
# =====================================================================================================
def _ico(sub):
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    bm.verts.ensure_lookup_table()
    V = np.array([tuple(v.co) for v in bm.verts]); F = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return V, F

def rock(c, size, seed, m='Stone', sub=2, rough=0.28, flat_bottom=None):
    """noise-displaced boulder centred at c with half-sizes `size`; darker in its hollows."""
    r = np.random.default_rng(seed)
    V, F = _ico(sub)
    dirs = r.normal(size=(5, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    fr = r.uniform(1.5, 4.0, 5); ph = r.uniform(0, 6.3, 5)
    n = sum(np.sin(fr[k] * (V @ dirs[k]) + ph[k]) for k in range(5)) / 5.0
    d = 1 + rough * n
    P = V * d[:, None] * np.asarray(size, float)
    if flat_bottom is not None: P[:, 2] = np.maximum(P[:, 2], flat_bottom)
    P += np.asarray(c, float)
    ao = np.clip(0.62 + 0.5 * (d - 1 + rough) / (2 * rough), 0.55, 1.0)
    return mesh(P, F, m, 'rock', ao=ao)

def worn_block(c, size, seed, m='Marble', sub=2, wear=0.16, chips=2, tilt=(0, 0, 0)):
    """ashlar block: chamfered box (flat faces) with a few chipped corners/edges, as a convex hull.
    c = centre, size = full extents (x, y, z); wear scales the chamfer."""
    from scipy.spatial import ConvexHull
    r = np.random.default_rng(seed)
    hx = np.asarray(size, float) / 2
    b = np.minimum(hx.min() * 0.9, 0.02 + wear * 0.35 * hx.min() * 2) * r.uniform(0.6, 1.2)
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                s_ = np.array([sx, sy, sz], float)
                for ax in range(3):
                    q = s_ * hx; q[ax] -= s_[ax] * b
                    pts.append(q)
    for ax in range(3):            # edge midpoints so long edges can take a chip
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                q = np.zeros(3); o = [i for i in range(3) if i != ax]
                q[o[0]] = s1 * (hx[o[0]] - b * 0.5); q[o[1]] = s2 * (hx[o[1]] - b * 0.5)
                for f in (-0.5, 0.0, 0.5):
                    q2 = q.copy(); q2[ax] = f * hx[ax] * 1.6; pts.append(q2)
    P = np.array(pts) * (1 + r.normal(size=(len(pts), 3)) * 0.01)
    for k in range(chips):
        sgn = r.choice([-1, 1], 3).astype(float); sgn[r.integers(3)] *= r.uniform(0.0, 0.6)
        nrm = sgn * r.uniform(0.5, 1.0, 3); nrm /= np.linalg.norm(nrm)
        off = float(np.abs(nrm) @ hx) * r.uniform(0.72, 0.9)
        proj = P @ nrm; cut = proj > off
        P[cut] -= np.outer(proj[cut] - off, nrm)
    hull = ConvexHull(P)
    F = [tuple(int(i) for i in t) for t in hull.simplices]
    # orient outward
    cen = P.mean(0); F2 = []
    for (i, j, k) in F:
        nn = np.cross(P[j] - P[i], P[k] - P[i])
        F2.append((i, j, k) if nn @ (P[i] - cen) > 0 else (i, k, j))
    used = sorted({i for f in F2 for i in f}); remap = {o: n_ for n_, o in enumerate(used)}
    V = P[used]; F2 = [tuple(remap[i] for i in f) for f in F2]
    ao = np.clip(0.82 + 0.18 * (np.abs(V / hx).max(1) > 0.97), 0.8, 1.0)
    ob = mesh(V, F2, m, 'blk', ao=ao)
    return apply(ob, tuple(c), tuple(math.radians(a) for a in tilt))

def sweep(path, prof, m, name='sweep', closed=True, frames=None):
    """sweep a 2-D profile (list of (side, up)) along a 3-D polyline (Blender coords). frames: optional (side, up) per point."""
    P = np.asarray(path, float); n = len(P); k = len(prof)
    V = []
    for i in range(n):
        if frames is not None: sd, up = frames[i]
        else:
            tg = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]; tg /= np.linalg.norm(tg)
            sd = np.cross(tg, [0, 0, 1.0]); sd /= np.linalg.norm(sd) + 1e-9
            up = np.cross(sd, tg)
        for (a, b) in prof: V.append(P[i] + sd * a + up * b)
    F = []
    for i in range(n - 1):
        for j in range(k if closed else k - 1):
            j2 = (j + 1) % k
            F.append((i * k + j, i * k + j2, (i + 1) * k + j2, (i + 1) * k + j))
    if closed:
        F.append(tuple(range(k - 1, -1, -1))); F.append(tuple((n - 1) * k + j for j in range(k)))
    return recalc(mesh(V, F, m, name))

def disc_uv(B, r0, r1, z, m, seg=48, cx=0.0, cy=0.0, scale=0.18):
    """flat annulus with planar UVs (u kept inside 0.25..0.75 so the flow shader draws no edge foam)."""
    rings = []; uvs = []
    for rr in (r0, r1):
        ring = []; uu = []
        for i in range(seg + 1):
            a = 2 * pi * i / seg
            x, y = cx + rr * cos(a), cy + rr * sin(a)
            ring.append((x, y, z)); uu.append((0.5 + x * scale * 0.5 / max(r1, 1), y * scale))
        rings.append(ring); uvs.append(uu)
    B.quad_strip(rings, uvs, m)

def poly_fill_uv(B, pts, z, m, scale=0.18):
    """fan-filled convex-ish polygon (list of (x, y)) at height z."""
    c = np.mean(np.asarray(pts, float), axis=0)
    for i in range(len(pts)):
        p0 = pts[i]; p1 = pts[(i + 1) % len(pts)]
        q = [(c[0], c[1], z), (p0[0], p0[1], z), (p1[0], p1[1], z), (c[0], c[1], z)]
        uv = [(0.5, c[1] * scale), (0.5 + p0[0] * scale * 0.04, p0[1] * scale), (0.5 + p1[0] * scale * 0.04, p1[1] * scale), (0.5, c[1] * scale)]
        base = sum(len(v) for v in B.V)
        B.V.append(np.array(q)); B.UV.append(np.array(uv)); mi = B.mat(m)
        B.F.append((base, base + 1, base + 2)); B.M.append(mi)

def ribbon(B, pts, width, m, u0=0.15, u1=0.85, vscale=0.5, crossed=False, side=None):
    """water ribbon along pts (Blender coords): flat strip (and optionally a second strip at 90 deg)."""
    P = np.asarray(pts, float); n = len(P)
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    w = np.broadcast_to(np.asarray(width, float), (n,))
    for rot in ((0, 1) if crossed else (0,)):
        rings = []; uvs = []
        for i in range(n):
            tg = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]; tg /= np.linalg.norm(tg) + 1e-9
            ref = np.array([0, 0, 1.0]) if abs(tg[2]) < 0.9 else np.array([1.0, 0, 0])
            sd = np.cross(tg, ref) if side is None else np.asarray(side, float)
            sd /= np.linalg.norm(sd) + 1e-9
            if rot: sd = np.cross(tg, sd); sd /= np.linalg.norm(sd) + 1e-9
            rings.append([P[i] - sd * w[i] / 2, P[i] + sd * w[i] / 2]); uvs.append([(u0, acc[i] * vscale), (u1, acc[i] * vscale)])
        B.quad_strip(rings, uvs, m)

def sheet(B, r_top, z_top, r_bot, z_bot, m, seg=48, arcs=6, n=10, cx=0.0, cy=0.0):
    """axisymmetric falling water curtain (overflow of a round bowl): parabola from (r_top, z_top) to (r_bot, z_bot)."""
    per = seg // arcs
    for a_ in range(arcs):
        rings = []; uvs = []
        for j in range(n + 1):
            t = j / n
            rr = r_top + (r_bot - r_top) * sqrt(t); z = z_top + (z_bot - z_top) * t * t
            ring = []; uu = []
            for i in range(per + 1):
                a = 2 * pi * (a_ * per + i) / seg
                ring.append((cx + rr * cos(a), cy + rr * sin(a), z)); uu.append((0.15 + 0.7 * i / per, t * (z_top - z_bot) * 0.6))
            rings.append(ring); uvs.append(uu)
        B.quad_strip(rings, uvs, m)

# =====================================================================================================
# 1. hall fountain: round basin, two tazze, jets (centre of every hall but the Colossus' and the cascade hall)
# =====================================================================================================
def hall_fountain():
    reset()
    parts = []
    # basin: plinth step, wall with a moulded lip, floor
    parts.append(K.lathe([(3.55, 0.0), (3.55, 0.14), (3.38, 0.14), (3.38, 0.2), (3.32, 0.26), (3.32, 0.5), (3.44, 0.54), (3.44, 0.64),
                          (3.38, 0.68), (3.0, 0.68), (3.0, 0.1), (0.001, 0.1)], 72, 'Marble', name='basin', cap_bottom=True, cap_top=False))
    parts.append(K.lathe([(3.335, 0.3), (3.345, 0.3), (3.345, 0.44), (3.335, 0.44)], 72, 'Verde', name='band', cap_top=False, cap_bottom=False))
    # pedestal + lower tazza + stem + upper tazza + finial
    parts.append(K.lathe([(0.62, 0.1), (0.62, 0.26), (0.5, 0.32), (0.36, 0.44), (0.26, 0.62), (0.22, 1.05), (0.3, 1.2), (0.34, 1.3),
                          (0.22, 1.4)], 40, 'Marble', name='ped', cap_top=False))
    parts.append(K.lathe([(0.22, 1.38), (0.7, 1.46), (1.25, 1.6), (1.55, 1.74), (1.62, 1.8), (1.62, 1.88), (1.5, 1.88), (1.1, 1.76),
                          (0.001, 1.72)], 64, 'Marble', name='tazza1', cap_bottom=False, cap_top=False))
    parts.append(K.lathe([(0.16, 1.72), (0.12, 2.0), (0.2, 2.15), (0.12, 2.3), (0.1, 2.52)], 24, 'Marble', name='stem', cap_bottom=False, cap_top=False))
    parts.append(K.lathe([(0.1, 2.5), (0.42, 2.56), (0.72, 2.7), (0.8, 2.76), (0.8, 2.82), (0.72, 2.82), (0.001, 2.74)], 48, 'Marble', name='tazza2', cap_bottom=False, cap_top=False))
    parts.append(K.lathe([(0.001, 2.74), (0.12, 2.78), (0.15, 2.9), (0.1, 3.02), (0.05, 3.1), (0.001, 3.12)], 16, 'Gold', name='finial', cap_bottom=False, cap_top=False))
    # four bronze dolphin-head spouts on the basin rim, facing the centre
    spouts = []
    for k in range(4):
        a = pi / 4 + k * pi / 2
        sp = K.lathe([(0.001, 0.0), (0.09, 0.03), (0.12, 0.12), (0.1, 0.24), (0.06, 0.3), (0.04, 0.34), (0.001, 0.35)], 12, 'Gold', name='spout')
        sp = apply(sp, (0, 0, 0), (pi / 2 - 0.35, 0, 0))                      # lying, nose toward -y, tilted up
        sp = apply(sp, (cos(a) * 3.28, sin(a) * 3.28, 0.66), (0, 0, a - pi / 2))
        parts.append(sp)
        spouts.append(a)
    finish(parts, 'HallFountain')
    # water: pool surface, bowl surfaces, overflow curtains, jet, rim spouts
    B = NA.Builder()
    disc_uv(B, 0.62, 3.0, 0.46, 'Pool')
    W = NA.Builder()
    for (r0, r1, z) in ((0.24, 1.5, 1.82), (0.12, 0.74, 2.78)):
        disc_uv(W, r0, r1, z, 'Flow', seg=40, scale=0.4)
    sheet(W, 1.64, 1.86, 1.98, 0.47, 'Flow', arcs=8)
    sheet(W, 0.82, 2.8, 1.08, 1.83, 'Flow', arcs=6)
    jet = [(0, 0, 3.05 + 0.08 * k) for k in range(9)]
    ribbon(W, jet, np.linspace(0.07, 0.16, 9), 'Flow', crossed=True, vscale=1.5)
    crown = []
    for k in range(6):                 # the jet's crown falling back into the upper bowl
        a = k * pi / 3
        crown.append([(cos(a) * 0.45 * t, sin(a) * 0.45 * t, 3.7 - 0.95 * t * t) for t in np.linspace(0, 1, 8)])
    for c in crown: ribbon(W, c, np.linspace(0.12, 0.05, 8), 'Flow', crossed=True, vscale=1.2)
    for a in spouts:
        x0, y0 = cos(a) * 3.05, sin(a) * 3.05
        arc = [(x0 - cos(a) * 1.4 * t, y0 - sin(a) * 1.4 * t, 0.78 + 0.35 * t - 0.68 * t * t) for t in np.linspace(0, 1, 10)]
        ribbon(W, arc, np.linspace(0.06, 0.1, 10), 'Flow', crossed=True, vscale=1.0)
    uv_export(B, 'HallFountainPool', {'Pool': POOL})
    uv_export(W, 'HallFountainWater', {'Flow': FLOW})
    EXTRA['hall_fountain'] = dict(r=3.55, pool=0.46)

# =====================================================================================================
# 2. the Trevi wall fountain for the Colossus' hall: frontispiece with a niche, rock-work, D-shaped pool
#    (side-module frame: inner wall face at y = 10, room toward -y)
# =====================================================================================================
def trevi():
    reset()
    parts = []
    # central bay (projects 1.8 m) with a deep round-headed niche; wings (0.7 m) with small niches
    cb = K.box(-3.3, 3.3, 8.2, 10.0, 0.0, 10.6, 'Marble', 'bay')
    K.boolean(cb, [K.arch_prism(3.2, 6.4, 0, 8.1, 9.65, z0=2.3, name='niche')])
    parts.append(cb)
    for sx in (-1, 1):
        w = K.box(min(3.3 * sx, 6.6 * sx), max(3.3 * sx, 6.6 * sx), 9.3, 10.0, 0.0, 10.6, 'Marble', 'wing')
        K.boolean(w, [K.arch_prism(1.5, 4.9, 4.95 * sx, 9.2, 9.75, z0=3.2, name='sn')])
        parts.append(w)
        parts.append(K.arch_molding(1.5, 4.9, 4.95 * sx, 9.3, 0.12, 0.18, m='Marble', name='snm', legs_to=3.2))
        parts.append(K.box(4.95 * sx - 0.95, 4.95 * sx + 0.95, 9.05, 9.3, 2.95, 3.2, 'Marble', 'snsill'))
        # paired columns on the bay front, pilasters on the wing ends
        for xc in (2.15, 2.95):
            parts += half_column(xc * sx, 8.2, 2.3, 10.2, 0.32, 'Marble')
        parts.append(K.box(6.0 * sx - 0.35, 6.0 * sx + 0.35, 9.12, 9.3, 2.3, 10.2, 'Marble', 'pil'))
    parts.append(K.arch_molding(3.2, 6.4, 0, 8.2, 0.16, 0.3, m='Marble', name='nm', legs_to=2.3))
    parts.append(K.box(-0.32, 0.32, 7.98, 8.25, 7.55, 8.35, 'Gold', 'key'))
    # half-dome shell (scalloped conch) in the niche head
    for k in range(9):
        a0 = pi * k / 9; a1 = pi * (k + 1) / 9
        V = [(0, 9.62, 6.4)]
        for a in np.linspace(a0, a1, 4): V.append((1.55 * cos(a), 9.62 - 0.28 * sin(pi * (a - a0) / (a1 - a0)), 6.4 + 1.55 * sin(a)))
        F = [(0, i + 1, i + 2) for i in range(3)]
        parts.append(recalc(mesh(V, F + [tuple(reversed(f)) for f in F], 'Gold' if k % 2 else 'Marble', 'conch')))
    # entablature + blank gold plaque on the attic
    for (x0, x1, y0) in ((-3.45, 3.45, 8.0), (-6.75, -3.3, 9.1), (3.3, 6.75, 9.1)):
        parts.append(K.box(x0, x1, y0, 10.0, 10.2, 10.65, 'Marble', 'arch'))
        parts.append(K.box(x0, x1, y0 + 0.08, 10.0, 10.65, 11.15, 'Wall', 'frieze'))
        parts.append(K.box(x0 - 0.12, x1 + 0.12, y0 - 0.18, 10.0, 11.15, 11.45, 'Marble', 'corn'))
    parts.append(K.box(-2.2, 2.2, 7.9, 8.0, 10.72, 11.08, 'Gold', 'plaque'))
    parts.append(K.box(-2.3, 2.3, 7.95, 8.02, 10.68, 11.12, 'Marble', 'plaquefr'))
    # rock-work (scogliera) across the front, stepping down to the pool
    rocks = []
    for k in range(34):
        x = rng.uniform(-6.6, 6.6); y = rng.uniform(7.0, 9.4)
        hgt = (2.4 - abs(x) * 0.18) * (y - 6.4) / 3.0 + rng.uniform(-0.3, 0.3)
        if abs(x) < 1.7: hgt = min(hgt, 1.7)          # keep the central cascade channel open
        s = rng.uniform(0.45, 0.95)
        rocks.append(rock((x, y, max(0.25, hgt * 0.6)), (s, s * rng.uniform(0.7, 1.0), max(0.35, hgt * 0.55)), 900 + k, 'Stone', flat_bottom=-0.02 - max(0.25, hgt * 0.6)))
    # cascade steps (three rough terraces)
    for (y0, y1, z, wdt) in ((8.25, 9.7, 2.3, 1.7), (7.75, 8.3, 1.55, 1.9), (7.25, 7.8, 0.9, 2.1)):
        parts.append(rock((0, (y0 + y1) / 2, z - 0.25), (wdt, (y1 - y0) / 2 + 0.1, 0.3), int(z * 100), 'Stone', sub=2, rough=0.12, flat_bottom=-z + 0.2))
    parts += rocks
    for sx in (-1, 1):     # rough plinths the two sea-horses rear on
        parts.append(rock((4.3 * sx, 7.75, 0.55), (0.95, 0.75, 0.6), 990 + sx, 'Stone', rough=0.16, flat_bottom=-0.55))
    # D-shaped pool rim: straight back at y=8.6, front arc to y=5.4
    def outline(off):
        pts = [(-6.7 - off, 8.6), (-6.7 - off, 7.0)]
        for a in np.linspace(pi, 2 * pi, 33)[1:-1]:
            pts.append(((6.7 + off) * cos(a), 7.0 + (1.6 + off) * sin(a)))
        pts += [(6.7 + off, 7.0), (6.7 + off, 8.6)]
        return pts
    outer = outline(0.42); inner = outline(0.0)
    rim = prism_xy(outer + inner[::-1], 0.0, 0.6, 'Marble', 'rim')
    parts.append(rim)
    parts.append(prism_xy(outline(0.55), 0.0, 0.14, 'Marble', 'rimstep'))
    parts.append(prism_xy(inner, 0.0, 0.06, 'Marble', 'poolfloor'))
    finish(parts, 'Trevi')
    # water: pool surface, cascade sheets over the three terraces, side spouts from the wing niches, a shell spill
    B = NA.Builder(); poly_fill_uv(B, inner, 0.42, 'Pool'); uv_export(B, 'TreviPool', {'Pool': POOL})
    W = NA.Builder()
    for (ya, za, yb, zb, wd) in ((9.6, 2.36, 8.3, 1.62, 1.5), (8.25, 1.62, 7.8, 0.96, 1.75), (7.75, 0.96, 7.1, 0.44, 1.95)):
        pts = [(0, ya + (yb - ya) * t, za + (zb - za) * t ** 1.6) for t in np.linspace(0, 1, 9)]
        ribbon(W, pts, wd, 'Flow', side=(1, 0, 0), vscale=0.8)
    for sx in (-1, 1):
        x = 4.95 * sx
        arc = [(x, 9.35 - 1.8 * t, 3.4 - 2.95 * t * t) for t in np.linspace(0, 1, 12)]
        ribbon(W, arc, np.linspace(0.12, 0.22, 12), 'Flow', crossed=True, vscale=0.8)
    shell = [(0, 9.55 - 0.25 * t, 3.05 - 0.7 * t * t) for t in np.linspace(0, 1, 6)]
    ribbon(W, shell, 1.1, 'Flow', side=(1, 0, 0), vscale=0.8)
    uv_export(W, 'TreviWater', {'Flow': FLOW})
    # the shell basin the central figure stands over
    reset()
    sh = K.lathe([(0.001, 0.0), (0.5, 0.05), (0.9, 0.2), (1.0, 0.32), (0.92, 0.36), (0.001, 0.26)], 24, 'Gold', name='shell',
                 radial=lambda t, z, r: r * (1 - 0.08 * abs(sin(t * 6))), cap_top=False, cap_bottom=False)
    sh = apply(sh, (0, 9.1, 2.55), (0, 0, 0), (1.0, 0.55, 1.0))
    finish([sh], 'TreviShell')
    EXTRA['trevi'] = dict(statue=[0.0, 2.75, 9.05], horses=[[-4.3, 1.08, 7.75], [4.3, 1.08, 7.75]], spouts=[[-4.95, 3.4, 9.35], [4.95, 3.4, 9.35]])

# =====================================================================================================
# 3. the open marble tower: arches on every face, inner helical stair, marble slide corkscrewing inside,
#    roof terrace with a tempietto. Frame: house wall at y=0, tower centre (0, 6.5), outward = +y.
# =====================================================================================================
TW = dict(half=6.5, cy=6.5, top=27.0, stair_r=(0.9, 3.6), turns=3, slide_r=4.55, slide_hw=0.72, slide_turns=3.25,
          slide_top=27.35, slide_bottom=1.05, phi_stair_top=90.0, phi_slide_start=270.0)

def tower_slide_path():
    """slide centreline in tower-local Blender coords (x, y, z): helix descending clockwise (decreasing phi), then a
    run out of the south arch into the water."""
    t = TW; cy = t['cy']
    total = t['slide_turns'] * 2 * pi
    phi0 = math.radians(t['phi_slide_start'])
    pts = []
    # level launch on the terrace
    for k in range(4):
        a = phi0 + math.radians(12) * (3 - k) / 3 * 0.0
        pts.append(np.array([t['slide_r'] * cos(phi0) + (3 - k) * 0.25, cy + t['slide_r'] * sin(phi0), t['slide_top'] + 0.05 * (3 - k)]))
    n = 260
    for i in range(1, n + 1):
        f = i / n
        phi = phi0 - total * f
        z = t['slide_top'] - (t['slide_top'] - t['slide_bottom']) * (f * 0.92 + 0.08 * f * f)
        pts.append(np.array([t['slide_r'] * cos(phi), cy + t['slide_r'] * sin(phi), z]))
    # end of helix at phi = 180 (x = -r), heading +y; ease inward and out through the south arch
    end = pts[-1]
    for k in range(1, 15):
        s = k / 14
        x = -t['slide_r'] + 2.1 * (3 * s * s - 2 * s * s * s)
        y = end[1] + s * 10.5
        z = t['slide_bottom'] - 0.75 * s ** 1.3
        pts.append(np.array([x, y, z]))
    P = np.array(pts)
    # resample at ~0.6 m
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]
    s = np.linspace(0, cum[-1], int(cum[-1] / 0.6) + 1)
    out = np.stack([np.interp(s, cum, P[:, j]) for j in range(3)], 1)
    return out, cum[-1]

def tower3():
    reset()
    t = TW; h = t['half']; cy = t['cy']; H = 26.2
    parts = []
    shell = K.box(-h, h, 0, 2 * h, -3.0, H, 'Wall', 'shell')
    cuts = [K.box(-h + 1.0, h - 1.0, 1.0, 2 * h - 1.0, 0.0, H + 0.2, 'Wall', 'inner')]
    for ax in ('x', 'y'):
        # lower storey: one great arch per face (10 m, spring 7 -> crown 12), upper: two tall arches + oculus
        if ax == 'x':
            cuts.append(K.arch_prism(10.0, 7.0, 0, -0.2, 2 * h + 0.2, z0=0.0, name='lo'))
            for xc in (-2.65, 2.65): cuts.append(K.arch_prism(3.5, 21.4, xc, -0.2, 2 * h + 0.2, z0=13.9, name='hi'))
        else:
            cuts.append(K.arch_prism(10.0, 7.0, cy, -h - 0.2, h + 0.2, z0=0.0, axis='y', name='lo'))
            for yc in (cy - 2.65, cy + 2.65): cuts.append(K.arch_prism(3.5, 21.4, yc, -h - 0.2, h + 0.2, z0=13.9, axis='y', name='hi'))
    K.boolean(shell, cuts)
    parts.append(shell)
    parts.append(K.box(-h + 1.0, h - 1.0, 1.0, 2 * h - 1.0, -3.0, 0.0, 'Floor', 'floor'))
    parts.append(K.box(-h, h, 0, 2 * h, -3.0, -0.02, 'Floor', 'floorx'))
    # outside dressing on every face: rusticated plinth, archivolts, keystones, string course, pilasters, cornice
    def face(fn):
        out = []
        for k in range(4):
            ps = fn()
            for p in ps:
                out.append(apply(p, (0, cy, 0), (0, 0, k * pi / 2)))
        return out
    def face_parts():
        ps = []
        y = -h  # face plane in tower-centred coords (front = -y), built then rotated about the centre and moved by cy
        for sx in (-1, 1):
            lo, hi = (5.0, h + 0.05) if sx > 0 else (-h - 0.05, -5.0)
            ps.append(K.box(lo, hi, y - 0.3, y, -1.2, 1.4, 'Stone', 'rust'))
            ps.append(K.box(lo, hi, y - 0.38, y, 1.4, 1.62, 'Marble', 'rustcap'))
            ps.append(K.box(5.75 * sx - 0.5, 5.75 * sx + 0.5, y - 0.25, y, 1.62, 12.4, 'Marble', 'pil'))
            ps.append(K.box(5.75 * sx - 0.6, 5.75 * sx + 0.6, y - 0.35, y, 11.95, 12.45, 'Marble', 'pilcap'))
            ps.append(K.box(5.75 * sx - 0.5, 5.75 * sx + 0.5, y - 0.25, y, 13.6, 25.2, 'Marble', 'pil2'))
            ps.append(K.box(5.75 * sx - 0.6, 5.75 * sx + 0.6, y - 0.35, y, 24.8, 25.3, 'Marble', 'pil2cap'))
            # gilded roundel in each spandrel of the great arch
            rd = K.lathe([(0.001, 0.0), (0.55, 0.0), (0.6, 0.06), (0.55, 0.12), (0.001, 0.12)], 24, 'Gold', name='roundel')
            ps.append(apply(rd, (4.55 * sx, y, 11.15), (pi / 2, 0, 0)))
        ps.append(apply(K.arch_molding(10.0, 7.0, 0, 0.0, 0.25, 0.45, m='Marble', name='av', legs_to=1.62), (0, y, 0)))
        ps.append(K.box(-0.45, 0.45, y - 0.35, y + 0.05, 11.5, 12.8, 'Gold', 'key'))
        for xc in (-2.65, 2.65):
            ps.append(apply(K.arch_molding(3.5, 21.4, xc, 0.0, 0.2, 0.3, m='Marble', name='av2', legs_to=13.9), (0, y, 0)))
            ps.append(K.box(xc - 2.0, xc + 2.0, y - 0.25, y + 0.9, 13.65, 13.9, 'Marble', 'sill'))
            ps += balustrade_x(xc - 1.7, xc + 1.7, y + 0.5, 13.9, h=0.95, depth=0.36)
        # string course + cornice + dentils
        ps.append(K.box(-h - 0.05, h + 0.05, y - 0.32, y, 12.75, 13.15, 'Marble', 'sc1'))
        ps.append(K.box(-h - 0.05, h + 0.05, y - 0.42, y, 13.15, 13.45, 'Marble', 'sc2'))
        ps.append(K.box(-h - 0.1, h + 0.1, y - 0.25, y, 25.3, 25.7, 'Marble', 'arch'))
        ps += dentils(-h, h, y - 0.38, 25.7, 25.9, 'Marble', 0.34, 0.17, 0.2)
        ps.append(K.box(-h - 0.25, h + 0.25, y - 0.55, y, 25.9, 26.2, 'Marble', 'corona'))
        return [p for p in ps if p is not None]
    parts += face(face_parts)
    # spandrel roundels above the great arches (gold)
    # roof terrace slab with the stair hatch and the slide slot cut out
    slab = K.box(-h, h, 0, 2 * h, H, H + 0.8, 'Floor', 'terrace')
    def sector(r0, r1, a0, a1, z0, z1, n=24):
        pts = [(r1 * cos(a), cy + r1 * sin(a)) for a in np.linspace(a0, a1, n)] + [(r0 * cos(a), cy + r0 * sin(a)) for a in np.linspace(a1, a0, n)]
        return prism_xy(pts, z0, z1, 'Wall', 'sec')
    st0 = math.radians(t['phi_stair_top'])
    sl0 = math.radians(t['phi_slide_start'])
    K.boolean(slab, [sector(t['stair_r'][0] - 0.02, t['stair_r'][1] + 0.12, st0 - math.radians(118), st0 + 0.02, H - 0.2, H + 1.0),
                     sector(t['slide_r'] - t['slide_hw'] - 0.25, t['slide_r'] + t['slide_hw'] + 0.3, sl0 - math.radians(125), sl0 + math.radians(14), H - 0.2, H + 1.0)])
    parts.append(slab)
    # terrace balustrade with corner pedestals + urns
    for k in range(4):
        bal = balustrade_x(-h + 0.6, h - 0.6, -h + 0.25, H + 0.8, posts=[-3.0, 3.0], h=1.05)
        for p in bal: parts.append(apply(p, (0, cy, 0), (0, 0, k * pi / 2)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(K.box(sx * h - 0.62 if sx > 0 else -h, h if sx > 0 else -h + 0.62, cy + sy * h - 0.62 if sy > 0 else cy - h,
                               cy + h if sy > 0 else cy - h + 0.62, H + 0.8, H + 2.2, 'Marble', 'cped'))
            parts.append(urn(sx * (h - 0.31), cy + sy * (h - 0.31), H + 2.2, 1.1))
    # guard rails around the stair hatch
    for a in np.linspace(st0 - math.radians(118), st0, 9):
        parts.append(cyl((t['stair_r'][1] + 0.2) * cos(a), cy + (t['stair_r'][1] + 0.2) * sin(a), H + 0.8, H + 1.85, 0.05, 'Iron', 8, 'rail'))
    rail = [((t['stair_r'][1] + 0.2) * cos(a), cy + (t['stair_r'][1] + 0.2) * sin(a), H + 1.85) for a in np.linspace(st0 - math.radians(118), st0, 20)]
    parts.append(sweep(rail, [(-0.04, -0.04), (0.04, -0.04), (0.04, 0.04), (-0.04, 0.04)], 'Iron', 'railtop'))
    # tempietto: 8 columns, ring entablature, ogee dome with ribs, lantern + gilded pine cone
    Rc = 5.85
    for k in range(8):
        a = pi / 8 + k * pi / 4
        x, y = Rc * cos(a), cy + Rc * sin(a)
        col = K.lathe([(0.36, 0.0), (0.36, 0.14), (0.3, 0.24), (0.27, 0.32), (0.22, 4.9), (0.26, 5.05), (0.32, 5.25), (0.38, 5.4)], 20, 'Marble', name='tcol')
        parts.append(apply(col, (x, y, H + 0.8)))
    zt = H + 0.8 + 5.4
    parts.append(K.lathe([(Rc - 0.6, zt), (Rc + 0.55, zt), (Rc + 0.55, zt + 0.55), (Rc + 0.75, zt + 0.7), (Rc + 0.75, zt + 0.95),
                          (Rc - 0.6, zt + 0.95)], 64, 'Marble', name='tent'))
    parts[-1] = apply(parts[-1], (0, cy, 0))
    prof_o = [(6.35, zt + 0.95), (6.2, zt + 1.6), (5.6, zt + 2.6), (4.4, zt + 3.5), (3.0, zt + 4.2), (1.8, zt + 4.8), (0.9, zt + 5.4), (0.55, zt + 5.9)]
    prof_i = [(0.5, zt + 5.6), (1.6, zt + 4.6), (2.8, zt + 3.9), (4.1, zt + 3.2), (5.2, zt + 2.3), (5.5, zt + 1.3), (5.3, zt + 0.95)]
    dome = K.lathe(prof_o + prof_i, 48, 'Marble', name='tdome', cap_top=False, cap_bottom=False)
    parts.append(apply(recalc(dome), (0, cy, 0)))
    for k in range(16):
        a = 2 * pi * k / 16
        rib = [((r + 0.12) * cos(a), cy + (r + 0.12) * sin(a), z) for (r, z) in prof_o[:-1]]
        parts.append(sweep(rib, [(-0.09, 0.0), (0.09, 0.0), (0.06, 0.12), (-0.06, 0.12)], 'Gold' if k % 4 == 0 else 'Marble', 'trib'))
    parts.append(apply(K.lathe([(0.55, zt + 5.9), (0.55, zt + 6.9), (0.7, zt + 7.0), (0.001, zt + 7.05)], 16, 'Marble', name='tlant'), (0, cy, 0)))
    for k in range(6):
        a = 2 * pi * k / 6
        parts.append(cyl(0.62 * cos(a), cy + 0.62 * sin(a), zt + 5.9, zt + 6.9, 0.06, 'Marble', 8, 'lc'))
    parts.append(apply(K.lathe([(0.001, zt + 7.0), (0.28, zt + 7.2), (0.3, zt + 7.55), (0.18, zt + 7.95), (0.001, zt + 8.3)], 16, 'Gold', name='cone'), (0, cy, 0)))
    EXTRA['tower3_top'] = zt + 8.3
    # helical stair (CCW up), newel
    r0, r1 = t['stair_r']; steps = 135; rise = t['top'] / steps
    phiB = math.radians(t['phi_stair_top']) - t['turns'] * 2 * pi
    dA = t['turns'] * 2 * pi / steps
    for i in range(steps):
        a0 = phiB + i * dA; a1 = a0 + dA * 1.04; z = (i + 1) * rise + (0.8 if i == steps - 1 else 0) * 0
        V = []
        for (r, a) in [(r0, a0), (r1, a0), (r1, a1), (r0, a1)]: V.append((r * cos(a), cy + r * sin(a), z - rise - 0.16))
        for (r, a) in [(r0, a0), (r1, a0), (r1, a1), (r0, a1)]: V.append((r * cos(a), cy + r * sin(a), z))
        F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        parts.append(mesh(V, F, 'Marble', 'step'))
    # top landing step up to the terrace level
    parts.append(apply(K.lathe([(r0, 0.0), (r0, H + 0.8)], 24, 'Marble', name='newel'), (0, cy, 0)))
    parts.append(apply(K.lathe([(r0 + 0.12, 0.0), (r0 + 0.12, 0.35), (r0, 0.45)], 24, 'Marble', name='newelbase', cap_top=False), (0, cy, 0)))
    # stair hand rail on the outer edge (iron, follows the helix)
    rail = []
    for i in range(0, steps * 4 + 1):
        a = phiB + i * dA / 4; z = i / 4 * rise + 1.0
        rail.append(((r1 + 0.05) * cos(a), cy + (r1 + 0.05) * sin(a), z))
    parts.append(sweep(rail, [(-0.03, -0.03), (0.03, -0.03), (0.03, 0.03), (-0.03, 0.03)], 'Iron', 'srail'))
    for i in range(0, steps, 3):
        a = phiB + (i + 0.5) * dA; z = (i + 1) * rise
        parts.append(cyl((r1 + 0.05) * cos(a), cy + (r1 + 0.05) * sin(a), z, z + 1.0, 0.02, 'Iron', 6, 'baluster'))
    # the marble slide: a helicoid trough with a solid underside, carried on corbels from the piers and colonnettes
    path, L = tower_slide_path()
    rr = 0.72
    prof = [(-rr - 0.14, 0.42), (-rr - 0.14, -0.75), (rr + 0.14, -0.75), (rr + 0.14, 0.42), (rr + 0.02, 0.42)]
    prof += [(rr * cos(a), rr * sin(a) * 0.82) for a in np.linspace(0, -pi, 15)]
    prof += [(-rr - 0.02, 0.42)]
    frames = []
    for i in range(len(path)):
        tg = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]; tg /= np.linalg.norm(tg)
        sd = np.cross(tg, [0, 0, 1.0]); sd /= np.linalg.norm(sd)
        frames.append((sd, np.array([0, 0, 1.0])))
    trough = [(p + np.array([0, 0, 0.42])) for p in path]
    parts.append(sweep(trough, prof, 'Marble', 'trough', frames=frames))
    # gilded lip line
    for sgn in (-1, 1):
        lip = [p + np.array([0, 0, 0.86]) + f[0] * sgn * (rr + 0.08) for p, f in zip(path, frames)]
        parts.append(sweep(lip[::2], [(-0.07, -0.02), (0.07, -0.02), (0.07, 0.03), (-0.07, 0.03)], 'Gold', 'lip'))
    # colonnettes: from the outer wall of each turn down to the outer wall of the turn below (or the floor)
    PH = np.array(path)
    for i in range(0, len(path) - 18, 9):
        p = PH[i]
        if p[2] < 2.0: continue
        rad = np.array([p[0], p[1] - cy, 0.0]); rad /= np.linalg.norm(rad) + 1e-9
        q = p + rad * 0.79
        d = np.hypot(PH[:, 0] + rad[0] * 0.79 - q[0], PH[:, 1] + rad[1] * 0.79 - q[1])
        cand = [j for j in range(len(PH)) if d[j] < 0.45 and 1.5 < p[2] - PH[j, 2] < 12.0]
        zb = max(PH[j, 2] for j in cand) + 0.84 if cand else 0.0
        zt = p[2] + 0.42 - 0.75
        if zt - zb < 1.0: continue
        col = K.lathe([(0.16, zb), (0.16, zb + 0.16), (0.1, zb + 0.28), (0.085, zt - 0.3), (0.15, zt - 0.16), (0.19, zt)], 10, 'Marble', name='coln')
        parts.append(apply(col, (q[0], q[1], 0)))
    finish(parts, 'Tower3')
    # slide water
    W = NA.Builder()
    wr = []; wu = []; acc = 0.0
    for i, (p, f) in enumerate(zip(path, frames)):
        if i: acc += float(np.linalg.norm(path[i] - path[i - 1]))
        q = p + np.array([0, 0, 0.42 - rr * 0.82 + 0.1])
        wr.append([q - f[0] * 0.48, q + f[0] * 0.48]); wu.append([(0.12, acc / 4), (0.88, acc / 4)])
    W.quad_strip(wr, wu, 'Flow')
    uv_export(W, 'Tower3SlideWater', {'Flow': FLOW})
    # ride spline: rider sits on the trough floor
    ride = [p + np.array([0, 0, 0.42 - rr * 0.82 + 0.08]) for p in path]
    EXTRA['tower3_ride'] = [[round(float(q[0]), 3), round(float(q[1]), 3), round(float(q[2]), 3)] for q in ride]   # blender local
    EXTRA['tower3'] = dict(TW, length=round(float(L), 1))
    print('tower3 slide length', round(L, 1), 'points', len(path))

# =====================================================================================================
# 4. sea hall (reached from the corner exit of hall 2,0) and the isle halls
#    frame: entrance on the y = 0 face, hall runs toward +y; floor at z = 0
# =====================================================================================================
def roof_shell(R, spring, y0, y1, holes=(), m='Wall', nu=29, step=0.75):
    """outer barrel roof (radius R about z = spring, along y) with round holes (y, r) open to the sky + wells + curbs."""
    ys = np.unique(np.r_[np.arange(y0, y1, step), y1, [h_[0] + d for h_ in holes for d in np.linspace(-h_[1] - 0.6, h_[1] + 0.6, 9)]])
    ys = ys[(ys >= y0) & (ys <= y1)]
    V = []; keep = []
    for y in ys:
        for k in range(nu):
            a = pi * k / (nu - 1); x = -R * cos(a); z = spring + R * sin(a)
            V.append((x, y, z)); keep.append(not any((y - yo) ** 2 + x * x < (ro + 0.15) ** 2 for yo, ro in holes))
    keep = np.array(keep).reshape(len(ys), nu)
    F = [(j * nu + i, j * nu + i + 1, (j + 1) * nu + i + 1, (j + 1) * nu + i) for j in range(len(ys) - 1) for i in range(nu - 1)
         if keep[j, i] and keep[j, i + 1] and keep[j + 1, i] and keep[j + 1, i + 1]]
    parts = [mesh(V, F, m, 'roof', smooth=True)]
    for yo, ro in holes:
        parts.append(apply(K.lathe([(ro, spring + R - 2.0), (ro, spring + R + 0.35)], 32, 'Marble', name='well', cap_top=False, cap_bottom=False), (0, yo, 0)))
        parts.append(apply(K.lathe([(ro, spring + R + 0.35), (ro + 0.7, spring + R + 0.35), (ro + 0.7, spring + R + 0.8), (ro, spring + R + 0.8)], 32, 'Marble',
                                   name='curb', cap_top=False, cap_bottom=False), (0, yo, 0)))
    return parts

def hall_block(Wd, Ln, Hw, door, wins, name, rear_window=True, stairs=True, lod=False, coffer=True):
    """generic classical hall. Wd/Ln = outer width/length, Hw = wall height, door = (w, spring), wins = (n, w, spring, z0).
    Entrance on the y = 0 face, hall runs toward +y, floor at z = 0."""
    reset()
    LOD[0] = lod
    t = 1.5 if Wd > 16 else 1.1
    X = Wd / 2; hw = X - t
    parts = []
    body = K.box(-X, X, 0, Ln, -4.0, Hw, 'Wall', 'body')
    cuts = [K.box(-hw, hw, t, Ln - t, 0.0, Hw + 0.2, 'Wall', 'room'), K.arch_prism(door[0], door[1], 0, -0.2, t + 0.2, z0=0.0, name='door')]
    n, ww, wsp, wz0 = wins
    wy = [t + (Ln - 2 * t) * (k + 0.5) / n for k in range(n)]
    for y in wy:
        cuts.append(K.arch_prism(ww, wsp, y, -X - 0.2, X + 0.2, z0=wz0, axis='y', name='win'))
    zw = Hw * 0.62; rw = min(3.4, Wd * 0.18)
    if rear_window:
        th = np.linspace(0, 2 * pi, 40, endpoint=False)
        cuts.append(prism_xz([(rw * cos(a), zw + rw * sin(a)) for a in th], Ln - t - 0.2, Ln + 0.2, 'Wall', 'rose'))
    K.boolean(body, cuts)
    parts.append(body)
    parts.append(K.box(-hw, hw, t, Ln - t, -4.0, 0.0, 'Floor', 'floor'))
    if rear_window:
        ring = K.lathe([(rw, 0.0), (rw + 0.35, 0.0), (rw + 0.4, 0.15), (rw, 0.15)], 48, 'Marble', name='rring', cap_top=False, cap_bottom=False)
        parts.append(apply(ring, (0, Ln - t, zw), (pi / 2, 0, 0)))
        parts.append(K.box(-0.06, 0.06, Ln - t * 0.5 - 0.05, Ln - t * 0.5 + 0.05, zw - rw, zw + rw, 'Iron', 'rm1'))
        parts.append(K.box(-rw, rw, Ln - t * 0.5 - 0.05, Ln - t * 0.5 + 0.05, zw - 0.06, zw + 0.06, 'Iron', 'rm2'))
        gl = prism_xz([(rw * cos(a), zw + rw * sin(a)) for a in np.linspace(0, 2 * pi, 40, endpoint=False)], Ln - t * 0.5 - 0.01, Ln - t * 0.5 + 0.01, 'Glass2', 'rglass')
        parts.append(gl)
    # interior: pilasters between the windows, gilded cornice, coffered barrel vault with an oculus
    piers = [t + 0.45] + [(wy[k] + wy[k + 1]) / 2 for k in range(n - 1)] + [Ln - t - 0.45]
    for y in piers:
        for sx in (-1, 1):
            lo, hi = (hw - 0.4, hw) if sx > 0 else (-hw, -hw + 0.4)
            parts.append(K.box(lo, hi, y - 0.45, y + 0.45, 0, Hw - 1.0, 'Marble', 'ipil'))
            parts.append(K.box(lo - (0.1 if sx > 0 else 0), hi + (0.1 if sx < 0 else 0), y - 0.55, y + 0.55, 0, 0.35, 'Marble', 'ipilb'))
    for sx in (-1, 1):
        lo, hi = (hw - 0.6, hw) if sx > 0 else (-hw, -hw + 0.6)
        parts.append(K.box(lo, hi, t, Ln - t, Hw - 1.0, Hw - 0.55, 'Marble', 'icorn'))
        lo, hi = (hw - 0.35, hw) if sx > 0 else (-hw, -hw + 0.35)
        parts.append(K.box(lo, hi, t, Ln - t, Hw - 0.55, Hw - 0.4, 'Gold', 'igold'))
    oc = (Ln / 2, min(1.8, hw * 0.3))
    parts.append(K.barrel_vault(hw, Hw, t, Ln - t, 'Marble', coffer=coffer and not lod, ribs=[(y, 0.6) for y in piers[1:-1]], oculi=[oc], name='vault', extrados=False))
    parts.append(K.oculus_ring(oc[1], Hw + hw, oc[0], 'Gold', 'ocring'))
    parts += roof_shell(hw + 0.9, Hw, t - 0.6, Ln - t + 0.6, holes=[oc])
    for y0, y1 in ((t - 0.6, t + 0.01), (Ln - t - 0.01, Ln - t + 0.6)):
        parts.append(prism_xz([((hw + 0.35) * cos(a), Hw + (hw + 0.35) * sin(a)) for a in np.linspace(0, pi, 33)], y0, y1, 'Wall', 'lun'))
    # exterior: rusticated plinth, pilasters, cornice, balustrade, pediments, door frame
    for sx in (-1, 1):
        lo, hi = (X, X + 0.3) if sx > 0 else (-X - 0.3, -X)
        parts.append(K.box(lo, hi, -0.3, Ln + 0.3, -4.0, 1.4, 'Stone', 'rust'))
        for y in [0.6] + piers[1:-1] + [Ln - 0.6]:
            parts.append(K.box(lo, hi, y - 0.5, y + 0.5, 1.4, Hw - 1.0, 'Marble', 'epil'))
    # front: corner pilasters and, on the wide halls, blind niches with shells between them and the door columns
    for sx in (-1, 1):
        parts.append(K.box(sx * (X - 0.6) - 0.5, sx * (X - 0.6) + 0.5, -0.3, 0.0, 1.4, Hw - 1.0, 'Marble', 'fpil'))
        if X - door[0] / 2 > 6.0:
            xn = sx * (door[0] / 2 + 1.25 + X - 0.6) / 2 + sx * 0.3
            parts.append(K.arch_molding(2.0, Hw * 0.36, xn, -0.0, 0.2, 0.3, m='Marble', name='fn', legs_to=Hw * 0.12))
            parts.append(K.box(xn - 1.25, xn + 1.25, -0.45, 0.0, Hw * 0.12 - 0.3, Hw * 0.12, 'Marble', 'fnsill'))
            parts.append(K.box(xn - 1.05, xn + 1.05, -0.25, 0.0, Hw * 0.36 + 1.6, Hw * 0.36 + 1.9, 'Marble', 'fnhood'))
            sh = K.lathe([(0.001, 0.0), (0.9, 0.0), (0.95, 0.06), (0.9, 0.1), (0.001, 0.1)], 24, 'Gold', name='fshell',
                         radial=lambda t_, z_, r_: r_ * (1 - 0.1 * abs(sin(t_ * 5))))
            parts.append(apply(sh, (xn, -0.1, Hw * 0.36 + 0.2), (pi / 2, 0, 0), (1, 1, 0.55)))
    parts.append(K.box(-X, -door[0] / 2 - 0.6, -0.3, 0.0, -4.0, 1.4, 'Stone', 'rustf1'))
    parts.append(K.box(door[0] / 2 + 0.6, X, -0.3, 0.0, -4.0, 1.4, 'Stone', 'rustf2'))
    parts.append(K.box(-X, X, Ln, Ln + 0.3, -4.0, 1.4, 'Stone', 'rustb'))
    for (xa, xb, ya, yb) in ((-X - 0.35, X + 0.35, -0.4, 0.0), (-X - 0.35, X + 0.35, Ln, Ln + 0.4), (-X - 0.4, -X, 0, Ln), (X, X + 0.4, 0, Ln)):
        parts.append(K.box(xa, xb, ya, yb, Hw - 1.0, Hw - 0.5, 'Marble', 'ecorn'))
    for (xa, xb, ya, yb) in ((-X - 0.55, X + 0.55, -0.6, 0.3), (-X - 0.55, X + 0.55, Ln - 0.3, Ln + 0.6), (-X - 0.55, -X + 0.3, 0.3, Ln - 0.3), (X - 0.3, X + 0.55, 0.3, Ln - 0.3)):
        parts.append(K.box(xa, xb, ya, yb, Hw - 0.5, Hw - 0.2, 'Marble', 'corona'))
    for sx in (-1, 1):
        for b_ in balustrade_x(0.6, Ln - 0.6, 0.0, Hw - 0.2, h=1.0, posts=piers[1:-1]):
            parts.append(apply(rot_z(b_, pi / 2), (sx * (X - 0.25), 0, 0)))
    ph = hw + 1.6
    for (y0, y1) in ((-0.55, 0.6), (Ln - 0.6, Ln + 0.55)):
        parts.append(prism_xz([(-X - 0.45, Hw - 0.2), (X + 0.45, Hw - 0.2), (0, Hw - 0.2 + ph)], y0, y1, 'Marble', 'ped'))
    parts.append(prism_xz([(-X + 0.7, Hw + 0.25), (X - 0.7, Hw + 0.25), (0, Hw + 0.25 + (ph - 0.9) * (X - 0.7) / (X + 0.45))], -0.57, -0.5, 'Wall', 'tymp'))
    parts.append(K.lathe([(0.001, 0.0), (1.1, 0.0), (1.2, 0.08), (1.1, 0.16), (0.001, 0.16)], 32, 'Gold', name='tympdisc'))
    parts[-1] = apply(parts[-1], (0, -0.57, Hw + 0.25 + ph * 0.38), (pi / 2, 0, 0))
    for sx in (-1, 0, 1):
        parts.append(urn(sx * X * 0.98, -0.0, Hw - 0.2 + (ph if sx == 0 else 0.0), 1.3))
    parts.append(K.arch_molding(door[0], door[1], 0, 0.0, 0.3, 0.55, m='Marble', name='dav', legs_to=0.0))
    kz = door[1] + door[0] / 2
    parts.append(K.box(-0.5, 0.5, -0.4, 0.3, kz - 0.4, kz + 0.7, 'Gold', 'dkey'))
    for sx in (-1, 1):
        parts += half_column(sx * (door[0] / 2 + 1.25), -0.45, 1.4, kz + 0.75, 0.38, 'Marble')
    parts.append(K.box(-door[0] / 2 - 1.9, door[0] / 2 + 1.9, -1.0, 0.0, kz + 0.75, kz + 1.25, 'Marble', 'dent'))
    parts.append(K.box(-door[0] / 2 - 2.05, door[0] / 2 + 2.05, -1.15, 0.0, kz + 1.25, kz + 1.5, 'Marble', 'dcorn'))
    parts.append(K.box(-1.4, 1.4, -0.48, -0.4, kz + 1.8, kz + 2.5, 'Gold', 'dplaque'))
    for y in wy:
        for sx in (-1, 1):
            mo = K.arch_molding(ww, wsp, 0, 0.0, 0.18, 0.28, m='Marble', name='wm', legs_to=wz0)
            parts.append(apply(mo, (sx * X, y, 0), (0, 0, pi / 2 if sx > 0 else -pi / 2)))
            g = K.arch_prism(ww, wsp, y, sx * (X - t * 0.5) - 0.01, sx * (X - t * 0.5) + 0.01, z0=wz0, axis='y', name='glass')
            g.data.materials.clear(); g.data.materials.append(K.mat('Glass2')); parts.append(g)
            parts.append(K.box(sx * (X - t * 0.5) - 0.04, sx * (X - t * 0.5) + 0.04, y - 0.03, y + 0.03, wz0, wsp + ww / 2, 'Iron', 'mv'))
            for z in np.arange(wz0 + 1.6, wsp, 1.6):
                parts.append(K.box(sx * (X - t * 0.5) - 0.04, sx * (X - t * 0.5) + 0.04, y - ww / 2, y + ww / 2, z - 0.03, z + 0.03, 'Iron', 'mh'))
            lo, hi = (X, X + 0.3) if sx > 0 else (-X - 0.3, -X)
            parts.append(K.box(lo, hi, y - ww / 2 - 0.25, y + ww / 2 + 0.25, wz0 - 0.25, wz0, 'Marble', 'wsill'))
    if stairs:   # entrance stairs down to the water / sand
        for i in range(8):
            y0 = -0.4 - i * 0.5
            parts.append(K.box(-door[0] / 2 - 1.2, door[0] / 2 + 1.2, y0 - 0.5, y0, -4.0, -0.25 * (i + 1) + 0.01, 'Stone', 'step'))
    ob = finish([p for p in parts if p is not None], name)
    LOD[0] = False
    return ob

def sea_hall():
    hall_block(22.0, 34.0, 22.0, (7.0, 9.0), (4, 2.6, 15.0, 3.2), 'SeaHall')
    hall_block(22.0, 34.0, 22.0, (7.0, 9.0), (4, 2.6, 15.0, 3.2), 'SeaHall_LOD1', lod=True)
    EXTRA['sea_hall'] = dict(len=34.0, width=22.0, height=22.0, centre=[0.0, 17.0])

def isle_hall():
    hall_block(14.0, 22.0, 12.5, (4.2, 5.2), (3, 1.8, 7.6, 2.6), 'IsleHall', stairs=True, coffer=False)
    hall_block(14.0, 22.0, 12.5, (4.2, 5.2), (3, 1.8, 7.6, 2.6), 'IsleHall_LOD1', stairs=True, lod=True)
    EXTRA['isle_hall'] = dict(len=22.0, width=14.0, height=12.5, centre=[0.0, 11.0])

# =====================================================================================================
# 5. the ruin isle: arch ruins over the colonnade, drum table, block seats, shards, eroded paths
#    (ruin-local Unity coords from ruin.py; built in Blender as (x, z_u, y_u))
# =====================================================================================================
def voussoir_arch(x0, x1, zrow, top, depth, thick, keep=(0.0, 1.0), seed=0, axis='x'):
    """semicircular arch of separate voussoirs between two capitals. axis 'x': spans along x at z=zrow (Unity),
    'z': spans along z at x=zrow. keep = (a0, a1) fraction of the arc that survives."""
    r = np.random.default_rng(seed)
    span = abs(x1 - x0); R = span / 2; c = (x0 + x1) / 2
    n = 13; out = []
    for i in range(n):
        f0, f1 = i / n, (i + 1) / n
        if f1 < keep[0] or f0 > keep[1]: continue
        a0 = pi - pi * f0; a1 = pi - pi * f1
        gap = 0.012
        pts = []
        for a in np.linspace(a0 - gap, a1 + gap, 4):
            pts.append((c + R * cos(a), top + R * sin(a)))
        for a in np.linspace(a1 + gap, a0 - gap, 4):
            pts.append((c + (R + thick) * cos(a), top + (R + thick) * sin(a)))
        jag = r.uniform(-0.03, 0.03)
        ob = prism_xz(pts, -depth / 2 + jag, depth / 2 + jag, 'Marble' if i % 3 else 'Stone', 'vous')
        # Blender (x, y, z): arch in the x-z plane, y = Unity z
        if axis == 'x': ob = apply(ob, (0, zrow, 0))
        else:
            ob = apply(ob, (0, 0, 0), (0, 0, pi / 2)); ob = apply(ob, (zrow, 0, 0))
        out.append(ob)
    return out

def arch_ruin():
    import ruin as RU
    reset()
    parts = []
    top = RU.TOP + 0.02
    # impost blocks on every standing capital
    for (x, z) in RU.COLUMNS:
        parts.append(worn_block((x, z, top + 0.2), (1.35, 1.35, 0.4), int(x * 10 + z * 100) % 997, 'Marble', wear=0.1, chips=1))
    cols = set(RU.COLUMNS)
    seed = 1
    for zr in RU.ROWS:
        xs = sorted(x for (x, z) in RU.COLUMNS if z == zr)
        for a, b in zip(xs, xs[1:]):
            if b - a > 5: continue
            keep = (0.0, 1.0)
            if seed % 4 == 3: keep = (0.0, rng.uniform(0.45, 0.7))      # one in four has lost its far half
            parts += voussoir_arch(a, b, zr, top + 0.4, 0.85, 0.62, keep, seed)
            seed += 1
        # the broken half-arch reaching toward the stump
        for (sx, sz) in RU.STUMPS:
            if sz != zr: continue
            near = max(xs, key=lambda x: -abs(x - sx))
            a, b = (near, sx) if sx > near else (sx, near)
            keep = (0.0, 0.42) if sx > near else (0.58, 1.0)
            parts += voussoir_arch(a, b, zr, top + 0.4, 0.85, 0.62, keep, seed); seed += 1
    # transverse arches between the rows (span 7)
    for x, keep in ((0.0, (0.0, 1.0)), (4.6, (0.0, 0.62)), (-4.6, (0.3, 1.0))):
        parts += voussoir_arch(RU.ROWS[0], RU.ROWS[1], x, top + 0.4, 0.75, 0.55, keep, 50 + int(x), axis='z')
    # fallen voussoirs in the grass
    for k in range(9):
        x = rng.uniform(-11, 11); z = rng.uniform(-6.5, 6.5)
        if abs(z) < 2.5 and abs(x) < 3: continue
        parts.append(worn_block((x, z, 0.2), (0.62, 0.85, 0.5), 300 + k, 'Marble', tilt=(rng.uniform(-20, 20), rng.uniform(-15, 15), rng.uniform(0, 360))))
    ob = finish(parts, 'ArchRuin')
    EXTRA['arch_ruin_top'] = top + 0.4 + 2.3 + 0.62

def table_drum():
    reset()
    def flute(t, z, r):
        ph = (t * 20 / (2 * pi)) % 1.0
        return r - 0.03 * sqrt(max(0, 1 - ((ph / 0.8) * 2 - 1) ** 2)) if ph < 0.8 else r
    zs = np.linspace(0.0, 0.78, 8)
    d = K.lathe([(0.82, z) for z in zs] + [(0.79, 0.8), (0.001, 0.8)], 96, 'Marble', radial=flute, name='drum', cap_top=False)
    me = d.data
    for v in me.vertices:            # chipped rim and a broken bite out of one side
        a = math.atan2(v.co.y, v.co.x)
        if v.co.z > 0.7 and abs(a - 2.3) < 0.5:
            v.co.z -= 0.12 * (1 - abs(a - 2.3) / 0.5)
        if v.co.z < 0.05: v.co.z += rng.uniform(-0.04, 0.0)
    finish([d], 'TableDrum')
    EXTRA['table_drum_top'] = 0.8

def block_seats():
    for k in range(4):
        reset()
        r = np.random.default_rng(700 + k)
        if k == 0:      # a squared block
            parts = [worn_block((0, 0, 0.23), (0.62, 0.55, 0.46), 710, 'Marble', wear=0.12, chips=3)]
        elif k == 1:    # a fallen capital, upside down
            parts = [worn_block((0, 0, 0.12), (0.8, 0.8, 0.24), 711, 'Marble', chips=2),
                     K.lathe([(0.33, 0.24), (0.36, 0.3), (0.42, 0.42), (0.45, 0.46), (0.001, 0.46)], 20, 'Marble', name='cap')]
        elif k == 2:    # a piece of cornice
            pts = [(-0.35, 0.0), (0.35, 0.0), (0.35, 0.3), (0.25, 0.36), (0.3, 0.44), (-0.35, 0.47)]
            parts = [prism_xz(pts, -0.45, 0.45, 'Marble', 'cornice')]
            parts.append(worn_block((0, 0, 0.1), (0.72, 0.92, 0.2), 712, 'Stone', chips=2))
        else:           # a short column drum on its side? no: a squat drum, upright
            parts = [K.lathe([(0.36, 0.0), (0.37, 0.44), (0.3, 0.46), (0.001, 0.46)], 24, 'Marble', name='sdrum')]
        finish(parts, f'BlockSeat_{k}')
    EXTRA['block_seat_h'] = 0.46

def shards():
    for k in range(4):
        reset()
        r = np.random.default_rng(800 + k)
        parts = []
        for j in range(3 if k < 3 else 1):
            s = r.uniform(0.15, 0.45) if k < 3 else 0.9
            parts.append(worn_block((r.uniform(-0.4, 0.4), r.uniform(-0.4, 0.4), s * 0.12), (s, s * r.uniform(0.5, 1.0), s * r.uniform(0.15, 0.35)),
                                    810 + k * 5 + j, 'Marble', chips=3, wear=0.05, tilt=(r.uniform(-8, 8), r.uniform(-8, 8), r.uniform(0, 360))))
        finish(parts, f'Shard_{k}')

def ruin_paths():
    """eroded marble flag paths following the sand (world coords): dock -> ruin, ruin -> isle hall, ruin -> east gate beach."""
    reset()
    rc = IS.ISLANDS[IS.INDEX['Isle_Ruin']][1]
    # routes relative to the ruin centre (designed around (142, 12)); the layout places the dock / hall / beach to match
    routes = [[(rc[0] + x - 142.0, rc[1] + z - 12.0) for x, z in r] for r in
              [[(108.0, 14.0), (118.0, 13.0), (128.0, 12.5), (131.5, 12.0)],
               [(150.0, 6.0), (155.0, 12.0), (159.0, 18.0), (160.0, 21.0)],
               [(132.0, -6.0), (124.0, -12.0), (114.0, -14.0)]]]
    parts = []
    k = 0
    for route in routes:
        P = np.array(route)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]
        for s in np.arange(0.4, cum[-1], 0.78):
            i = min(np.searchsorted(cum, s) - 1, len(P) - 2)
            f = (s - cum[i]) / seg[i]; c = P[i] * (1 - f) + P[i + 1] * f
            tg = (P[i + 1] - P[i]) / seg[i]; sd = np.array([-tg[1], tg[0]])
            for lane in (-0.82, 0.0, 0.82):
                k += 1
                if rng.random() < 0.18: continue                  # eroded away
                q = c + sd * (lane + rng.uniform(-0.08, 0.08)) + tg * rng.uniform(-0.1, 0.1)
                g = float(IS.ground(q[0], q[1]))
                if g < -0.2: continue
                w = rng.uniform(0.62, 0.78); l = rng.uniform(0.6, 0.74)
                yaw = math.degrees(math.atan2(tg[1], tg[0])) + rng.uniform(-6, 6)
                b = worn_block((0, 0, 0), (l, w, 0.12), 2000 + k, 'Floor' if rng.random() < 0.7 else 'Marble', wear=0.22, chips=rng.integers(1, 4),
                               tilt=(rng.uniform(-3, 3), rng.uniform(-3, 3), 0))
                b = apply(b, (0, 0, 0), (0, 0, math.radians(yaw)))
                parts.append(apply(b, (q[0], q[1], g + rng.uniform(-0.05, 0.02))))
    finish(parts, 'RuinPaths')

# =====================================================================================================
# 6. eroded sea gate (both water stairs), broken stairs in front, gold plaques, floating dock
# =====================================================================================================
def seagate3():
    reset()
    parts = [K.box(-11, 11, 12, 22, -8, -0.02, 'Floor', 'terrace')]
    sd = 4242
    # terrace paving edge + coping, parapets of worn blocks (some missing, some slumped)
    for sx in (-1, 1):
        y = 12.0
        while y < 22.0:
            L = rng.uniform(1.1, 1.9); L = min(L, 22.0 - y)
            sd += 1
            if not (y > 17.5 and rng.random() < 0.25):
                parts.append(worn_block((sx * 11.3, y + L / 2, 0.45), (0.6, L - 0.03, 0.9), sd, 'Wall', chips=2,
                                        tilt=(rng.uniform(-2, 2), 0, rng.uniform(-2, 2))))
            y += L
        # capstones under the statues stay whole
        parts.append(K.box(9.2 * sx - 1.6, 9.2 * sx + 1.6, 22.2, 25.4, 0.9, 1.3, 'Marble', 'capstone'))
        parts.append(K.box(9.2 * sx - 1.75, 9.2 * sx + 1.75, 22.05, 25.55, 0.75, 0.9, 'Marble', 'capbase'))
    # cheeks of three courses, the top course crumbling toward the sea
    for sx in (-1, 1):
        xc = 8.6 * sx
        for course, (z0, z1) in enumerate(((-8.0, -0.6), (-0.6, 0.15), (0.15, 0.9))):
            y = 22.0
            while y < 31.9:
                L = rng.uniform(1.2, 2.2); L = min(L, 31.9 - y)
                sd += 1
                frac = (y - 22.0) / 9.9
                if course == 2 and frac > 0.55 and rng.random() < 0.6: y += L; continue
                if course == 1 and frac > 0.85 and rng.random() < 0.4: y += L; continue
                zz1 = z1 - (rng.uniform(0, 0.25) if frac > 0.6 else 0)
                if course == 0:
                    parts.append(K.box(xc - 0.6, xc + 0.6, y, y + L, z0, z1, 'Stone', 'cheekcore'))
                else:
                    parts.append(worn_block((xc, y + L / 2, (z0 + zz1) / 2), (1.2, L - 0.03, zz1 - z0), sd, 'Wall', chips=2))
                y += L
    # 18 steps of worn blocks over a stepped core; the lower flights broken and missing pieces
    steps = 18; rise = 0.25; run = 0.55
    for i in range(steps):
        y0 = 22 + i * run; ztop = -rise * (i + 1)
        parts.append(K.box(-7.95, 7.95, y0, y0 + run - 0.02, -8, ztop - 0.18, 'Stone', 'core'))
        x = -8.0; br = i / steps
        while x < 8.0:
            L = min(rng.uniform(1.6, 3.0), 8.0 - x)
            sd += 1
            if rng.random() < 0.06 + 0.4 * max(0, br - 0.45): x += L; continue
            tilt = (rng.uniform(-1, 1) * 4 * br, rng.uniform(-1, 1) * 3 * br, rng.uniform(-1, 1) * 2 * br)
            parts.append(worn_block((x + L / 2, y0 + run / 2, ztop - 0.12 - rng.uniform(0, 0.08) * br), (L - 0.03, run + 0.04, 0.27), sd,
                                    'Marble' if i < 5 else 'Stone', chips=2 + int(br * 3), wear=0.12 + 0.12 * br, tilt=tilt))
            x += L
    # fallen blocks in the shallows at the foot
    for k in range(7):
        sd += 1
        parts.append(worn_block((rng.uniform(-9, 9), rng.uniform(31.5, 36), -1.9 + rng.uniform(-0.3, 0.3)), (rng.uniform(0.9, 1.8), rng.uniform(0.5, 0.8), 0.4), sd,
                                'Wall', chips=3, tilt=(rng.uniform(-25, 25), rng.uniform(-25, 25), rng.uniform(0, 360))))
    finish(parts, 'SeaGate3')

def broken_stairs():
    """a collapsed flight of marble stairs lying on the seabed (origin on the seabed)."""
    reset()
    parts = []
    for i in range(9):
        y = i * 0.62 + rng.uniform(-0.1, 0.1); x0 = rng.uniform(-0.6, 0.6)
        for j in range(3):
            if rng.random() < 0.3: continue
            x = x0 - 2.4 + j * 2.4 + rng.uniform(-0.2, 0.2)
            parts.append(worn_block((x, y, 0.12 + i * 0.05 + rng.uniform(-0.08, 0.12)), (2.3, 0.6, 0.28), 3000 + i * 3 + j, 'Marble', chips=3, wear=0.2,
                                    tilt=(rng.uniform(-14, 14), rng.uniform(-10, 10), rng.uniform(-12, 12))))
    for k in range(3):     # broken newel posts
        parts.append(K.lathe([(0.3, 0), (0.3, 0.2), (0.22, 0.3), (0.2, 1.0 + k * 0.3)], 12, 'Marble', name='post'))
        parts[-1] = apply(parts[-1], (rng.uniform(-4, 4), rng.uniform(0, 5), -0.2), (math.radians(rng.uniform(40, 85)), 0, rng.uniform(0, 6)))
    finish(parts, 'BrokenStairs')

def plaque():
    reset()
    parts = [K.box(-0.34, 0.34, -0.02, 0.0, -0.17, 0.17, 'Gold', 'frame'),
             K.box(-0.3, 0.3, -0.03, -0.015, -0.13, 0.13, 'Gold', 'panel'),
             K.box(-0.36, 0.36, -0.025, 0.0, -0.19, -0.17, 'Gold', 'b1'), K.box(-0.36, 0.36, -0.025, 0.0, 0.17, 0.19, 'Gold', 'b2'),
             K.box(-0.36, -0.34, -0.025, 0.0, -0.17, 0.17, 'Gold', 'b3'), K.box(0.34, 0.36, -0.025, 0.0, -0.17, 0.17, 'Gold', 'b4')]
    finish(parts, 'Plaque_Gold')      # face toward -y (Blender) = -z (Unity); back at 0

def docks():
    """floating dock deck (rides on the tide) + fixed piles. Deck top at local y = 0 (Unity)."""
    import kit2 as K2
    B = NA.Builder()
    W = 3.0; L = 14.0
    for k in range(int(L / 0.25)):
        y = k * 0.25
        K2.box_uv(B, -W / 2, W / 2, y, y + 0.23, -0.07, 0.0, 'Planks')
    K2.box_uv(B, -W / 2, -W / 2 + 0.12, 0, L, 0.0, 0.1, 'Planks'); K2.box_uv(B, W / 2 - 0.12, W / 2, 0, L, 0.0, 0.1, 'Planks')
    for y in np.arange(1.0, L, 3.3):         # pontoon barrels under the deck
        rr = [[(x, y + 0.45 * cos(a), -0.42 + 0.3 * sin(a)) for a in np.linspace(0, 2 * pi, 9)] for x in (-1.2, 1.2)]
        B.quad_strip(rr, [[(a / 6.28, 0) for a in np.linspace(0, 2 * pi, 9)], [(a / 6.28, 1.6) for a in np.linspace(0, 2 * pi, 9)]], 'Planks')
    for y in np.arange(0.3, L, 2.2):         # guide hoops around the piles
        for x in (-W / 2 - 0.12, W / 2 + 0.12):
            rr = [[(x + 0.17 * cos(a), y + 0.17 * sin(a), z) for a in np.linspace(0, 2 * pi, 9)] for z in (-0.05, 0.05)]
            B.quad_strip(rr, [[(a / 6.28, 0) for a in np.linspace(0, 2 * pi, 9)], [(a / 6.28, 0.1) for a in np.linspace(0, 2 * pi, 9)]], 'Rope')
    uv_export(B, 'DockDeck', {'Planks': K2.M('Planks'), 'Rope': K2.M('Rope')})
    B = NA.Builder()
    for y in np.arange(0.3, L, 2.2):
        for x in (-W / 2 - 0.12, W / 2 + 0.12):
            rr = [[(x + 0.12 * cos(a), y + 0.12 * sin(a), z) for a in np.linspace(0, 2 * pi, 7)] for z in (-4.0, 1.85)]
            B.quad_strip(rr, [[(a / 6.28, z) for a in np.linspace(0, 2 * pi, 7)] for z in (0, 6)], 'Planks')
            rr = [[(x + rad * cos(a), y + rad * sin(a), 1.85 + dz) for a in np.linspace(0, 2 * pi, 7)] for rad, dz in ((0.12, 0), (0.001, 0.06))]
            B.quad_strip(rr, [[(0, 0)] * 7, [(0, 0.1)] * 7], 'Planks')
    uv_export(B, 'DockPiles', {'Planks': K2.M('Planks')})
    EXTRA['dock'] = dict(freeboard=0.32, length=L, width=W)

# =====================================================================================================
# 7. new sand bars + the extended seabed (near grid +-350 and a coarse far ring to +-760)
# =====================================================================================================
def wing_lengths():
    import ivy
    out = {}
    for w in ('Wing_1', 'Wing_2', 'Wing_3'):
        P = ivy.read_pms(w)[0]; out[w] = float(P[:, 0].max() - P[:, 0].min())
    return out

def sand_islands():
    IS.add_wing_bars(wing_lengths())
    for ix, isl in enumerate(IS.ISLANDS):
        name = isl[0]
        reset()
        (cx, cz), (rx, rz) = isl[1], isl[2]
        ext = 1.45; R = max(rx, rz) * ext
        n = int(np.clip(R * 2 / 1.6, 40, 160))
        xs = np.linspace(cx - R, cx + R, n); zs = np.linspace(cz - R, cz + R, n)
        X, Z = np.meshgrid(xs, zs)
        H, D = IS.island_height(X, Z, ix)
        keep = D < ext * 0.98
        V = np.stack([X - cx, H, Z - cz], -1).reshape(-1, 3)
        F = [(j * n + i, (j + 1) * n + i, (j + 1) * n + i + 1, j * n + i + 1) for j in range(n - 1) for i in range(n - 1)
             if keep[j, i] and keep[j, i + 1] and keep[j + 1, i] and keep[j + 1, i + 1]]
        ob = K.obj_from(V[:, [0, 2, 1]], [tuple(reversed(f)) for f in F], 'Sand', smooth=True, name=name)
        K.export_bytes(ob, name)

def seabed3():
    IS.add_wing_bars(wing_lengths())
    reset()
    Lh = 350.0; n = 221
    xs = np.linspace(-Lh, Lh, n); X, Z = np.meshgrid(xs, xs)
    Hh = IS.seabed_height(X, Z)
    V = np.stack([X, Hh, Z], -1).reshape(-1, 3)
    F = [(j * n + i, (j + 1) * n + i, (j + 1) * n + i + 1, j * n + i + 1) for j in range(n - 1) for i in range(n - 1)]
    ob = K.obj_from(V[:, [0, 2, 1]], [tuple(reversed(f)) for f in F], 'Sand', smooth=True, name='Seabed3')
    K.export_bytes(ob, 'Seabed3')
    reset()
    Lf = 770.0; step = 10.0; m = int(2 * Lf / step) + 1
    xs = np.linspace(-Lf, Lf, m); X, Z = np.meshgrid(xs, xs)
    Hf = IS.seabed_height(X, Z)
    V = np.stack([X, Hf, Z], -1).reshape(-1, 3)
    F = []
    for j in range(m - 1):
        for i in range(m - 1):
            x0, x1, z0, z1 = xs[i], xs[i + 1], xs[j], xs[j + 1]
            if max(abs(x0), abs(x1)) <= Lh - step and max(abs(z0), abs(z1)) <= Lh - step: continue
            F.append((j * m + i, (j + 1) * m + i, (j + 1) * m + i + 1, j * m + i + 1))
    # sink the far ring 3 cm where it overlaps the near grid so the near grid always wins
    V[:, 1] -= 0.03 * ((np.abs(V[:, 0]) < Lh + 1) & (np.abs(V[:, 2]) < Lh + 1))
    ob = K.obj_from(V[:, [0, 2, 1]], [tuple(reversed(f)) for f in F], 'Sand', smooth=True, name='SeabedFar')
    K.export_bytes(ob, 'SeabedFar')

# =====================================================================================================
BUILDERS = {}
def builder(name):
    def deco(fn):
        BUILDERS[name] = fn; return fn
    return deco
for _n, _f in [('HallFountain', hall_fountain), ('Trevi', trevi), ('Tower3', tower3), ('SeaHall', sea_hall), ('IsleHall', isle_hall),
               ('ArchRuin', arch_ruin), ('TableDrum', table_drum), ('BlockSeats', block_seats), ('Shards', shards), ('RuinPaths', ruin_paths),
               ('SeaGate3', seagate3), ('BrokenStairs', broken_stairs), ('Plaque', plaque), ('Docks', docks),
               ('SandIslands', sand_islands), ('Seabed3', seabed3)]:
    builder(_n)(_f)

def save():
    json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1)
    json.dump(EXTRA, open(K3.EXP, 'w'), indent=1)

if __name__ == '__main__':
    names = sys.argv[1:] or list(BUILDERS)
    for n in names:
        print('== building', n, flush=True)
        BUILDERS[n]()
        save()
    print('kit3b done')
