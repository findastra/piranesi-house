"""House v2 layout: the Colossus with its palm seat, the islands that replaced the 'show' wings (south beach,
ruin isle, pump isle, albatross isle), gondolas and docks, the aqueduct + noria feeding the cascade, the stair tower
and water slide, coral reefs and a wreck, crabs and dolphins, and ivy grown on the House.
Called from layout.py; adds to the same layout dict (Unity space, metres, degrees)."""
import os, json, math, numpy as np
import islands as IS
import ruin as RU
from ivy import euler, read_pms

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'out', 'Data')
EX = json.load(open(os.path.join(DATA, 'Kit2Extra.json')))
rng = np.random.default_rng(4242)
_bounds = {}

def bounds(m):
    if m not in _bounds:
        P = read_pms(m)[0]; _bounds[m] = (P.min(0), P.max(0))
    return _bounds[m]

def R3(p): return [round(float(v), 4) for v in p]

def rot_y(x, z, deg):
    a = math.radians(deg)
    return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)

def yaw_to(dx, dz): return math.degrees(math.atan2(dx, dz)) % 360

# coral colour variants (base, tip, glow)
VARIANTS = {
    'rose': ([0.62, 0.22, 0.36], [1.0, 0.62, 0.72], 0.3), 'violet': ([0.35, 0.2, 0.55], [0.8, 0.6, 1.0], 0.35),
    'amber': ([0.75, 0.38, 0.12], [1.0, 0.8, 0.35], 0.25), 'lemon': ([0.6, 0.55, 0.18], [0.98, 0.95, 0.55], 0.2),
    'teal': ([0.12, 0.45, 0.42], [0.5, 0.95, 0.85], 0.35), 'coral': ([0.85, 0.3, 0.25], [1.0, 0.7, 0.55], 0.25),
    'ochre': ([0.5, 0.4, 0.25], [0.85, 0.75, 0.55], 0.12), 'olive': ([0.3, 0.36, 0.2], [0.62, 0.7, 0.42], 0.1),
}
SPECIES = {  # mesh: (weight, palette)
    'Coral_Brain': (3, ['ochre', 'olive', 'lemon']), 'Coral_BrainGrooved': (2, ['ochre', 'teal', 'olive']),
    'Coral_Maze': (2, ['lemon', 'ochre', 'olive']), 'Coral_Staghorn': (4, ['amber', 'ochre', 'violet']),
    'Coral_Table': (3, ['amber', 'ochre', 'teal']), 'Coral_Montipora': (2, ['violet', 'amber', 'rose']),
    'Coral_Fire': (2, ['lemon', 'amber']), 'Coral_Lace': (2, ['rose', 'violet', 'coral']),
    'Coral_Lettuce': (2, ['rose', 'lemon', 'teal']), 'Coral_Cactus': (2, ['teal', 'olive', 'rose']),
    'Coral_Cauliflower': (2, ['rose', 'coral', 'violet']), 'Coral_Lobo': (2, ['teal', 'ochre', 'rose']),
    'Coral_Lobe': (2, ['olive', 'ochre', 'teal']), 'Coral_Honeycomb': (2, ['ochre', 'lemon', 'teal']),
    'Coral_Mushroom': (2, ['rose', 'amber', 'teal']),
}
SHELLS = ['Shell_ConeGlory', 'Shell_ConeTextile', 'Shell_Lambis']
STARS = ['SeaStar_Blue', 'SeaStar_Crown', 'SeaStar_Cushion']
PLANTS = ['Plant_Fern_0', 'Plant_Fern_1', 'Plant_Fern_2', 'Plant_Anthurium_0', 'Plant_Anthurium_1', 'Plant_Anthurium_3',
          'Plant_Calathea_0', 'Plant_Calathea_1', 'Plant_Calathea_2', 'Plant_Periwinkle_0', 'Plant_Periwinkle_1', 'Plant_Pachira_0', 'Plant_Pachira_2']

def build(L, vpos, local):
    O = L['objects']; ST = L['statues']; LI = L['lights']; SH = L['shafts']; EM = L['emitters']; SO = L['sounds']; SE = L['seats']
    boats = []; crabs = []; variants = [dict(name=k, base=v[0], tip=v[1], glow=v[2]) for k, v in VARIANTS.items()]

    def obj(mesh, p, r=0.0, e=None, s=1.0, col='none', name=None, stat=True, mv=None, noshadow=False, spin=None, tag=''):
        d = dict(name=name or mesh, mesh=mesh, p=R3(p), r=round(float(r) % 360, 3), s=[float(s)] * 3 if np.isscalar(s) else list(s),
                 col=col, stat=stat, tag=tag)
        if e is not None: d['e'] = [float(v) for v in e]
        if mv: d['mv'] = mv
        if noshadow: d['noshadow'] = True
        if spin: d['spin'] = list(spin)
        O.append(d); return d

    def box(name, p, size, r=0.0, tag=''):
        O.append(dict(name=name, mesh='', p=R3(p), r=round(float(r) % 360, 3), s=list(size), col='box', stat=True, tag=tag))

    def gy(x, z): return IS.ground(x, z)

    def lantern(p, rng_=6.0, inten=1.4, mesh=True, r=0.0):
        if mesh: obj('Lantern_Wood', p, r, col='none', stat=False)
        LI.append(dict(kind='lantern', p=R3([p[0], p[1] + 0.32, p[2]]), range=rng_, intensity=inten, color=[1.0, 0.66, 0.36]))

    def sample_isle(name, dmin, dmax, n, avoid=(), minsep=0.0, tries=4000):
        cx, cz = IS.ISLANDS[IS.INDEX[name]][1]; rx, rz = IS.ISLANDS[IS.INDEX[name]][2]
        out = []
        for _ in range(tries):
            if len(out) >= n: break
            x = cx + rng.uniform(-1.4, 1.4) * rx; z = cz + rng.uniform(-1.4, 1.4) * rz
            d = IS.island_d(x, z, name)
            if not (dmin <= d <= dmax): continue
            if any((x - a) ** 2 + (z - b) ** 2 < rr * rr for a, b, rr in avoid): continue
            if minsep and any((x - a) ** 2 + (z - b) ** 2 < minsep * minsep for a, b in out): continue
            out.append((x, z))
        return out

    def shore_point(name, x0, z0, dx, dz, d_want=0.93):
        """walk from (x0, z0) along (dx, dz) until the island 'd' crosses d_want."""
        best = None
        for t in np.linspace(0, 80, 1601):
            x, z = x0 + dx * t, z0 + dz * t
            if IS.island_d(x, z, name) >= d_want: best = (x, z); break
        return best

    def deco_boat_contents(gl):
        """shells & starfish lying on the floorboards of a gondola (gondola-local positions)."""
        items = []
        for z in (-1.25, -0.95, 1.65, 1.95, 2.25):
            m = STARS[rng.integers(3)] if rng.random() < 0.45 else SHELLS[rng.integers(3)]
            items.append(dict(mesh=m, p=[round(rng.uniform(-0.25, 0.25), 3), 0.13, z], r=round(rng.uniform(0, 360), 1), s=round(rng.uniform(0.8, 1.2), 2)))
        return items

    def gondola(p, yaw, drivable=True, name='Gondola'):
        boats.append(dict(name=name, p=R3([p[0], 0.0, p[2]]), r=round(yaw % 360, 2), drivable=drivable, items=deco_boat_contents(None)))

    # =========================================================== the Colossus (hall 1,2)
    o = vpos((1, 2)); col = EX['colossus']; palm = col['palm']; ped = col['pedestal']
    ry = 180.0
    ox, oz = rot_y(palm[0], palm[2], ry)
    base = [o[0] - ox, 0.0, o[2] - oz]
    obj('Colossus_Pedestal', base, ry, col='mesh', name='Colossus Pedestal')
    ST.append(dict(mesh='Colossus', p=R3([base[0], ped, base[2]]), r=ry, s=1.0, role='The Colossus: a figure holding its palm up to the light (seat)'))
    pw = [o[0], ped + palm[1], o[2]]
    nrm = col['palm_normal']; nx, nz = rot_y(nrm[0], nrm[2], ry)
    seat_p = [pw[0] + nx * 0.06, pw[1] + nrm[1] * 0.06, pw[2] + nz * 0.06]
    SE.append(dict(p=R3(seat_p), r=ry, kind='palm', text="Rest in the Colossus' palm", exit=R3([base[0], 0.05, base[2] - 6.2]),
                   size=[0.9, 0.5, 0.9], trigger=dict(p=R3([base[0], 1.0, base[2] - 4.75]), size=[3.4, 2.0, 0.6])))
    LI.append(dict(kind='spot', p=R3([o[0], 26.2, o[2]]), dir=[0, -1, 0], angle=20, range=16, intensity=3.0, color=[1.0, 0.95, 0.86]))
    EM.append(dict(kind='sparkle', p=R3([pw[0], pw[1] + 0.7, pw[2]]), size=[1.8, 1.6, 1.8]))
    SH.append(dict(p=R3([o[0], 26.6, o[2]]), radius=0.9, height=26.6 - pw[1], kind='palm', face=0))

    # =========================================================== islands
    for name, (cx, cz), *_ in IS.ISLANDS:
        obj(name, [cx, 0, cz], 0, col='mesh', name='Sand_' + name)

    # ---------------- south beach (0, -128)
    SB = 'Isle_SouthBeach'
    slide_end = EX['slide_path'][-1]
    ex_x, ex_z = slide_end[0], slide_end[2] - 4.5
    dock0 = shore_point(SB, 12.0, -128.0, 0, 1, 0.9)            # walk north from the centre to the waterline
    avoid = [(ex_x, ex_z, 5.0), (12.0, dock0[1] + 7, 4.0), (32.3, -124.0, 4.0)]
    clusters = sample_isle(SB, 0.15, 0.75, 7, avoid=avoid, minsep=14)
    palms = []
    for (cx_, cz_) in clusters:
        for k in range(rng.integers(3, 5)):
            x, z = cx_ + rng.normal() * 3.5, cz_ + rng.normal() * 3.0
            if IS.island_d(x, z, SB) > 0.85 or any((x - a) ** 2 + (z - b) ** 2 < 4 for a, b in palms): continue
            palms.append((x, z))
    for (x, z) in [(30.0, -124.0), (34.6, -124.0)]: palms.append((x, z))
    for i, (x, z) in enumerate(palms):
        obj(f'Palm_{i % 3}', [x, gy(x, z) - 0.05, z], rng.uniform(0, 360), s=rng.uniform(0.85, 1.15), col='none', stat=False)
        box('Palm Trunk', [x, gy(x, z) + 1.5, z], [0.5, 3.0, 0.5])
    for (x, z) in sample_isle(SB, 0.15, 0.82, 16, avoid=avoid, minsep=3):
        obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.2), stat=False)
    for (x, z) in sample_isle(SB, 0.05, 0.92, 70, avoid=avoid, minsep=1.2):
        obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.4), stat=False, noshadow=True)
    for (x, z) in sample_isle(SB, 0.2, 0.7, 12, avoid=avoid, minsep=2):
        obj(PLANTS[rng.integers(len(PLANTS))], [x, gy(x, z) - 0.02, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.4), stat=False)
    for (x, z) in sample_isle(SB, 0.88, 1.03, 34, avoid=avoid, minsep=1.0):
        m = STARS[rng.integers(3)] if rng.random() < 0.4 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(SB, 0.92, 1.12, 5, avoid=avoid, minsep=12):
        obj('Boulder_01', [x, gy(x, z) - 0.25, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.6), col='mesh')
    for (x, z) in sample_isle(SB, 0.96, 1.08, 2, avoid=avoid, minsep=40):
        obj('Rock_SandSmall', [x, gy(x, z) - 0.15, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.2), col='mesh')
    for (x, z) in sample_isle(SB, 0.8, 0.97, 10, avoid=avoid, minsep=3):
        crabs.append(dict(p=R3([x, gy(x, z), z]), r=round(rng.uniform(0, 360), 1)))
    # dock + gondola + lantern
    dy = 0.55
    obj('Dock', [12.0, dy, dock0[1] - 1.0], 0, col='mesh', name='Dock (South Beach)')
    gondola([14.8, 0, dock0[1] + 8.0], 0)
    lantern([10.6, dy + 0.9, dock0[1] + 12.5])
    # hammock between two palms
    hz = -124.0; hy = gy(32.3, hz) + 1.3
    obj('Hammock', [32.3, hy, hz], 90, stat=False)
    SE.append(dict(p=R3([32.3, hy - 0.4, hz]), r=0, kind='hammock', text='Rest in the hammock', exit=R3([32.3, gy(32.3, hz - 1.6) + 0.05, hz - 1.6]), size=[1.2, 0.4, 0.8]))
    SO.append(dict(clip='Ocean_Near_Loop', p=[0, 1, -104], vol=0.8, minD=8, maxD=90, spatial=1))
    SO.append(dict(clip='Wind_Loop', p=[0, 6, -128], vol=0.35, minD=10, maxD=70, spatial=1))
    EM.append(dict(kind='season', p=[0, 16, -128], size=[110, 1, 44], fall=15))

    # ---------------- ruin isle (142, 12)
    RI = 'Isle_Ruin'; rc = IS.ISLANDS[IS.INDEX[RI]][1]
    g0 = gy(rc[0], rc[1]); RO = np.array([rc[0], g0, rc[1]])
    for (x, z) in RU.COLUMNS:
        obj('Column', RO + [x, RU.BASE_Y, z], 0, col='capsule', name='Ruin Column')
    for b in RU.BEAMS:
        obj('Column', RO + np.array(b['p']), e=b['e'], col='none', name='Fallen Column (lying across the capitals)')
    obj('Ivy_Ruin', RO, 0, name='Ivy (Ruin)')
    for (x, z) in RU.STUMPS:
        y = RU.BASE_Y + 0.1
        for k in range(rng.integers(2, 4)):
            obj('Fragment_Drum', RO + [x + rng.normal() * 0.04, y, z + rng.normal() * 0.04], rng.uniform(0, 360), col='box', name='Broken Column Drum')
            y += 0.92
        # the fallen top drum lies in the grass beside it
        obj('Fragment_Drum', RO + [x + 1.4, 0.42, z + 0.6], rng.uniform(0, 360), e=[90, rng.uniform(0, 360), 0], col='box', name='Fallen Drum')
        if (x, z) == RU.STUMPS[0]:
            obj('Marble_Bust', RO + [x, y - 0.02, z], 250, s=1.6, col='none', name='Bust on the broken column')
    for (hx, hz), yaw in RU.HAMMOCKS:
        hy = gy(rc[0] + hx, rc[1] + hz) + RU.HAMMOCK_Y
        obj('Hammock', [rc[0] + hx, hy, rc[1] + hz], yaw, stat=False)
        sx, sz = rot_y(0, 1.0, yaw)
        SE.append(dict(p=R3([rc[0] + hx, hy - 0.4, rc[1] + hz]), r=yaw + 90, kind='hammock', text='Rest in the hammock',
                       exit=R3([rc[0] + hx - sz * 1.4, g0 + 0.05, rc[1] + hz + sx * 1.4]), size=[1.2, 0.4, 0.8]))
    # garden table, benches, the feast
    T = RO + [RU.TABLE[0], gy(rc[0], rc[1]) - g0, RU.TABLE[1]]
    top = T[1] + 0.82
    obj('GardenTable', T, 0, col='mesh', name='Garden Table')
    for yaw in (0, 180):
        obj('ExedraBench', T, yaw, col='mesh', name='Exedra Bench')
        for a in (-28, 0, 28):
            aa = math.radians(a)
            lx, lz = 2.0 * math.cos(aa), 2.0 * math.sin(aa)
            wx, wz = rot_y(lx, lz, yaw)
            SE.append(dict(p=R3([T[0] + wx, T[1] + 0.46, T[2] + wz]), r=yaw_to(-wx, -wz), kind='bench', text='Sit at the table',
                           exit=R3([T[0] + wx * 1.35, T[1] + 0.05, T[2] + wz * 1.35]), size=[0.6, 0.4, 0.6]))
    def on_table(m, lx, lz, yaw=None, s=1.0, dy=0.0):
        obj(m, [T[0] + lx, top + dy, T[2] + lz], rng.uniform(0, 360) if yaw is None else yaw, s=s, stat=False)
    on_table('Bowl_Wood', 0, 0, s=1.6)
    heap = ['Fruit_Apple', 'Fruit_Apple', 'Fruit_Lemon', 'Fruit_Lime', 'Fruit_Pomegranate', 'Fruit_Kiwi', 'Fruit_Apple', 'Fruit_Lemon']
    for k, m in enumerate(heap):
        a = k * 2.4; r_ = 0.09 if k < 6 else 0.03
        on_table(m, math.cos(a) * r_, math.sin(a) * r_, dy=0.03 + (0.07 if k >= 6 else 0))
    for k in range(5):
        on_table('Fruit_Lychee', 0.12 + rng.normal() * 0.03, -0.42 + rng.normal() * 0.03)
    on_table('Fruit_Bananas', 0.38, -0.2, yaw=30)
    on_table('Fruit_Pears', -0.3, 0.38)
    for k, a in enumerate((45, 135, 225, 315)):
        aa = math.radians(a); on_table('Plate_Carved', math.cos(aa) * 0.6, math.sin(aa) * 0.6)
        if k % 2 == 0: on_table(['Fruit_Pomegranate', 'Fruit_Apple'][k // 2], math.cos(aa) * 0.6, math.sin(aa) * 0.6, dy=0.03)
    on_table('Goblets_Brass', -0.5, -0.12, yaw=80)
    on_table('Jug', 0.12, 0.52, yaw=200)
    on_table('Vase_Antique', 0.55, 0.25)
    on_table('Horse_Statue', -0.1, -0.62, yaw=20)
    on_table('Elephant_Carved', 0.3, -0.58, yaw=160)
    on_table('Candleholders_0', -0.22, -0.4, yaw=10)
    LI.append(dict(kind='lantern', p=R3([T[0] - 0.22, top + 0.95, T[2] - 0.4]), range=4.5, intensity=1.1, color=[1.0, 0.7, 0.4]))
    obj('Basket_Wicker', T + [0.0, 0.0, 1.35], 20, s=1.4, stat=False)
    for k, m in enumerate(['Fruit_Apple', 'Fruit_Lemon', 'Fruit_Lime', 'Fruit_Apple']):
        obj(m, T + [0.08 * math.cos(k * 1.6), 0.05, 1.35 + 0.08 * math.sin(k * 1.6)], rng.uniform(0, 360), stat=False)
    # the two kings' chess game, on a column drum
    obj('Fragment_Drum', T + [0.0, -0.3, -2.25], 0, col='box', name='Chess Drum')
    obj('Chess_Set', T + [0.0, 0.64, -2.25], 12, s=1.2, stat=False)
    obj('Treasure_Chest', RO + [-10.8, gy(rc[0] - 10.8, rc[1] + 1.2) - g0, 1.2], 75, col='box')
    obj('Plinth_Round', RO + [-12.6, gy(rc[0] - 12.6, rc[1] - 1.0) - g0 - 0.1, -1.0], 0, col='box')
    obj('Whale_Bronze', RO + [-12.6, gy(rc[0] - 12.6, rc[1] - 1.0) - g0 + 1.15, -1.0], 120, s=1.2, col='none')
    obj('Lion_Head', RO + [9.2, RU.BASE_Y + 0.1 + 0.92 * 2 - 0.02, -3.5], 200, s=1.5, col='none', name='Lion head on the broken column')
    # lanterns around the colonnade
    for (x, z) in [(-6.9, -5.0), (6.9, 5.0), (2.3, 5.2), (-2.3, -5.2)]:
        lantern(RO + [x, gy(rc[0] + x, rc[1] + z) - g0, z], rng_=5.0, inten=1.1, r=rng.uniform(0, 360))
    # garden planting
    for (x, z) in RU.COLUMNS + RU.STUMPS:
        for k in range(rng.integers(1, 3)):
            a = rng.uniform(0, 6.28); r_ = rng.uniform(1.0, 1.6)
            px, pz = x + math.cos(a) * r_, z + math.sin(a) * r_
            if abs(pz) < 2.6 and abs(px) < 3.0: continue
            obj(PLANTS[rng.integers(len(PLANTS))], RO + [px, gy(rc[0] + px, rc[1] + pz) - g0 - 0.02, pz], rng.uniform(0, 360), s=rng.uniform(1.0, 1.5), stat=False)
    ravoid = [(rc[0], rc[1], 14.0)]
    for (x, z) in sample_isle(RI, 0.4, 0.82, 7, avoid=ravoid, minsep=7):
        obj(f'Palm_{rng.integers(3)}', [x, gy(x, z) - 0.05, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.15), stat=False)
        box('Palm Trunk', [x, gy(x, z) + 1.5, z], [0.5, 3.0, 0.5])
    for (x, z) in sample_isle(RI, 0.3, 0.85, 8, avoid=ravoid, minsep=4):
        obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.25), stat=False)
    for (x, z) in sample_isle(RI, 0.05, 0.92, 45, avoid=[(rc[0], rc[1], 6.0)], minsep=1.5):
        obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(RI, 0.88, 1.03, 16, minsep=1.5):
        m = STARS[rng.integers(3)] if rng.random() < 0.4 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(RI, 0.8, 0.97, 4, minsep=5):
        crabs.append(dict(p=R3([x, gy(x, z), z]), r=round(rng.uniform(0, 360), 1)))
    rd = shore_point(RI, rc[0], 14.0, -1, 0, 0.9)
    obj('Dock', [rd[0] + 1.0, dy, 14.0], 270, col='mesh', name='Dock (Ruin)')
    gondola([rd[0] - 8.0, 0, 16.8], 270)
    lantern([rd[0] + 1.0 - 13.5, dy + 0.9, 14.0 - 1.4])
    SO.append(dict(clip='Ocean_Near_Loop', p=R3([rd[0], 1, 14]), vol=0.7, minD=6, maxD=60, spatial=1))
    SO.append(dict(clip='Wind_Loop', p=R3(RO + [0, 8, 0]), vol=0.3, minD=6, maxD=50, spatial=1))
    EM.append(dict(kind='season', p=R3(RO + [0, 14, 0]), size=[30, 1, 20], fall=14))
    EM.append(dict(kind='dust', p=R3(RO + [0, 5, 0]), size=[22, 9, 10]))

    # ---------------- pump isle, aqueduct and noria (feeds the cascade in hall 2,2)
    AQ_Y = -0.5
    v22 = vpos((2, 2)); ax, az0 = v22[0], v22[2] + 12.0
    obj('Aqueduct', [ax, AQ_Y, az0], 0, col='mesh', name='Aqueduct')
    obj('AqueductWater', [ax, AQ_Y, az0], 0, noshadow=True, stat=False)
    obj('Ivy_Aqueduct', [ax, AQ_Y, az0], 0, name='Ivy (Aqueduct)')
    aL = float(bounds('Aqueduct')[1][2])
    nz = az0 + aL - 1.0; nxp = ax + 3.6; axle = EX['noria']['axle_h']
    obj('NoriaFrame', [nxp, axle, nz], 0, col='mesh', name='Noria Frame')
    obj('NoriaWheel', [nxp, axle, nz], 0, stat=False, spin=[1, 0, 0, -9], name='Noria (water wheel)')
    EM.append(dict(kind='spray', p=R3([nxp, 0.3, nz]), size=[2.4, 0.2, 4.0]))
    EM.append(dict(kind='splash', p=R3([ax, 16.8 + AQ_Y, nz]), size=[1.2, 0.2, 1.2]))
    SO.append(dict(clip='Cascade_Loop', p=R3([nxp, 1.0, nz]), vol=0.6, minD=3, maxD=40, spatial=1))
    PI = 'Isle_Pump'; pc = IS.ISLANDS[IS.INDEX[PI]][1]
    phx, phz = pc[0] + 8.0, pc[1] - 3.0
    obj('PumpHouse', [phx, gy(phx, phz) - 0.1, phz], 0, col='mesh', name='Pump House')
    obj('Barrels', [phx - 1.0, gy(phx - 1.0, phz + 6.0) - 0.04, phz + 6.0], 30, col='box')
    for k in range(2):
        bx, bz = phx - 4.2, phz - 1.2 + k * 0.6
        obj('Bucket_Wood', [bx, gy(bx, bz), bz], rng.uniform(0, 360), stat=False)
    lantern([phx - 3.4, gy(phx - 3.4, phz + 1.6), phz + 1.6])
    pavoid = [(phx, phz, 6.0), (nxp, nz, 9.0)]
    for (x, z) in sample_isle(PI, 0.3, 0.8, 4, avoid=pavoid, minsep=6):
        obj(f'Palm_{rng.integers(3)}', [x, gy(x, z) - 0.05, z], rng.uniform(0, 360), s=rng.uniform(0.85, 1.1), stat=False)
        box('Palm Trunk', [x, gy(x, z) + 1.5, z], [0.5, 3.0, 0.5])
    for (x, z) in sample_isle(PI, 0.1, 0.9, 25, avoid=pavoid, minsep=1.5):
        obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(PI, 0.3, 0.8, 4, avoid=pavoid, minsep=3):
        obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), stat=False)
    pd = shore_point(PI, pc[0], pc[1] + 2.0, -1, 0, 0.9)
    obj('Dock', [pd[0] + 1.0, dy, pc[1] + 2.0], 270, col='mesh', name='Dock (Pump Isle)')
    gondola([pd[0] - 8.0, 0, pc[1] + 4.8], 270)

    # ---------------- albatross isle (-152, 150): the easter egg
    AI = 'Isle_Albatross'; ac = IS.ISLANDS[IS.INDEX[AI]][1]
    dxh, dzh = -ac[0], -ac[1]; ln = math.hypot(dxh, dzh); dxh, dzh = dxh / ln, dzh / ln
    gp = shore_point(AI, ac[0], ac[1], dxh, dzh, 0.78)
    gyaw = yaw_to(-dxh, -dzh)                     # bow pulled up the beach, pointing inland
    ge = [-3.0, gyaw, 7.0]                          # nose up the slope a little, leaning on its side
    gpos = np.array([gp[0], gy(gp[0], gp[1]) - 0.12, gp[1]])
    obj('Gondola', gpos, e=ge, col='mesh', name='Beached Gondola (Albatross Nest)')
    Rg = euler(*ge)
    def in_boat(m, lp, yaw, s=1.0):
        wp = gpos + Rg @ np.array(lp, float)
        obj(m, wp, e=[ge[0], (ge[1] + yaw) % 360, ge[2]], s=s, stat=True, noshadow=s < 0.5)
    in_boat('Nest', [0.0, 0.14, 0.35], 0, s=0.85)
    in_boat('Albatross', [0.0, 0.30, 0.3], -90)
    for it in deco_boat_contents(None):
        in_boat(it['mesh'], it['p'], it['r'], it['s'])
    for (x, z) in sample_isle(AI, 0.85, 1.02, 10, avoid=[(gp[0], gp[1], 4.5)], minsep=1.0):
        m = STARS[rng.integers(3)] if rng.random() < 0.45 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.4), stat=False, noshadow=True)
    for (x, z) in sample_isle(AI, 0.3, 1.05, 5, avoid=[(gp[0], gp[1], 5.0)], minsep=5):
        obj('Boulder_01', [x, gy(x, z) - 0.3, z], rng.uniform(0, 360), s=rng.uniform(1.0, 2.2), col='mesh')
    for (x, z) in sample_isle(AI, 0.1, 0.9, 22, avoid=[(gp[0], gp[1], 3.5)], minsep=1.2):
        obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.4), stat=False, noshadow=True)
    for (x, z) in sample_isle(AI, 0.8, 0.97, 3, minsep=4):
        crabs.append(dict(p=R3([x, gy(x, z), z]), r=round(rng.uniform(0, 360), 1)))
    SO.append(dict(clip='Wind_Loop', p=R3([ac[0], 6, ac[1]]), vol=0.35, minD=5, maxD=45, spatial=1))

    # =========================================================== boats at the House's water stairs
    for (n, d) in (((0, 1), 270), ((2, 1), 90)):
        g = vpos(n)
        gondola(local(g, d, 3.6, 0, 27.5), d)

    # =========================================================== stair tower + water slide (hall 1,0 south)
    tw = [o_ for o_ in O if o_.get('name') == 'StairTower'][0]
    obj('Ivy_Tower', tw['p'], tw['r'], name='Ivy (Stair Tower)')
    obj('Slide', [0, 0, 0], 0, name='Water Slide', col='none')
    obj('SlideWater', [0, 0, 0], 0, noshadow=True, stat=False)
    L['slide'] = dict(exit=R3([ex_x, gy(ex_x, ex_z) + 0.05, ex_z]), exitR=180.0,
                     path=[round(float(v), 3) for pt in EX['slide_path'] for v in pt])
    EM.append(dict(kind='spray', p=R3([slide_end[0], 0.3, slide_end[2]]), size=[3, 0.2, 3]))

    # =========================================================== coral reefs (+ a wreck)
    def reef_patch(cx, cz, n, rad=4.0):
        pal = rng.choice(list(VARIANTS.keys()), size=3, replace=False)
        names = list(SPECIES.keys()); w = np.array([SPECIES[k][0] for k in names], float); w /= w.sum()
        placed = []
        for k in range(n):
            x, z = cx + rng.normal() * rad * 0.5, cz + rng.normal() * rad * 0.5
            if any((x - a) ** 2 + (z - b) ** 2 < 0.8 for a, b in placed): continue
            g = IS.ground(x, z)
            m = names[rng.choice(len(names), p=w)]
            h = float(bounds(m)[1][1])
            room = (-0.9 - g)                          # keep tops under the lowest tide (-0.45) + a boat's draft
            if room < 0.25: continue
            s = float(min(rng.uniform(0.7, 1.5), room / max(h, 0.05)))
            if s < 0.35: continue
            pal_m = [v for v in SPECIES[m][1] if v in pal] or SPECIES[m][1]
            mv = None if rng.random() < 0.12 else pal_m[rng.integers(len(pal_m))]
            obj(m, [x, g - 0.06, z], rng.uniform(0, 360), s=s, stat=False, mv=mv, noshadow=True, tag='reef')
            placed.append((x, z))
        for k in range(rng.integers(1, 3)):
            x, z = cx + rng.normal() * rad * 0.7, cz + rng.normal() * rad * 0.7; g = IS.ground(x, z)
            m = ['Sponge_Barrel', 'Sponge_Grass'][rng.integers(2)]
            if -0.9 - g > 0.5: obj(m, [x, g - 0.05, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.4), stat=False, noshadow=True, tag='reef')
        for k in range(rng.integers(1, 4)):
            x, z = cx + rng.normal() * rad, cz + rng.normal() * rad; g = IS.ground(x, z)
            m = STARS[rng.integers(3)] if rng.random() < 0.8 else 'Clam_Giant'
            if g < -0.9: obj(m, [x, g + 0.01, z], rng.uniform(0, 360), s=rng.uniform(1.0, 1.5), stat=False, noshadow=True, tag='reef')

    def clear_of_structures(x, z):
        if abs(x) < 74 and abs(z) < 74: return False                       # the House itself
        if abs(x - 60) < 8 and 70 < z < 112: return False                  # aqueduct + noria
        if abs(x) < 9 and -86 < z < -70: return False                      # stair tower
        for (gx, gz, rr) in ((-90, 0, 14), (90, 0, 14)):                   # water stairs
            if (x - gx) ** 2 + (z - gz) ** 2 < rr * rr: return False
        return True
    patches = 0
    for k in range(400):
        if patches >= 46: break
        a = rng.uniform(0, 2 * math.pi); r_ = rng.uniform(80, 112)
        x, z = math.cos(a) * r_ * 1.05, math.sin(a) * r_
        if not clear_of_structures(x, z) or IS.ground(x, z) > -1.4: continue
        reef_patch(x, z, rng.integers(7, 14)); patches += 1
    for k in range(10):          # lagoon between the House and the south beach
        x, z = rng.uniform(-50, 50), rng.uniform(-100, -78)
        if clear_of_structures(x, z) and IS.ground(x, z) < -1.4: reef_patch(x, z, rng.integers(6, 11))
    for name, (cx, cz), (rx, rz), *_ in IS.ISLANDS:
        for k in range(9 if name != 'Isle_Albatross' else 5):
            a = rng.uniform(0, 2 * math.pi); f = rng.uniform(1.12, 1.45)
            x, z = cx + math.cos(a) * rx * f, cz + math.sin(a) * rz * f
            if clear_of_structures(x, z) and IS.ground(x, z) < -1.4: reef_patch(x, z, rng.integers(6, 12), rad=3.5)
    wx, wz = -128.0, -118.0
    obj('Ship_Dutch', [wx, IS.ground(wx, wz) + 0.9, wz], e=[-4, 35, 24], col='none', name='Wreck of the Dutch ship', stat=True)
    for k in range(7):
        a = rng.uniform(0, 6.28); reef_patch(wx + math.cos(a) * 11, wz + math.sin(a) * 9, rng.integers(6, 11))

    # =========================================================== ivy on the House
    by_name = {o_['name']: o_ for o_ in O if 'name' in o_}
    def follow(target, ivy, extra_r=0.0, dy=0.0, local_off=None):
        t = by_name.get(target)
        if t is None: return
        p = list(t['p'])
        if local_off is not None:
            lx, lz = rot_y(local_off[0], local_off[2], t['r']); p = [p[0] + lx, p[1] + local_off[1], p[2] + lz]
        obj(ivy, p, t['r'] + extra_r, name=f'Ivy ({target})')
    for i, t in enumerate(['Vestibule_10_E', 'Vestibule_12_E', 'Vestibule_20_W', 'Vestibule_22_N', 'Vestibule_10_N']):
        follow(t, f'Ivy_VestBlind_{i % 2}')
    for t in ['Vestibule_00_W', 'Vestibule_02_N', 'Vestibule_20_E', 'Vestibule_22_E']:
        follow(t, 'Ivy_VestWindow')
    for t in ['Arcade_00_01', 'Arcade_21_22', 'Arcade_02_12']:
        follow(t, 'Ivy_ArcadeWin')
    for t in ['Vestibule_11_S', 'Vestibule_12_E', 'Vestibule_20_W']:
        follow(t, 'Ivy_VestInnerBlind')
    for t in ['Vestibule_01_W', 'Vestibule_11_W', 'Vestibule_21_E']:
        follow(t, 'Ivy_VestInnerOpen')
    for t in ['Vestibule_01_N', 'Vestibule_11_N', 'Vestibule_21_N', 'Vestibule_02_E']:
        follow(t, 'Ivy_HangLine_S', local_off=(0, 15.95, 9.8))
    for t in ['Vestibule_01_W', 'Vestibule_21_E']:     # curtains over the water-stair arches (outside face)
        follow(t, 'Ivy_HangLine_L', extra_r=180, local_off=(0, 12.25, 12.45))
    for n in [(1, 1), (0, 0), (2, 2), (0, 2)]:
        v = vpos(n); obj('Ivy_HangRing', [v[0], 26.35, v[2]], rng.uniform(0, 360), name='Ivy (oculus)')
    navec = [o_ for o_ in O if o_.get('mesh') == 'Column' and o_.get('name') == 'Column']
    for k, c_ in enumerate(navec):
        if k % 3 == 0:
            obj(f'Ivy_Column_{(k // 3) % 2}', c_['p'], rng.uniform(0, 360), name='Ivy (Nave column)')

    # =========================================================== creatures, wading floor
    L['boats'] = boats
    L['crabs'] = crabs
    L['dolphins'] = dict(period=110.0, duration=22.0, routes=[
        dict(a=[-112, 0, -150], b=[-112, 0, 120]), dict(a=[95, 0, -110], b=[95, 0, 75]), dict(a=[-150, 0, -92], b=[140, 0, -94])])
    L['variants'] = variants
    L['wade'] = dict(y=-1.3, size=700)
    print(f'world2: boats {len(boats)}, crabs {len(crabs)}, seats {len(SE)}, objects {len(O)}')
