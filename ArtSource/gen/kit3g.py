"""v3 comforts and quests: window-bay daybeds for the high-tide shelter (marble platform + linen bedding), wine bottles,
the lived-in hall's marble beds, bar, stools, linen screens and rugs, the vine pergola (+ its ivy canopy), and the six
Far Hall Quest prizes. Run: python3 gen/kit3g.py [name ...]"""
import os, sys, json, math, numpy as np
from math import pi, sin, cos
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import K, AS, NA, bpy, reset, apply, finish, cyl, MAN, EXTRA
from kit3b import worn_block, uv_export, sweep
import kit2 as K2

rng = np.random.default_rng(6161)
LINEN = lambda n: K2.M(n)
TOP = 1.0          # daybed platform top: just above the highest tide (0.85)

# ------------------------------------------------------------------ soft-box helper for linen (PMS2)
def pillow(B, cx, cy, cz, w, d, h, m, puff=0.35, seg=8):
    """a puffy pillow / mattress: a box whose faces bulge (Blender coords, z up), centred at (cx, cy, cz)."""
    def P(u, v, face):
        # u, v in [-1, 1] on each face; bulge ~ (1-u^2)(1-v^2)
        b = puff * (1 - u * u) * (1 - v * v)
        if face == 'top': return (cx + u * w / 2, cy + v * d / 2, cz + h / 2 * (1 + b))
        if face == 'bot': return (cx + u * w / 2, cy - v * d / 2, cz - h / 2 * (1 + b * 0.3))
        if face == 'n': return (cx + u * w / 2 * (1 + 0.1 * b), cy + d / 2 * (1 + b * 0.25), cz + v * h / 2)
        if face == 's': return (cx - u * w / 2 * (1 + 0.1 * b), cy - d / 2 * (1 + b * 0.25), cz + v * h / 2)
        if face == 'e': return (cx + w / 2 * (1 + b * 0.25), cy - u * d / 2, cz + v * h / 2)
        return (cx - w / 2 * (1 + b * 0.25), cy + u * d / 2, cz + v * h / 2)
    for face in ('top', 'bot', 'n', 's', 'e', 'w'):
        us = np.linspace(-1, 1, seg + 1)
        rings = [[P(u, v, face) for u in us] for v in us]
        uvs = [[((u + 1) / 2 * w, (v + 1) / 2 * d) for u in us] for v in us]
        B.quad_strip(rings, uvs, m)

def throw(B, x0, x1, y0, y1, z, m, drape=0.25, seg=10):
    """a folded throw / blanket lying over a bed, hanging a little over the sides."""
    xs = np.linspace(x0, x1, seg + 1); ys = np.linspace(y0, y1, seg + 1)
    rings = []; uvs = []
    for y in ys:
        row = []; uv = []
        for x in xs:
            e = min(x - x0, x1 - x) / max(x1 - x0, 1e-6)
            zz = z + 0.02 * sin(x * 9 + y * 5) - (drape if e < 0.06 else 0)
            row.append((x, y, zz)); uv.append((x * 0.8, y * 0.8))
        rings.append(row); uvs.append(uv)
    B.quad_strip(rings, uvs, m)

# ------------------------------------------------------------------ the window daybed (high-tide shelter)
def window_daybed():
    """marble platform for one window bay of a window side (side frame: x across, y toward the wall, z up; the bay spans
    y 8.4 .. 11.55), top at TOP. Width 1; scale x to the window width."""
    reset()
    parts = [K.box(-0.5, 0.5, 8.4, 11.55, 0.0, TOP - 0.12, 'Marble', 'block'), K.box(-0.53, 0.53, 8.3, 11.55, TOP - 0.12, TOP, 'Marble', 'top'),
             K.box(-0.49, 0.49, 8.25, 8.4, 0.0, 0.18, 'Marble', 'plinth')]
    finish(parts, 'WindowDaybed')
    for v in range(3):                    # three bedding variants
        B = NA.Builder()
        pillow(B, 0.0, 9.9, TOP + 0.09, 0.92, 3.0, 0.16, 'Mattress', puff=0.25)
        for k in range(int(rng.integers(2, 4))):
            pillow(B, rng.uniform(-0.22, 0.22), 11.2 - k * 0.08, TOP + 0.3 + k * 0.03, rng.uniform(0.42, 0.55), 0.22, 0.24, 'Pillow' if k else 'Pillow2', puff=0.6)
        if v != 1:
            throw(B, -0.48, 0.48, 8.6 + rng.uniform(0, 0.3), 9.5 + rng.uniform(0, 0.4), TOP + 0.2, 'Throw')
        pillow(B, 0.32 if v == 2 else -0.3, 8.9, TOP + 0.28, 0.36, 0.36, 0.14, 'Pillow2', puff=0.7)
        mats = [('LinenCream', 'LinenTeal', 'LinenRed'), ('LinenCream', 'LinenRed', 'LinenTeal'), ('LinenCream', 'LinenTeal', 'LinenTeal')][v]
        uv_export(B, f'DaybedLinen_{v}', {'Mattress': LINEN(mats[0]), 'Pillow': LINEN(mats[0]), 'Pillow2': LINEN(mats[1]), 'Throw': LINEN(mats[2])})
    EXTRA['window_daybed'] = dict(top=TOP, front=8.3, back=11.55)

def wine():
    B = NA.Builder()
    prof = [(0.0, 0.0), (0.037, 0.0), (0.038, 0.2), (0.03, 0.235), (0.013, 0.26), (0.012, 0.31), (0.014, 0.315), (0.0, 0.315)]
    th = np.linspace(0, 2 * pi, 17)
    rings = [[(r * cos(t), r * sin(t), z) for t in th] for r, z in prof]
    B.quad_strip(rings, [[(t / 6.28, z * 3) for t in th] for r, z in prof], 'Glass')
    uv_export(B, 'WineBottle', {'Glass': dict(shader='prop', alpha='OPAQUE', tint=[0.06, 0.16, 0.08], smooth=0.95, metal=0.0)})

# ------------------------------------------------------------------ the lived-in hall: beds, bar, stools, screens, rugs
def marble_bed():
    """a bed someone built from marble scraps: two slabs on drums, a headboard slab (along +y, head at y = 2.3)."""
    reset()
    parts = [worn_block((0, 0.6, 0.22), (1.5, 1.15, 0.44), 901, 'Marble', chips=2, wear=0.08), worn_block((0.02, 1.75, 0.22), (1.5, 1.1, 0.44), 902, 'Marble', chips=2, wear=0.08),
             worn_block((0, 2.33, 0.75), (1.6, 0.16, 1.5), 903, 'Marble', chips=3, wear=0.12), K.box(-0.72, 0.72, 0.05, 2.26, 0.44, 0.5, 'Marble', 'top')]
    finish(parts, 'MarbleBed')
    for v in range(3):
        B = NA.Builder()
        pillow(B, 0.0, 1.16, 0.6, 1.36, 2.12, 0.18, 'Mattress', puff=0.22)
        for sx in (-1, 1):
            pillow(B, sx * 0.33, 2.02, 0.8, 0.55, 0.3, 0.2, 'Pillow', puff=0.6)
        throw(B, -0.74, 0.74, 0.1, 1.2 + v * 0.2, 0.71, 'Throw', drape=0.3)
        mats = [('LinenCream', 'LinenRed'), ('LinenCream', 'LinenTeal'), ('LinenCream', 'LinenCream')][v]
        uv_export(B, f'BedLinen_{v}', {'Mattress': LINEN(mats[0]), 'Pillow': LINEN(mats[0]), 'Throw': LINEN(mats[1])})

def marble_bar():
    """a bar counter of marble: a long slab on column drums, a foot rail of stone, and a back shelf on brackets (length on +x)."""
    reset()
    parts = []
    for x in (-1.9, -0.65, 0.65, 1.9):
        parts.append(K.lathe([(0.32, 0.0), (0.32, 1.0), (0.36, 1.02)], 20, 'Marble', name='drum'))
        parts[-1] = apply(parts[-1], (x, 0.0, 0.0))
    parts.append(worn_block((0, 0.0, 1.06), (4.6, 0.82, 0.12), 911, 'Marble', chips=3, wear=0.05))
    parts.append(K.box(-2.2, 2.2, -0.5, -0.38, 0.12, 0.24, 'Stone', 'rail'))
    for x in (-1.8, 0.0, 1.8):            # the back shelf (against a wall at y = +1.4)
        parts.append(K.box(x - 0.08, x + 0.08, 1.12, 1.4, 1.2, 1.55, 'Marble', 'bracket'))
        parts.append(K.box(x - 0.08, x + 0.08, 1.12, 1.4, 1.95, 2.25, 'Marble', 'bracket'))
    parts.append(K.box(-2.3, 2.3, 1.05, 1.4, 1.55, 1.63, 'Marble', 'shelf1'))
    parts.append(K.box(-2.3, 2.3, 1.05, 1.4, 2.25, 2.33, 'Marble', 'shelf2'))
    finish(parts, 'MarbleBar')
    EXTRA['bar'] = dict(top=1.12, shelf=[1.63, 2.33], shelf_y=1.22)
    reset()
    finish([K.lathe([(0.0, 0.0), (0.24, 0.0), (0.22, 0.66), (0.24, 0.7), (0.0, 0.7)], 18, 'Marble', name='stool')], 'MarbleStool')

def linen_screen():
    """a privacy curtain: linen panels hanging from a rod between two slim marble posts (2.4 m wide, along x)."""
    reset()
    finish([cyl(-1.25, 0, 0, 2.3, 0.05, 'Marble', 10, 'p1'), cyl(1.25, 0, 0, 2.3, 0.05, 'Marble', 10, 'p2'),
            K.box(-1.28, 1.28, -0.02, 0.02, 2.22, 2.26, 'Iron', 'rod')], 'ScreenPosts')
    B = NA.Builder()
    xs = np.linspace(-1.2, 1.2, 40)
    rings = [[(x, 0.06 * sin(x * 13) * (0.6 + 0.4 * z / 2.2), z) for x in xs] for z in np.linspace(0.08, 2.2, 8)]
    B.quad_strip(rings, [[(x * 0.8 + 1, z * 0.8) for x in xs] for z in np.linspace(0.08, 2.2, 8)], 'Curtain')
    uv_export(B, 'LinenScreen', {'Curtain': dict(LINEN('LinenCream'), doubleSided=True)})

def rug():
    for v, m in enumerate(('LinenRed', 'LinenTeal')):
        B = NA.Builder()
        B.quad_strip([[(-1.3, -0.85, 0.012), (1.3, -0.85, 0.012)], [(-1.3, 0.85, 0.012), (1.3, 0.85, 0.012)]], [[(0, 0), (2.6, 0)], [(0, 1.7), (2.6, 1.7)]], 'Rug')
        uv_export(B, f'Rug_{v}', {'Rug': LINEN(m)})

# ------------------------------------------------------------------ the vine pergola (shade) and its ivy canopy
PERG = dict(L=9.0, W=5.4, H=2.9)
def pergola():
    reset()
    L, W, H = PERG['L'], PERG['W'], PERG['H']
    parts = []
    for x in (-L / 2, 0.0, L / 2):
        for y in (-W / 2, W / 2):
            parts.append(K.lathe([(0.2, 0.0), (0.2, 0.18), (0.15, 0.24), (0.14, H - 0.2), (0.19, H - 0.12), (0.19, H)], 16, 'Marble', name='col'))
            parts[-1] = apply(parts[-1], (x, y, 0))
    for y in (-W / 2, W / 2):
        parts.append(K.box(-L / 2 - 0.4, L / 2 + 0.4, y - 0.13, y + 0.13, H, H + 0.3, 'Marble', 'beam'))
    for x in np.linspace(-L / 2 - 0.2, L / 2 + 0.2, 10):
        parts.append(K.box(x - 0.06, x + 0.06, -W / 2 - 0.45, W / 2 + 0.45, H + 0.3, H + 0.42, 'Stone', 'batten'))
    finish(parts, 'VinePergola')
    EXTRA['pergola'] = PERG

def pergola_ivy():
    import ivy3, ivy as IV
    from ivy3 import grow, hang, export3, Surface
    rects = ivy3.leaf_rects(); frects = ivy3.flower_atlas()
    L, W, H = PERG['L'], PERG['W'], PERG['H']
    S = Surface(0.05, 61).add_mesh('VinePergola').build()
    seeds = []
    for x in (-L / 2, 0.0, L / 2):
        for z in (-W / 2, W / 2):
            for k in range(2):
                a = rng.uniform(0, 2 * pi); seeds.append(((x + cos(a) * 0.22, 0.2, z + sin(a) * 0.22), (0, 1, 0)))
    st = grow(S, seeds, rng, length=(6, 14), budget=900, w_up=0.5, w_rand=0.5, branch_p=0.08, max_strands=2600,
              bounds=lambda p: -0.1 < p[1] < H + 0.9 and abs(p[0]) < L / 2 + 0.9 and abs(p[2]) < W / 2 + 0.9)
    # canopy: dense strands along every batten and beam, tendrils and flowers hanging through
    canopy = []
    UP = np.array([0, 1.0, 0])
    for x in np.linspace(-L / 2 - 0.2, L / 2 + 0.2, 10):
        for j in range(3):
            P = np.array([[x + rng.normal() * 0.08, H + 0.45 + rng.uniform(0, 0.06), z] for z in np.linspace(-W / 2 - 0.4, W / 2 + 0.4, 50)])
            canopy.append(dict(p=P, n=np.tile(UP, (len(P), 1)), att=np.zeros(len(P), bool), gen=0, hang=False))
    for z in (-W / 2, W / 2):
        for j in range(3):
            P = np.array([[x, H + 0.32 + rng.uniform(0, 0.05), z + rng.normal() * 0.1] for x in np.linspace(-L / 2 - 0.4, L / 2 + 0.4, 80)])
            canopy.append(dict(p=P, n=np.tile(UP, (len(P), 1)), att=np.zeros(len(P), bool), gen=0, hang=False))
    tips = [(rng.uniform(-L / 2, L / 2), H + 0.3, rng.uniform(-W / 2, W / 2)) for _ in range(46)]
    hs = hang(tips, rng, length=(0.4, 1.6), face=None, sway=0.12)
    export3('Ivy_Pergola', st + canopy + hs, rng, rects, frects, MAN, flower_p=0.16, fsize=(0.07, 0.13), size=(0.1, 0.2), density=1.4)

# ------------------------------------------------------------------ the six Far Hall Quest prizes
def prizes():
    # 1 the Drowned Halls: a page of Piranesi's journal on a marble lectern
    reset()
    finish([K.box(-0.25, 0.25, -0.2, 0.2, 0.0, 0.08, 'Marble', 'foot'), cyl(0, 0, 0.08, 1.0, 0.07, 'Marble', 12, 'stem'),
            apply(K.box(-0.32, 0.32, -0.24, 0.24, -0.03, 0.03, 'Marble', 'desk'), (0, 0, 1.05), (math.radians(-25), 0, 0))], 'Lectern')
    B = NA.Builder()
    B.card((-0.21, -0.15, 0.0), (0.21, -0.15, 0.0), (0.21, 0.15, 0.0), (-0.21, 0.15, 0.0), (0, 0, 1, 1), 'Page', double=True)
    uv_export(B, 'JournalPage', {'Page': dict(shader='prop', alpha='OPAQUE', albedo='Quests/JournalPage.png', smooth=0.2)})
    # 2 the Derelict Halls: a marble shard mended with gold
    reset()
    a = worn_block((-0.12, 0, 0.18), (0.32, 0.26, 0.36), 931, 'Marble', chips=3, wear=0.1, tilt=(4, 0, 12))
    b = worn_block((0.14, 0.02, 0.16), (0.28, 0.24, 0.32), 932, 'Marble', chips=3, wear=0.1, tilt=(-6, 3, -9))
    seam = K.box(-0.015, 0.015, -0.13, 0.13, 0.0, 0.36, 'Gold', 'seam')
    finish([a, b, apply(seam, (0.01, 0, 0), (0, 0, 0.1))], 'GoldShard')
    # 3 the Ninth Vestibule: golden honeycomb
    reset()
    cells = []
    for i in range(-3, 4):
        for j in range(-2, 3):
            x = i * 0.052 + (j % 2) * 0.026; y = j * 0.045
            if x * x / 0.03 + y * y / 0.012 > 1: continue
            c = K.lathe([(0.0, 0.0), (0.026, 0.0), (0.026, 0.05), (0.02, 0.05), (0.02, 0.012), (0.0, 0.012)], 6, 'Gold', name='cell')
            cells.append(apply(c, (x, y, 0)))
    finish(cells, 'Honeycomb')
    # 4 the Upper Halls: a glass jar (the cloud and its stars are particles inside)
    B = NA.Builder()
    prof = [(0.0, 0.0), (0.11, 0.0), (0.12, 0.03), (0.12, 0.24), (0.09, 0.28), (0.075, 0.3), (0.075, 0.33)]
    th = np.linspace(0, 2 * pi, 25)
    B.quad_strip([[(r * cos(t), r * sin(t), z) for t in th] for r, z in prof], [[(t / 6.28, z * 3) for t in th] for r, z in prof], 'Glass')
    B.quad_strip([[(0.08 * cos(t), 0.08 * sin(t), z) for t in th] for z in (0.32, 0.37)], [[(t / 6.28, 0) for t in th], [(t / 6.28, 0.2) for t in th]], 'Cork')
    uv_export(B, 'CloudJar', {'Glass': dict(shader='prop', alpha='BLEND', tint=[0.85, 0.92, 1.0], smooth=0.98, metal=0.0, doubleSided=True),
                             'Cork': dict(shader='prop', alpha='OPAQUE', tint=[0.55, 0.4, 0.25], smooth=0.2)})
    # 5 the Hall of the Minotaurs: Ariadne's golden thread on a spool
    reset()
    sp = [K.lathe([(0.0, 0.0), (0.09, 0.0), (0.09, 0.02), (0.03, 0.02), (0.03, 0.16), (0.09, 0.16), (0.09, 0.18), (0.0, 0.18)], 20, 'Marble', name='spool'),
          K.lathe([(0.032, 0.022), (0.075, 0.022), (0.078, 0.09), (0.075, 0.158), (0.032, 0.158)], 24, 'Gold', name='thread')]
    finish(sp, 'ThreadSpool')
    print('prizes done')

def journal_page():
    """the page of Piranesi's journal: an invented entry in his manner (not a quotation), with a tide sketch."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 768, 548
    y, x = np.mgrid[0:H, 0:W] / 512.0
    base = np.stack([0.93 - 0.05 * y, 0.89 - 0.06 * y, 0.78 - 0.07 * y], -1)
    im = Image.fromarray((np.clip(base + np.random.default_rng(2).normal(0, 0.012, (H, W, 1)), 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(os.path.join(HERE, '..', 'assets', 'fonts', 'CormorantGaramond-Italic[wght].ttf'), 30)
    ink = (52, 40, 32)
    lines = ['Entry for the Day the Lilies Opened', '', 'I waded into the Drowned Halls to see', 'the lilies. The water remembers every hall',
             'it has filled. I write this so that I', 'remember too: what is written down', 'is never wholly lost.']
    for i, t in enumerate(lines):
        d.text((48, 40 + i * 42), t, font=f, fill=ink)
    for k in range(3):                       # a little tide sketch
        pts = [(420 + t * 3, 420 + 26 * k + 10 * math.sin(t / 7.0 + k)) for t in range(90)]
        d.line(pts, fill=ink, width=2)
    od = os.path.join(AS.OUTI if hasattr(AS, 'OUTI') else os.path.join(HERE, '..', 'out', 'Imported'), 'Quests'); os.makedirs(od, exist_ok=True)
    im.save(os.path.join(od, 'JournalPage.png'))

BUILDERS = {'Daybed': window_daybed, 'Wine': wine, 'Bed': marble_bed, 'Bar': marble_bar, 'Screen': linen_screen, 'Rug': rug,
            'Pergola': pergola, 'PergolaIvy': pergola_ivy, 'Page': journal_page, 'Prizes': prizes}
if __name__ == '__main__':
    names = sys.argv[1:] or list(BUILDERS)
    for n in names:
        print('== kit3g', n, flush=True)
        BUILDERS[n]()
        json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1); json.dump(EXTRA, open(K3.EXP, 'w'), indent=1)
    print('kit3g done')
