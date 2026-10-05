"""House v2 kit: window-seat walls, islands + seabed, Venetian long canoe, hammock, garden table, docks,
aqueduct + noria + pump house, stair tower with helical stair, and the water slide (flume + ride spline).
Stone parts export as PMS1 (triplanar shaders); UV-textured parts export as PMS2 with manifest entries."""
import os, sys, json, math, numpy as np
from math import pi, sin, cos, sqrt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit as K              # stone kit helpers (Blender), resets scene on import
import assets as AS
import nature as NA
import bpy
from PIL import Image

ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'assets'); OUTI = AS.OUTI
DATA = os.path.join(ROOT, 'out', 'Data')
rng = np.random.default_rng(77)
MAN = json.load(open(AS.MANIFEST)) if os.path.exists(AS.MANIFEST) else {}
EXTRA = {}   # data for the layout (splines, anchor points)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

# ------------------------------------------------------------------ textures used by UV parts
def tex_prep():
    import glob
    def first(p):
        g = glob.glob(p); return g[0] if g else None
    def pack(src_dir, dst, name, res=1024, tint=None):
        os.makedirs(dst, exist_ok=True)
        im = Image.open(first(src_dir + '/*diff*') or first(src_dir + '/*Color*')).convert('RGB').resize((res, res), Image.LANCZOS)
        if tint is not None:
            g = np.asarray(im.convert('L'), np.float32)[..., None]
            g = g / max(g.mean(), 1) * 200      # normalise brightness, then dye
            a = g * np.array(tint)[None, None]; im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        im.save(os.path.join(dst, name + '_Albedo.png'))
        n = first(src_dir + '/*nor_gl*') or first(src_dir + '/*NormalGL*')
        if n: Image.open(n).convert('RGB').resize((res, res)).save(os.path.join(dst, name + '_Normal.png'))
        NA.mask_png(first(src_dir + '/*rough*') or first(src_dir + '/*Roughness*'), first(src_dir + '/*_ao_*') or first(src_dir + '/*arm*'), (res, res), os.path.join(dst, name + '_Mask.png'))
    d = os.path.join(OUTI, 'Kit2')
    pack(os.path.join(A, 'polyhaven_tex', 'weathered_planks'), d, 'Planks')
    pack(os.path.join(A, 'polyhaven_tex', 'rough_linen'), d, 'LinenCream', tint=(1.0, 0.96, 0.88))
    pack(os.path.join(A, 'polyhaven_tex', 'rough_linen'), d, 'LinenRed', tint=(0.75, 0.16, 0.14))
    pack(os.path.join(A, 'polyhaven_tex', 'rough_linen'), d, 'LinenTeal', tint=(0.2, 0.55, 0.58))
    pack(os.path.join(A, 'ambientcg', 'Rope001_2K-JPG'), d, 'Rope')
    # lacquered black hull with a little wood grain showing through
    im = np.asarray(Image.open(os.path.join(d, 'Planks_Albedo.png')), np.float32) * 0.09 + 6
    Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).save(os.path.join(d, 'Lacquer_Albedo.png'))
    return 'Kit2/'

T = None
def M(name, **kw):
    """manifest entry factory for Kit2 textures"""
    base = dict(shader='prop', alpha='OPAQUE')
    if name in ('Planks', 'LinenCream', 'LinenRed', 'LinenTeal', 'Rope'):
        base.update(albedo=f'Kit2/{name}_Albedo.png', normal=f'Kit2/{name}_Normal.png', mask=f'Kit2/{name}_Mask.png')
    elif name == 'Lacquer':
        base.update(albedo='Kit2/Lacquer_Albedo.png', normal='Kit2/Planks_Normal.png', smooth=0.85)
    base.update(kw); return base

def export_uv(B, name, mats):
    ob = B.build(name)
    subs = [f'{name}_{m}' for m in B.mats]
    AS.export_pms2(ob, name, subs)
    MAN[name] = [dict(sub=f'{name}_{m}', **mats[m]) for m in B.mats]
    print(name, B.mats, flush=True)

def export_stone(ob, name):
    K.export_bytes(ob, name)

# ================================================================== window-seat walls
def vest_side_window():
    """Outward-facing vestibule wall: a grand arched window with a deep window seat inside the 2 m wall."""
    reset()
    wall = K.box(-12, 12, 10, 12, 0, 24, 'Wall', 'wall')
    cuts = [K.arch_prism(8, 7.2, 0, 9.9, 12.1, z0=0.55, name='win')]
    th = np.linspace(0, 2 * pi, 40, endpoint=False); rw = 2.2; zw = 18.2
    pts = [(rw * cos(t), zw + rw * sin(t)) for t in th]; n = len(pts)
    Vc = [(p[0], 9.9, p[1]) for p in pts] + [(p[0], 12.1, p[1]) for p in pts]
    Fc = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    cuts.append(K.obj_from(Vc, Fc, 'Wall', name='lun'))
    K.boolean(wall, cuts)
    parts = [wall]
    parts.append(K.arch_molding(8, 7.2, 0, 10.0, 0.25, 0.5, m='Marble', name='av', legs_to=0.55))
    parts.append(K.box(-0.45, 0.45, 9.75, 10.05, 10.7, 11.9, 'Gold', 'key'))
    # window seat: marble bench filling the bay floor, with a raised back step toward the glass
    parts.append(K.box(-4.0, 4.0, 10.0, 12.0, 0.0, 0.55, 'Marble', 'seat'))
    parts.append(K.box(-4.0, 4.0, 11.55, 11.95, 0.55, 0.85, 'Marble', 'sill'))
    # mullioned glazing at the outer face: iron grid + glass
    for x in np.linspace(-4, 4, 6)[1:-1]:
        parts.append(K.box(x - 0.05, x + 0.05, 11.8, 11.9, 0.85, 7.2 + sqrt(max(0, 16 - x * x)), 'Iron', 'mv'))
    for z in (2.6, 4.6, 6.6, 8.6, 10.2):
        hw = 4 if z <= 7.2 else sqrt(max(0, 16 - (z - 7.2) ** 2))
        parts.append(K.box(-hw, hw, 11.8, 11.9, z - 0.05, z + 0.05, 'Iron', 'mh'))
    gl = K.arch_prism(8, 7.2, 0, 11.84, 11.86, z0=0.85, name='glass')
    gl.data.materials.clear(); gl.data.materials.append(K.mat('Glass2'))
    parts.append(gl)
    # pilasters & window ring as on the other sides
    ring = K.lathe([(2.2, 0.0), (2.55, 0.0), (2.6, 0.15), (2.2, 0.15)], 48, 'Marble', name='winring', cap_top=False, cap_bottom=False)
    ring.rotation_euler.x = pi / 2; ring.location = (0, 10.0, zw)
    with bpy.context.temp_override(active_object=ring, selected_editable_objects=[ring], object=ring):
        bpy.ops.object.transform_apply(location=True, rotation=True)
    parts.append(ring)
    for sx in (-1, 1):
        x0 = sx * 7.2
        parts.append(K.box(x0 - 0.7, x0 + 0.7, 9.65, 10.0, 0, 11.8, 'Marble', 'pil'))
        parts.append(K.box(x0 - 0.85, x0 + 0.85, 9.5, 10.0, 11.8, 12.3, 'Marble', 'pilcap'))
    ob = K.join(parts, 'Vest_SideWindow')
    export_stone(ob, 'Vest_SideWindow')
    EXTRA['Vest_SideWindow_seats'] = [[x, 0.55, 11.0] for x in (-2.6, -0.9, 0.9, 2.6)]

def arcade_window():
    """Arcade whose +X wall has 8 window bays (seat + glass) instead of statue niches."""
    reset()
    parts = [K.box(-7, 7, -18, 18, -8, 0, 'Floor', 'floor')]
    bays = [-15.75 + 4.5 * k for k in range(8)]
    for sx in (-1, 1):
        w = K.box(5 if sx > 0 else -7, 7 if sx > 0 else -5, -18, 18, 0, 15.5, 'Wall', 'wall')
        if sx > 0:
            cuts = [K.arch_prism(2.4, 4.2, yc, 4.9, 7.1, z0=0.9, axis='y', name='bay') for yc in bays]
        else:
            cuts = [K.arch_prism(2.4, 4.2, yc, -6.0, -4.9, z0=0.9, axis='y', name='niche') for yc in bays]
        K.boolean(w, cuts); parts.append(w)
        def bx(a, b, y0, y1, z0, z1, m, nm):
            lo, hi = (a, b) if sx > 0 else (-b, -a)
            return K.box(lo, hi, y0, y1, z0, z1, m, nm)
        parts.append(bx(4.35, 5.0, -18, 18, 0, 0.75, 'Stone', 'ledge'))
        parts.append(bx(4.25, 5.0, -18, 18, 0.75, 0.9, 'Stone', 'ledgecap'))
        for k in range(1, 8):
            yp = -18 + 4.5 * k
            parts.append(bx(4.6, 5.0, yp - 0.45, yp + 0.45, 0.9, 8.5, 'Stone', 'pil'))
            parts.append(bx(4.45, 5.0, yp - 0.6, yp + 0.6, 8.5, 8.85, 'Stone', 'pilcap'))
        for yc in bays:
            mo = K.arch_molding(2.4, 4.2, 0, 0.0, 0.12, 0.22, m='Stone', name='nm', legs_to=0.9)
            mo.rotation_euler.z = (pi / 2 if sx > 0 else -pi / 2); mo.location = (5.0 * sx, yc, 0)
            with bpy.context.temp_override(active_object=mo, selected_editable_objects=[mo], object=mo):
                bpy.ops.object.transform_apply(location=True, rotation=True)
            parts.append(mo)
            if sx > 0:
                parts.append(K.box(5.0, 7.0, yc - 1.2, yc + 1.2, 0.9, 1.0, 'Marble', 'bayseat'))
                for z in (2.4, 3.9):
                    parts.append(K.box(6.85, 6.95, yc - 1.2, yc + 1.2, z - 0.04, z + 0.04, 'Iron', 'mh'))
                parts.append(K.box(6.85, 6.95, yc - 0.04, yc + 0.04, 1.0, 5.4, 'Iron', 'mv'))
                gl = K.arch_prism(2.4, 4.2, yc, 6.89, 6.91, z0=1.0, axis='y', name='glass')
                gl.data.materials.clear(); gl.data.materials.append(K.mat('Glass2')); parts.append(gl)
        parts.append(bx(4.4, 5.0, -18, 18, 8.85, 9.3, 'Stone', 'cornice'))
    ribs = [(-13.5, 0.9), (-4.5, 0.9), (4.5, 0.9), (13.5, 0.9)]
    parts.append(K.barrel_vault(5.0, 9.3, -18, 18, 'Wall', coffer=False, ribs=ribs, sky_holes=[(-9.0, 0.8), (9.0, 0.8)], base_step=0.3, name='vault'))
    parts += K.end_caps(7, 15.5)
    ob = K.join(parts, 'Arcade_Win')
    export_stone(ob, 'Arcade_Win')
    EXTRA['Arcade_Win_seats'] = [[5.9, 1.0, yc] for yc in bays]   # unity local (x, y, z)

# ================================================================== islands & seabed (Unity-space heightfields)
ISLANDS = [  # name, centre (x, z), radii, crest height, interior height, seed
    ('Isle_SouthBeach', (0.0, -128.0), (58.0, 22.0), 1.4, 2.6, 1),
    ('Isle_Ruin', (142.0, 12.0), (36.0, 30.0), 1.2, 2.2, 2),
    ('Isle_Albatross', (-152.0, 150.0), (16.0, 13.0), 1.0, 4.5, 3),
    ('Isle_Pump', (60.0, 118.0), (18.0, 12.0), 0.8, 1.6, 4),
]

def island_height(x, z, ix):
    name, (cx, cz), (rx, rz), crest, inner, seed = ISLANDS[ix]
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6, 4)
    ang = np.arctan2(z - cz, x - cx)
    wob = 1 + 0.12 * np.sin(ang * 3 + ph[0]) + 0.07 * np.sin(ang * 5 + ph[1])
    d = np.sqrt(((x - cx) / (rx * wob)) ** 2 + ((z - cz) / (rz * wob)) ** 2)   # 1 = shoreline
    h = np.where(d < 1, crest + (inner - crest) * np.clip(1 - d, 0, 1) ** 0.7 * np.clip((1 - d) * 3, 0, 1), crest - (d - 1) * 9)
    h += 0.08 * np.sin(x * 0.7 + ph[2]) * np.sin(z * 0.6 + ph[3]) * (d < 1)
    return h, d

def make_islands():
    for ix, (name, (cx, cz), (rx, rz), crest, inner, seed) in enumerate(ISLANDS):
        reset()
        ext = 1.45; n = 90
        xs = np.linspace(cx - rx * ext, cx + rx * ext, n); zs = np.linspace(cz - rz * ext, cz + rz * ext, int(n * rz / rx) + 10)
        X, Z = np.meshgrid(xs, zs)
        H, D = island_height(X, Z, ix)
        H = np.maximum(H, -4.0)
        keep = D < ext * 0.98
        nz, nx = X.shape
        V = np.stack([X - cx, H, Z - cz], -1).reshape(-1, 3)       # Unity space, local to island centre
        F = []
        for j in range(nz - 1):
            for i in range(nx - 1):
                if keep[j, i] and keep[j, i + 1] and keep[j + 1, i] and keep[j + 1, i + 1]:
                    a = j * nx + i
                    F.append((a, a + nx, a + nx + 1, a + 1))
        # build directly in Blender coords (x, z, y)
        Vb = V[:, [0, 2, 1]]
        Fb = [tuple(reversed(f)) for f in F]
        ob = K.obj_from(Vb, Fb, 'Sand', smooth=True, name=name)
        export_stone(ob, name)
        EXTRA.setdefault('islands', {})[name] = dict(centre=[cx, cz], radii=[rx, rz], crest=crest, inner=inner)

def seabed_height(x, z):
    # house footprint shelf
    dh = np.maximum(np.abs(x), np.abs(z)) - 72
    d = np.maximum(dh, 0)
    for ix, isl in enumerate(ISLANDS):
        _, (cx, cz), (rx, rz), *_ = isl
        di = np.sqrt(((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2) - 1
        d = np.minimum(d, np.maximum(di, 0) * min(rx, rz))
    shelf = -1.6 - 2.2 * np.clip(d / 30, 0, 1) - 10 * np.clip((d - 35) / 120, 0, 1) ** 1.4
    ripple = 0.25 * np.sin(x * 0.21 + np.sin(z * 0.05) * 3) * np.sin(z * 0.17)
    return shelf + ripple

def make_seabed():
    reset()
    L = 700; n = 220
    xs = np.linspace(-L / 2, L / 2, n)
    X, Z = np.meshgrid(xs, xs)
    H = seabed_height(X, Z)
    V = np.stack([X, H, Z], -1).reshape(-1, 3)
    F = [(j * n + i, (j + 1) * n + i, (j + 1) * n + i + 1, j * n + i + 1) for j in range(n - 1) for i in range(n - 1)]
    Vb = V[:, [0, 2, 1]]; Fb = [tuple(reversed(f)) for f in F]
    ob = K.obj_from(Vb, Fb, 'Sand', smooth=True, name='Seabed2')
    export_stone(ob, 'Seabed2')

# ================================================================== Venetian long canoe (gondola style)
def make_gondola():
    B = NA.Builder()
    L = 7.2; nseg = 40; nr = 9
    def section(t):
        # t 0 (stern) .. 1 (bow); returns half-beam, depth, sheer height, centre-line offset (asymmetry)
        beam = 0.68 * np.sin(pi * np.clip(t, 0.02, 0.98)) ** 0.55
        depth = 0.42 * np.sin(pi * np.clip(t, 0.05, 0.95)) ** 0.4
        sheer = 0.45 + 1.1 * np.clip((t - 0.82) / 0.18, 0, 1) ** 2.2 + 0.55 * np.clip((0.12 - t) / 0.12, 0, 1) ** 2
        offs = 0.06 * np.sin(pi * t)
        return beam, depth, sheer, offs
    outer = []; uvo = []; inner = []; uvi = []
    for k in range(nseg + 1):
        t = k / nseg; y = (t - 0.5) * L
        beam, depth, sheer, offs = section(t)
        ring = []; ru = []; ring_i = []; ru_i = []
        for i in range(nr):
            a = pi * i / (nr - 1)       # 0 = port gunwale, pi = starboard gunwale
            x = -cos(a) * beam + offs
            z = sheer - (sin(a) ** 0.8) * (depth + 0.0) - (sheer - 0.45)
            z = 0.45 - (sin(a) ** 0.8) * depth if t > 0.1 and t < 0.86 else z
            ring.append((x, y, z)); ru.append((i / (nr - 1), t * 6))
            ring_i.append((x * 0.9, y, z + 0.035)); ru_i.append((i / (nr - 1), t * 6))
        outer.append(ring); uvo.append(ru); inner.append(ring_i); uvi.append(ru_i)
    B.quad_strip(outer, uvo, 'Lacquer')
    B.quad_strip(inner[::-1], uvi[::-1], 'Planks')
    # gunwale trim (gold)
    for side in (0, nr - 1):
        rr = []; uu = []
        for k in range(nseg + 1):
            p = np.array(outer[k][side])
            rr.append([p + np.array([0, 0, 0.03 * cos(q)]) + np.array([0.03 * sin(q), 0, 0]) for q in np.linspace(0, 2 * pi, 5)])
            uu.append([(q, k / nseg) for q in np.linspace(0, 1, 5)])
        B.quad_strip(rr, uu, 'Gold')
    # floor boards + seats with cushions
    B.card((-0.42, -2.4, 0.12), (0.42, -2.4, 0.12), (0.42, 2.4, 0.12), (-0.42, 2.4, 0.12), (0, 0, 1, 4), 'Planks')
    seats = []
    for ys, w in ((-1.9, 0.5), (-0.4, 0.62), (1.1, 0.58)):
        z = 0.42
        for (x0, x1, y0, y1, z0, z1, m) in [(-w, w, ys - 0.25, ys + 0.25, z - 0.06, z, 'Planks'), (-w + 0.05, w - 0.05, ys - 0.22, ys + 0.22, z, z + 0.08, 'LinenRed')]:
            box_uv(B, x0, x1, y0, y1, z0, z1, m)
        seats.append([0.0, z + 0.08, ys])
    # bow ferro: stylised six-tooth comb blade
    yb = L / 2 - 0.15
    for k in range(6):
        z = 1.25 + k * 0.11
        box_uv(B, -0.015, 0.015, yb - 0.02, yb + 0.28 + 0.02 * (k == 5), z, z + 0.05, 'Gold')
    box_uv(B, -0.02, 0.02, yb - 0.05, yb + 0.05, 0.95, 1.95, 'Gold')
    # stern forcola (oarlock) + oar
    box_uv(B, 0.35, 0.47, -2.75, -2.6, 0.45, 1.25, 'Planks')
    EXTRA['Gondola_seats'] = [[s[0], s[1], s[2]] for s in seats]   # Blender (x, y, z) -> unity (x, z, y) handled in layout
    export_uv(B, 'Gondola', {'Lacquer': M('Lacquer'), 'Planks': M('Planks'), 'Gold': dict(shader='prop', alpha='OPAQUE', tint=[1.0, 0.76, 0.35], smooth=0.75, metal=1.0), 'LinenRed': M('LinenRed')})

def box_uv(B, x0, x1, y0, y1, z0, z1, m):
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for f in faces:
        p = [c[i] for i in f]
        sx = max(abs(x1 - x0), abs(y1 - y0)); B.card(p[0], p[1], p[2], p[3], (0, 0, sx, max(abs(z1 - z0), abs(y1 - y0))), m)

# ================================================================== hammock
def make_hammock():
    B = NA.Builder()
    span = 3.6; sag = 0.55; W = 1.1; nl = 22; nw = 7
    rings = []; uvs = []
    for i in range(nl + 1):
        t = i / nl; y = (t - 0.5) * span * 0.78
        z = -sag * (1 - (2 * t - 1) ** 2)
        wid = W * (0.25 + 0.75 * sin(pi * t) ** 0.6)
        ring = []; uu = []
        for j in range(nw):
            s = j / (nw - 1) - 0.5
            ring.append((s * wid, y, z + 0.18 * (abs(s) * 2) ** 2 * sin(pi * t)))
            uu.append((j / (nw - 1), t * 2.5))
        rings.append(ring); uvs.append(uu)
    B.quad_strip(rings, uvs, 'LinenCream')
    # spreader ropes to the two anchor points
    for end in (0, nl):
        for j in range(0, nw, 2):
            p = np.array(rings[end][j]); q = np.array([0, (1 if end else -1) * span / 2, 0.15])
            d = q - p; L = np.linalg.norm(d); d /= L; s = np.cross(d, [0, 0, 1.0]); s /= np.linalg.norm(s) + 1e-9; u = np.cross(s, d)
            rr = [[p + (s * cos(a) + u * sin(a)) * 0.008 for a in np.linspace(0, 2 * pi, 4)], [q + (s * cos(a) + u * sin(a)) * 0.008 for a in np.linspace(0, 2 * pi, 4)]]
            B.quad_strip(rr, [[(0, 0)] * 4, [(0, L)] * 4], 'Rope')
    export_uv(B, 'Hammock', {'LinenCream': M('LinenCream', doubleSided=True), 'Rope': M('Rope')})
    EXTRA['Hammock_seat'] = [0, -sag + 0.1, 0]

# ================================================================== garden table & exedra benches (marble, triplanar)
def make_table():
    reset()
    parts = []
    parts.append(K.lathe([(0.001, 0.74), (0.82, 0.74), (0.86, 0.76), (0.86, 0.8), (0.82, 0.82), (0.001, 0.82)], 64, 'Marble', name='top'))
    parts.append(K.lathe([(0.84, 0.775), (0.875, 0.78), (0.875, 0.79), (0.84, 0.795)], 64, 'Gold', name='rim', cap_top=False, cap_bottom=False))
    ped = [(0.36, 0.0), (0.36, 0.06), (0.3, 0.1), (0.2, 0.14), (0.12, 0.2), (0.1, 0.32), (0.16, 0.42), (0.18, 0.5), (0.1, 0.6), (0.08, 0.68), (0.16, 0.72), (0.2, 0.74)]
    def flute(t, z, r):
        return r * (1 - 0.06 * max(0, cos(t * 12)) * (0.2 < z < 0.6))
    parts.append(K.lathe(ped, 48, 'Marble', radial=flute, name='ped'))
    ob = K.join(parts, 'GardenTable'); export_stone(ob, 'GardenTable')
    # curved exedra bench: quarter-ring seat with lion-paw-ish ends
    reset()
    parts = []
    r0, r1 = 1.75, 2.25
    n = 24
    V = []; F = []
    for i in range(n + 1):
        a = -pi / 3 + (2 * pi / 3) * i / n
        for (r, z) in [(r0, 0.0), (r1, 0.0), (r1, 0.46), (r0, 0.46)]:
            V.append((r * cos(a), r * sin(a), z))
    for i in range(n):
        for k in range(4):
            a = i * 4 + k; b = i * 4 + (k + 1) % 4
            F.append((a, b, b + 4, a + 4))
    F.append((3, 2, 1, 0)); F.append((n * 4, n * 4 + 1, n * 4 + 2, n * 4 + 3))
    parts.append(K.obj_from(V, F, 'Marble', name='seat'))
    V = []; F = []
    for i in range(n + 1):
        a = -pi / 3 + (2 * pi / 3) * i / n
        for (r, z) in [(r1 - 0.12, 0.46), (r1, 0.46), (r1 + 0.05, 1.0), (r1 - 0.08, 1.0)]:
            V.append((r * cos(a), r * sin(a), z))
    for i in range(n):
        for k in range(4):
            a = i * 4 + k; b = i * 4 + (k + 1) % 4
            F.append((a, b, b + 4, a + 4))
    F.append((3, 2, 1, 0)); F.append((n * 4, n * 4 + 1, n * 4 + 2, n * 4 + 3))
    parts.append(K.obj_from(V, F, 'Marble', name='back'))
    ob = K.join(parts, 'ExedraBench'); export_stone(ob, 'ExedraBench')

# ================================================================== dock (weathered planks)
def make_dock():
    B = NA.Builder()
    W = 3.0; L = 14.0
    for k in range(int(L / 0.25)):
        y = k * 0.25
        box_uv(B, -W / 2, W / 2, y, y + 0.23, 0.55, 0.62, 'Planks')
    for y in np.arange(0.3, L, 2.2):
        for x in (-W / 2 + 0.1, W / 2 - 0.1):
            rr = [[(x + 0.12 * cos(a), y + 0.12 * sin(a), z) for a in np.linspace(0, 2 * pi, 7)] for z in (-4.0, 0.9)]
            B.quad_strip(rr, [[(a / 6.28, z) for a in np.linspace(0, 2 * pi, 7)] for z in (0, 4)], 'Planks')
    box_uv(B, -W / 2, -W / 2 + 0.12, 0, L, 0.62, 0.72, 'Planks'); box_uv(B, W / 2 - 0.12, W / 2, 0, L, 0.62, 0.72, 'Planks')
    export_uv(B, 'Dock', {'Planks': M('Planks')})

# ================================================================== aqueduct, noria, pump house
def make_aqueduct(L=29.0):
    """Runs along +Y (Blender) from y=0 (House wall) to y=L (noria). Channel floor slopes 16.9 -> 17.4."""
    reset()
    W = 3.0; bays = 4; bw = L / bays
    parts = []
    body = K.box(-W / 2, W / 2, 0, L, -6, 17.0, 'Wall', 'body')
    cuts = []
    for b in range(bays):
        yc = (b + 0.5) * bw
        cuts.append(K.arch_prism(bw - 2.2, 6.5, yc, -W, W, z0=-6, axis='y', name='a1'))
        cuts.append(K.arch_prism(bw - 3.2, 12.6, yc, -W, W, z0=9.5, axis='y', name='a2'))
    K.boolean(body, cuts); parts.append(body)
    # channel walls on top + string courses
    parts.append(K.box(-W / 2 - 0.15, -W / 2 + 0.35, 0, L, 17.0, 18.0, 'Stone', 'cw1'))
    parts.append(K.box(W / 2 - 0.35, W / 2 + 0.15, 0, L, 17.0, 18.0, 'Stone', 'cw2'))
    parts.append(K.box(-W / 2 - 0.2, W / 2 + 0.2, 0, L, 9.2, 9.5, 'Marble', 'course'))
    # spout reaching into the lunette window
    parts.append(K.box(-0.6, 0.6, -2.2, 0, 16.85, 17.15, 'Stone', 'spout'))
    ob = K.join(parts, 'Aqueduct'); export_stone(ob, 'Aqueduct')
    # flowing water ribbon in the channel and pouring off the spout
    B = NA.Builder()
    rings = []; uvs = []
    for k in range(41):
        y = L - k * (L + 2.2) / 40
        z = 17.4 - 0.5 * k / 40 + 0.05
        rings.append([(-1.15, y, z), (1.15, y, z)] if y > 0 else [(-0.5, y, z), (0.5, y, z)])
        uvs.append([(0, k / 40 * 10), (1, k / 40 * 10)])
    B.quad_strip(rings, uvs, 'Flow')
    rings = []; uvs = []
    for k in range(12):           # free fall arc out of the spout
        t = k / 11
        y = -2.2 - 0.9 * t; z = 16.95 - 1.8 * t * t
        rings.append([(-0.45, y, z), (0.45, y, z)]); uvs.append([(0, t * 3), (1, t * 3)])
    B.quad_strip(rings, uvs, 'Flow')
    export_uv(B, 'AqueductWater', {'Flow': dict(shader='flow', alpha='BLEND')})

def make_noria(axle_h=8.2):
    """Water wheel (rotates about Blender X axis at origin) + stone frame + trough; pump house separate."""
    R = 8.0; wid = 1.6; n = 24
    B = NA.Builder()
    for side in (-1, 1):
        x = side * wid / 2
        for rr_ in (R, R - 0.6):
            ring = []; uu = []
            for k in range(n * 2 + 1):
                a = 2 * pi * k / (n * 2)
                ring.append([(x - 0.08, rr_ * cos(a) - 0.0, rr_ * sin(a)), (x + 0.08, rr_ * cos(a), rr_ * sin(a))])
            rows = [[r[0] for r in ring], [r[1] for r in ring]]
            B.quad_strip([[ (p[0], p[1], p[2]) for p in row] for row in rows], [[(k / (n * 2) * 8, 0) for k in range(n * 2 + 1)], [(k / (n * 2) * 8, 0.2) for k in range(n * 2 + 1)]], 'Planks')
        for k in range(n // 2):
            a = 2 * pi * k / (n // 2)
            p0 = np.array([x, 0, 0]); p1 = np.array([x, R * cos(a), R * sin(a)])
            d = p1 - p0; s = np.array([1.0, 0, 0]); u = np.cross(d / np.linalg.norm(d), s)
            box_like = [[p0 + s * dx + u * du for dx, du in ((-0.07, -0.09), (0.07, -0.09), (0.07, 0.09), (-0.07, 0.09))],
                        [p1 + s * dx + u * du for dx, du in ((-0.07, -0.09), (0.07, -0.09), (0.07, 0.09), (-0.07, 0.09))]]
            B.quad_strip(box_like, [[(0, 0), (0.2, 0), (0.4, 0), (0.6, 0)], [(0, 4), (0.2, 4), (0.4, 4), (0.6, 4)]], 'Planks', wrap=True)
    # buckets between the rims
    for k in range(n):
        a = 2 * pi * k / n
        c = np.array([0, (R - 0.3) * cos(a), (R - 0.3) * sin(a)])
        tg = np.array([0, -sin(a), cos(a)])
        rad = np.array([0, cos(a), sin(a)])
        q = [c + np.array([sx * wid / 2, 0, 0]) + tg * st * 0.3 + rad * sr * 0.25 for sx, st, sr in
             ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))]
        for f in [(0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (3, 0, 4, 7)]:
            B.card(q[f[0]], q[f[1]], q[f[2]], q[f[3]], (0, 0, 1, 1), 'Planks')
    # axle
    rr = [[(x, 0.35 * cos(a), 0.35 * sin(a)) for a in np.linspace(0, 2 * pi, 9)] for x in (-wid / 2 - 1.2, wid / 2 + 1.2)]
    B.quad_strip(rr, [[(a / 6.28, 0) for a in np.linspace(0, 2 * pi, 9)], [(a / 6.28, 2) for a in np.linspace(0, 2 * pi, 9)]], 'Planks')
    export_uv(B, 'NoriaWheel', {'Planks': M('Planks')})
    # stone frame (origin at the axle): two piers down to the seabed, bearing blocks, and a trough that catches
    # the buckets at the top and runs over the aqueduct channel on the -x side
    reset()
    parts = []
    for sx in (-1, 1):
        x0 = sx * (wid / 2 + 0.6)
        parts.append(K.box(x0 - 0.5, x0 + 0.5, -2.0, 2.0, -axle_h - 4.0, 1.2, 'Wall', 'pier'))
        parts.append(K.box(x0 - 0.65, x0 + 0.65, -1.0, 1.0, 0.3, 1.2, 'Marble', 'bearing'))
    parts.append(K.box(-wid / 2 - 3.2, wid / 2 + 0.3, -0.9, 0.9, R + 0.35, R + 0.55, 'Stone', 'trough'))
    for y0 in (-0.9, 0.75):
        parts.append(K.box(-wid / 2 - 3.2, wid / 2 + 0.3, y0, y0 + 0.15, R + 0.55, R + 0.85, 'Stone', 'troughwall'))
    for x in (-wid / 2 - 1.1, wid / 2 + 0.6):
        parts.append(K.box(x - 0.25, x + 0.25, -0.25, 0.25, 1.2, R + 0.35, 'Stone', 'post'))
    ob = K.join(parts, 'NoriaFrame'); export_stone(ob, 'NoriaFrame')
    # pump house (origin on the ground at the door sill): stone hut with an arched door and a marble roof
    reset()
    ph = K.box(-3.0, 3.0, -4.0, 4.0, -1.0, 6.0, 'Wall', 'house')
    K.boolean(ph, [K.arch_prism(1.8, 2.6, 0, -3.1, -2.4, z0=0.0, axis='y', name='door'), K.box(-2.4, 2.4, -3.4, 3.4, 0.0, 5.4, 'Wall', 'room')])
    parts = [ph, K.box(-3.3, 3.3, -4.3, 4.3, 6.0, 6.5, 'Marble', 'roof'), K.box(-2.4, 2.4, -3.4, 3.4, -0.05, 0.05, 'Floor', 'floor')]
    for sy in (-1, 1):
        parts.append(K.box(-3.15, -2.95, sy * 1.6 - 0.12, sy * 1.6 + 0.12, 0.0, 6.0, 'Marble', 'pil'))
    ob = K.join(parts, 'PumpHouse'); export_stone(ob, 'PumpHouse')
    EXTRA['noria'] = dict(radius=R, axle_h=axle_h, trough_x=-wid / 2 - 3.2)

# ================================================================== stair tower + helical stair
def make_tower():
    """10 x 10 m tower (Blender local: x across, y outward from the House wall at y=0), 27 m tall,
    door on the -y face, helical stair (r 1.0 .. 4.0) rising to a roof platform at z=26."""
    reset()
    parts = []
    t = 0.8; s = 5.0; H = 27.0
    shell = K.box(-s, s, 0, 2 * s, -8, H, 'Wall', 'shell')
    inner = K.box(-s + t, s - t, t, 2 * s - t, 0, H - 0.6, 'Wall', 'inner')
    cuts = [inner, K.arch_prism(3.0, 2.6, 0, -0.1, t + 0.1, z0=0, name='door')]
    for z in (6.0, 12.0, 18.0, 23.0):          # slit windows on three faces
        for (ax, a0, a1) in (('x', s - t - 0.1, s + 0.1), ('x', -s - 0.1, -s + t + 0.1)):
            v = [(a0, s - 0.35, z), (a1, s - 0.35, z), (a1, s + 0.35, z), (a0, s - 0.35 + 0.7, z)]
            cuts.append(K.box(a0, a1, s - 0.35, s + 0.35, z, z + 2.2, 'Wall', 'slit'))
        cuts.append(K.box(-0.35, 0.35, 2 * s - t - 0.1, 2 * s + 0.1, z, z + 2.2, 'Wall', 'slit'))
    # roof hatch over the stair top
    cuts.append(K.box(-1.1, 4.15, 2.2, 9.2, H - 1.0, H + 0.2, 'Wall', 'hatch'))
    K.boolean(shell, cuts)
    parts.append(shell)
    # helical stair
    steps = 137; rise = H / steps; dA = 2 * pi / 30
    for i in range(steps):
        a0 = i * dA - pi / 2; a1 = a0 + dA * 1.02; z = (i + 1) * rise
        V = []
        for (r, a) in [(1.0, a0), (4.1, a0), (4.1, a1), (1.0, a1)]:
            V.append((r * cos(a), s + r * sin(a), z - rise - 0.1));
        for (r, a) in [(1.0, a0), (4.1, a0), (4.1, a1), (1.0, a1)]:
            V.append((r * cos(a), s + r * sin(a), z))
        F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        parts.append(K.obj_from(V, F, 'Marble', name='step'))
    parts.append(K.lathe([(1.0, 0), (1.0, H - 1.2)], 24, 'Marble', name='newel'))
    # roof platform parapet + slide pavilion columns
    parts.append(K.box(-s, s, 0, 0.4, H, H + 1.1, 'Marble', 'par1')); parts.append(K.box(-s, s, 2 * s - 0.4, 2 * s, H, H + 1.1, 'Marble', 'par2'))
    parts.append(K.box(-s, -s + 0.4, 0, 2.6, H, H + 1.1, 'Marble', 'par3a'))
    parts.append(K.box(-s, -s + 0.4, 5.4, 2 * s, H, H + 1.1, 'Marble', 'par3b'))     # gap on -x (world +x) for the slide
    parts.append(K.box(s - 0.4, s, 0, 2 * s, H, H + 1.1, 'Marble', 'par4'))
    # hatch guard rail around the stair opening
    parts.append(K.box(-1.1, 4.15, 2.0, 2.2, H, H + 1.0, 'Marble', 'rail1'))
    parts.append(K.box(4.15, 4.35, 2.0, 7.0, H, H + 1.0, 'Marble', 'rail2'))
    for (x, y) in ((-4.4, 0.6), (-4.4, 9.4), (4.4, 0.6), (4.4, 9.4)):
        parts.append(K.lathe([(0.3, H), (0.25, H + 0.4), (0.22, H + 3.6), (0.32, H + 3.9)], 24, 'Marble', name='pc'))
        parts[-1].location = (x, y, 0)
        with bpy.context.temp_override(active_object=parts[-1], selected_editable_objects=[parts[-1]], object=parts[-1]):
            bpy.ops.object.transform_apply(location=True)
    parts.append(K.box(-s, s, 0, 2 * s, H + 3.9, H + 4.3, 'Marble', 'canopy'))
    ob = K.join(parts, 'StairTower'); export_stone(ob, 'StairTower')
    EXTRA['tower'] = dict(height=H, top=[-4.4, 4.0])

# ================================================================== water slide (flume along a spline)
def catmull(pts, n_per):
    P = np.array(pts, float); out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(i + 2, len(P) - 1)]
        for t in np.linspace(0, 1, n_per, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1]); return np.array(out)

def make_slide(tower_origin):
    """Spline in Unity world space. tower_origin = (x, z) of the tower's door centre on the House wall,
    tower extends toward -z (south)."""
    tx, tz = tower_origin
    s = 5.0; top = 27.0
    cx, cz = tx, tz - s      # tower centre
    ctrl = [(cx + 5.6, top + 0.4, cz + 1.0), (cx + 8.5, top - 2.0, cz - 3.5), (cx + 6.0, top - 5.0, cz - 9.0),
            (cx - 1.0, top - 8.0, cz - 10.5), (cx - 8.0, top - 11.0, cz - 7.0), (cx - 9.5, top - 14.0, cz + 0.5),
            (cx - 6.0, top - 17.0, cz - 6.5), (cx - 9.0, top - 19.5, cz - 14.0), (cx - 15.0, top - 22.5, cz - 19.0),
            (cx - 19.0, 2.6, cz - 23.0), (cx - 21.0, 0.9, cz - 27.0), (cx - 22.0, 0.3, cz - 30.0)]
    path = catmull(ctrl, 10)
    EXTRA['slide_path'] = path.round(3).tolist()
    # flume: half pipe of radius 0.75 + lip, with water ribbon inside; supports to the seabed
    B = NA.Builder(); W = NA.Builder()
    rings = []; uvs = []; wr = []; wu = []
    acc = 0.0
    for k, p in enumerate(path):
        tg = path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]; tg /= np.linalg.norm(tg)
        side = np.cross([0, 1.0, 0], tg); side /= np.linalg.norm(side) + 1e-9
        up = np.cross(tg, side)
        if k: acc += np.linalg.norm(path[k] - path[k - 1])
        ring = []; uu = []
        for i in range(13):
            a = pi * i / 12
            off = side * cos(a) * 0.75 - up * sin(a) * 0.75 + up * 0.45
            q = p + off
            ring.append((q[0], q[2], q[1]))            # unity -> blender (x, z, y)
            uu.append((i / 12, acc / 3))
        rings.append(ring); uvs.append(uu)
        w0 = p - side * 0.5 - up * 0.18 + up * 0.45 * 0; w1 = p + side * 0.5 - up * 0.18
        wr.append([(w0[0], w0[2], w0[1] + 0.02), (w1[0], w1[2], w1[1] + 0.02)]); wu.append([(0, acc / 4), (1, acc / 4)])
    B.quad_strip(rings, uvs, 'Flume')
    # supports
    for k in range(0, len(path), 9):
        p = path[k]
        if p[1] < 3: continue
        rr = [[(p[0] + 0.18 * cos(a), p[2] + 0.18 * sin(a), z) for a in np.linspace(0, 2 * pi, 7)] for z in (-6.0, p[1] - 0.3)]
        B.quad_strip(rr, [[(a / 6.28, 0) for a in np.linspace(0, 2 * pi, 7)], [(a / 6.28, 3) for a in np.linspace(0, 2 * pi, 7)]], 'Flume')
    W.quad_strip(wr, wu, 'Flow')
    flume_mat = dict(shader='prop', alpha='OPAQUE', tint=[0.93, 0.95, 0.97], smooth=0.9, doubleSided=True)
    ob = B.build('Slide'); AS.export_pms2(ob, 'Slide', [f'Slide_{m}' for m in B.mats]); MAN['Slide'] = [dict(sub='Slide_Flume', **flume_mat)]
    ob = W.build('SlideWater'); AS.export_pms2(ob, 'SlideWater', ['SlideWater_Flow']); MAN['SlideWater'] = [dict(sub='SlideWater_Flow', shader='flow', alpha='BLEND')]
    print('Slide', len(path), 'points, length', round(acc, 1), flush=True)

if __name__ == '__main__':
    T = tex_prep()
    vest_side_window(); arcade_window()
    make_islands(); make_seabed()
    make_gondola(); make_hammock(); make_table(); make_dock()
    make_aqueduct(); make_noria(); make_tower()
    make_slide((0.0, -72.0))
    json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1)
    json.dump(EXTRA, open(os.path.join(DATA, 'Kit2Extra.json'), 'w'), indent=1)
    print('kit2 done')
