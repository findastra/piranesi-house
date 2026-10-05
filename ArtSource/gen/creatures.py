"""Hand-modelled creatures (no free realistic scans exist): bottlenose dolphin, Laysan-style albatross, nest + egg."""
import os, sys, json, math, numpy as np
from math import pi, sin, cos
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import assets as AS, nature as NA
from PIL import Image
from scipy.ndimage import gaussian_filter
OUT = os.path.join(AS.OUTI, 'Creatures'); os.makedirs(OUT, exist_ok=True)
MAN = json.load(open(AS.MANIFEST))
rng = np.random.default_rng(5)

def interp(t, keys):
    ks = np.array(keys, float)
    return np.interp(t, ks[:, 0], ks[:, 1])

# ------------------------------------------------------------------ dolphin
def dolphin_texture():
    W, H = 512, 256
    v, u = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]  # v along body (0 tail .. 1 snout), u around (0 = top)
    up = np.cos(2 * pi * u)                                      # 1 on the back, -1 on the belly
    cape = np.clip((up - 0.15 + 0.35 * np.sin(v * pi * 1.4)) * 3, 0, 1)
    belly = np.clip((-up - 0.35) * 3, 0, 1)
    n = gaussian_filter(rng.random((H, W)), 3)
    col = np.array([0.5, 0.53, 0.56])[None, None] * (1 - cape[..., None]) + np.array([0.24, 0.26, 0.29])[None, None] * cape[..., None]
    col = col * (1 - belly[..., None]) + np.array([0.86, 0.84, 0.84])[None, None] * belly[..., None]
    col *= (0.95 + 0.1 * n)[..., None]
    # eye (dark spot both sides near the snout)
    for su in (0.27, 0.73):
        d = np.sqrt(((u - su) * 4) ** 2 + ((v - 0.86) * 10) ** 2)
        col = col * (1 - np.exp(-d * d * 30)[..., None] * 0.8)
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, 'Dolphin_Albedo.png'))

def make_dolphin():
    B = NA.Builder()
    L = 2.5; nl = 48; nr = 18
    hk = [(0, 0.035), (0.08, 0.07), (0.18, 0.12), (0.35, 0.2), (0.55, 0.26), (0.72, 0.24), (0.82, 0.2), (0.88, 0.17), (0.92, 0.1), (0.96, 0.06), (1.0, 0.025)]
    wk = [(0, 0.02), (0.08, 0.035), (0.18, 0.07), (0.35, 0.17), (0.55, 0.23), (0.72, 0.21), (0.82, 0.17), (0.88, 0.13), (0.92, 0.07), (0.96, 0.045), (1.0, 0.02)]
    ck = [(0, 0.0), (0.5, 0.0), (0.84, 0.02), (0.9, -0.03), (1.0, -0.05)]  # centre-line height (snout lower than melon)
    rings = []; uvs = []
    for i in range(nl + 1):
        t = i / nl; x = (t - 0.5) * L
        h = interp(t, hk); w = interp(t, wk); c = interp(t, ck)
        ring = []; uu = []
        for j in range(nr + 1):
            a = 2 * pi * j / nr
            y = sin(a) * w; z = c + cos(a) * h * (1.0 if cos(a) > 0 else 0.85)
            ring.append((x, y, z)); uu.append((j / nr, t))
        rings.append(ring); uvs.append(uu)
    B.quad_strip(rings, uvs, 'Dolphin')
    def fin(base_pts, tip, mat='Dolphin'):
        p = [np.array(q) for q in base_pts]
        B.card(p[0], p[1], tip, tip, (0.05, 0.05, 0.06, 0.06), mat)
        B.card(p[1], p[0], tip, tip, (0.05, 0.05, 0.06, 0.06), mat)
    # dorsal fin (falcate)
    fin([(-0.05, 0, 0.24), (0.32, 0, 0.25)], np.array([-0.2, 0, 0.55]))
    # pectorals
    for s in (-1, 1):
        fin([(0.42, s * 0.18, -0.08), (0.62, s * 0.17, -0.1)], np.array([0.38, s * 0.48, -0.22]))
    # flukes
    for s in (-1, 1):
        fin([(-1.22, 0, 0.0), (-1.05, 0, 0.0)], np.array([-1.38, s * 0.34, 0.0]))
        fin([(-1.25, s * 0.02, 0.0), (-1.38, s * 0.34, 0.0)], np.array([-1.3, s * 0.15, 0.0]))
    dolphin_texture()
    ob = B.build('Dolphin'); AS.export_pms2(ob, 'Dolphin', ['Dolphin_Dolphin'])
    MAN['Dolphin'] = [dict(sub='Dolphin_Dolphin', shader='prop', alpha='OPAQUE', albedo='Creatures/Dolphin_Albedo.png', smooth=0.8, doubleSided=True)]
    print('Dolphin', flush=True)

# ------------------------------------------------------------------ albatross (swatch atlas texture)
SW = {'white': (0, 0), 'dark': (1, 0), 'bill': (2, 0), 'tip': (3, 0), 'eye': (0, 1), 'grey': (1, 1), 'egg': (2, 1), 'mud': (3, 1)}
def swatch_texture():
    cols = {'white': (0.94, 0.94, 0.92), 'dark': (0.2, 0.18, 0.17), 'bill': (0.93, 0.66, 0.68), 'tip': (0.35, 0.33, 0.33),
            'eye': (0.08, 0.07, 0.07), 'grey': (0.62, 0.62, 0.6), 'egg': (0.96, 0.94, 0.88), 'mud': (0.42, 0.35, 0.26)}
    im = np.zeros((256, 512, 3))
    n = gaussian_filter(rng.random((256, 512)), 2)
    for k, (cx, cy) in SW.items():
        im[cy * 128:(cy + 1) * 128, cx * 128:(cx + 1) * 128] = cols[k]
    im *= (0.93 + 0.12 * n)[..., None]
    Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, 'Swatch_Albedo.png'))
def sw(k):
    cx, cy = SW[k]
    return (cx / 4 + 0.03, 1 - (cy + 1) / 2 + 0.03, (cx + 1) / 4 - 0.03, 1 - cy / 2 - 0.03)

def loft(B, pts, radii, mat, nr=12, flat=1.0):
    rings = []; uvs = []
    u0, v0, u1, v1 = sw(mat)
    for i, (p, r) in enumerate(zip(pts, radii)):
        p = np.array(p, float)
        tg = np.array(pts[min(i + 1, len(pts) - 1)], float) - np.array(pts[max(i - 1, 0)], float); tg /= np.linalg.norm(tg) + 1e-9
        s = np.cross(tg, [0, 0, 1.0]); s /= np.linalg.norm(s) + 1e-9; u = np.cross(s, tg)
        rings.append([p + s * cos(a) * r + u * sin(a) * r * flat for a in np.linspace(0, 2 * pi, nr + 1)])
        uvs.append([(u0 + (u1 - u0) * j / nr, v0 + (v1 - v0) * i / max(1, len(pts) - 1)) for j in range(nr + 1)])
    B.quad_strip(rings, uvs, mat)

def make_albatross():
    swatch_texture()
    B = NA.Builder()
    # body (white), sitting: along +x (head end)
    bx = np.linspace(-0.42, 0.3, 12)
    loft(B, [(x, 0, 0.17 + 0.02 * sin(x * 4)) for x in bx], [0.05 + 0.14 * max(0.0, sin(pi * (x + 0.42) / 0.72)) ** 0.7 for x in bx], 'white', nr=16)
    # neck + head
    loft(B, [(0.26, 0, 0.22), (0.32, 0, 0.3), (0.37, 0, 0.36), (0.42, 0, 0.38)], [0.08, 0.07, 0.07, 0.065], 'white', nr=12)
    loft(B, [(0.4, 0, 0.38), (0.45, 0, 0.385), (0.49, 0, 0.375)], [0.07, 0.068, 0.05], 'white', nr=12)
    # bill: long, slightly hooked
    loft(B, [(0.49, 0, 0.372), (0.55, 0, 0.366), (0.6, 0, 0.358), (0.64, 0, 0.35)], [0.026, 0.02, 0.015, 0.01], 'bill', nr=8, flat=1.3)
    loft(B, [(0.64, 0, 0.35), (0.665, 0, 0.343), (0.672, 0, 0.33)], [0.011, 0.009, 0.004], 'tip', nr=8)
    # eyes + dark smudge
    for s in (-1, 1):
        B.sphere((0.455, s * 0.055, 0.395), 0.012, 'eye', seg=4)
    # folded wings: long dark slabs over the back & sides
    for s in (-1, 1):
        wp = [(0.2, s * 0.12, 0.27), (0.0, s * 0.15, 0.3), (-0.25, s * 0.13, 0.28), (-0.5, s * 0.08, 0.24), (-0.62, s * 0.04, 0.21)]
        loft(B, wp, [0.05, 0.065, 0.06, 0.04, 0.015], 'dark', nr=10, flat=0.45)
    loft(B, [(-0.4, 0, 0.2), (-0.55, 0, 0.21), (-0.6, 0, 0.215)], [0.06, 0.04, 0.01], 'dark', nr=8, flat=0.4)
    ob = B.build('Albatross'); AS.export_pms2(ob, 'Albatross', [f'Albatross_{m}' for m in B.mats])
    MAN['Albatross'] = [dict(sub=f'Albatross_{m}', shader='prop', alpha='OPAQUE', albedo='Creatures/Swatch_Albedo.png', smooth=0.3) for m in B.mats]
    # nest: mud/grass ring + egg
    N = NA.Builder()
    rings = []; uvs = []
    for i in range(9):
        t = i / 8; a = None
    prof = [(0.0, 0.05), (0.28, 0.06), (0.42, 0.14), (0.52, 0.2), (0.6, 0.12), (0.65, 0.0)]
    u0, v0, u1, v1 = sw('mud')
    rings = [[(r * cos(a) * (1 + 0.06 * sin(a * 5)), r * sin(a) * (1 + 0.06 * sin(a * 5)), z) for a in np.linspace(0, 2 * pi, 25)] for r, z in prof]
    uvs = [[(u0 + (u1 - u0) * j / 24, v0 + (v1 - v0) * i / 5) for j in range(25)] for i in range(len(prof))]
    N.quad_strip(rings, uvs, 'mud')
    blades = [[0.05, 0.05, 0.1, 0.95]]
    for k in range(70):
        a = rng.uniform(0, 2 * pi); r = rng.uniform(0.42, 0.62)
        p = np.array([r * cos(a), r * sin(a), 0.12])
        d = np.array([cos(a + rng.uniform(1.2, 1.9)), sin(a + rng.uniform(1.2, 1.9)), rng.uniform(0.0, 0.25)])
        q = p + d * rng.uniform(0.2, 0.35); sd = np.array([0, 0, 0.012])
        N.card(p - sd, p + sd, q + sd, q - sd, (0.2, 0.05, 0.25, 0.95), 'grass')
    egg = [(0.0, -0.02), (0.035, -0.015), (0.05, 0.02), (0.045, 0.06), (0.03, 0.09), (0.0, 0.1)]
    u0, v0, u1, v1 = sw('egg')
    rings = [[(0.1 + r * cos(a), r * sin(a), 0.07 + z) for a in np.linspace(0, 2 * pi, 13)] for r, z in egg]
    N.quad_strip(rings, [[(u0 + (u1 - u0) * j / 12, v0 + (v1 - v0) * i / 5) for j in range(13)] for i in range(len(egg))], 'egg')
    ob = N.build('Nest'); AS.export_pms2(ob, 'Nest', [f'Nest_{m}' for m in N.mats])
    leaf = MAN.get('BeachGrass', [{}])[0]
    MAN['Nest'] = []
    for m in N.mats:
        if m == 'grass':
            MAN['Nest'].append(dict(sub='Nest_grass', shader='foliage', alpha='MASK', albedo='Palm/PalmLeaf_Albedo.png', tint=[0.85, 0.75, 0.5], wind=0.2, windScale=0.5))
        else:
            MAN['Nest'].append(dict(sub=f'Nest_{m}', shader='prop', alpha='OPAQUE', albedo='Creatures/Swatch_Albedo.png', smooth=0.2))
    print('Albatross + Nest', flush=True)

if __name__ == '__main__':
    make_dolphin(); make_albatross()
    json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1)
