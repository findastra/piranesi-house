"""v3 labyrinth pieces: the court of dead ends (unique King, Queen, Joker, Knave, Bishop, Knight, Rook, Ace), sea-worn family
statues for the exit halls, a marble albatross statue, numeral plaques, low and broken plinths.
Run: python3 gen/kit3c.py [name ...]"""
import os, sys, json, math, struct, numpy as np
from math import pi, sin, cos, sqrt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import K, AS, NA, bpy, reset, apply, mesh, prism_xz, prism_xy, recalc, cyl, ring_band, finish, MAN, EXTRA
from kit3b import worn_block, rock, sweep, uv_export
from ivy import read_pms
from PIL import Image, ImageDraw, ImageFont, ImageFilter

MESH = os.path.join(HERE, '..', 'out', 'Meshes'); IMP = AS.OUTI if hasattr(AS, 'OUTI') else os.path.join(HERE, '..', 'out', 'Imported')
rng = np.random.default_rng(777)

# =====================================================================================================
# the court of dead ends: stylised figures ~3.2 m on their own stepped base (Blender, Z up, facing -y = Unity -z)
# =====================================================================================================
def body(parts, robe=1.0, h=1.0, m='Marble'):
    prof = [(0.78, 0.0), (0.78, 0.18), (0.66, 0.24), (0.66, 0.3), (0.6 * robe, 0.36), (0.5 * robe, 0.9), (0.38, 1.5), (0.31, 1.85),
            (0.33, 2.05), (0.4, 2.25), (0.43, 2.4), (0.36, 2.5), (0.15, 2.56), (0.13, 2.64)]
    parts.append(K.lathe([(r, z * h) for r, z in prof], 40, m, name='body', cap_top=False,
                         radial=lambda t, z, r: r * (1 + 0.04 * sin(t * 9) * (0.4 < z < 1.6))))
    parts.append(apply(K.lathe([(0.001, 2.62), (0.16, 2.66), (0.21, 2.78), (0.2, 2.9), (0.15, 2.98), (0.001, 3.02)], 24, m, name='head'), (0, 0, (h - 1) * 2.6)))
    return 2.62 * h + 0.4

def court_king(parts):
    top = body(parts)
    crown = K.lathe([(0.17, top - 0.06), (0.2, top), (0.22, top + 0.16), (0.19, top + 0.18), (0.17, top + 0.04)], 24, 'Gold', name='crown', cap_top=False, cap_bottom=False)
    parts.append(crown)
    for k in range(8):
        a = 2 * pi * k / 8
        parts.append(apply(K.lathe([(0.001, 0), (0.035, 0.0), (0.001, 0.13)], 6, 'Gold', name='pt'), (0.2 * cos(a), 0.2 * sin(a), top + 0.16)))
    parts.append(K.box(-0.025, 0.025, -0.025, 0.025, top + 0.15, top + 0.5, 'Gold', 'cross1')); parts.append(K.box(-0.1, 0.1, -0.025, 0.025, top + 0.36, top + 0.42, 'Gold', 'cross2'))
    parts.append(cyl(0.48, -0.2, 0.9, 2.6, 0.035, 'Gold', 8, 'sceptre'))
    parts.append(apply(K.lathe([(0.001, 0), (0.09, 0.05), (0.08, 0.13), (0.001, 0.17)], 12, 'Gold', name='orb'), (0.48, -0.2, 2.6)))
    # the chessboard he plays on, alone
    parts.append(K.box(-0.62, 0.62, -1.55, -0.95, 0.0, 0.85, 'Marble', 'table'))
    for i in range(8):
        for j in range(8):
            if (i + j) % 2: parts.append(K.box(-0.6 + i * 0.15, -0.45 + i * 0.15, -1.53 + j * 0.0725, -1.4575 + j * 0.0725, 0.85, 0.87, 'Verde', 'sq'))

def court_queen(parts):
    top = body(parts, robe=1.12)
    parts.append(K.lathe([(0.19, top - 0.04), (0.23, top + 0.05), (0.26, top + 0.12), (0.22, top + 0.12), (0.19, top + 0.04)], 24, 'Gold', name='coronet', cap_top=False, cap_bottom=False))
    for k in range(9):
        a = 2 * pi * k / 9
        parts.append(apply(K.lathe([(0.001, -0.04), (0.04, 0.0), (0.001, 0.04)], 8, 'Gold', name='ball'), (0.25 * cos(a), 0.25 * sin(a), top + 0.17)))
    veil = K.lathe([(0.24, top + 0.02), (0.34, top - 0.3), (0.48, top - 1.2), (0.62, top - 1.9)], 32, 'Marble', name='veil', cap_top=False, cap_bottom=False,
                   radial=lambda t, z, r: r * (1 + 0.05 * sin(t * 13)) if sin(t) > -0.2 else r * 0.4)
    parts.append(veil)
    rose = K.lathe([(0.001, 0), (0.07, 0.03), (0.08, 0.08), (0.04, 0.11), (0.001, 0.1)], 12, 'Gold', name='rose', radial=lambda t, z, r: r * (1 + 0.25 * sin(t * 5)))
    parts.append(apply(rose, (0.0, -0.46, 1.95)))
    parts.append(cyl(0.0, -0.44, 1.35, 1.95, 0.012, 'Gold', 6, 'stem'))

def court_joker(parts):
    top = body(parts, robe=0.9)
    # ruff collar
    parts.append(K.lathe([(0.15, 2.5), (0.42, 2.52), (0.42, 2.6), (0.15, 2.6)], 48, 'Marble', name='ruff', radial=lambda t, z, r: r * (1 + 0.12 * sin(t * 18) * (r > 0.3))))
    # three-pointed cap with bells
    parts.append(K.lathe([(0.22, top - 0.18), (0.24, top), (0.2, top + 0.08), (0.001, top + 0.1)], 24, 'Marble', name='cap'))
    for k, a in enumerate((-1.0, 0.0, 1.0)):
        pts = [(0.22 * t * 0.0 + a * 0.55 * t ** 0.8, -0.05 * t, top + 0.05 + 0.7 * sin(pi * t * 0.6) - 0.35 * t * t) for t in np.linspace(0, 1, 12)]
        prof = [(cos(q) * 0.11, sin(q) * 0.11) for q in np.linspace(0, 2 * pi, 8, endpoint=False)]
        P = np.array(pts)
        rings = []
        parts.append(sweep(pts, prof, 'Marble', 'prong'))
        parts.append(apply(K.lathe([(0.001, -0.07), (0.07, -0.03), (0.07, 0.03), (0.001, 0.07)], 10, 'Gold', name='bell'), tuple(P[-1] + np.array([0, 0, -0.06]))))
    # a laughing mask held up, and a little bauble sceptre
    parts.append(apply(K.lathe([(0.001, 0), (0.12, 0.02), (0.14, 0.12), (0.1, 0.22), (0.001, 0.24)], 16, 'Gold', name='mask'), (-0.42, -0.25, 1.9), (pi / 2, 0, 0.3)))
    parts.append(cyl(0.42, -0.25, 1.0, 2.2, 0.03, 'Marble', 8, 'marotte'))
    parts.append(apply(K.lathe([(0.001, -0.1), (0.1, -0.05), (0.11, 0.05), (0.001, 0.1)], 12, 'Gold', name='bauble'), (0.42, -0.25, 2.3)))

def court_knave(parts):
    top = body(parts, robe=0.85)
    beret = K.lathe([(0.001, top - 0.02), (0.36, top - 0.02), (0.38, top + 0.05), (0.3, top + 0.12), (0.001, top + 0.14)], 24, 'Marble', name='beret')
    parts.append(apply(beret, (0, 0, 0), (0.15, 0, 0)))
    feather = [(0.25, 0.0, top + 0.1 + 0.0), (0.45, 0.1, top + 0.45), (0.6, 0.3, top + 0.7), (0.65, 0.55, top + 0.82)]
    parts.append(sweep(feather, [(-0.1, 0), (0.1, 0), (0.0, 0.02)], 'Gold', 'feather'))
    parts.append(K.box(-0.025, 0.025, -0.48, -0.42, 0.25, 1.65, 'Marble', 'blade'))
    parts.append(K.box(-0.2, 0.2, -0.5, -0.4, 1.65, 1.71, 'Gold', 'guard'))
    parts.append(K.box(-0.03, 0.03, -0.48, -0.42, 1.71, 1.92, 'Gold', 'grip'))

def court_bishop(parts):
    top = body(parts, robe=1.05)
    mitre = K.lathe([(0.2, top - 0.04), (0.24, top + 0.2), (0.2, top + 0.45), (0.1, top + 0.62), (0.001, top + 0.68)], 24, 'Marble', name='mitre')
    K.boolean(mitre, [K.box(-0.3, 0.3, -0.02, 0.02, top + 0.38, top + 0.8, 'Marble', 'slit')])
    parts.append(mitre)
    parts.append(K.box(-0.02, 0.02, -0.27, -0.2, top + 0.0, top + 0.4, 'Gold', 'orph'))
    # crozier and an open book
    parts.append(cyl(-0.5, -0.1, 0.25, 2.9, 0.03, 'Gold', 8, 'staff'))
    crook = [(-0.5, -0.1, 2.9), (-0.5, -0.1, 3.1), (-0.42, -0.1, 3.22), (-0.3, -0.1, 3.18), (-0.28, -0.1, 3.05)]
    parts.append(sweep(crook, [(cos(q) * 0.03, sin(q) * 0.03) for q in np.linspace(0, 2 * pi, 6, endpoint=False)], 'Gold', 'crook'))
    parts.append(apply(K.box(-0.22, 0.22, -0.02, 0.02, 0, 0.3, 'Marble', 'book'), (0.12, -0.46, 1.75), (0.5, 0, 0)))

def court_knight(parts):
    parts.append(K.lathe([(0.78, 0.0), (0.78, 0.18), (0.66, 0.24), (0.6, 0.36), (0.5, 0.9), (0.42, 1.4)], 40, 'Marble', name='base'))
    # a horse's head and neck carved like a chess knight
    neck = [(0.0, 0.1, 1.35), (0.0, 0.0, 1.9), (0.0, -0.15, 2.4), (0.0, -0.35, 2.75), (0.0, -0.6, 2.85), (0.0, -0.75, 2.7)]
    prof = [(cos(q) * 0.26, sin(q) * 0.36) for q in np.linspace(0, 2 * pi, 10, endpoint=False)]
    parts.append(sweep(neck, prof, 'Marble', 'neck'))
    mane = [(0.0, 0.32, 1.5), (0.0, 0.26, 2.1), (0.0, 0.12, 2.65), (0.0, -0.1, 2.98)]
    parts.append(sweep(mane, [(-0.06, 0), (0.06, 0), (0.0, 0.14)], 'Gold', 'mane'))
    for s in (-1, 1):
        parts.append(apply(K.lathe([(0.001, 0), (0.05, 0.02), (0.001, 0.18)], 6, 'Marble', name='ear'), (s * 0.1, -0.2, 2.82)))

def court_rook(parts):
    parts.append(K.lathe([(0.8, 0.0), (0.8, 0.2), (0.68, 0.28), (0.62, 0.4), (0.55, 1.9), (0.66, 2.1), (0.7, 2.6), (0.001, 2.6)], 40, 'Marble', name='tower'))
    for k in range(8):
        a = 2 * pi * k / 8
        parts.append(apply(K.box(-0.12, 0.12, -0.08, 0.08, 2.6, 2.95, 'Marble', 'merlon'), (0.6 * cos(a), 0.6 * sin(a), 0), (0, 0, a)))
    parts.append(apply(K.box(-0.32, 0.32, -0.6, -0.55, 0.35, 1.25, 'Gold', 'doorframe'), (0, 0, 0)))

def court_ace(parts):
    parts.append(K.box(-0.8, 0.8, -0.35, 0.35, 0.0, 0.35, 'Marble', 'base'))
    card = K.box(-0.62, 0.62, -0.08, 0.08, 0.35, 2.15, 'Marble', 'card')
    parts.append(card)
    # spade in relief + corner pips
    sp = [(0.0, 1.62)]
    for t in np.linspace(0, 1, 18):
        a = pi * t
        sp.append((0.32 * sin(a) * (1 - 0.3 * t), 1.62 - 0.45 * (1 - cos(a)) * 0.9))
    pts = [(x, z) for (x, z) in sp] + [(-x, z) for (x, z) in sp[::-1]]
    parts.append(prism_xz(pts, -0.13, -0.08, 'Gold', 'spade'))
    parts.append(prism_xz([(-0.05, 0.85), (0.05, 0.85), (0.12, 0.7), (-0.12, 0.7)], -0.13, -0.08, 'Gold', 'stem'))
    for (x, z) in ((-0.48, 1.98), (0.48, 0.52)):
        parts.append(prism_xz([(x - 0.06, z - 0.08), (x + 0.06, z - 0.08), (x + 0.06, z + 0.08), (x - 0.06, z + 0.08)], -0.12, -0.08, 'Gold', 'pip'))

COURT_FNS = {'King': court_king, 'Queen': court_queen, 'Joker': court_joker, 'Knave': court_knave, 'Bishop': court_bishop,
             'Knight': court_knight, 'Rook': court_rook, 'Ace': court_ace}

def court_figures():
    for name, fn in COURT_FNS.items():
        reset()
        parts = [K.box(-0.95, 0.95, -0.95, 0.95, -0.3, 0.0, 'Marble', 'pedestal'), K.box(-1.05, 1.05, -1.05, 1.05, -0.45, -0.3, 'Marble', 'pedestal2')]
        fn(parts)
        ob = finish([p for p in parts if p is not None], 'Court_' + name, export=False)
        apply(ob, (0, 0, 0.45))
        K.export_bytes(ob, 'Court_' + name)

# =====================================================================================================
# sea-worn family statues for the exit halls (eroded copies of the scanned statues) + the marble albatross
# =====================================================================================================
def write_pms1(name, P, N, C, subs):
    with open(os.path.join(MESH, name + '.bytes'), 'wb') as f:
        f.write(b'PMS1'); f.write(struct.pack('<iii', len(P), len(subs), 0))
        f.write(P.astype('<f4').tobytes()); f.write(N.astype('<f4').tobytes()); f.write(C.astype(np.uint8).tobytes())
        for nm, idx in subs:
            b = nm.encode(); f.write(struct.pack('<i', len(b))); f.write(b)
            idx = np.asarray(idx, '<i4').ravel(); f.write(struct.pack('<i', len(idx))); f.write(idx.tobytes())

def read_full(name):
    with open(os.path.join(MESH, name + '.bytes'), 'rb') as f:
        mg = f.read(4); nv, ns, fl = struct.unpack('<iii', f.read(12))
        P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3).astype(np.float64)
        N = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3).astype(np.float64)
        C = np.frombuffer(f.read(nv * 4), np.uint8).reshape(-1, 4).copy()
        U = np.frombuffer(f.read(nv * 8), '<f4').reshape(-1, 2) if mg == b'PMS2' else None
        subs = []
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln).decode()
            ni = struct.unpack('<i', f.read(4))[0]; subs.append((nm, np.frombuffer(f.read(ni * 4), '<i4').reshape(-1, 3)))
    return mg, P, N, C, U, subs

def vertex_normals(P, F):
    n = np.zeros_like(P)
    fn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    for k in range(3): np.add.at(n, F[:, k], fn)
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)

def noise3(P, freqs, seed):
    r = np.random.default_rng(seed); out = np.zeros(len(P))
    for f, amp in freqs:
        for k in range(3):
            d = r.normal(size=3); d /= np.linalg.norm(d); ph = r.uniform(0, 6.3)
            out += amp * np.sin(P @ d * f + ph) / 3
    return out

def worn_statues():
    for st in ('Statue_Horse', 'Statue_Beast', 'Statue_WingedFigure', 'Statue_Hare', 'Statue_Dragon', 'Statue_Albatross'):
        mg, P, N, C, U, subs = read_full(st)
        F = np.concatenate([s[1] for s in subs])
        h = P[:, 1].max() - P[:, 1].min()
        n = noise3(P / h, [(9, 1.0), (23, 0.5), (51, 0.25)], sum(map(ord, st)))
        bite = np.clip(n - 0.15, 0, None) * 0.11 * h                         # pits and bitten edges
        smooth = 0.012 * h * (1 + noise3(P / h, [(4, 1.0)], 7))              # everything softened
        Pw = P - N * (bite + smooth)[:, None]
        top = (P[:, 1] - P[:, 1].min()) / h
        Pw[:, 1] -= np.clip(n * 0.03 * h, 0, None) * top                     # sagging, slumped tops
        Nw = vertex_normals(Pw, F)
        Cw = C.copy(); ao = C[:, 0].astype(np.float64) / 255 * np.clip(1.0 - bite / (0.05 * h + 1e-6) * 0.5, 0.45, 1.0)
        Cw[:, 0] = Cw[:, 1] = Cw[:, 2] = (np.clip(ao, 0, 1) * 255).astype(np.uint8)
        write_pms1(st + '_Worn', Pw, Nw, Cw, [(subs[0][0], F)])
        if os.path.exists(os.path.join(MESH, st + '_LOD1.bytes')):
            import shutil; shutil.copy(os.path.join(MESH, st + '_LOD1.bytes'), os.path.join(MESH, st + '_Worn_LOD1.bytes'))
        print(st + '_Worn', len(Pw))

def albatross_statue():
    mg, P, N, C, U, subs = read_full('Albatross')
    F = np.concatenate([s[1] for s in subs])
    P = P - np.array([P[:, 0].mean(), P[:, 1].min(), P[:, 2].mean()])
    s = 1.9 / max(np.ptp(P[:, 0]), np.ptp(P[:, 2]))                        # 1.9 m wingspan / length, life-size+
    P = P * s
    P = np.stack([-P[:, 2], P[:, 1], P[:, 0]], 1)                           # the bird faced +x; statues face +z
    Nn = vertex_normals(P, F)
    Cc = np.full((len(P), 4), 255, np.uint8)
    write_pms1('Statue_Albatross', P, Nn, Cc, [('Statue', F)])
    write_pms1('Statue_Albatross_LOD1', P, Nn, Cc, [('Statue', F)])
    print('Statue_Albatross', len(P), np.ptp(P, axis=0).round(2))

# =====================================================================================================
# plaques with Roman numerals (and the Colossus' 'Climb to the light') on a gold atlas; low and broken plinths
# =====================================================================================================
ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']
PLAQUES = ROMAN[1:11] + ['CLIMB TO THE LIGHT', 'CLIMB', 'SPAWN', 'DEAD ENDS FOUND', 'RETURN TO THE HOUSE'] + [f'{n} / 5' for n in range(6)] + \
    ['FAR HALL QUESTS'] + [f'{n} / 6' for n in range(7)] + ['THE REMEMBERER', 'THE MENDER', 'THE BEEKEEPER', 'THE CLOUD-WALKER', 'THE THREAD-BEARER', 'KEEPER OF THE DEAD']
PLAQUE_NAMES = {'CLIMB TO THE LIGHT': 'ClimbToTheLight', 'CLIMB': 'CLIMB', 'SPAWN': 'Spawn', 'DEAD ENDS FOUND': 'DeadEnds', 'RETURN TO THE HOUSE': 'Return',
                'FAR HALL QUESTS': 'Quests', 'THE REMEMBERER': 'Role0', 'THE MENDER': 'Role1', 'THE BEEKEEPER': 'Role2', 'THE CLOUD-WALKER': 'Role3',
                'THE THREAD-BEARER': 'Role4', 'KEEPER OF THE DEAD': 'Role5'}
def plaque_name(txt): return 'Plaque_' + PLAQUE_NAMES.get(txt, txt if '/' not in txt else ('Count' if txt.endswith('5') else 'Quest') + txt[0])
def plaque_atlas():
    W = 2048; cols = 4; rows = 10; cw, ch = W // cols, W // (cols * 2)
    font = ImageFont.truetype(os.path.join(HERE, '..', 'assets', 'fonts', 'CormorantGaramond[wght].ttf'), 150)
    try: font.set_variation_by_axes([700])
    except Exception: pass
    hgt = Image.new('L', (W, ch * rows), 0); d = ImageDraw.Draw(hgt); HH = ch * rows
    rects = []
    for k, txt in enumerate(PLAQUES):
        cx, cy = (k % cols) * cw, (k // cols) * ch
        d.rectangle([cx + 10, cy + 10, cx + cw - 10, cy + ch - 10], outline=200, width=10)
        d.rectangle([cx + 26, cy + 26, cx + cw - 26, cy + ch - 26], outline=150, width=4)
        f = font if len(txt) < 6 else ImageFont.truetype(os.path.join(HERE, '..', 'assets', 'fonts', 'CormorantGaramond[wght].ttf'), 54 if len(txt) > 15 else 62 if len(txt) > 8 else 120)
        d.text((cx + cw / 2, cy + ch / 2 + 4), txt, font=f, fill=255, anchor='mm')
        rects.append([cx / W, 1 - (cy + ch) / HH, (cx + cw) / W, 1 - cy / HH])
    hgt = hgt.filter(ImageFilter.GaussianBlur(2.2))
    h = np.asarray(hgt, np.float32) / 255
    gold = np.stack([0.86 - 0.25 * h, 0.66 - 0.22 * h, 0.3 - 0.12 * h], -1)            # letters sunk + darker in the recesses
    grain = np.random.default_rng(3).normal(0, 0.015, h.shape)[..., None]
    alb = np.clip(gold + grain, 0, 1)
    d_ = os.path.join(IMP, 'Plaques'); os.makedirs(d_, exist_ok=True)
    Image.fromarray((alb * 255).astype(np.uint8)).save(os.path.join(d_, 'Plaques_Albedo.png'))
    Image.fromarray(NA.AS_normal(-h, 3.5)).save(os.path.join(d_, 'Plaques_Normal.png'))
    mask = np.stack([0.75 - 0.25 * h, np.ones_like(h) - 0.25 * h, np.ones_like(h), np.ones_like(h)], -1)
    Image.fromarray((mask * 255).astype(np.uint8), 'RGBA').save(os.path.join(d_, 'Plaques_Mask.png'))
    return rects

def plaques():
    rects = plaque_atlas()
    ent = dict(shader='prop', albedo='Plaques/Plaques_Albedo.png', normal='Plaques/Plaques_Normal.png', mask='Plaques/Plaques_Mask.png', alpha='OPAQUE', smooth=0.85, metal=1.0)
    for k, txt in enumerate(PLAQUES):
        B = NA.Builder()
        wide = 0.9 if len(txt) > 8 else 0.68
        hw, hh = wide / 2, 0.17
        # face (toward -y Blender = -z Unity), back at y = 0, edges
        B.card((-hw, -0.03, -hh), (hw, -0.03, -hh), (hw, -0.03, hh), (-hw, -0.03, hh), rects[k], 'Plaque')
        e = (rects[k][0], rects[k][1], rects[k][0] + 0.002, rects[k][1] + 0.002)
        for (a, b) in (((-hw, -hh), (hw, -hh)), ((hw, -hh), (hw, hh)), ((hw, hh), (-hw, hh)), ((-hw, hh), (-hw, -hh))):
            B.card((a[0], 0.0, a[1]), (b[0], 0.0, b[1]), (b[0], -0.03, b[1]), (a[0], -0.03, a[1]), e, 'Plaque')
        nm = plaque_name(txt)
        uv_export(B, nm, {'Plaque': ent})
    EXTRA['plaques'] = PLAQUES

def plinths():
    reset()
    parts = [K.box(-0.55, 0.55, -0.55, 0.55, 0, 0.12, 'Marble', 'b'), K.box(-0.46, 0.46, -0.46, 0.46, 0.12, 0.5, 'Verde', 'die'),
             K.box(-0.52, 0.52, -0.52, 0.52, 0.5, 0.6, 'Marble', 'c')]
    finish(parts, 'Plinth_Low')
    reset()
    parts = [worn_block((0, 0, 0.18), (1.0, 1.0, 0.36), 41, 'Stone', chips=3, wear=0.3),
             worn_block((0.05, -0.04, 0.5), (0.8, 0.82, 0.3), 42, 'Marble', chips=4, wear=0.35, tilt=(3, -2, 8))]
    finish(parts, 'Plinth_Broken')
    EXTRA['plinth_low_top'] = 0.6; EXTRA['plinth_broken_top'] = 0.63

BUILDERS = {'Court': court_figures, 'Albatross': albatross_statue, 'Worn': worn_statues, 'Plaques': plaques, 'Plinths': plinths}
if __name__ == '__main__':
    names = sys.argv[1:] or list(BUILDERS)
    for n in names:
        print('== kit3c', n, flush=True)
        BUILDERS[n]()
        json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1); json.dump(EXTRA, open(K3.EXP, 'w'), indent=1)
    print('kit3c done')
