"""Water lilies (Nymphaea), built in Blender: floating pads with the narrow sinus cut to the petiole, waxy veined
tops, purple-red undersides that show where a rim curls up, beads of water; open flowers with four sepals, four
whorls of cupped pointed petals, a crown of golden stamens round the stigmatic disc; a closed bud on its stalk.

Exports WaterLily (pad + white flower), WaterLily_Pink (pads + pink flower + bud), WaterLily_Pads (a cluster of pads),
each with a LOD1. Textures: out/Imported/WaterLily/.

    python3 gen/real/lily.py            (textures + meshes + manifest)
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, zoom

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mesh as MK
from mesh import nrm, smoothstep

TEX = os.path.join(MK.OUTI, 'WaterLily')
TAU = 2 * math.pi

# ============================================================================================ textures
def _veins(S, seed, nmain=26, w0=7.0):
    """palmate veins radiating from the centre of an S x S square (radius 0.48 S), forking twice toward the margin."""
    r = np.random.default_rng(seed)
    c = S / 2; R = 0.48 * S
    im = Image.new('L', (S, S), 0); d = ImageDraw.Draw(im)
    def P(rho, th): return (c + R * rho * math.cos(th), c - R * rho * math.sin(th))
    def stroke(th0, dth, r0, r1, wa, wb, wob):
        n = max(4, int((r1 - r0) * 60))
        pts = []
        for k in range(n + 1):
            t = k / n; rho = r0 + (r1 - r0) * t
            th = th0 + dth * (3 * t * t - 2 * t ** 3) + wob * math.sin(rho * 9 + th0 * 5) + wob * 0.6 * math.sin(rho * 31 + th0 * 3)
            pts.append((P(rho, th), wa + (wb - wa) * t, th))
        for (p0, w, _), (p1, _, _) in zip(pts[:-1], pts[1:]):
            d.line([p0, p1], fill=255, width=max(1, int(round(w))))
        return pts[-1][2]
    step = TAU / nmain
    for k in range(nmain):
        th = k * step + r.uniform(-0.06, 0.06)
        f1 = r.uniform(0.36, 0.5); f2 = r.uniform(0.64, 0.8)
        th = stroke(th, r.uniform(-0.05, 0.05), 0.02, f1, w0, w0 * 0.72, 0.012)
        for s in (-1, 1):
            d1 = s * step * r.uniform(0.2, 0.3)
            t1 = stroke(th, d1, f1, f2, w0 * 0.62, w0 * 0.5, 0.003)
            for s2 in (-1, 1):
                if r.random() < 0.85:
                    stroke(t1, s2 * step * r.uniform(0.08, 0.14), f2, 0.995, w0 * 0.42, w0 * 0.3, 0.002)
    return np.asarray(im, np.float32) / 255

def _reticulate(S, seed, n=5000):
    """fine net of veinlets between the main veins: the edges of random cells."""
    from scipy.spatial import cKDTree
    r = np.random.default_rng(seed)
    pts = r.uniform(0, S, (n, 2))
    yy, xx = np.mgrid[0:S, 0:S]
    q = np.stack([xx.ravel(), yy.ravel()], 1)
    dd, ii = cKDTree(pts).query(q, k=2)
    edge = np.clip(1 - (dd[:, 1] - dd[:, 0]) / 2.2, 0, 1).reshape(S, S)
    return edge

def pad_textures(seed=11):
    S = 2048; F = 1024
    r = np.random.default_rng(seed)
    yy, xx = (np.mgrid[0:F, 0:F] + 0.5)
    X = (xx - F / 2) / (0.48 * F); Y = (F / 2 - yy) / (0.48 * F)
    rho = np.sqrt(X * X + Y * Y); th = np.arctan2(Y, X) % TAU
    down = lambda a: zoom(gaussian_filter(a, 1.0), 0.5, order=1)
    veins = down(_veins(S, seed, 26, 7.5))
    veins_b = down(_veins(S, seed, 26, 12.0))                       # the underside's raised ribs are broader
    fine = gaussian_filter(_reticulate(F, seed + 1), 0.6) * (rho < 0.995)
    low = MK.fbm((F, F), [70, 25], seed + 2, [1.0, 0.5])
    mid = MK.fbm((F, F), [9, 3], seed + 3, [1.0, 0.4])

    # ---- top: waxy deep green, paler veins, a sun-yellowed sector, bronze mottling, a few dead spots and water beads
    deep = np.array([0.20, 0.33, 0.10]); light = np.array([0.33, 0.47, 0.16])
    col = deep + (light - deep) * np.clip(0.5 + 0.35 * low + 0.12 * mid, 0, 1)[..., None]
    col *= (1.0 + 0.06 * smoothstep(0.3, 0.0, rho))[..., None]
    col = col + (np.array([0.40, 0.52, 0.2]) - col) * (0.4 * veins)[..., None]
    col = col + (np.array([0.36, 0.5, 0.18]) - col) * (0.22 * fine)[..., None]
    yel = smoothstep(0.45, 1.0, rho) * np.exp(-((((th - 4.2 + math.pi) % TAU) - math.pi) / 0.8) ** 2) * (0.6 + 0.4 * low)
    col = col + (np.array([0.58, 0.56, 0.2]) - col) * np.clip(yel, 0, 0.8)[..., None]
    mott = np.clip((MK.fbm((F, F), [5, 2], seed + 4) - 1.3) * 2.5, 0, 1) * np.exp(-((((th - 1.3 + math.pi) % TAU) - math.pi) / 0.9) ** 2)
    col = col + (np.array([0.30, 0.16, 0.12]) - col) * (0.6 * mott)[..., None]
    smooth = np.full((F, F), 0.5) - 0.08 * veins
    hgt = -0.9 * veins - 0.35 * fine + 0.12 * mid
    wob = MK.fbm((F, F), [6, 2], seed + 6, [1.0, 0.5])
    for k in range(3):                                              # dead patches: irregular, brown, with a yellow halo
        a = r.uniform(0, TAU); rr = r.uniform(0.7, 0.95); rad = r.uniform(0.02, 0.05)
        dd = np.hypot(X - rr * math.cos(a), Y - rr * math.sin(a)) / rad + 0.35 * wob
        halo = smoothstep(2.2, 1.0, dd)
        col = col + (np.array([0.55, 0.50, 0.18]) - col) * (0.55 * halo)[..., None]
        core = smoothstep(1.0, 0.7, dd)
        col = col + (np.array([0.36, 0.25, 0.12]) * (0.85 + 0.3 * mid[..., None]) - col) * core[..., None]
        hgt -= 0.3 * core
    for k in range(34):                                             # beads of water
        a = r.uniform(0, TAU); rr = math.sqrt(r.uniform(0.01, 0.9)); rad = r.uniform(0.004, 0.016)
        dd = np.hypot(X - rr * math.cos(a), Y - rr * math.sin(a)) / rad
        inb = dd < 1
        dome = np.sqrt(np.clip(1 - dd * dd, 0, 1))
        col = np.where(inb[..., None], col * (0.78 + 0.5 * dome[..., None]) + 0.05 * dome[..., None] ** 4, col)
        smooth = np.where(inb, 0.97, smooth)
        hgt += 2.6 * dome
    rim = smoothstep(0.975, 0.995, rho)
    col = col + (np.array([0.36, 0.16, 0.10]) - col) * rim[..., None]
    col = np.where((rho > 1.0)[..., None], np.array([0.3, 0.14, 0.1]), col)
    top_col, top_h, top_s = col, hgt, smooth

    # ---- underside: purple-red, raised pale ribs, matte
    base = np.array([0.40, 0.11, 0.16]); b2 = np.array([0.30, 0.07, 0.13])
    col = base + (b2 - base) * np.clip(0.5 + 0.4 * low, 0, 1)[..., None]
    col = col + (np.array([0.58, 0.30, 0.28]) - col) * (0.75 * veins_b)[..., None]
    col = col + (np.array([0.47, 0.20, 0.22]) - col) * (0.25 * fine)[..., None]
    col = col + (np.array([0.36, 0.30, 0.12]) - col) * (0.5 * smoothstep(0.9, 1.0, rho))[..., None]
    col = np.where((rho > 1.0)[..., None], np.array([0.3, 0.14, 0.1]), col)
    bot_col, bot_h, bot_s = col, 1.4 * veins_b + 0.3 * fine + 0.1 * mid, np.full((F, F), 0.3)

    alb = np.concatenate([top_col, bot_col], 1)
    nm = np.concatenate([MK.normal_from_height(top_h, 1.4), MK.normal_from_height(bot_h, 1.6)], 1)
    ao = np.concatenate([1 - 0.25 * veins, 1 - 0.15 * veins_b], 1)
    mk = MK.mask(np.concatenate([top_s, bot_s], 1), ao)
    MK.save_rgb(alb, os.path.join(TEX, 'LilyPad_Albedo.png'))
    MK.save_rgb(nm, os.path.join(TEX, 'LilyPad_Normal.png'))
    MK.save_rgb(mk, os.path.join(TEX, 'LilyPad_Mask.png'))

def flower_textures(seed=21):
    Q = 512; r = np.random.default_rng(seed)
    yy, xx = (np.mgrid[0:Q, 0:Q] + 0.5) / Q
    t = xx * 2 - 1; s = 1 - yy                                     # t across the petal, s from base (0) to tip (1)
    n1 = MK.fbm((Q, Q), [2, 6], seed, [0.6, 1.0])
    streak = gaussian_filter(r.standard_normal((Q, Q)), [14, 1.2]); streak /= streak.std()
    def vein_field(nv=15, w=0.016):
        v = np.zeros((Q, Q))
        for k in range(nv):
            tk = (k / (nv - 1) * 2 - 1) * 0.92
            path = tk * (0.86 + 0.14 * s) + 0.01 * np.sin(s * 9 + k)
            v = np.maximum(v, np.exp(-((t - path) / w) ** 2) * smoothstep(0.98, 0.7, s))
        # side veinlets branching off toward the edges
        for k in range(10):
            s0 = 0.15 + 0.07 * k; tk = (0.25 + 0.06 * (k % 4))
            for sg in (-1, 1):
                path_t = sg * (tk + (s - s0) * 1.6)
                m = (s > s0) & (s < s0 + 0.35)
                v = np.maximum(v, 0.6 * np.exp(-((t - path_t) / 0.012) ** 2) * m)
        return v
    V = vein_field()
    # white petal: green-gold at the base, white body, faint grey-cream veins, a blush at the very tip
    white = np.ones((Q, Q, 3)) * np.array([0.96, 0.955, 0.93])
    white = white + (np.array([0.80, 0.85, 0.52]) - white) * smoothstep(0.22, 0.0, s)[..., None]
    white = white + (np.array([0.97, 0.88, 0.9]) - white) * (0.5 * smoothstep(0.82, 1.0, s))[..., None]
    white = white * (1 - 0.06 * V[..., None]) - 0.012 * n1[..., None]
    # pink petal: deeper rose at the base and in the veins, paling toward the tip
    pink = np.array([0.93, 0.56, 0.68]) + (np.array([0.98, 0.80, 0.86]) - np.array([0.93, 0.56, 0.68])) * smoothstep(0.1, 1.0, s)[..., None]
    pink = pink + (np.array([0.86, 0.80, 0.42]) - pink) * smoothstep(0.12, 0.0, s)[..., None]
    pink = pink + (np.array([0.80, 0.36, 0.52]) - pink) * (0.4 * V)[..., None]
    pink = pink - 0.015 * n1[..., None]
    # sepal back: olive green, darker streaks, purple-brown flecks, white margins
    sep = np.array([0.33, 0.41, 0.18]) * (1 + 0.1 * streak[..., None]) * (0.85 + 0.15 * s[..., None])
    fl = np.clip((MK.fbm((Q, Q), [2.5], seed + 5) - 1.4) * 3, 0, 1)
    sep = sep + (np.array([0.38, 0.18, 0.18]) - sep) * fl[..., None]
    sep = sep + (np.array([0.86, 0.84, 0.74]) - sep) * smoothstep(0.78, 0.97, np.abs(t))[..., None]
    # stamens (left half of the quadrant, along s) and the stigmatic disc (right half, radial)
    sta = np.zeros((Q, Q, 3))
    left = xx < 0.5
    g = np.array([0.95, 0.66, 0.10]) + (np.array([1.0, 0.82, 0.22]) - np.array([0.95, 0.66, 0.10])) * smoothstep(0.3, 0.6, s)[..., None]
    g = g + (np.array([1.0, 0.94, 0.66]) - g) * smoothstep(0.82, 1.0, s)[..., None]
    g = g * (1 - 0.12 * (np.abs(np.sin(xx * 2 * math.pi * 3)) < 0.15)[..., None] * (s > 0.55)[..., None])
    cx, cy = 0.75, 0.5
    R_ = np.hypot(xx - cx, yy - cy) / 0.23; A_ = np.arctan2(yy - cy, xx - cx)
    disc = np.array([0.98, 0.80, 0.22]) + (np.array([0.88, 0.52, 0.08]) - np.array([0.98, 0.80, 0.22])) * smoothstep(0.5, 0.0, R_)[..., None]
    ray = (np.abs(np.sin(A_ * 9)) ** 6) * smoothstep(0.25, 0.9, R_)
    disc = disc * (1 - 0.18 * ray[..., None])
    sta = np.where(left[..., None], g, disc)
    top = np.concatenate([white, pink], 1); bot = np.concatenate([sep, sta], 1)
    alb = np.concatenate([top, bot], 0)
    hp = -0.5 * V
    hs = 0.6 * streak * 0.2
    hst = np.where(left, -0.3 * (np.abs(np.sin(xx * 2 * math.pi * 3)) < 0.2), 0.5 * ray)
    H = np.concatenate([np.concatenate([hp, hp], 1), np.concatenate([hs, hst], 1)], 0)
    nm = MK.normal_from_height(gaussian_filter(H, 0.8), 2.0)
    sm = np.concatenate([np.concatenate([np.full((Q, Q), 0.42)] * 2, 1),
                         np.concatenate([np.full((Q, Q), 0.45), np.full((Q, Q), 0.3)], 1)], 0)
    MK.save_rgb(alb, os.path.join(TEX, 'LilyFlower_Albedo.png'), alpha=np.ones(alb.shape[:2]))
    MK.save_rgb(nm, os.path.join(TEX, 'LilyFlower_Normal.png'))
    MK.save_rgb(MK.mask(sm), os.path.join(TEX, 'LilyFlower_Mask.png'))

# UV rects in the flower atlas: (u0, v0, u1, v1)
UV_WHITE = (0.004, 0.504, 0.496, 0.996)
UV_PINK = (0.504, 0.504, 0.996, 0.996)
UV_SEPAL = (0.004, 0.004, 0.496, 0.496)
UV_STAMEN = (0.51, 0.01, 0.74, 0.49)
UV_DISC_C = (0.75 + 0.0, 0.25); UV_DISC_R = (0.115, 0.115)

# ============================================================================================ geometry
def pad(M, R, c=(0, 0, 0), rot=0.0, seed=0, nth=72, rhos=None, notch=0.13, curl=0.0, curl_at=0.0, uvrot=None,
        under=True, und=1.0):
    """one floating pad of radius R centred at c; the sinus opens toward angle `rot`."""
    r = np.random.default_rng(seed)
    rhos = np.array(rhos if rhos is not None else [0, 0.07, 0.16, 0.27, 0.39, 0.51, 0.62, 0.72, 0.81, 0.88, 0.94, 0.98, 1.0])
    uvrot = r.uniform(0, TAU) if uvrot is None else uvrot
    ph = r.uniform(0, TAU, 6)
    nr = len(rhos)
    T = np.zeros((nth + 1, nr, 3)); UVt = np.zeros((nth + 1, nr, 2)); UVb = np.zeros((nth + 1, nr, 2))
    Au = 0.006 * R / 0.24 * und
    for j in range(nth + 1):
        for i, rho in enumerate(rhos):
            g = notch * rho ** 0.7
            th = g / 2 + (TAU - g) * j / nth
            edge_d = min(th - g / 2, TAU - g / 2 - th)               # angular distance from the sinus edge
            Rm = R * (1 + 0.014 * math.sin(3 * th + ph[0]) + 0.008 * math.sin(7 * th + ph[1]))
            Rm *= 1 - 0.07 * math.exp(-edge_d / 0.09) * rho ** 4     # the lobe tips round off
            x = rho * Rm * math.cos(th + rot); y = rho * Rm * math.sin(th + rot)
            z = 0.0022 + Au * rho ** 3 * (0.6 * math.sin(4 * th + ph[2]) + 0.4 * math.sin(9 * th + ph[3]))
            z += 0.012 * R / 0.24 * rho ** 2 * math.exp(-edge_d / 0.25)          # the lobes lift a little at the sinus
            if curl:
                dang = ((th - curl_at + math.pi) % TAU) - math.pi
                z += curl * smoothstep(0.62, 1.0, rho) ** 2 * math.exp(-(dang / 0.7) ** 2)
            T[j, i] = (c[0] + x, c[1] + y, c[2] + z)
            UVt[j, i] = (0.25 + 0.24 * rho * math.cos(th + uvrot), 0.5 + 0.48 * rho * math.sin(th + uvrot))
            UVb[j, i] = (0.75 + 0.24 * rho * math.cos(th + uvrot), 0.5 + 0.48 * rho * math.sin(th + uvrot))
    # fix the curled rim's thickness direction: offset the underside along the local surface normal
    M.grid(T, UVt, 'Pad', flip=True)
    if not under: return T
    th_ = 0.0018
    Nrm = np.zeros_like(T)
    du = np.gradient(T, axis=0); dv = np.gradient(T, axis=1)
    Nrm = nrm(np.cross(dv, du))
    Nrm[:, 0] = (0, 0, 1)
    Nrm = np.where(Nrm[..., 2:3] < 0, -Nrm, Nrm)
    B = T - Nrm * th_
    M.grid(B, UVb, 'Pad', flip=False)
    # the cut edges: margin ring and the two sides of the sinus
    rim = np.stack([T[:, -1], B[:, -1]], 1); ruv = np.stack([UVb[:, -1], UVb[:, -1]], 1)
    M.grid(rim, ruv, 'Pad', flip=True)
    for j, fl in ((0, False), (nth, True)):
        e = np.stack([T[j], B[j]], 0); euv = np.stack([UVb[j], UVb[j]], 0)
        M.grid(e, euv, 'Pad', flip=fl)
    return T

def _uv(rect, u, v):
    u0, v0, u1, v1 = rect
    return np.stack([u0 + (u1 - u0) * u, v0 + (v1 - v0) * v], -1)

def width_petal(s):
    return 0.2 * (1 - s) ** 2 + 0.8 * np.sin(math.pi * np.clip(s, 0, 1) ** 0.66) ** 0.8

def width_sepal(s):
    return 0.28 * (1 - s) ** 2 + 0.72 * np.sin(math.pi * np.clip(s, 0, 1) ** 0.6) ** 0.9

def ribbon(M, base, d, n, L, W, cup=0.3, curl=0.0, twist=0.0, nu=7, nv=9, wfun=width_petal, rect=UV_WHITE,
           back=None, thick=0.0008, m='Flower', droop=0.0):
    """a petal/sepal/stamen blade: from base along d, inner face n; curls toward n by `curl` radians along its length,
    edges cupped toward n; back = UV rect for a separate underside (sepals)."""
    d = nrm(d); n = nrm(n - d * np.dot(n, d)); side = nrm(np.cross(n, d))
    S = np.linspace(0, 1, nv); Tt = np.linspace(-1, 1, nu)
    phi = curl * S ** 1.4 - droop * S ** 2
    dirs = np.outer(np.cos(phi), d) + np.outer(np.sin(phi), n)
    nn = np.outer(np.cos(phi), n) - np.outer(np.sin(phi), d)
    ds = L / (nv - 1)
    cl = np.concatenate([[np.asarray(base, float)], np.asarray(base, float) + np.cumsum((dirs[:-1] + dirs[1:]) / 2 * ds, 0)])
    P = np.zeros((nu, nv, 3))
    for j, s in enumerate(S):
        w = W * wfun(s)
        a = twist * s
        sd = side * math.cos(a) + np.cross(dirs[j], side) * math.sin(a)
        for i, t in enumerate(Tt):
            P[i, j] = cl[j] + sd * (w * t) + nn[j] * (cup * w * t * t)
    uu, vv = np.meshgrid((Tt + 1) / 2, S, indexing='ij')
    M.grid(P, _uv(rect, uu, vv), m, flip=True)               # the inner face (+n) faces out
    if back is not None:
        Pn = np.zeros_like(P)
        for j in range(nv): Pn[:, j] = P[:, j] - nn[j] * thick
        M.grid(Pn, _uv(back, uu, vv), m, flip=False)
    return P

def flower(M, c, fs=1.0, kind='white', seed=0, rot=0.0, lod=0):
    """an open Nymphaea flower, base at c, overall ~16 cm across at fs = 1."""
    r = np.random.default_rng(seed)
    rect = UV_WHITE if kind == 'white' else UV_PINK
    c = np.asarray(c, float)
    up = np.array([0, 0, 1.0])
    nu, nv = (7, 9) if lod == 0 else (3, 4)
    def blade(alpha, elev, r0, z0, L, W, **kw):
        a = math.radians(alpha + rot); e = math.radians(elev)
        d = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        n = np.array([-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e)])
        base = c + np.array([r0 * math.cos(a), r0 * math.sin(a), z0]) * fs
        return ribbon(M, base, d, n, L * fs, W * fs, nu=kw.pop('nu', nu), nv=kw.pop('nv', nv), **kw)
    # receptacle: a small green cup under it all
    nth, nph = (12, 5) if lod == 0 else (6, 3)
    P = np.zeros((nth + 1, nph, 3)); UV = np.zeros((nth + 1, nph, 2))
    for j in range(nth + 1):
        for i in range(nph):
            a = TAU * j / nth; p = math.pi * (0.5 + 0.45 * i / (nph - 1))
            P[j, i] = c + np.array([0.013 * math.sin(p) * math.cos(a), 0.013 * math.sin(p) * math.sin(a), 0.006 + 0.011 * math.cos(p)]) * fs
            UV[j, i] = _uv(UV_SEPAL, j / nth, 0.2 + 0.6 * i / (nph - 1))
    M.grid(P, UV, 'Flower', flip=True)
    # four sepals lying almost flat, white inside, olive outside
    for k in range(4):
        blade(45 + 90 * k + r.uniform(-8, 8), r.uniform(4, 12), 0.011, 0.004, 0.068 * r.uniform(0.95, 1.05), 0.026,
              cup=0.28, curl=-0.1, droop=0.12, wfun=width_sepal, rect=rect, back=UV_SEPAL, twist=r.uniform(-0.15, 0.15))
    whorls = [(8, 0, 18, 0.011, 0.006, 0.071, 0.025, 0.42), (8, 22.5, 34, 0.010, 0.009, 0.064, 0.023, 0.5),
              (7, 9, 52, 0.009, 0.012, 0.055, 0.020, 0.6), (5, 37, 68, 0.008, 0.015, 0.046, 0.017, 0.7)]
    if kind != 'white':
        whorls = [(n_, o, e + 6, r0, z0, L, W, cu) for (n_, o, e, r0, z0, L, W, cu) in whorls]
    if lod: whorls = whorls[:2] + whorls[3:]
    for (cnt, off, elev, r0, z0, L, W, cup) in whorls:
        for k in range(cnt):
            blade(off + 360 * k / cnt + r.uniform(-7, 7), elev + r.uniform(-6, 6), r0, z0, L * r.uniform(0.92, 1.06), W * r.uniform(0.92, 1.08),
                  cup=cup, curl=0.18 + 0.004 * elev, twist=r.uniform(-0.25, 0.25), rect=rect)
    # stigmatic disc
    nd = 14 if lod == 0 else 6
    P = [c + np.array([0, 0, 0.0165]) * fs]; UV = [UV_DISC_C]; F = []
    for j in range(nd):
        a = TAU * j / nd
        P.append(c + np.array([0.0078 * math.cos(a), 0.0078 * math.sin(a), 0.0185]) * fs)
        UV.append((UV_DISC_C[0] + UV_DISC_R[0] * math.cos(a), UV_DISC_C[1] + UV_DISC_R[1] * math.sin(a)))
        F.append((0, 1 + j, 1 + (j + 1) % nd))
    M.tris(P, UV, F, 'Flower')
    if lod: return
    # stamens: outer petaloid ones broad, inner ones slender, all curving in over the disc
    for ring, (cnt, r0, z0, L, W, elev, curl) in enumerate([(26, 0.0095, 0.014, 0.026, 0.0036, 62, 0.55), (22, 0.0082, 0.016, 0.019, 0.0018, 74, 0.7)]):
        for k in range(cnt):
            blade(360 * (k + 0.5 * ring) / cnt + r.uniform(-4, 4), elev + r.uniform(-6, 6), r0, z0, L * r.uniform(0.9, 1.1), W,
                  cup=0.2, curl=curl, nu=2, nv=5, rect=UV_STAMEN, wfun=lambda s: 0.7 + 0.3 * np.sin(math.pi * s))
    for k in range(12):                                             # carpellary appendages round the disc
        a = 360 * k / 12
        blade(a, 70, 0.0074, 0.0182, 0.006, 0.0016, cup=0.1, curl=0.9, nu=2, nv=3, rect=UV_STAMEN, wfun=lambda s: 1 - 0.6 * s)

def bud(M, c, fs=1.0, kind='white', seed=0, lod=0):
    r = np.random.default_rng(seed)
    rect = UV_WHITE if kind == 'white' else UV_PINK
    c = np.asarray(c, float)
    nu, nv = (5, 7) if lod == 0 else (3, 4)
    # the stalk rising out of the water
    nth = 6
    P = np.zeros((nth + 1, 2, 3)); UV = np.zeros((nth + 1, 2, 2))
    for j in range(nth + 1):
        a = TAU * j / nth
        for i, z in enumerate((-0.08, 0.0)):
            P[j, i] = c + np.array([0.0045 * math.cos(a), 0.0045 * math.sin(a), z]) * fs + np.array([0.004 * (z + 0.08) * 10, 0, 0])
            UV[j, i] = _uv(UV_SEPAL, j / nth, 0.1 + 0.3 * i)
    M.grid(P, UV, 'Flower', flip=False)
    def blade(alpha, elev, r0, z0, L, W, **kw):
        a = math.radians(alpha); e = math.radians(elev)
        d = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        n = np.array([-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e)])
        base = c + np.array([r0 * math.cos(a), r0 * math.sin(a), z0]) * fs
        return ribbon(M, base, d, n, L * fs, W * fs, nu=nu, nv=nv, **kw)
    for k in range(5):                                              # petal tips showing at the top
        blade(72 * k + 20, 82, 0.006, 0.004, 0.05, 0.022, cup=0.5, curl=0.55, rect=rect)
    for k in range(4):                                              # sepals wrapped round the bud
        blade(90 * k + r.uniform(-5, 5), 74, 0.008, 0.0, 0.052, 0.03, cup=0.75, curl=0.62, wfun=width_sepal,
              rect=UV_SEPAL, back=UV_SEPAL)

# ============================================================================================ the three lilies
PAD = dict(shader='prop', albedo='WaterLily/LilyPad_Albedo.png', normal='WaterLily/LilyPad_Normal.png', mask='WaterLily/LilyPad_Mask.png',
           alpha='OPAQUE', smooth=1.0, metal=0.0, doubleSided=False)
FLOWER = dict(shader='foliage', albedo='WaterLily/LilyFlower_Albedo.png', normal='WaterLily/LilyFlower_Normal.png', mask='WaterLily/LilyFlower_Mask.png',
              alpha='MASK', cutoff=0.3, wind=0.0, windScale=1.0, translucency=0.9, smooth=0.9)
MATS = {'Pad': PAD, 'Flower': FLOWER}
LOD_RHO = [0, 0.3, 0.62, 0.86, 1.0]

def lily_white(lod=0):
    M = MK.Mesh()
    kw = dict(nth=72) if lod == 0 else dict(nth=24, rhos=LOD_RHO, under=False)
    pad(M, 0.24, (0, 0, 0), rot=0.0, seed=1, uvrot=0.4, **kw)
    flower(M, (0.235, 0.02, 0.012), 1.0, 'white', seed=3, rot=10, lod=lod)
    return M

def lily_pink(lod=0):
    M = MK.Mesh()
    kw = dict(nth=72) if lod == 0 else dict(nth=24, rhos=LOD_RHO, under=False)
    kw2 = dict(nth=48) if lod == 0 else dict(nth=16, rhos=LOD_RHO, under=False)
    pad(M, 0.22, (0, 0, 0), rot=2.4, seed=5, uvrot=2.0, **kw)
    pad(M, 0.11, (0.27, 0.17, 0.003), rot=4.0, seed=6, uvrot=4.4, curl=0.012, curl_at=1.0, **kw2)
    flower(M, (0.05, -0.26, 0.012), 0.92, 'pink', seed=7, rot=40, lod=lod)
    bud(M, (0.3, -0.06, 0.03), 0.9, 'pink', seed=8, lod=lod)
    return M

def lily_pads(lod=0):
    M = MK.Mesh()
    kw = dict(nth=72) if lod == 0 else dict(nth=24, rhos=LOD_RHO, under=False)
    kw2 = dict(nth=56) if lod == 0 else dict(nth=18, rhos=LOD_RHO, under=False)
    pad(M, 0.24, (0, 0, 0), rot=1.1, seed=9, uvrot=1.0, **kw)
    pad(M, 0.17, (0.37, 0.15, 0.0035), rot=5.0, seed=10, uvrot=3.1, curl=0.03, curl_at=0.3, **kw2)
    pad(M, 0.12, (-0.1, 0.33, 0.003), rot=3.6, seed=12, uvrot=5.2, curl=0.022, curl_at=4.9, **kw2)
    return M

def main(tex=True):
    if tex:
        pad_textures(); flower_textures()
        print('textures written', flush=True)
    man = MK.load_manifest()
    for name, fn in (('WaterLily', lily_white), ('WaterLily_Pink', lily_pink), ('WaterLily_Pads', lily_pads)):
        MK.export(fn(0), name, MATS, man, lod1=fn(1))
    MK.save_manifest(man)

if __name__ == '__main__':
    main(tex='--notex' not in sys.argv)
