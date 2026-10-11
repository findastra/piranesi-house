"""v3 ivy, flowers and vines (redlines 2, 3, 5, 6, 9, 10): exterior curtains that climb from the water to the top and over
the roof terraces with flowers, vines round the tall windows inside and out, the naves' window rows, floating vines on the
water, the marble tower, the sea hall and isle halls, the ruin's arches with vine drapes, and woven vine hammocks.
Run: python3 gen/ivy3.py [name ...]"""
import os, sys, json, math, numpy as np
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ivy as IV
from ivy import Surface, grow, hang, leaves, stems, Geo, write_pms2, norm, UP, DOWN, LEAF, LEAF_HANG, STEM, read_pms

IMP = IV.IMP; MANIFEST = IV.MANIFEST
FLOWER = dict(shader='foliage', albedo='Ivy/Flower_Albedo.png', normal='Ivy/Flower_Normal.png', mask='Ivy/Flower_Mask.png', alpha='MASK',
              wind=0.25, windScale=12, translucency=1.1, vertexTint=1, smooth=0.3, cutoff=0.4)
TINTS = [(1.0, 1.0, 1.0), (1.0, 0.62, 0.78), (0.82, 0.66, 1.0), (1.0, 0.93, 0.62), (1.0, 0.4, 0.66), (1.0, 0.78, 0.6)]

def leaf_rects():
    a = np.asarray(Image.open(os.path.join(IMP, 'Ivy', 'Ivy_Albedo.png')))[..., 3]
    small = np.asarray(Image.fromarray(a).resize((512, 256)), np.float32) / 255 > 0.4
    lab, n = ndimage.label(small)
    rects = []
    for sl in ndimage.find_objects(lab):
        y0, y1 = sl[0].start, sl[0].stop; x0, x1 = sl[1].start, sl[1].stop
        if (y1 - y0) > 30 and (x1 - x0) > 30:
            rects.append([(x0 - 1) / 512, 1 - (y1 + 1) / 256, (x1 + 1) / 512, 1 - (y0 - 1) / 256])
    return rects

def flower_atlas():
    base = os.path.join(IV.ACG, 'FlowerSet001_2K-JPG', 'FlowerSet001_2K-JPG')
    W = 1024
    col = Image.open(base + '_Color.jpg').convert('RGB').resize((W, W), Image.LANCZOS)
    op = Image.open(base + '_Opacity.jpg').convert('L').resize((W, W), Image.LANCZOS)
    nm = Image.open(base + '_NormalGL.jpg').convert('RGB').resize((W, W), Image.LANCZOS)
    ro = Image.open(base + '_Roughness.jpg').convert('L').resize((W, W), Image.LANCZOS)
    c = np.asarray(col, np.float32); a = np.asarray(op, np.float32) / 255
    idx = ndimage.distance_transform_edt(~(a > 0.5), return_distances=False, return_indices=True)
    c = c[idx[0], idx[1]]
    d = os.path.join(IMP, 'Ivy')
    Image.fromarray(np.concatenate([np.clip(c, 0, 255), (a * 255)[..., None]], -1).astype(np.uint8), 'RGBA').save(os.path.join(d, 'Flower_Albedo.png'))
    nm.save(os.path.join(d, 'Flower_Normal.png'))
    r = np.asarray(ro, np.float32) / 255
    Image.fromarray((np.stack([np.clip(1.0 - r, 0, 1), np.ones_like(r), np.zeros_like(r), np.ones_like(r)], -1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(d, 'Flower_Mask.png'))
    lab, n = ndimage.label(a > 0.4)
    rects = []
    for sl in ndimage.find_objects(lab):
        y0, y1 = sl[0].start, sl[0].stop; x0, x1 = sl[1].start, sl[1].stop
        if (y1 - y0) > 100:
            rects.append([x0 / W, 1 - y1 / W, x1 / W, 1 - y0 / W])
    print('flower atlas', len(rects))
    return rects

def flowers(strands, rng, frects, p=0.06, size=(0.06, 0.11), every=0.1, tints=TINTS, cluster=3):
    """small flower cards along the strands, facing out from the surface (or up for floating vines)."""
    G = Geo(); count = 0
    for s in strands:
        P, N = s['p'], s['n']
        Q, cum, idx = IV.resample(P, every)
        tint = tints[rng.integers(len(tints))]
        for k in range(1, len(Q)):
            if rng.random() > p: continue
            n = norm(N[min(idx[k], len(N) - 1)])
            for j in range(rng.integers(1, cluster + 1)):
                c = Q[k] + rng.normal(size=3) * 0.05 + n * rng.uniform(0.03, 0.08)
                f = norm(n * 0.8 + UP * 0.35 + rng.normal(size=3) * 0.35)
                r1 = norm(np.cross(f, UP if abs(f[1]) < 0.95 else np.array([1.0, 0, 0]))); r2 = np.cross(f, r1)
                a = rng.uniform(0, 6.28); r1, r2 = r1 * math.cos(a) + r2 * math.sin(a), -r1 * math.sin(a) + r2 * math.cos(a)
                sz = rng.uniform(*size)
                V = [c - r1 * sz - r2 * sz, c + r1 * sz - r2 * sz, c + r1 * sz + r2 * sz, c - r1 * sz + r2 * sz]
                rc = frects[rng.integers(len(frects))]
                U = [(rc[0], rc[1]), (rc[2], rc[1]), (rc[2], rc[3]), (rc[0], rc[3])]
                tt = np.clip(np.array(tint) * rng.uniform(0.92, 1.04), 0, 1)
                C = np.tile([255, int(tt[0] * 255), int(tt[1] * 255), int(tt[2] * 255)], (4, 1))
                G.add(V, [f] * 4, C, U, [(0, 1, 2), (0, 2, 3)])
                count += 1
    print(f'  {count} flowers', flush=True)
    return G

def export3(name, strands, rng, rects, frects, man, hanging=False, flower_p=0.0, fsize=(0.06, 0.11), lod=True, **leafkw):
    recs = leaves(strands, rng, rects, **leafkw)
    GL = Geo(); GS = Geo()
    IV.emit_leaves(GL, recs); stems(GS, strands, rng)
    groups = [(f'{name}_Leaf', GL), (f'{name}_Stem', GS)]
    entries = [dict(sub=f'{name}_Leaf', **(LEAF_HANG if hanging else LEAF)), dict(sub=f'{name}_Stem', **STEM)]
    GF = None
    if flower_p > 0:
        GF = flowers(strands, rng, frects, flower_p, fsize)
        groups.append((f'{name}_Flower', GF)); entries.append(dict(sub=f'{name}_Flower', **FLOWER))
    write_pms2(name, groups)
    man[name] = entries
    if lod:
        GL = Geo(); GS = Geo()
        IV.emit_leaves(GL, recs, keep=0.33, grow_=1.55, rng=rng); stems(GS, strands, rng, max_gen=0, every=0.5)
        g2 = [(f'{name}_Leaf', GL), (f'{name}_Stem', GS)]
        if GF is not None: g2.append((f'{name}_Flower', GF))
        write_pms2(name + '_LOD1', g2)
        man[name + '_LOD1'] = entries
    print(f'  {name}: {len(recs)} leaves', flush=True)

WIN = [(-3.6, 1.9, 11.0), (0.0, 2.2, 13.0), (3.6, 1.9, 11.0)]
def in_window(p, pad=0.12):
    for (wx, ww, sp) in WIN:
        if abs(p[0] - wx) < ww / 2 + pad and 0.45 < p[1] < sp + ww / 2 + pad: return True
    return abs(p[0]) < 2.4 and 15.6 < p[1] < 20.8           # lunette

# ------------------------------------------------------------------ pieces
def ext_window(rng, rects, frects, man):
    for i in range(2):
        S = Surface(0.05, 20 + i).add_mesh('Vest_SideWindow', keep=lambda c, n: c[:, 2] > 11.4).add_mesh('VestExt_Window')
        S.add_plane(24.03, -11.9, 11.9, 10.45, 11.95).build()
        bnd = lambda p: p[2] > 9.9 and abs(p[0]) < 10.3 and 0.25 < p[1] < 25.6 and not in_window(p)
        xs = [s * rng.uniform(5.2, 9.4) for s in (-1, 1) for _ in range(4)] + [s * rng.uniform(1.4, 2.4) for s in (-1, 1)]
        climb = [((x, 0.35, 12.42), (0, 1, 0)) for x in xs]
        casc = [((rng.uniform(-9.5, 9.5), 25.1, 12.45), (0, -1, 0)) for _ in range(9)]
        top = [((rng.uniform(-10, 10), 24.1, rng.uniform(10.6, 11.8)), (rng.normal(), 0, rng.normal())) for _ in range(8)]
        st = grow(S, climb, rng, length=(12, 26), budget=720, w_up=0.42, w_rand=0.55, branch_p=0.08, max_strands=2400, bounds=bnd)
        st += grow(S, casc, rng, length=(3, 12), budget=420, w_up=-0.5, w_rand=0.6, branch_p=0.07, max_float=0.9, max_strands=2400, bounds=bnd)
        st += grow(S, top, rng, length=(3, 9), budget=260, w_up=0.0, w_rand=0.9, branch_p=0.1, max_strands=2400, bounds=bnd)
        # curtains falling from the balustrade over the cornice
        anchors = [(rng.uniform(-10, 10), 24.0, 12.85 + rng.uniform(0, 0.15)) for _ in range(40)]
        hs = hang(anchors, rng, length=(1.0, 6.5), face=np.array([0, 0, 1.0]), sway=0.2)
        hs = [h for h in hs if not any(in_window(q) for q in h['p'][::6])]
        export3(f'Ivy_ExtWin_{i}', st + hs, rng, rects, frects, man, flower_p=0.07, size=(0.09, 0.19))

def ext_blind(rng, rects, frects, man):
    for i in range(2):
        S = Surface(0.05, 30 + i).add_mesh('Vest_SideBlind', keep=lambda c, n: c[:, 2] > 11.4).add_mesh('VestExt_Blind').build()
        bnd = lambda p: p[2] > 9.9 and abs(p[0]) < 12.3 and 0.25 < p[1] < 25.4
        cx = rng.uniform(-6, 6)
        climb = [((float(np.clip(cx + rng.normal() * 4, -11, 11)), 0.35, 12.42), (0, 1, 0)) for _ in range(9)]
        casc = [((float(np.clip(-cx + rng.normal() * 4, -11, 11)), 25.1, 12.45), (0, -1, 0)) for _ in range(8)]
        st = grow(S, climb, rng, length=(8, 22), budget=560, w_up=0.35, w_rand=0.6, branch_p=0.075, max_strands=2400, bounds=bnd)
        st += grow(S, casc, rng, length=(3, 11), budget=340, w_up=-0.5, w_rand=0.6, branch_p=0.07, max_float=0.9, max_strands=2400, bounds=bnd)
        export3(f'Ivy_ExtBlind_{i}', st, rng, rects, frects, man, flower_p=0.035, size=(0.09, 0.19))

def win_in(rng, rects, frects, man):
    S = Surface(0.045, 40).add_mesh('Vest_SideWindow', keep=lambda c, n: (c[:, 2] < 12.05) & (np.abs(c[:, 0]) < 6)).build()
    bnd = lambda p: 9.4 < p[2] < 12.05 and abs(p[0]) < 6 and 0.4 < p[1] < 15.5
    seeds = []
    for (wx, ww, sp) in WIN:
        for s in (-1, 1):
            seeds.append(((wx + s * (ww / 2 - 0.03), 0.65, rng.uniform(10.2, 11.4)), (0, 1, 0)))
    st = grow(S, seeds, rng, length=(5, 12), budget=150, w_up=0.5, w_rand=0.5, branch_p=0.07, max_strands=800, bounds=bnd)
    anchors = []
    for (wx, ww, sp) in WIN:
        for k in range(10):
            a = rng.uniform(0.15, math.pi - 0.15); r = ww / 2 - 0.05
            anchors.append((wx + math.cos(a) * r, sp + math.sin(a) * r - 0.05, rng.uniform(10.15, 11.5)))
    hs = hang(anchors, rng, length=(0.8, 4.5), face=np.array([0, 0, -1.0]), sway=0.12)
    export3('Ivy_WinIn', st + hs, rng, rects, frects, man, flower_p=0.05, size=(0.08, 0.15))

def floating(rng, rects, frects, man):
    for i in range(2):
        strands = []
        for k in range(16):
            p = np.array([rng.uniform(-10.5, 10.5), 0.0, 12.45]); d = norm(np.array([rng.normal() * 0.6, 0, 1.0]))
            pts = [p.copy()]
            L = rng.uniform(2.5, 9.0)
            for j in range(int(L / 0.08)):
                d = norm(d + np.array([rng.normal() * 0.12, 0, rng.normal() * 0.05 + 0.02]))
                p = p + d * 0.08; p[1] = 0.012 * math.sin(j * 0.3); pts.append(p.copy())
            P = np.array(pts)
            strands.append(dict(p=P, n=np.tile(UP, (len(P), 1)), att=np.zeros(len(P), bool), gen=0))
            for b in range(rng.integers(1, 4)):     # side shoots
                j0 = rng.integers(len(P) // 5, len(P) - 2); q = P[j0].copy(); dd = norm(np.array([rng.choice([-1, 1]), 0, rng.uniform(0, 0.6)]))
                pts2 = [q.copy()]
                for j in range(int(rng.uniform(0.8, 3.0) / 0.08)):
                    dd = norm(dd + np.array([rng.normal() * 0.15, 0, rng.normal() * 0.15])); q = q + dd * 0.08; q[1] = 0.01; pts2.append(q.copy())
                strands.append(dict(p=np.array(pts2), n=np.tile(UP, (len(pts2), 1)), att=np.zeros(len(pts2), bool), gen=1))
        export3(f'Ivy_Float_{i}', strands, rng, rects, frects, man, flower_p=0.05, size=(0.1, 0.2), lod=False)

def nave_win(rng, rects, frects, man):
    import kit as K
    COL_Y = K.COL_Y
    bays = [(COL_Y[k] + COL_Y[k + 1]) / 2 for k in range(7)]
    S = Surface(0.05, 50).add_mesh('Nave', keep=lambda c, n: np.abs(c[:, 0]) > 9.6).add_mesh('NaveExt', keep=lambda c, n: np.abs(c[:, 0]) > 9.6).build()
    def inwin(p):
        return any(abs(p[2] - b) < 0.78 for b in bays) and 5.5 < p[1] < 10.45
    bnd = lambda p: abs(p[0]) > 9.6 and abs(p[2]) < 18.0 and 0.25 < p[1] < 17.6 and not inwin(p)
    climb = []; casc = []
    for s in (-1, 1):
        for z in COL_Y[1:-1]:
            if rng.random() < 0.75: climb.append(((s * 10.42, 0.35, z + rng.normal() * 0.2), (0, 1, 0)))
        for k in range(8): casc.append(((s * 10.62, 17.4, rng.uniform(-17, 17)), (0, -1, 0)))
    st = grow(S, climb, rng, length=(8, 18), budget=640, w_up=0.42, w_rand=0.55, branch_p=0.08, max_strands=2400, bounds=bnd)
    st += grow(S, casc, rng, length=(3, 9), budget=360, w_up=-0.5, w_rand=0.6, branch_p=0.07, max_float=0.9, max_strands=2400, bounds=bnd)
    anchors = []
    for s in (-1, 1):
        for b in bays:
            for k in range(rng.integers(2, 6)):
                anchors.append((s * 10.35, 10.3 + rng.uniform(0, 0.25), b + rng.uniform(-0.6, 0.6)))
    hs = hang(anchors, rng, length=(0.6, 2.8), face=None, sway=0.1)
    for h in hs: h['n'] = np.tile(np.array([np.sign(h['p'][0, 0]), 0, 0.0]), (len(h['p']), 1))
    export3('Ivy_NaveWin', st + hs, rng, rects, frects, man, flower_p=0.04, size=(0.09, 0.18))

def arcade_win(rng, rects, frects, man):
    S = Surface(0.05, 60).add_mesh('Arcade_Win', keep=lambda c, n: c[:, 0] > 6.3).add_mesh('ArcadeExt', keep=lambda c, n: c[:, 0] > 6.3).build()
    bays = [-15.75 + 4.5 * k for k in range(8)]
    inwin = lambda p: any(abs(p[2] - b) < 1.3 for b in bays) and 0.85 < p[1] < 5.55
    bnd = lambda p: p[0] > 5.5 and abs(p[2]) < 18.1 and 0.25 < p[1] < 16.5 and not inwin(p)
    climb = [((7.42, 0.35, rng.uniform(-17, 17)), (0, 1, 0)) for _ in range(11)]
    casc = [((7.62, 16.4, rng.uniform(-17, 17)), (0, -1, 0)) for _ in range(10)]
    st = grow(S, climb, rng, length=(6, 16), budget=520, w_up=0.33, w_rand=0.6, branch_p=0.07, max_strands=2400, bounds=bnd)
    st += grow(S, casc, rng, length=(3, 11), budget=340, w_up=-0.5, w_rand=0.6, branch_p=0.07, max_float=0.9, max_strands=2400, bounds=bnd)
    export3('Ivy_ArcadeWin3', st, rng, rects, frects, man, flower_p=0.04, size=(0.09, 0.19))

def tower(rng, rects, frects, man):
    ext = lambda c, n: (np.abs(c[:, 0]) > 6.1) | (c[:, 2] < 0.4) | (c[:, 2] > 12.6) | (c[:, 1] > 26.0)
    S = Surface(0.05, 70).add_mesh('Tower3', keep=ext).build()
    cy = 6.5
    def bnd(p):
        if not (-0.2 < p[1] < 39.0 and abs(p[0]) < 7.3 and -0.9 < p[2] < 13.9): return False
        inner = abs(p[0]) < 5.9 and 0.6 < p[2] < 12.4
        return not inner or p[1] > 26.1
    climb = []
    for (sx, sz) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        for k in range(3):
            if rng.random() < 0.8:
                x = sx * rng.uniform(5.2, 6.4); z = cy + sz * 6.65
                climb.append(((x, 0.35, z), (0, 1, 0)))
                x = sx * 6.65; z = cy + sz * rng.uniform(5.2, 6.4)
                climb.append(((x, 0.35, z), (0, 1, 0)))
    st = grow(S, climb, rng, length=(12, 30), budget=900, w_up=0.45, w_rand=0.55, branch_p=0.075, max_strands=3000, bounds=bnd)
    top = [((rng.uniform(-6, 6), 27.1, cy + rng.uniform(-6, 6)), (rng.normal(), 0, rng.normal())) for _ in range(10)]
    top = [t for t in top if math.hypot(t[0][0], t[0][2] - cy) > 5.4]
    st += grow(S, top, rng, length=(3, 10), budget=320, w_up=0.25, w_rand=0.8, branch_p=0.1, max_strands=3000, bounds=bnd)
    anchors = []
    for k in range(4):            # curtains from the terrace cornice and the upper arch heads, all four faces
        for j in range(16):
            u = rng.uniform(-6.2, 6.2); a = k * math.pi / 2
            x, z = u * math.cos(a) - (-6.95) * math.sin(a), u * math.sin(a) + (-6.95) * math.cos(a)
            anchors.append((x, 26.0, cy + z))
        for xc in (-2.65, 2.65):
            for j in range(5):
                u = xc + rng.uniform(-1.5, 1.5); a = k * math.pi / 2
                x, z = u * math.cos(a) - (-6.6) * math.sin(a), u * math.sin(a) + (-6.6) * math.cos(a)
                anchors.append((x, 22.9 - 0.4 * abs(u - xc), cy + z))
    hs = hang(anchors, rng, length=(1.5, 8.0), face=None, sway=0.2)
    for h in hs:
        o = h['p'][0]; d = norm(np.array([o[0], 0, o[2] - cy])); h['n'] = np.tile(d, (len(h['p']), 1))
    export3('Ivy_Tower3', st + hs, rng, rects, frects, man, flower_p=0.06, size=(0.09, 0.19))

def ruin(rng, rects, frects, man):
    import ruin as RU
    S = Surface(0.045, 80)
    for (x, z) in RU.COLUMNS: S.add_mesh('Column', t=(x, RU.BASE_Y, z))
    S.add_mesh('ArchRuin'); S.build()
    seeds = []
    for (x, z) in RU.COLUMNS:
        for k in range(4):
            a = rng.uniform(0, 2 * math.pi)
            seeds.append(((x + math.cos(a) * 0.62, RU.BASE_Y + 0.5, z + math.sin(a) * 0.62), (0, 1, 0)))
    st = grow(S, seeds, rng, length=(9, 20), budget=1100, w_up=0.42, w_rand=0.55, branch_p=0.065, max_strands=3200,
              bounds=lambda p: -0.2 < p[1] < 14.2 and abs(p[0]) < 13 and abs(p[2]) < 8)
    top = RU.TOP + 0.42
    anchors = []
    xs_rows = {zr: sorted(x for (x, z) in RU.COLUMNS if z == zr) for zr in RU.ROWS}
    for zr, xs in xs_rows.items():          # hanging off the arch intrados
        for a_, b_ in zip(xs, xs[1:]):
            c = (a_ + b_) / 2; R = (b_ - a_) / 2
            for k in range(9):
                t = rng.uniform(0.2, math.pi - 0.2)
                anchors.append((c + math.cos(t) * R, top + math.sin(t) * R - 0.05, zr + rng.uniform(-0.3, 0.3)))
    hs = hang(anchors, rng, length=(1.5, 6.5), face=None, sway=0.2)
    # drapes: vine swags slung between the capitals, along the rows and across, with tendrils falling from them
    drapes = []
    caps = {(x, z): np.array([x, RU.TOP + 0.3, z]) for (x, z) in RU.COLUMNS}
    pairs = []
    for zr, xs in xs_rows.items():
        pairs += [((a_, zr), (b_, zr)) for a_, b_ in zip(xs, xs[1:])]
    for x in (-4.6, 0.0, 4.6):
        if (x, RU.ROWS[0]) in caps and (x, RU.ROWS[1]) in caps: pairs.append(((x, RU.ROWS[0]), (x, RU.ROWS[1])))
    pairs += [((-9.2, 3.5), (-4.6, -3.5)), ((4.6, 3.5), (9.2, -3.5))]
    for (p0, p1) in pairs:
        A = caps[p0]; B = caps[p1]
        for j in range(rng.integers(2, 4)):
            sag = rng.uniform(1.2, 2.6); off = rng.normal(size=3) * 0.12
            pts = [A + (B - A) * t + np.array([0, -sag * 4 * t * (1 - t), 0]) + off for t in np.linspace(0, 1, 60)]
            P = np.array(pts)
            nrm = norm(np.cross(B - A, UP)) if np.linalg.norm(np.cross(B - A, UP)) > 0 else np.array([0, 0, 1.0])
            drapes.append(dict(p=P, n=np.tile(nrm, (len(P), 1)), att=np.zeros(len(P), bool), gen=0, hang=True))
            tips = [P[i] for i in rng.choice(np.arange(8, 52), size=rng.integers(5, 10), replace=False)]
            drapes += hang(tips, rng, length=(0.6, 3.2), face=nrm, sway=0.12)
    export3('Ivy_Ruin3', st + hs + drapes, rng, rects, frects, man, flower_p=0.06, size=(0.09, 0.19))

def dome_top(rng, rects, frects, man):
    S = Surface(0.06, 90).add_mesh('Vest_Dome', keep=lambda c, n: c[:, 1] < 33.0).add_plane(24.03, -11.9, 11.9, -11.9, 11.9).build()
    def bnd(p):
        r = math.hypot(p[0], p[2])
        return 23.9 < p[1] < 32.5 and max(abs(p[0]), abs(p[2])) < 11.95 and r > 3.4
    seeds = []
    for k in range(16):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(10.6, 11.6)
        seeds.append(((math.cos(a) * r, 24.08, math.sin(a) * r), (math.cos(a + 1.6), 0, math.sin(a + 1.6))))
    for k in range(8):
        a = rng.uniform(0, 2 * math.pi); seeds.append(((math.cos(a) * 10.45, 24.4, math.sin(a) * 10.45), (0, 1, 0)))
    st = grow(S, seeds, rng, length=(4, 12), budget=520, w_up=0.2, w_rand=0.8, branch_p=0.1, max_strands=2400, bounds=bnd)
    export3('Ivy_DomeTop', st, rng, rects, frects, man, flower_p=0.12, fsize=(0.07, 0.13), size=(0.09, 0.19))

def hall_ivy(rng, rects, frects, man, mesh, name, X, Ln, Hw):
    ext = lambda c, n: (np.abs(c[:, 0]) > X - 0.35) | (c[:, 2] < 0.35) | (c[:, 2] > Ln - 0.35) | (c[:, 1] > Hw - 0.3)
    S = Surface(0.06, 100).add_mesh(mesh, keep=ext).build()
    bnd = lambda p: -0.9 < p[2] < Ln + 0.9 and abs(p[0]) < X + 0.9 and 0.2 < p[1] < Hw + 6 and \
        (abs(p[0]) > X - 0.4 or p[2] < 0.4 or p[2] > Ln - 0.4 or p[1] > Hw - 0.4)
    climb = []
    for (x, z) in ((-X + 0.4, -0.38), (X - 0.4, -0.38), (-X - 0.38, 0.6), (X + 0.38, 0.6), (-X - 0.38, Ln - 0.6), (X + 0.38, Ln - 0.6)):
        for k in range(2): climb.append(((x + rng.normal() * 0.2, 0.35, z), (0, 1, 0)))
    for k in range(5):
        z = rng.uniform(2, Ln - 2); s = rng.choice([-1, 1]); climb.append(((s * (X + 0.32), 0.35, z), (0, 1, 0)))
    st = grow(S, climb, rng, length=(6, Hw * 1.4), budget=Hw * 40, w_up=0.42, w_rand=0.55, branch_p=0.075, max_strands=2400, bounds=bnd)
    anchors = [(rng.uniform(-X + 1, X - 1), Hw - 1.0, -0.42) for _ in range(18)]
    hs = hang(anchors, rng, length=(1.0, Hw * 0.35), face=np.array([0, 0, -1.0]), sway=0.15)
    export3(name, st + hs, rng, rects, frects, man, flower_p=0.05, size=(0.09, 0.19))

def hammock(rng, rects, frects, man):
    """a hammock woven from vine stems (span along z, sag in -y, Unity local; anchors at z = +-1.8, y = 0.15)."""
    span = 3.6; sag = 0.55; W = 1.1
    def surf(t, s):
        z = (t - 0.5) * span * 0.78; y = -sag * (1 - (2 * t - 1) ** 2)
        wid = W * (0.25 + 0.75 * math.sin(math.pi * t) ** 0.6)
        return np.array([s * wid, y + 0.18 * (abs(s) * 2) ** 2 * math.sin(math.pi * t), z])
    cords = []
    for j in range(9):
        s = j / 8 - 0.5
        P = np.array([surf(t, s) for t in np.linspace(0, 1, 70)])
        P = np.vstack([np.array([[0, 0.15, -span / 2]]), P, np.array([[0, 0.15, span / 2]])])
        cords.append(P)
    weaves = []
    for k, t in enumerate(np.linspace(0.06, 0.94, 26)):
        P = []
        for i, s in enumerate(np.linspace(-0.5, 0.5, 30)):
            q = surf(t, s); q[1] += 0.012 * math.sin(i * math.pi / 3.5 + k * math.pi)       # over and under the cords
            q[2] += 0.02 * math.sin(i * 0.9 + k)
            P.append(q)
        weaves.append(np.array(P))
    G = Geo()
    def tube(P, r, tw=0.0):
        V = []; N = []; U = []
        acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
        for i, q in enumerate(P):
            tg = norm(P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)])
            b = norm(np.cross(tg, UP if abs(tg[1]) < 0.9 else np.array([1.0, 0, 0]))); u = np.cross(b, tg)
            for j in range(5):
                a = j * 2 * math.pi / 5 + tw * i
                dv = b * math.cos(a) + u * math.sin(a); V.append(q + dv * r); N.append(dv); U.append((j / 5 * 0.25, acc[i] / 0.6))
        F = []
        for i in range(len(P) - 1):
            for j in range(5):
                a = i * 5 + j; b2 = i * 5 + (j + 1) % 5
                F += [(a, b2, b2 + 5), (a, b2 + 5, a + 5)]
        G.add(V, N, np.tile([200, 255, 255, 255], (len(V), 1)), U, F)
    for P in cords: tube(P, 0.016)
    for P in cords[::2]: tube(P + np.array([0.008, 0.006, 0]), 0.008, tw=0.4)     # twisted second stem
    for P in weaves: tube(P, 0.009)
    # leaves along the cords and edges, a few tendrils and flowers
    strands = [dict(p=P, n=np.tile(UP, (len(P), 1)), att=np.zeros(len(P), bool), gen=1) for P in (cords[0], cords[-1], cords[4])]
    tips = [cords[0][i] for i in range(8, 64, 7)] + [cords[-1][i] for i in range(10, 64, 7)]
    tend = hang(tips, rng, length=(0.3, 1.2), face=None, sway=0.08)
    recs = leaves(strands + tend, rng, rects, every=0.07, density=0.7, size=(0.07, 0.14))
    GL = Geo(); IV.emit_leaves(GL, recs)
    stems(G, tend, rng)
    GF = flowers(strands, rng, frects, 0.05, (0.05, 0.09))
    name = 'Hammock_Vine'
    write_pms2(name, [(f'{name}_Leaf', GL), (f'{name}_Stem', G), (f'{name}_Flower', GF)])
    man[name] = [dict(sub=f'{name}_Leaf', **LEAF), dict(sub=f'{name}_Stem', **dict(STEM, tint=[0.5, 0.45, 0.3])), dict(sub=f'{name}_Flower', **FLOWER)]

PIECES = ['ExtWin', 'ExtBlind', 'WinIn', 'Float', 'NaveWin', 'ArcadeWin', 'Tower', 'Ruin', 'DomeTop', 'SeaHall', 'IsleHall', 'Hammock']
if __name__ == '__main__':
    only = sys.argv[1:] or PIECES
    rng = np.random.default_rng(3033)
    rects = leaf_rects(); frects = flower_atlas()
    for name in only:
        print('== ivy3', name, flush=True)
        man = json.load(open(MANIFEST))
        {'ExtWin': ext_window, 'ExtBlind': ext_blind, 'WinIn': win_in, 'Float': floating, 'NaveWin': nave_win, 'ArcadeWin': arcade_win,
         'Tower': tower, 'Ruin': ruin, 'DomeTop': dome_top, 'Hammock': hammock,
         'SeaHall': lambda *a: hall_ivy(*a, 'SeaHall', 'Ivy_SeaHall', 11.0, 34.0, 22.0),
         'IsleHall': lambda *a: hall_ivy(*a, 'IsleHall', 'Ivy_IsleHall', 7.0, 22.0, 12.5)}[name](rng, rects, frects, man)
        json.dump(man, open(MANIFEST, 'w'), indent=1)
    print('ivy3 done')
