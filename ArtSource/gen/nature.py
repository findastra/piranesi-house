"""Coconut palms, hibiscus shrubs and beach grass, built in Blender from real scanned textures
(Poly Haven palm bark, ambientCG blade/leaf atlases) plus generated hibiscus leaf/petal textures."""
import bpy, os, sys, json, math, numpy as np, glob
from math import pi, sin, cos
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter, label, find_objects

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import assets as AS  # exporter + manifest helpers

ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'assets')
OUTI = AS.OUTI
rng = np.random.default_rng(31)

def mask_png(rough_path, ao_path, size, out):
    r = np.asarray(Image.open(rough_path).convert('L').resize(size), np.float32) / 255 if rough_path else np.full(size[::-1], 0.6)
    a = np.asarray(Image.open(ao_path).convert('L').resize(size), np.float32) / 255 if ao_path else np.ones(size[::-1])
    m = np.stack([1 - r, a, np.zeros_like(r), np.ones_like(r)], -1)
    Image.fromarray((m * 255).astype(np.uint8), 'RGBA').save(out)

def first(pattern):
    g = glob.glob(pattern); return g[0] if g else None

# ------------------------------------------------------------------ textures
def prep_textures():
    T = {}
    # palm bark (Poly Haven palm_tree_bark)
    d = os.path.join(OUTI, 'Palm'); os.makedirs(d, exist_ok=True)
    src = os.path.join(A, 'polyhaven_tex', 'palm_tree_bark')
    Image.open(first(src + '/*diff*')).convert('RGB').resize((1024, 1024)).save(os.path.join(d, 'PalmBark_Albedo.png'))
    Image.open(first(src + '/*nor_gl*')).convert('RGB').resize((1024, 1024)).save(os.path.join(d, 'PalmBark_Normal.png'))
    mask_png(first(src + '/*rough*'), first(src + '/*ao*') or first(src + '/*arm*'), (1024, 1024), os.path.join(d, 'PalmBark_Mask.png'))
    # palm leaflets from ambientCG Foliage001 long blades (colour + opacity -> RGBA)
    f = os.path.join(A, 'ambientcg', 'Foliage001_2K-JPG')
    col = Image.open(first(f + '/*_Color.jpg')).convert('RGB')
    op = Image.open(first(f + '/*_Opacity.jpg')).convert('L')
    rgba = col.copy(); rgba.putalpha(op)
    # shift the grass green towards a sunlit tropical palm green
    arr = np.asarray(rgba, np.float32); arr[..., 0] *= 0.92; arr[..., 1] *= 1.05; arr[..., 2] *= 0.75
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA').resize((1024, 1024), Image.LANCZOS).save(os.path.join(d, 'PalmLeaf_Albedo.png'))
    Image.open(first(f + '/*_NormalGL.jpg')).convert('RGB').resize((1024, 1024)).save(os.path.join(d, 'PalmLeaf_Normal.png'))
    mask_png(first(f + '/*_Roughness.jpg'), None, (1024, 1024), os.path.join(d, 'PalmLeaf_Mask.png'))
    # blade rectangles in UV space (connected components of the opacity map, columns)
    o = np.asarray(op.resize((512, 512)), np.float32) / 255 > 0.3
    lab, n = label(o)
    rects = []
    for sl in find_objects(lab):
        y0, y1 = sl[0].start, sl[0].stop; x0, x1 = sl[1].start, sl[1].stop
        if (y1 - y0) > 120 and (x1 - x0) < 60:
            rects.append([x0 / 512, 1 - y1 / 512, x1 / 512, 1 - y0 / 512])
    T['blades'] = rects
    # coconut
    n = 512
    yy, xx = np.mgrid[0:n, 0:n] / n
    fib = gaussian_filter(rng.random((n, n)), [8, 0.8])
    base = np.stack([0.35 + 0.1 * fib, 0.42 + 0.15 * fib, 0.12 + 0.05 * fib], -1)
    brown = np.stack([0.38 + 0.1 * fib, 0.25 + 0.08 * fib, 0.12 + 0.03 * fib], -1)
    t = np.clip((yy - 0.55) * 3, 0, 1)[..., None]
    c = base * (1 - t) + brown * t
    Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(os.path.join(d, 'Coconut_Albedo.png'))

    # hibiscus leaf: ovate, serrated, pinnate veins, glossy dark green
    d = os.path.join(OUTI, 'Hibiscus'); os.makedirs(d, exist_ok=True)
    n = 512
    yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / n
    x = (xx - 0.5) * 2; y = yy * 2 - 1           # y: -1 tip .. +1 stem
    width = 0.78 * np.sqrt(np.clip(1 - y ** 2, 0, 1)) * (1 - 0.25 * y) * np.clip((1 - y) * 1.6, 0, 1) ** 0.25
    serr = 0.035 * (np.abs(np.sin(y * 34)) - 0.5)
    inside = np.abs(x) < (width + serr)
    alpha = gaussian_filter(inside.astype(float), 0.8)
    midrib = np.exp(-np.abs(x) * 70) * (y < 0.95)
    vein_ph = (y * 9 + np.abs(x) * 6.5)
    veins = np.exp(-np.abs(np.sin(vein_ph * pi)) * 14) * (np.abs(x) < width) * 0.7
    tone = gaussian_filter(rng.random((n, n)), 6)
    g = np.stack([0.07 + 0.05 * tone, 0.26 + 0.1 * tone, 0.06 + 0.03 * tone], -1)
    g = g * (1 + 0.6 * (midrib + veins)[..., None] * np.array([1.4, 1.2, 1.0]))
    g *= (0.85 + 0.25 * (1 - np.abs(x) / (width + 1e-3)).clip(0, 1))[..., None]
    rgba = np.concatenate([np.clip(g, 0, 1), alpha[..., None]], -1)
    Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA').save(os.path.join(d, 'HibLeaf_Albedo.png'))
    h = 0.5 - 0.08 * midrib - 0.04 * veins + 0.02 * tone
    Image.fromarray(AS_normal(h, 6)).save(os.path.join(d, 'HibLeaf_Normal.png'))
    mk = np.stack([np.full((n, n), 0.75), np.ones((n, n)), np.zeros((n, n)), np.ones((n, n))], -1)
    Image.fromarray((mk * 255).astype(np.uint8), 'RGBA').save(os.path.join(d, 'HibLeaf_Mask.png'))
    # hibiscus petals (3 colourways): broad obovate petal, radial veins, dark eye at base, ruffled edge
    for name, (c_main, c_eye) in {'Red': ((0.86, 0.06, 0.12), (0.35, 0.0, 0.05)),
                                   'Pink': ((0.97, 0.45, 0.62), (0.62, 0.05, 0.22)),
                                   'Orange': ((0.98, 0.52, 0.16), (0.8, 0.12, 0.08))}.items():
        yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / n
        x = (xx - 0.5) * 2; y = 1 - yy                # y: 0 base .. 1 tip
        wdt = 0.12 + 0.88 * np.sin(np.clip(y, 0, 1) * pi * 0.62) ** 0.8
        ruffle = 0.05 * np.sin(np.arctan2(y, x + 1e-6) * 28)
        r = np.sqrt((x / np.maximum(wdt, 0.05)) ** 2)
        inside = (np.abs(x) < wdt + ruffle * (y > 0.7)) & (y < 0.98 + ruffle)
        alpha = gaussian_filter(inside.astype(float), 1.0)
        ang = np.arctan2(x, y + 0.05)
        veins = np.exp(-np.abs(np.sin(ang * 22)) * 6) * 0.25 * y
        eye = np.exp(-y * 7)
        col = np.array(c_main)[None, None, :] * (1 - 0.25 * veins[..., None]) * (0.9 + 0.1 * y[..., None])
        col = col * (1 - eye[..., None]) + np.array(c_eye) * eye[..., None]
        rgba = np.concatenate([np.clip(col, 0, 1), alpha[..., None]], -1)
        Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA').save(os.path.join(d, f'HibPetal{name}_Albedo.png'))
    return T

def AS_normal(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny, nz = -dx * strength * 20, dy * strength * 20, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return (((np.stack([nx / l, ny / l, nz / l], -1)) * 0.5 + 0.5) * 255).astype(np.uint8)

# ------------------------------------------------------------------ mesh helpers
class Builder:
    def __init__(self):
        self.V = []; self.UV = []; self.F = []; self.M = []; self.mats = []
    def mat(self, name):
        if name not in self.mats: self.mats.append(name)
        return self.mats.index(name)
    def quad_strip(self, rings, uvs, m, wrap=False):
        """rings: list of arrays (k, 3); uvs same shape (k, 2)."""
        base = sum(len(v) for v in self.V)
        k = len(rings[0])
        for r, u in zip(rings, uvs): self.V.append(np.asarray(r)); self.UV.append(np.asarray(u))
        mi = self.mat(m)
        for j in range(len(rings) - 1):
            for i in range(k - (0 if wrap else 1)):
                i2 = (i + 1) % k
                a = base + j * k + i; b = base + j * k + i2; c = base + (j + 1) * k + i2; d = base + (j + 1) * k + i
                self.F.append((a, b, c, d)); self.M.append(mi)
    def card(self, p0, p1, p2, p3, uvrect, m, double=False):
        base = sum(len(v) for v in self.V)
        u0, v0, u1, v1 = uvrect
        self.V.append(np.array([p0, p1, p2, p3])); self.UV.append(np.array([[u0, v0], [u1, v0], [u1, v1], [u0, v1]]))
        mi = self.mat(m)
        self.F.append((base, base + 1, base + 2, base + 3)); self.M.append(mi)
    def sphere(self, c, r, m, seg=10, uv_scale=1.0):
        rings = []; uvs = []
        for j in range(seg + 1):
            th = pi * j / seg
            ring = []; uu = []
            for i in range(seg * 2 + 1):
                ph = 2 * pi * i / (seg * 2)
                ring.append((c[0] + r * sin(th) * cos(ph), c[1] + r * sin(th) * sin(ph), c[2] + r * cos(th)))
                uu.append((i / (seg * 2) * uv_scale, j / seg))
            rings.append(ring); uvs.append(uu)
        self.quad_strip(rings, uvs, m)
    def build(self, name):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        V = np.concatenate(self.V); UV = np.concatenate(self.UV)
        me = bpy.data.meshes.new(name)
        me.from_pydata(V.tolist(), [], self.F)
        uvl = me.uv_layers.new(name='UVMap')
        loops_v = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', loops_v)
        uvl.data.foreach_set('uv', UV[loops_v].astype(np.float32).ravel())
        for m in self.mats: me.materials.append(bpy.data.materials.new(m))
        me.polygons.foreach_set('material_index', np.array(self.M, np.int32))
        me.shade_smooth()
        me.validate()
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        return ob

def curve_point(p0, p1, p2, t):
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2

# ------------------------------------------------------------------ coconut palm
def make_palm(seed, T):
    r = np.random.default_rng(seed)
    B = Builder()
    H = r.uniform(7.5, 11.5)
    lean = r.uniform(1.2, 3.5); ang = r.uniform(0, 2 * pi)
    p0 = np.array([0, 0, 0.0]); p2 = np.array([cos(ang) * lean, sin(ang) * lean, H]); p1 = np.array([cos(ang) * lean * 0.1, sin(ang) * lean * 0.1, H * 0.55])
    seg = 14; nh = 36
    rings = []; uvs = []
    for j in range(nh + 1):
        t = j / nh
        c = curve_point(p0, p1, p2, t)
        tan = 2 * (1 - t) * (p1 - p0) + 2 * t * (p2 - p1); tan /= np.linalg.norm(tan)
        side = np.cross(tan, [0, 0, 1.0]); side /= np.linalg.norm(side) + 1e-9
        up = np.cross(side, tan)
        rad = 0.17 + 0.06 * (1 - t) + 0.12 * max(0, 0.08 - t) * 12 + 0.012 * sin(t * H * 8)
        ring = []; uu = []
        for i in range(seg + 1):
            a = 2 * pi * i / seg
            ring.append(c + (side * cos(a) + up * sin(a)) * rad)
            uu.append((i / seg * 1.5, t * H / 1.2))
        rings.append(ring); uvs.append(uu)
    B.quad_strip(rings, uvs, 'PalmBark')
    top = p2
    tan_top = 2 * (p2 - p1); tan_top /= np.linalg.norm(tan_top)
    # coconuts
    for k in range(r.integers(5, 10)):
        a = r.uniform(0, 2 * pi); d = r.uniform(0.18, 0.3)
        c = top + np.array([cos(a) * d, sin(a) * d, -r.uniform(0.15, 0.45)])
        B.sphere(c, r.uniform(0.11, 0.14), 'Coconut', seg=6)
    # fronds
    blades = T['blades'] or [[0.05, 0.05, 0.1, 0.95]]
    nf = r.integers(13, 18)
    for f in range(nf):
        a = 2 * pi * f / nf + r.uniform(-0.15, 0.15)
        dead = f < 2 and r.random() < 0.7
        elev = r.uniform(0.15, 0.85) if not dead else -1.1
        L = r.uniform(3.4, 4.6)
        d0 = np.array([cos(a) * cos(elev), sin(a) * cos(elev), sin(elev)])
        droop = r.uniform(1.3, 2.4)
        pts = []
        for k in range(16):
            t = k / 15
            p = top + d0 * L * t + np.array([0, 0, -droop * t * t * L / 4])
            pts.append(p)
        pts = np.array(pts)
        # rachis tube (thin, bark)
        rr = []; ru = []
        for k, p in enumerate(pts):
            tg = pts[min(k + 1, 15)] - pts[max(k - 1, 0)]; tg /= np.linalg.norm(tg)
            sd = np.cross(tg, [0, 0, 1.0]); sd /= np.linalg.norm(sd) + 1e-9; upv = np.cross(sd, tg)
            rad = 0.035 * (1 - k / 16) + 0.008
            rr.append([p + (sd * cos(q) + upv * sin(q)) * rad for q in np.linspace(0, 2 * pi, 5)])
            ru.append([(q / (2 * pi) * 0.2, k / 15 * 2) for q in np.linspace(0, 2 * pi, 5)])
        B.quad_strip(rr, ru, 'PalmBark')
        # leaflets
        nl = 46
        for k in range(2, nl):
            t = k / nl
            idx = t * 15; i0 = int(idx); fr = idx - i0
            p = pts[i0] * (1 - fr) + pts[min(i0 + 1, 15)] * fr
            tg = pts[min(i0 + 1, 15)] - pts[i0]; tg /= np.linalg.norm(tg)
            sd = np.cross(tg, [0, 0, 1.0]); sd /= np.linalg.norm(sd) + 1e-9
            ln = (0.35 + 0.55 * sin(pi * min(1, t * 1.15))) * r.uniform(0.85, 1.1)
            w = 0.12 * (0.7 + 0.3 * sin(pi * t))
            for s in (-1, 1):
                dirv = sd * s * 0.8 + tg * 0.45 + np.array([0, 0, -0.35 - 0.2 * t])
                dirv /= np.linalg.norm(dirv)
                wv = np.cross(dirv, sd * s); wv /= np.linalg.norm(wv) + 1e-9
                tip = p + dirv * ln + np.array([0, 0, -0.1 * ln])
                rect = blades[r.integers(len(blades))]
                B.card(p - wv * w * 0.5, p + wv * w * 0.5, tip + wv * w * 0.3, tip - wv * w * 0.3, rect, 'PalmLeafDead' if dead else 'PalmLeaf')
    return B

# ------------------------------------------------------------------ hibiscus shrub
def make_hibiscus(seed, color):
    r = np.random.default_rng(seed)
    B = Builder()
    stems = r.integers(5, 9)
    for s in range(stems):
        a = r.uniform(0, 2 * pi); lean = r.uniform(0.2, 0.6); Hs = r.uniform(0.9, 1.7)
        p0 = np.array([0, 0, 0.0]); p2 = np.array([cos(a) * lean, sin(a) * lean, Hs]); p1 = np.array([cos(a) * lean * 0.3, sin(a) * lean * 0.3, Hs * 0.5])
        pts = [curve_point(p0, p1, p2, t) for t in np.linspace(0, 1, 10)]
        rr = []; ru = []
        for k, p in enumerate(pts):
            rad = 0.018 * (1 - k / 11) + 0.004
            rr.append([p + np.array([cos(q) * rad, sin(q) * rad, 0]) for q in np.linspace(0, 2 * pi, 5)])
            ru.append([(q / 6.28 * 0.2, k * 0.2) for q in np.linspace(0, 2 * pi, 5)])
        B.quad_strip(rr, ru, 'HibStem')
        # leaves along the upper stem
        for k in range(r.integers(16, 28)):
            t = r.uniform(0.25, 1.0)
            p = curve_point(p0, p1, p2, t) + r.normal(0, 0.06, 3)
            la = r.uniform(0, 2 * pi); ls = r.uniform(0.09, 0.15)
            d = np.array([cos(la), sin(la), r.uniform(-0.2, 0.35)]); d /= np.linalg.norm(d)
            side = np.cross(d, [0, 0, 1.0]); side /= np.linalg.norm(side) + 1e-9
            tilt = np.array([0, 0, 1.0]) * 0.15
            tip = p + d * ls * 1.4
            B.card(p - side * ls * 0.5 + tilt * ls, p + side * ls * 0.5 + tilt * ls, tip + side * ls * 0.5, tip - side * ls * 0.5, (0, 1, 1, 0), 'HibLeaf')
        # flowers near the tips
        for k in range(r.integers(1, 4)):
            t = r.uniform(0.7, 1.0)
            c = curve_point(p0, p1, p2, t) + r.normal(0, 0.08, 3)
            fd = np.array([r.normal(), r.normal(), abs(r.normal()) + 0.6]); fd /= np.linalg.norm(fd)
            flower(B, c, fd, r.uniform(0.07, 0.1), color, r)
    return B

def flower(B, c, fd, size, color, r):
    side = np.cross(fd, [0.3, 0.2, 0.9]); side /= np.linalg.norm(side)
    up = np.cross(fd, side)
    for p in range(5):
        a = 2 * pi * p / 5 + r.uniform(-0.1, 0.1)
        dirp = side * cos(a) + up * sin(a)
        rings = []; uvs = []
        for j in range(5):
            t = j / 4
            cup = 0.45 * t - 0.25 * t * t     # cupped then flaring
            centre = c + dirp * size * t * 1.1 + fd * size * cup
            w = size * (0.15 + 0.55 * sin(t * pi * 0.62))
            perp = np.cross(fd, dirp)
            ring = [centre - perp * w + fd * size * 0.05 * t, centre + perp * w + fd * size * 0.05 * t]
            rings.append(ring); uvs.append([(0.0, t), (1.0, t)])
        B.quad_strip(rings, uvs, f'HibPetal{color}')
    # staminal column
    tip = c + fd * size * 1.3
    rr = [[c + (side * cos(q) + up * sin(q)) * 0.004 for q in np.linspace(0, 2 * pi, 4)],
          [tip + (side * cos(q) + up * sin(q)) * 0.003 for q in np.linspace(0, 2 * pi, 4)]]
    B.quad_strip(rr, [[(0, 0)] * 4, [(0, 1)] * 4], 'HibStamen')
    B.sphere(tip, 0.008, 'HibStamen', seg=3)

# ------------------------------------------------------------------ beach grass tufts
def make_grass(seed, T):
    r = np.random.default_rng(seed)
    B = Builder()
    blades = T['blades']
    for k in range(r.integers(40, 70)):
        a = r.uniform(0, 2 * pi); d = r.uniform(0, 0.35)
        p = np.array([cos(a) * d, sin(a) * d, 0])
        h = r.uniform(0.35, 0.8); lean = r.uniform(0.05, 0.3)
        dirv = np.array([cos(a) * lean, sin(a) * lean, 1]); dirv /= np.linalg.norm(dirv)
        side = np.array([-sin(a + 1), cos(a + 1), 0]) * 0.025
        tip = p + dirv * h + np.array([cos(a), sin(a), 0]) * h * 0.25
        B.card(p - side, p + side, tip + side * 0.3, tip - side * 0.3, blades[r.integers(len(blades))], 'BeachGrass')
    return B

# ------------------------------------------------------------------ export
def export(B, name, manifest, shaders):
    ob = B.build(name)
    subs = [f'{name}_{m}' for m in B.mats]
    AS.export_pms2(ob, name, subs)
    manifest[name] = [dict(sub=f'{name}_{m}', **shaders[m]) for m in B.mats]
    print(name, 'mats', B.mats, flush=True)

if __name__ == '__main__':
    T = prep_textures()
    manifest = json.load(open(AS.MANIFEST)) if os.path.exists(AS.MANIFEST) else {}
    P = 'Palm/'; H = 'Hibiscus/'
    sh = {
        'PalmBark': dict(shader='prop', albedo=P + 'PalmBark_Albedo.png', normal=P + 'PalmBark_Normal.png', mask=P + 'PalmBark_Mask.png', alpha='OPAQUE'),
        'PalmLeaf': dict(shader='foliage', albedo=P + 'PalmLeaf_Albedo.png', normal=P + 'PalmLeaf_Normal.png', mask=P + 'PalmLeaf_Mask.png', alpha='MASK', wind=0.55, windScale=10),
        'PalmLeafDead': dict(shader='foliage', albedo=P + 'PalmLeaf_Albedo.png', normal=P + 'PalmLeaf_Normal.png', mask=P + 'PalmLeaf_Mask.png', alpha='MASK', tint=[0.75, 0.55, 0.3], wind=0.4, windScale=10),
        'Coconut': dict(shader='prop', albedo=P + 'Coconut_Albedo.png', alpha='OPAQUE', smooth=0.35),
        'HibStem': dict(shader='prop', albedo=P + 'PalmBark_Albedo.png', alpha='OPAQUE', tint=[0.45, 0.4, 0.3], smooth=0.2),
        'HibLeaf': dict(shader='foliage', albedo=H + 'HibLeaf_Albedo.png', normal=H + 'HibLeaf_Normal.png', mask=H + 'HibLeaf_Mask.png', alpha='MASK', wind=0.25, windScale=1.5),
        'HibPetalRed': dict(shader='foliage', albedo=H + 'HibPetalRed_Albedo.png', alpha='MASK', wind=0.2, windScale=1.5, translucency=1.2),
        'HibPetalPink': dict(shader='foliage', albedo=H + 'HibPetalPink_Albedo.png', alpha='MASK', wind=0.2, windScale=1.5, translucency=1.2),
        'HibPetalOrange': dict(shader='foliage', albedo=H + 'HibPetalOrange_Albedo.png', alpha='MASK', wind=0.2, windScale=1.5, translucency=1.2),
        'HibStamen': dict(shader='prop', albedo=H + 'HibPetalRed_Albedo.png', alpha='OPAQUE', tint=[1.0, 0.85, 0.2], smooth=0.4),
        'BeachGrass': dict(shader='foliage', albedo=P + 'PalmLeaf_Albedo.png', normal=P + 'PalmLeaf_Normal.png', alpha='MASK', tint=[0.85, 0.85, 0.6], wind=0.6, windScale=0.8),
    }
    for i in range(3):
        export(make_palm(100 + i, T), f'Palm_{i}', manifest, sh)
    for i, col in enumerate(['Red', 'Pink', 'Orange']):
        export(make_hibiscus(200 + i, col), f'Hibiscus_{col}', manifest, sh)
    export(make_grass(300, T), 'BeachGrass', manifest, sh)
    json.dump(manifest, open(AS.MANIFEST, 'w'), indent=1)
    print('nature done; blade rects', len(T['blades']))
