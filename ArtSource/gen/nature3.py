"""v3 nature: palms without the dead hanging fronds (redline 2), tall coconut palms + fallen coconuts (redline 4),
and GPU-animated tropical fish schools (redlines 1, 6). Run: python3 gen/nature3.py"""
import os, sys, json, math, numpy as np
from math import pi, sin, cos
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nature as NA
import assets as AS
from PIL import Image
from scipy.ndimage import label, find_objects
import bpy

A = os.path.join(HERE, '..', 'assets')

def blade_rects():
    f = os.path.join(A, 'ambientcg', 'Foliage001_2K-JPG')
    op = Image.open(NA.first(f + '/*_Opacity.jpg')).convert('L')
    o = np.asarray(op.resize((512, 512)), np.float32) / 255 > 0.3
    lab, n = label(o)
    rects = []
    for sl in find_objects(lab):
        y0, y1 = sl[0].start, sl[0].stop; x0, x1 = sl[1].start, sl[1].stop
        if (y1 - y0) > 120 and (x1 - x0) < 60:
            rects.append([x0 / 512, 1 - y1 / 512, x1 / 512, 1 - y0 / 512])
    return rects

def make_palm3(seed, blades, tall=False):
    r = np.random.default_rng(seed)
    B = NA.Builder()
    if tall:
        H = r.uniform(13.0, 17.0); lean = r.uniform(1.8, 4.2)
    else:
        H = r.uniform(7.5, 11.5); lean = r.uniform(1.2, 3.5)
    ang = r.uniform(0, 2 * pi)
    p0 = np.array([0, 0, 0.0]); p2 = np.array([cos(ang) * lean, sin(ang) * lean, H])
    p1 = np.array([cos(ang) * lean * (0.05 if tall else 0.1), sin(ang) * lean * (0.05 if tall else 0.1), H * (0.5 if tall else 0.55)])
    seg = 14; nh = 48 if tall else 36
    rings = []; uvs = []
    for j in range(nh + 1):
        t = j / nh
        c = NA.curve_point(p0, p1, p2, t)
        tan = 2 * (1 - t) * (p1 - p0) + 2 * t * (p2 - p1); tan /= np.linalg.norm(tan)
        side = np.cross(tan, [0, 0, 1.0]); side /= np.linalg.norm(side) + 1e-9
        up = np.cross(side, tan)
        rad = (0.16 if tall else 0.17) + 0.07 * (1 - t) + 0.12 * max(0, 0.08 - t) * 12 + 0.012 * sin(t * H * 8)
        ring = []; uu = []
        for i in range(seg + 1):
            a = 2 * pi * i / seg
            ring.append(c + (side * cos(a) + up * sin(a)) * rad)
            uu.append((i / seg * 1.5, t * H / 1.2))
        rings.append(ring); uvs.append(uu)
    B.quad_strip(rings, uvs, 'PalmBark')
    top = p2
    # crown shaft bulge + coconut cluster hanging under the fronds
    for k in range(r.integers(7, 13) if tall else r.integers(5, 10)):
        a = r.uniform(0, 2 * pi); d = r.uniform(0.18, 0.32)
        c = top + np.array([cos(a) * d, sin(a) * d, -r.uniform(0.15, 0.55)])
        B.sphere(c, r.uniform(0.11, 0.15), 'Coconut', seg=6)
    nf = r.integers(16, 21) if tall else r.integers(13, 18)
    for f in range(nf):
        a = 2 * pi * f / nf + r.uniform(-0.15, 0.15)
        elev = r.uniform(0.1, 0.8) if f % 3 else r.uniform(-0.25, 0.25)       # some fronds level, none hanging limp
        L = r.uniform(4.0, 5.4) if tall else r.uniform(3.4, 4.6)
        d0 = np.array([cos(a) * cos(elev), sin(a) * cos(elev), sin(elev)])
        droop = r.uniform(1.3, 2.4)
        pts = np.array([top + d0 * L * (k / 15) + np.array([0, 0, -droop * (k / 15) ** 2 * L / 4]) for k in range(16)])
        rr = []; ru = []
        for k, p in enumerate(pts):
            tg = pts[min(k + 1, 15)] - pts[max(k - 1, 0)]; tg /= np.linalg.norm(tg)
            sd = np.cross(tg, [0, 0, 1.0]); sd /= np.linalg.norm(sd) + 1e-9; upv = np.cross(sd, tg)
            rad = 0.035 * (1 - k / 16) + 0.008
            rr.append([p + (sd * cos(q) + upv * sin(q)) * rad for q in np.linspace(0, 2 * pi, 5)])
            ru.append([(q / (2 * pi) * 0.2, k / 15 * 2) for q in np.linspace(0, 2 * pi, 5)])
        B.quad_strip(rr, ru, 'PalmBark')
        nl = 50 if tall else 46
        for k in range(2, nl):
            t = k / nl
            idx = t * 15; i0 = int(idx); fr = idx - i0
            p = pts[i0] * (1 - fr) + pts[min(i0 + 1, 15)] * fr
            tg = pts[min(i0 + 1, 15)] - pts[i0]; tg /= np.linalg.norm(tg)
            sd = np.cross(tg, [0, 0, 1.0]); sd /= np.linalg.norm(sd) + 1e-9
            ln = (0.35 + 0.55 * sin(pi * min(1, t * 1.15))) * r.uniform(0.85, 1.1) * (1.1 if tall else 1.0)
            w = 0.12 * (0.7 + 0.3 * sin(pi * t))
            for s in (-1, 1):
                dirv = sd * s * 0.8 + tg * 0.45 + np.array([0, 0, -0.35 - 0.2 * t]); dirv /= np.linalg.norm(dirv)
                wv = np.cross(dirv, sd * s); wv /= np.linalg.norm(wv) + 1e-9
                tip = p + dirv * ln + np.array([0, 0, -0.1 * ln])
                rect = blades[r.integers(len(blades))]
                B.card(p - wv * w * 0.5, p + wv * w * 0.5, tip + wv * w * 0.3, tip - wv * w * 0.3, rect, 'PalmLeaf')
    return B, H

def coconuts(seed):
    r = np.random.default_rng(seed)
    B = NA.Builder()
    for k in range(3):
        c = np.array([r.uniform(-0.35, 0.35), r.uniform(-0.35, 0.35), 0.11])
        B.sphere(c, 0.13, 'CoconutHusk', seg=7)
    # flatten into husky ovoids
    for i, v in enumerate(B.V):
        B.V[i] = v * np.array([1.0, 0.82, 0.78]) + np.array([0, 0, 0])
    return B

# ------------------------------------------------------------------ fish schools (animated in the Fish shader)
def fish_school(seed, n, length, rho, height, species):
    """vertex colour: R phase, G radius fraction, B body coordinate (0 tail .. 1 nose), A species*64.
    Fish swim counter-clockwise (seen from above) around the object's Y axis; the shader turns the whole school."""
    r = np.random.default_rng(seed)
    V = []; N = []; C = []; U = []; F = []
    for k in range(n):
        L = r.uniform(*length)
        rad = r.uniform(*rho); ang = r.uniform(0, 2 * pi); y = r.uniform(-height, height)
        c = np.array([cos(ang) * rad, y, sin(ang) * rad])
        fwd = np.array([-sin(ang), 0.0, cos(ang)])                  # CCW tangent in x-z (Unity)
        jit = r.uniform(-0.2, 0.2)
        fwd = np.array([fwd[0] * cos(jit) - fwd[2] * sin(jit), r.uniform(-0.08, 0.08), fwd[0] * sin(jit) + fwd[2] * cos(jit)])
        fwd /= np.linalg.norm(fwd)
        up = np.array([0, 1.0, 0]); lat = np.cross(up, fwd); lat /= np.linalg.norm(lat); up = np.cross(fwd, lat)
        sp = species[r.integers(len(species))]
        deep = 0.18 if sp in (0, 1) else 0.11
        pts = {'nose': c + fwd * 0.5 * L, 'top': c + fwd * 0.05 * L + up * deep * L * 1.6, 'bot': c - up * deep * L * 1.1,
               'l': c + lat * 0.08 * L, 'r': c - lat * 0.08 * L, 'tail': c - fwd * 0.32 * L,
               'ft': c - fwd * 0.56 * L + up * 0.17 * L, 'fb': c - fwd * 0.56 * L - up * 0.17 * L}
        bodyc = {'nose': 1.0, 'top': 0.55, 'bot': 0.55, 'l': 0.55, 'r': 0.55, 'tail': 0.2, 'ft': 0.0, 'fb': 0.0}
        order = ['nose', 'top', 'bot', 'l', 'r', 'tail', 'ft', 'fb']
        base = len(V)
        ph = r.random()
        for key in order:
            p = pts[key]; V.append(p)
            nn = p - c; nn = nn / (np.linalg.norm(nn) + 1e-9); N.append(nn)
            C.append([int(ph * 255), int(255 * (rad - rho[0]) / max(1e-3, rho[1] - rho[0])), int(bodyc[key] * 255), sp * 64 + 16])
            vv = 0.5 + float((p - c) @ up) / (0.45 * L)
            U.append([bodyc[key], vv])
        i = {kk: base + j for j, kk in enumerate(order)}
        F += [(i['nose'], i['top'], i['l']), (i['nose'], i['l'], i['bot']), (i['nose'], i['bot'], i['r']), (i['nose'], i['r'], i['top']),
              (i['tail'], i['l'], i['top']), (i['tail'], i['bot'], i['l']), (i['tail'], i['r'], i['bot']), (i['tail'], i['top'], i['r']),
              (i['tail'], i['ft'], i['fb'])]
    return np.array(V), np.array(N), np.array(C, np.uint8), np.array(U), np.array(F)

def write_uv_mesh(name, V, N, C, U, F, sub):
    import struct
    MESH = os.path.join(HERE, '..', 'out', 'Meshes')
    with open(os.path.join(MESH, name + '.bytes'), 'wb') as f:
        f.write(b'PMS2'); f.write(struct.pack('<iii', len(V), 1, 1))
        f.write(V.astype('<f4').tobytes()); f.write(N.astype('<f4').tobytes()); f.write(C.astype(np.uint8).tobytes()); f.write(U.astype('<f4').tobytes())
        b = sub.encode(); f.write(struct.pack('<i', len(b))); f.write(b)
        idx = F.ravel().astype('<i4'); f.write(struct.pack('<i', len(idx))); f.write(idx.tobytes())
    print(name, len(V), 'verts', len(F), 'tris')

if __name__ == '__main__':
    man = json.load(open(AS.MANIFEST))
    P = 'Palm/'
    sh = {
        'PalmBark': dict(shader='prop', albedo=P + 'PalmBark_Albedo.png', normal=P + 'PalmBark_Normal.png', mask=P + 'PalmBark_Mask.png', alpha='OPAQUE'),
        'PalmLeaf': dict(shader='foliage', albedo=P + 'PalmLeaf_Albedo.png', normal=P + 'PalmLeaf_Normal.png', mask=P + 'PalmLeaf_Mask.png', alpha='MASK', wind=0.55, windScale=10),
        'Coconut': dict(shader='prop', albedo=P + 'Coconut_Albedo.png', alpha='OPAQUE', smooth=0.35),
        'CoconutHusk': dict(shader='prop', albedo=P + 'PalmBark_Albedo.png', alpha='OPAQUE', tint=[0.62, 0.45, 0.3], smooth=0.2),
    }
    blades = blade_rects()
    heights = {}
    for i in range(3):
        B, H = make_palm3(100 + i, blades); NA.export(B, f'Palm_{i}', man, sh); heights[f'Palm_{i}'] = H
    for i in range(3):
        B, H = make_palm3(150 + i, blades, tall=True); NA.export(B, f'Palm_Tall_{i}', man, sh); heights[f'Palm_Tall_{i}'] = H
    NA.export(coconuts(170), 'Coconuts', man, sh)
    FISH = dict(shader='fish', alpha='OPAQUE')
    for name, seed, n, ln, rho, hgt, spc, spd in (('FishSchool_Tang', 1, 46, (0.22, 0.3), (1.2, 2.6), 0.5, (0, 0, 1), 0.22),
                                                  ('FishSchool_Chromis', 2, 90, (0.09, 0.13), (0.8, 1.9), 0.35, (3,), 0.35),
                                                  ('FishSchool_Reef', 3, 32, (0.14, 0.24), (0.7, 2.2), 0.45, (0, 1, 2, 3), 0.28)):
        V, N, C, U, F = fish_school(seed, n, ln, rho, hgt, spc)
        write_uv_mesh(name, V, N, C, U, F, name + '_Fish')
        man[name] = [dict(sub=name + '_Fish', wind=spd, **FISH)]
    json.dump(man, open(AS.MANIFEST, 'w'), indent=1)
    json.dump(heights, open(os.path.join(HERE, '..', 'out', 'Data', 'PalmHeights.json'), 'w'), indent=1)
    print('nature3 done', heights)
