"""House v3 layout (redlines 1). Called from layout.py after the vestibules and galleries are placed; adds to the same layout
dict (Unity space, metres, degrees):
  the Colossus in the centre hall with the Trevi wall fountain, fountains in every hall, roof water channels flowing out from
  the aqueduct, the open marble tower and its slide, the corner exit + sand bar + sea hall, isle halls on every island, the far
  wings on sand bars, the ruin's arches / vine drapes / vine hammocks / drum table / block seats / paths / shards, eroded water
  stairs with broken stairs, coral and fish in front of them, tall palms and coconuts, floating docks, floating vines,
  gold plaques, gate torches, ivy and flowers."""
import os, json, math, numpy as np
import islands as IS
import ruin as RU
from ivy import euler, read_pms

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'out', 'Data')
EX = json.load(open(os.path.join(DATA, 'Kit2Extra.json')))
EX3 = json.load(open(os.path.join(DATA, 'Kit3Extra.json')))
rng = np.random.default_rng(4343)
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

VARIANTS = {
    'rose': ([0.62, 0.22, 0.36], [1.0, 0.62, 0.72], 0.3), 'violet': ([0.35, 0.2, 0.55], [0.8, 0.6, 1.0], 0.35),
    'amber': ([0.75, 0.38, 0.12], [1.0, 0.8, 0.35], 0.25), 'lemon': ([0.6, 0.55, 0.18], [0.98, 0.95, 0.55], 0.2),
    'teal': ([0.12, 0.45, 0.42], [0.5, 0.95, 0.85], 0.35), 'coral': ([0.85, 0.3, 0.25], [1.0, 0.7, 0.55], 0.25),
    'ochre': ([0.5, 0.4, 0.25], [0.85, 0.75, 0.55], 0.12), 'olive': ([0.3, 0.36, 0.2], [0.62, 0.7, 0.42], 0.1),
}
SPECIES = {
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
FISH = ['FishSchool_Tang', 'FishSchool_Chromis', 'FishSchool_Reef']

def wing_lengths():
    return {w: float(bounds(w)[1][0] - bounds(w)[0][0]) for w in ('Wing_1', 'Wing_2', 'Wing_3')}

def build(L, vpos, local, info):
    """info: dict from layout.py with 'chosen' (gallery edges), 'sides' {(node, dir): kind}, 'naves'."""
    IS.add_wing_bars(wing_lengths())
    O = L['objects']; ST = L['statues']; LI = L['lights']; SH = L['shafts']; EM = L['emitters']; SO = L['sounds']; SE = L['seats']
    PR = L['probes']; RV = L['reverbs']
    boats = []; crabs = []; variants = [dict(name=k, base=v[0], tip=v[1], glow=v[2]) for k, v in VARIANTS.items()]

    def obj(mesh, p, r=0.0, e=None, s=1.0, col='none', name=None, stat=True, mv=None, noshadow=False, spin=None, tag='', floats=None):
        d = dict(name=name or mesh, mesh=mesh, p=R3(p), r=round(float(r) % 360, 3), s=[float(s)] * 3 if np.isscalar(s) else [float(v) for v in s],
                 col=col, stat=stat, tag=tag)
        if e is not None: d['e'] = [float(v) for v in e]
        if mv: d['mv'] = mv
        if noshadow: d['noshadow'] = True
        if spin: d['spin'] = list(spin)
        if floats is not None: d['floats'] = True; d['fy'] = float(floats); d['stat'] = False
        O.append(d); return d

    def box(name, p, size, r=0.0, tag=''):
        O.append(dict(name=name, mesh='', p=R3(p), r=round(float(r) % 360, 3), s=list(size), col='box', stat=True, tag=tag))

    def gy(x, z): return IS.ground(x, z)

    def lantern(p, rng_=6.0, inten=1.4, mesh=True, r=0.0):
        if mesh: obj('Lantern_Wood', p, r, col='none', stat=False)
        LI.append(dict(kind='lantern', p=R3([p[0], p[1] + 0.32, p[2]]), range=rng_, intensity=inten, color=[1.0, 0.66, 0.36]))

    def sample_isle(name, dmin, dmax, n, avoid=(), minsep=0.0, tries=5000, near=None):
        isl = IS.ISLANDS[IS.INDEX[name]]; cx, cz = isl[1]; rr = max(isl[2])
        out = []
        for _ in range(tries):
            if len(out) >= n: break
            if near is not None:
                x = near[0] + rng.normal() * near[2]; z = near[1] + rng.normal() * near[2]
            else:
                x = cx + rng.uniform(-1.4, 1.4) * rr; z = cz + rng.uniform(-1.4, 1.4) * rr
            d = IS.island_d(x, z, name)
            if not (dmin <= d <= dmax): continue
            if any((x - a) ** 2 + (z - b) ** 2 < q * q for a, b, q in avoid): continue
            if minsep and any((x - a) ** 2 + (z - b) ** 2 < minsep * minsep for a, b in out): continue
            out.append((x, z))
        return out

    def shore_point(name, x0, z0, dx, dz, d_want=0.93):
        for t in np.linspace(0, 120, 2401):
            x, z = x0 + dx * t, z0 + dz * t
            if IS.island_d(x, z, name) >= d_want: return (x, z)
        return None

    def deco_boat_contents():
        items = []
        for z in (-1.25, -0.95, 1.65, 1.95, 2.25):
            m = STARS[rng.integers(3)] if rng.random() < 0.45 else SHELLS[rng.integers(3)]
            items.append(dict(mesh=m, p=[round(rng.uniform(-0.25, 0.25), 3), 0.13, z], r=round(rng.uniform(0, 360), 1), s=round(rng.uniform(0.8, 1.2), 2)))
        return items

    def gondola(p, yaw, drivable=True, name='Gondola'):
        boats.append(dict(name=name, p=R3([p[0], 0.0, p[2]]), r=round(yaw % 360, 2), drivable=drivable, items=deco_boat_contents()))

    FREE = EX3['dock']['freeboard']
    def dock(p, yaw, name):
        """floating deck (rides on the tide) on fixed piles; p = landward end of the dock."""
        obj('DockPiles', [p[0], 0.0, p[2]], yaw, col='none', name=name + ' piles')
        obj('DockDeck', [p[0], 0.2 + FREE, p[2]], yaw, col='mesh', name=name, floats=FREE)

    def plaque(p, yaw, role):
        obj('Plaque_Gold', p, yaw, name=f'Plaque (blank) - {role}', noshadow=True)

    def fountain(c, s=1.0, ry=0.0, name='Fountain'):
        obj('HallFountain', c, ry, s=s, col='mesh', name=name)
        obj('HallFountainPool', c, ry, s=s, noshadow=True, stat=False, name=name + ' (pool)')
        obj('HallFountainWater', c, ry, s=s, noshadow=True, stat=False, name=name + ' (water)')
        SO.append(dict(clip='Cascade_Loop', p=R3([c[0], c[1] + 1.5, c[2]]), vol=0.32 * s, minD=1.5, maxD=16 * s, spatial=1))
        EM.append(dict(kind='spray', p=R3([c[0], c[1] + 0.5, c[2]]), size=[2.0 * s, 0.2, 2.0 * s]))

    def isle_hall(entrance, ry, s=1.0, name='Isle Hall', palms=0):
        """walk-in hall: floor at the highest sand under its footprint; returns the floor height."""
        Ln = EX3['isle_hall']['len'] * s; Wd = EX3['isle_hall']['width'] * s
        hs = []
        for lx in np.linspace(-Wd / 2, Wd / 2, 5):
            for lz in np.linspace(0, Ln, 7):
                x, z = rot_y(lx, lz, ry); hs.append(gy(entrance[0] + x, entrance[1] + z))
        fy = max(0.15, max(hs) + 0.05)
        obj('IsleHall', [entrance[0], fy, entrance[1]], ry, s=s, col='mesh', name=name)
        cx, cz = rot_y(0, Ln / 2, ry)
        fountain([entrance[0] + cx, fy, entrance[1] + cz], 0.55 * s, name=name + ' fountain')
        obj('Ivy_IsleHall', [entrance[0], fy, entrance[1]], ry, s=s, name=f'Ivy ({name})')
        for k in range(2):        # statues on plinths either side of the fountain
            lx = (-1) ** k * Wd * 0.28; lz = Ln * 0.5
            x, z = rot_y(lx, lz, ry)
            p = [entrance[0] + x, fy, entrance[1] + z]
            obj('Plinth_Square', p, ry, s=s, col='box', name='Plinth')
            st = ['Statue_Hare', 'Statue_SeatedSage', 'Statue_Queen', 'Statue_Child'][rng.integers(4)]
            ST.append(dict(mesh=st, p=R3([p[0], fy + 1.3 * s, p[2]]), r=round((ry + (90 if k else 270)) % 360, 2), s=0.9 * s, role=f'Statue of {name}'))
            px, pz = rot_y(lx - (-1) ** k * 0.52 * s, lz, ry)
            plaque([entrance[0] + px, fy + 0.7 * s, entrance[1] + pz], ry + (90 if (-1) ** k > 0 else 270), f'{name} statue')
        for k in range(3):
            lz = Ln * (k + 0.5) / 3; x, z = rot_y(0, lz, ry)
            SH.append(dict(p=R3([entrance[0] + x, fy + 11.0 * s, entrance[1] + z]), radius=0.8 * s, height=10.5 * s, kind='window', face=ry + 90, dim=0.5))
        x, z = rot_y(0, Ln / 2, ry)
        PR.append(dict(p=R3([entrance[0] + x, fy + 6 * s, entrance[1] + z]), size=[Wd - 2, 14 * s, Ln - 2] if ry % 180 == 0 else [Ln - 2, 14 * s, Wd - 2], name=name.replace(' ', '_')))
        RV.append(dict(p=R3([entrance[0] + x, fy + 4, entrance[1] + z]), minD=6 * s, maxD=12 * s, preset='StoneCorridor'))
        return fy

    # =========================================================== the Colossus: centre hall (1,1), palm under the oculus
    o = vpos((1, 1)); col = EX['colossus']; palm = col['palm']; ped = col['pedestal']
    ry = 180.0
    ox, oz = rot_y(palm[0], palm[2], ry)
    base = [o[0] - ox, 0.0, o[2] - oz]
    obj('Colossus_Pedestal', base, ry, col='mesh', name='Colossus Pedestal')
    ST.append(dict(mesh='Colossus', p=R3([base[0], ped, base[2]]), r=ry, s=1.0, role='The Colossus: a figure holding its palm up to the light (seat)'))
    bx_, bz_ = rot_y(0, 4.71, ry)
    plaque([base[0] + bx_, 1.0, base[2] + bz_], ry + 180, 'The Colossus')
    pw = [o[0], ped + palm[1], o[2]]
    nrm = col['palm_normal']; nx, nz = rot_y(nrm[0], nrm[2], ry)
    seat_p = [pw[0] + nx * 0.06, pw[1] + nrm[1] * 0.06, pw[2] + nz * 0.06]
    SE.append(dict(p=R3(seat_p), r=ry, kind='palm', text="Rest in the Colossus' palm", exit=R3([base[0], 0.05, base[2] - 6.2]),
                   size=[0.9, 0.5, 0.9], trigger=dict(p=R3([base[0], 1.0, base[2] - 4.75]), size=[3.4, 2.0, 0.6])))
    LI.append(dict(kind='spot', p=R3([o[0], 26.2, o[2]]), dir=[0, -1, 0], angle=20, range=16, intensity=3.0, color=[1.0, 0.95, 0.86]))
    EM.append(dict(kind='sparkle', p=R3([pw[0], pw[1] + 0.7, pw[2]]), size=[1.8, 1.6, 1.8]))
    SH.append(dict(p=R3([o[0], 26.6, o[2]]), radius=0.9, height=26.6 - pw[1], kind='palm', face=0))
    # the Trevi on the hall's south wall (blind side), fed through the wall from the roof channels
    tr = EX3['trevi']; sry = 180.0
    for m in ('Trevi', 'TreviShell'):
        obj(m, o, sry, col='mesh' if m == 'Trevi' else 'none', name='Trevi fountain' if m == 'Trevi' else 'Trevi shell')
    obj('TreviPool', o, sry, noshadow=True, stat=False, name='Trevi (pool)')
    obj('TreviWater', o, sry, noshadow=True, stat=False, name='Trevi (water)')
    ST.append(dict(mesh='Statue_WingedFigure', p=local(o, sry, tr['statue'][0], tr['statue'][1], tr['statue'][2]), r=(sry + 180) % 360, s=1.15, role='Figure in the Trevi niche'))
    for k, hp in enumerate(tr['horses']):
        ST.append(dict(mesh='Statue_Horse', p=local(o, sry, hp[0], hp[1], hp[2]), r=(sry + 180 + (30 if hp[0] < 0 else -30)) % 360, s=0.78,
                       role='Sea-horse of the Trevi'))
    plaque(local(o, sry, 0, 0.32, 4.96), sry, 'The Trevi fountain')
    SO.append(dict(clip='Cascade_Loop', p=local(o, sry, 0, 1.5, 8.0), vol=0.7, minD=2.5, maxD=30, spatial=1))
    EM.append(dict(kind='splash', p=local(o, sry, 0, 0.45, 7.3), size=[2.4, 0.2, 0.6]))
    EM.append(dict(kind='spray', p=local(o, sry, 0, 0.5, 7.0), size=[8, 0.2, 2.4]))
    L['spawn'] = dict(p=R3([o[0] - 4.5, 0.1, o[2] - 3.7]), r=35.0)

    # =========================================================== fountains in every other hall (not the cascade hall)
    for n in [(i, j) for i in range(3) for j in range(3)]:
        if n in ((1, 1), (2, 2)): continue
        v = vpos(n); fountain([v[0], 0.0, v[2]], 1.0, name=f'Fountain (hall {n[0]},{n[1]})')

    # =========================================================== islands
    for isl in IS.ISLANDS:
        name, (cx, cz) = isl[0], isl[1]
        obj(name, [cx, 0, cz], 0, col='mesh', name='Sand_' + name)

    # ---------------- south beach (0, -128)
    SB = 'Isle_SouthBeach'
    dock0 = shore_point(SB, 12.0, -128.0, 0, 1, 0.9)
    hall_sb = (-34.0, -118.0)
    avoid = [(12.0, dock0[1] + 7, 4.0), (32.3, -124.0, 4.0), (hall_sb[0], hall_sb[1] - 11, 15.0)]
    clusters = sample_isle(SB, 0.15, 0.75, 8, avoid=avoid, minsep=14)
    palms = []
    for (cx_, cz_) in clusters:
        for k in range(rng.integers(3, 5)):
            x, z = cx_ + rng.normal() * 3.5, cz_ + rng.normal() * 3.0
            if IS.island_d(x, z, SB) > 0.85 or any((x - a) ** 2 + (z - b) ** 2 < 4 for a, b in palms) or any((x - a) ** 2 + (z - b) ** 2 < q * q for a, b, q in avoid): continue
            palms.append((x, z))
    for (x, z) in [(30.0, -124.0), (34.6, -124.0)]: palms.append((x, z))
    def palm(x, z, tall, s=None):
        m = f'Palm_Tall_{rng.integers(3)}' if tall else f'Palm_{rng.integers(3)}'
        obj(m, [x, gy(x, z) - 0.05, z], rng.uniform(0, 360), s=s or rng.uniform(0.88, 1.12), col='none', stat=False)
        box('Palm Trunk', [x, gy(x, z) + 1.5, z], [0.5, 3.0, 0.5])
        if rng.random() < 0.6:
            a = rng.uniform(0, 6.28); d = rng.uniform(0.8, 2.2)
            cx2, cz2 = x + math.cos(a) * d, z + math.sin(a) * d
            obj('Coconuts', [cx2, gy(cx2, cz2) - 0.02, cz2], rng.uniform(0, 360), s=rng.uniform(0.9, 1.15), stat=False, noshadow=True)
    for i, (x, z) in enumerate(palms):
        palm(x, z, tall=(i % 3 == 0))
    isle_hall(hall_sb, 180.0, name='Isle Hall (South Beach)')
    for (x, z) in sample_isle(SB, 0.15, 0.82, 16, avoid=avoid, minsep=3):
        obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.2), stat=False)
    for (cx_, cz_) in sample_isle(SB, 0.1, 0.7, 9, avoid=avoid, minsep=9):          # grass in clumps
        for (x, z) in sample_isle(SB, 0.0, 0.9, rng.integers(5, 9), avoid=avoid, minsep=0.8, near=(cx_, cz_, 1.6)):
            obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.4), stat=False, noshadow=True)
    for (x, z) in sample_isle(SB, 0.2, 0.7, 12, avoid=avoid, minsep=2):
        obj(PLANTS[rng.integers(len(PLANTS))], [x, gy(x, z) - 0.02, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.4), stat=False)
    for (x, z) in sample_isle(SB, 0.88, 1.03, 34, avoid=avoid, minsep=1.0):
        m = STARS[rng.integers(3)] if rng.random() < 0.4 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(SB, 0.92, 1.12, 5, avoid=avoid, minsep=12):
        obj('Boulder_01', [x, gy(x, z) - 0.25, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.6), col='mesh')
    for (x, z) in sample_isle(SB, 0.8, 0.97, 10, avoid=avoid, minsep=3):
        crabs.append(dict(p=R3([x, gy(x, z), z]), r=round(rng.uniform(0, 360), 1)))
    dock([12.0, 0, dock0[1] - 1.0], 0, 'Dock (South Beach)')
    gondola([14.8, 0, dock0[1] + 8.0], 0)
    lantern([10.6, gy(10.6, dock0[1] - 2.0) + 0.02, dock0[1] - 2.0])
    hz = -124.0; hy = gy(32.3, hz) + 1.3
    obj('Hammock_Vine', [32.3, hy, hz], 90, stat=False, name='Vine hammock')
    SE.append(dict(p=R3([32.3, hy - 0.4, hz]), r=0, kind='hammock', text='Rest in the hammock', exit=R3([32.3, gy(32.3, hz - 1.6) + 0.05, hz - 1.6]), size=[1.2, 0.4, 0.8]))
    SO.append(dict(clip='Ocean_Near_Loop', p=[0, 1, -104], vol=0.8, minD=8, maxD=90, spatial=1))
    SO.append(dict(clip='Wind_Loop', p=[0, 6, -128], vol=0.35, minD=10, maxD=70, spatial=1))
    EM.append(dict(kind='season', p=[0, 16, -128], size=[110, 1, 44], fall=15))

    # ---------------- ruin isle (142, 12): arch ruins, drapes, vine hammocks, drum table, block seats, paths, shards
    RI = 'Isle_Ruin'; rc = IS.ISLANDS[IS.INDEX[RI]][1]
    g0 = gy(rc[0], rc[1]); RO = np.array([rc[0], g0, rc[1]])
    for (x, z) in RU.COLUMNS:
        obj('Column', RO + [x, RU.BASE_Y, z], 0, col='capsule', name='Ruin Column')
    obj('ArchRuin', RO, 0, col='mesh', name='Arch ruins over the colonnade')
    obj('Ivy_Ruin3', RO, 0, name='Ivy and vine drapes (Ruin)')
    for (x, z) in RU.STUMPS:
        y = RU.BASE_Y + 0.1
        for k in range(rng.integers(2, 4)):
            obj('Fragment_Drum', RO + [x + rng.normal() * 0.04, y, z + rng.normal() * 0.04], rng.uniform(0, 360), col='box', name='Broken Column Drum')
            y += 0.92
        obj('Fragment_Drum', RO + [x + 1.4, 0.42, z + 0.6], rng.uniform(0, 360), e=[90, rng.uniform(0, 360), 0], col='box', name='Fallen Drum')
        if (x, z) == RU.STUMPS[0]:
            obj('Marble_Bust', RO + [x, y - 0.02, z], 250, s=1.6, col='none', name='Bust on the broken column')
    for (hx, hz_), yaw in RU.HAMMOCKS:
        hy = gy(rc[0] + hx, rc[1] + hz_) + RU.HAMMOCK_Y
        obj('Hammock_Vine', [rc[0] + hx, hy, rc[1] + hz_], yaw, stat=False, name='Vine hammock')
        sx_, sz_ = rot_y(0, 1.0, yaw)
        SE.append(dict(p=R3([rc[0] + hx, hy - 0.4, rc[1] + hz_]), r=yaw + 90, kind='hammock', text='Rest in the hammock',
                       exit=R3([rc[0] + hx - sz_ * 1.4, g0 + 0.05, rc[1] + hz_ + sx_ * 1.4]), size=[1.2, 0.4, 0.8]))
    # the table: a slice of column with only the fruit bowl left on it; rough blocks for chairs
    T = RO + [RU.TABLE[0], gy(rc[0], rc[1]) - g0, RU.TABLE[1]]
    top = T[1] + EX3['table_drum_top']
    obj('TableDrum', T, rng.uniform(0, 360), col='mesh', name='Table (a slice of column)')
    obj('Bowl_Wood', [T[0], top, T[2]], rng.uniform(0, 360), s=1.6, stat=False)
    heap = ['Fruit_Apple', 'Fruit_Apple', 'Fruit_Lemon', 'Fruit_Lime', 'Fruit_Pomegranate', 'Fruit_Kiwi', 'Fruit_Apple', 'Fruit_Lemon']
    for k, m in enumerate(heap):
        a = k * 2.4; r_ = 0.09 if k < 6 else 0.03
        obj(m, [T[0] + math.cos(a) * r_, top + 0.03 + (0.07 if k >= 6 else 0), T[2] + math.sin(a) * r_], rng.uniform(0, 360), stat=False)
    obj('Basket_Wicker', T + [0.0, 0.0, 1.95], 20, s=1.4, stat=False)
    for k, m in enumerate(['Fruit_Apple', 'Fruit_Lemon', 'Fruit_Lime', 'Fruit_Apple']):
        obj(m, T + [0.08 * math.cos(k * 1.6), 0.05, 1.95 + 0.08 * math.sin(k * 1.6)], rng.uniform(0, 360), stat=False)
    for k, a in enumerate((20, 75, 135, 200, 255, 315)):
        aa = math.radians(a + rng.uniform(-8, 8)); rr_ = 1.45 + rng.uniform(-0.1, 0.15)
        px, pz = T[0] + math.cos(aa) * rr_, T[2] + math.sin(aa) * rr_
        pyy = gy(px, pz) - 0.02
        face = yaw_to(T[0] - px, T[2] - pz)
        obj(f'BlockSeat_{k % 4}', [px, pyy, pz], face + rng.uniform(-25, 25), col='box', name='Block seat (a scrap of the ruin)')
        SE.append(dict(p=R3([px, pyy + EX3['block_seat_h'] + 0.01, pz]), r=face, kind='bench', text='Sit at the table',
                       exit=R3([px + (px - T[0]) * 0.5, pyy + 0.05, pz + (pz - T[2]) * 0.5]), size=[0.6, 0.4, 0.6]))
    # the two kings' chess game on a drum, the treasure chest beside it
    obj('Fragment_Drum', T + [0.0, -0.3, -2.45], 0, col='box', name='Chess Drum')
    obj('Chess_Set', T + [0.0, 0.64, -2.45], 12, s=1.2, stat=False)
    cxp, czp = T[0] + 1.25, T[2] - 2.9
    obj('Treasure_Chest', [cxp, gy(cxp, czp) - 0.02, czp], 300, col='box', name='Treasure Chest (beside the chess drum)')
    obj('Plinth_Round', RO + [-12.6, gy(rc[0] - 12.6, rc[1] - 1.0) - g0 - 0.1, -1.0], 0, col='box')
    obj('Whale_Bronze', RO + [-12.6, gy(rc[0] - 12.6, rc[1] - 1.0) - g0 + 1.15, -1.0], 120, s=1.2, col='none')
    obj('Lion_Head', RO + [9.2, RU.BASE_Y + 0.1 + 0.92 * 2 - 0.02, -3.5], 200, s=1.5, col='none', name='Lion head on the broken column')
    for (x, z) in [(-6.9, -5.0), (6.9, 5.0), (2.3, 5.2), (-2.3, -5.2)]:
        lantern(RO + [x, gy(rc[0] + x, rc[1] + z) - g0, z], rng_=5.0, inten=1.1, r=rng.uniform(0, 360))
    obj('RuinPaths', [0, 0, 0], 0, col='mesh', name='Eroded marble paths', noshadow=True)
    for k in range(48):     # marble shards in the grass and along the paths
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(3.2, 17.0)
        x, z = rc[0] + math.cos(a) * d * 1.2, rc[1] + math.sin(a) * d * 0.8
        if abs(x - T[0]) < 2.5 and abs(z - T[2]) < 3.4: continue
        obj(f'Shard_{rng.integers(4)}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.7, 1.4), stat=False, noshadow=True, name='Marble shard')
    for (x, z) in RU.COLUMNS + RU.STUMPS:
        for k in range(rng.integers(1, 3)):
            a = rng.uniform(0, 6.28); r_ = rng.uniform(1.0, 1.6)
            px, pz = x + math.cos(a) * r_, z + math.sin(a) * r_
            if abs(pz) < 3.2 and abs(px) < 3.0: continue
            obj(PLANTS[rng.integers(len(PLANTS))], RO + [px, gy(rc[0] + px, rc[1] + pz) - g0 - 0.02, pz], rng.uniform(0, 360), s=rng.uniform(1.0, 1.5), stat=False)
    hall_ri = (160.0, 22.0)
    ravoid = [(rc[0], rc[1], 14.0), (hall_ri[0], hall_ri[1] + 11, 14.0)]
    for i, (x, z) in enumerate(sample_isle(RI, 0.35, 0.85, 10, avoid=ravoid, minsep=6)):
        palm(x, z, tall=(i % 2 == 0))
    isle_hall(hall_ri, 0.0, name='Isle Hall (Ruin)')
    for (x, z) in sample_isle(RI, 0.3, 0.85, 8, avoid=ravoid, minsep=4):
        obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.25), stat=False)
    # grass gathered in clumps toward the middle of the isle (round the columns, clear of the table)
    for (cx_, cz_) in sample_isle(RI, 0.08, 0.5, 14, avoid=[(T[0], T[2], 3.2), (hall_ri[0], hall_ri[1] + 11, 12.0)], minsep=4.5):
        for (x, z) in sample_isle(RI, 0.0, 0.62, rng.integers(6, 11), avoid=[(T[0], T[2], 2.6)], minsep=0.55, near=(cx_, cz_, 1.3)):
            obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.85, 1.35), stat=False, noshadow=True)
    for (x, z) in sample_isle(RI, 0.88, 1.03, 16, minsep=1.5):
        m = STARS[rng.integers(3)] if rng.random() < 0.4 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    # starfish on the beach that faces the East Water Stair (redline 1)
    for (x, z) in sample_isle(RI, 0.86, 1.02, 16, minsep=1.2, near=(rc[0] - 33, rc[1] - 4, 7.0)):
        obj(STARS[rng.integers(3)], [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(1.0, 1.5), stat=False, noshadow=True, name='Starfish')
    for (x, z) in sample_isle(RI, 0.8, 0.97, 4, minsep=5):
        crabs.append(dict(p=R3([x, gy(x, z), z]), r=round(rng.uniform(0, 360), 1)))
    rd = shore_point(RI, rc[0], 14.0, -1, 0, 0.9)
    dock([rd[0] + 1.0, 0, 14.0], 270, 'Dock (Ruin)')
    gondola([rd[0] - 8.0, 0, 16.8], 270)
    lantern([rd[0] + 2.5, gy(rd[0] + 2.5, 12.0), 12.0])
    SO.append(dict(clip='Ocean_Near_Loop', p=R3([rd[0], 1, 14]), vol=0.7, minD=6, maxD=60, spatial=1))
    SO.append(dict(clip='Wind_Loop', p=R3(RO + [0, 8, 0]), vol=0.3, minD=6, maxD=50, spatial=1))
    EM.append(dict(kind='season', p=R3(RO + [0, 14, 0]), size=[30, 1, 20], fall=14))
    EM.append(dict(kind='dust', p=R3(RO + [0, 5, 0]), size=[22, 9, 10]))

    # ---------------- pump isle: aqueduct + noria feed the cascade and the roof channels; the pump house became an isle hall
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
    hall_pi = (66.0, 107.0)
    isle_hall(hall_pi, 0.0, name='Isle Hall (Pump Isle)')
    obj('Barrels', [57.5, gy(57.5, 110.0) - 0.04, 110.0], 30, col='box')
    for k in range(2):
        bx2, bz2 = 56.0, 108.4 + k * 0.6
        obj('Bucket_Wood', [bx2, gy(bx2, bz2), bz2], rng.uniform(0, 360), stat=False)
    lantern([57.8, gy(57.8, 107.6), 107.6])
    pavoid = [(hall_pi[0], hall_pi[1] + 11, 12.0), (nxp, nz, 9.0)]
    for i, (x, z) in enumerate(sample_isle(PI, 0.3, 0.8, 5, avoid=pavoid, minsep=6)):
        palm(x, z, tall=(i % 2 == 1))
    for (cx_, cz_) in sample_isle(PI, 0.1, 0.7, 5, avoid=pavoid, minsep=6):
        for (x, z) in sample_isle(PI, 0.0, 0.9, rng.integers(5, 9), avoid=pavoid, minsep=0.7, near=(cx_, cz_, 1.4)):
            obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(PI, 0.3, 0.8, 4, avoid=pavoid, minsep=3):
        obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), stat=False)
    pd = shore_point(PI, pc[0], pc[1] + 2.0, -1, 0, 0.9)
    dock([pd[0] + 1.0, 0, pc[1] + 2.0], 270, 'Dock (Pump Isle)')
    gondola([pd[0] - 8.0, 0, pc[1] + 4.8], 270)

    # ---------------- albatross isle (-152, 150): the easter egg, and a small hall behind the nest
    AI = 'Isle_Albatross'; ac = IS.ISLANDS[IS.INDEX[AI]][1]
    dxh, dzh = -ac[0], -ac[1]; ln = math.hypot(dxh, dzh); dxh, dzh = dxh / ln, dzh / ln
    gp = shore_point(AI, ac[0], ac[1], dxh, dzh, 0.78)
    gyaw = yaw_to(-dxh, -dzh)
    ge = [-3.0, gyaw, 7.0]
    gpos = np.array([gp[0], gy(gp[0], gp[1]) - 0.12, gp[1]])
    obj('Gondola', gpos, e=ge, col='mesh', name='Beached Gondola (Albatross Nest)')
    Rg = euler(*ge)
    def in_boat(m, lp, yaw, s=1.0):
        wp = gpos + Rg @ np.array(lp, float)
        obj(m, wp, e=[ge[0], (ge[1] + yaw) % 360, ge[2]], s=s, stat=True, noshadow=s < 0.5)
    in_boat('Nest', [0.0, 0.14, 0.35], 0, s=0.85)
    in_boat('Albatross', [0.0, 0.30, 0.3], -90)
    for it in deco_boat_contents():
        in_boat(it['mesh'], it['p'], it['r'], it['s'])
    isle_hall((ac[0] + 1.0, ac[1] - 1.0), yaw_to(-dxh, -dzh), s=0.62, name='Isle Hall (Albatross Isle)')
    for (x, z) in sample_isle(AI, 0.85, 1.02, 10, avoid=[(gp[0], gp[1], 4.5)], minsep=1.0):
        m = STARS[rng.integers(3)] if rng.random() < 0.45 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.4), stat=False, noshadow=True)
    for (x, z) in sample_isle(AI, 0.75, 1.05, 4, avoid=[(gp[0], gp[1], 5.0)], minsep=5):
        obj('Boulder_01', [x, gy(x, z) - 0.3, z], rng.uniform(0, 360), s=rng.uniform(1.0, 2.2), col='mesh')
    for (x, z) in sample_isle(AI, 0.5, 0.95, 16, avoid=[(gp[0], gp[1], 3.5)], minsep=1.2):
        obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.4), stat=False, noshadow=True)
    for (x, z) in sample_isle(AI, 0.8, 0.97, 3, minsep=4):
        crabs.append(dict(p=R3([x, gy(x, z), z]), r=round(rng.uniform(0, 360), 1)))
    SO.append(dict(clip='Wind_Loop', p=R3([ac[0], 6, ac[1]]), vol=0.35, minD=5, maxD=45, spatial=1))

    # =========================================================== the far wings, each on a sand bar with an entrance hall
    for f in IS.wing_frames(wing_lengths()):
        px, pz = f['pos']; dx, dz = f['d']
        obj(f['mesh'], [px, 0.0, pz], f['ry'], col='none', name='Far wing of the House', noshadow=True)
        ent = (px + dx * 36.0, pz + dz * 36.0)
        isle_hall(ent, f['ry'], name=f'Entrance hall ({f["name"][-1]})')
        for k in range(rng.integers(3, 6)):
            a = rng.uniform(0, 6.28); d = rng.uniform(8, 18)
            x, z = f['bar'][0] + math.cos(a) * d * 1.6, f['bar'][1] + math.sin(a) * d * 0.6
            if IS.island_d(x, z, f['name']) < 0.8 and (x - ent[0]) ** 2 + (z - ent[1]) ** 2 > 140: palm(x, z, tall=True)

    # =========================================================== the corner exit of hall (2,0): sand bar, gondola, the sea hall
    CB = 'Isle_CornerBar'; cb = IS.ISLANDS[IS.INDEX[CB]][1]
    for (x, z) in sample_isle(CB, 0.1, 0.8, 3, minsep=5):
        palm(x, z, tall=True)
    for (x, z) in sample_isle(CB, 0.85, 1.02, 12, minsep=1.0):
        m = STARS[rng.integers(3)] if rng.random() < 0.5 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(CB, 0.0, 0.85, 14, minsep=0.8, near=(cb[0] - 3, cb[1] + 3, 2.0)):
        obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
    gondola([cb[0] + 9.0, 0, cb[1] + 7.0], 225)
    lantern([cb[0] + 2.0, gy(cb[0] + 2.0, cb[1] - 2.0), cb[1] - 2.0])
    sh_ent = (100.5, -100.5); sh_ry = 135.0
    obj('SeaHall', [sh_ent[0], 0.0, sh_ent[1]], sh_ry, col='mesh', name='The Sea Hall')
    obj('Ivy_SeaHall', [sh_ent[0], 0.0, sh_ent[1]], sh_ry, name='Ivy (Sea Hall)')
    shc = local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 0, 17.0)
    fountain(shc, 1.0, name='Fountain (Sea Hall)')
    for k, lz in enumerate((7.0, 12.0, 22.0, 27.0)):
        for sx in (-1, 1):
            p = local([sh_ent[0], 0, sh_ent[1]], sh_ry, 6.4 * sx, 0, lz)
            obj('Plinth_Square', p, sh_ry, col='box', name='Plinth')
            st = ['Statue_WingedFigure', 'Statue_Beast', 'Statue_SeatedSage', 'Statue_Hare'][(k + (sx > 0)) % 4]
            ST.append(dict(mesh=st, p=R3([p[0], 1.3, p[2]]), r=round((sh_ry - 90 * sx) % 360, 2), s=1.0, role='Statue of the Sea Hall'))
            plaque(local([sh_ent[0], 0, sh_ent[1]], sh_ry, 6.4 * sx - 0.52 * sx, 0.7, lz), sh_ry + (90 if sx > 0 else 270), 'Sea Hall statue')
    for lz in (7.6, 14.2, 20.8, 27.4):
        for sx in (-1, 1):
            SH.append(dict(p=local([sh_ent[0], 0, sh_ent[1]], sh_ry, 9.0 * sx, 17.5, lz), radius=1.2, height=15.0, kind='window', face=sh_ry - 90 * sx, dim=0.4))
    SH.append(dict(p=local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 31.4, 17.0), radius=1.7, height=31.4, kind='oculus'))
    PR.append(dict(p=local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 11, 17.0), size=[30, 30, 30], name='SeaHall'))
    RV.append(dict(p=local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 6, 17.0), minD=10, maxD=22, preset='Auditorium'))
    EM.append(dict(kind='dust', p=local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 9, 17.0), size=[16, 16, 28], rot=sh_ry))
    SO.append(dict(clip='Ocean_Near_Loop', p=R3([cb[0], 1, cb[1]]), vol=0.6, minD=5, maxD=50, spatial=1))

    # =========================================================== boats at the water stairs (floating, tide-following)
    for (n, d) in (((0, 1), 270), ((2, 1), 90)):
        g = vpos(n)
        gondola(local(g, d, 3.6, 0, 27.5), d)

    # =========================================================== the open marble tower + inner slide (hall 1,0 south)
    tw = [o_ for o_ in O if o_.get('name') == 'Marble Tower'][0]
    tp, tr_ = tw['p'], tw['r']
    obj('Tower3SlideWater', tp, tr_, noshadow=True, stat=False, name='Slide water')
    obj('Ivy_Tower3', tp, tr_, name='Ivy (Marble Tower)')
    ride = [local(tp, tr_, q[0], q[2], q[1]) for q in EX3['tower3_ride']]
    end = ride[-1]
    ex_p = (end[0] - 0.4, end[2] - 4.6)
    L['slide'] = dict(exit=R3([ex_p[0], gy(ex_p[0], ex_p[1]) + 0.05, ex_p[1]]), exitR=float((tr_ + 0) % 360),
                      path=[round(float(v), 3) for pt in ride for v in pt])
    EM.append(dict(kind='spray', p=R3([end[0], 0.3, end[2]]), size=[3, 0.2, 3]))
    SO.append(dict(clip='Cascade_Loop', p=R3([tp[0], 8.0, tp[2] - 6.5]), vol=0.35, minD=3, maxD=25, spatial=1))
    PR.append(dict(p=R3([tp[0], 13.0, tp[2] - 6.5]), size=[13, 27, 13], name='MarbleTower'))
    # broken columns, coral and fish round the base of the tower (redline 6)
    TS = 'Isle_TowerShoal'; tsc = IS.ISLANDS[IS.INDEX[TS]][1]
    for k in range(9):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(8.0, 12.0)
        x, z = tp[0] + math.cos(a) * d, tp[2] - 6.5 + math.sin(a) * d
        if abs(z - (tp[2] + 1.0)) < 3.5 and abs(x - tp[0]) < 12: continue        # keep the house side clear
        g = gy(x, z)
        if rng.random() < 0.5:
            obj('Fragment_Drum', [x, g + 0.32, z], rng.uniform(0, 360), e=[90 + rng.uniform(-8, 8), rng.uniform(0, 360), rng.uniform(-8, 8)], col='box', name='Fallen column drum')
        else:
            y = g - 0.15
            for j in range(rng.integers(1, 4)):
                obj('Fragment_Drum', [x + rng.normal() * 0.05, y, z + rng.normal() * 0.05], rng.uniform(0, 360), col='box', name='Broken column'); y += 0.9
        if rng.random() < 0.6:
            obj('Ivy_Column_1', [x, g - 0.2, z], rng.uniform(0, 360), s=0.6, name='Ivy (broken column)')
    for (x, z) in sample_isle(TS, 0.0, 0.8, 2, minsep=4):
        palm(x, z, tall=True)
    for (x, z) in sample_isle(TS, 0.85, 1.02, 10, minsep=1.0):
        m = STARS[rng.integers(3)] if rng.random() < 0.5 else SHELLS[rng.integers(3)]
        obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.3), stat=False, noshadow=True)
    for (x, z) in sample_isle(TS, 0.2, 0.8, 8, minsep=1.5):
        obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.1), stat=False)

    # =========================================================== water stairs: eroded steps, broken stairs, coral + fish in front
    for (n, d, nm) in (((0, 1), 'W', 'Sea Gate'), ((2, 1), 'E', 'East Water Stair')):
        g = vpos(n); ryg = {'E': 90, 'W': 270}[d]
        bp = local(g, ryg, 0.0, 0.0, 38.5)
        obj('BrokenStairs', [bp[0], gy(bp[0], bp[2]) + 0.05, bp[2]], ryg + rng.uniform(-12, 12), col='none', name=f'Broken stairs ({nm})')

    # =========================================================== coral reefs (+ the wreck) and fish
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
            room = (-0.9 - g)
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

    def fish(x, z, kind=None, depth=None):
        g = IS.ground(x, z)
        top = -1.15
        if g > top - 1.0: return
        y = (top + g) / 2 if depth is None else max(g + 0.7, min(top - 0.4, depth))
        obj(kind or FISH[rng.integers(3)], [x, y, z], rng.uniform(0, 360), s=rng.uniform(0.85, 1.2), noshadow=True, stat=False, tag='reef', name='Fish school')

    tcz = tp[2] - 6.5
    def clear_of_structures(x, z):
        if abs(x) < 74 and abs(z) < 74: return False                       # the House itself
        if abs(x - 60) < 8 and 70 < z < 112: return False                  # aqueduct + noria
        if abs(x) < 9 and tcz - 8.5 < z < -70: return False                # marble tower
        if abs(x) < 6 and tcz - 13 < z < tcz: return False                 # slide run-out
        for (gx_, gz_, rr) in ((-90, 0, 10), (90, 0, 10)):                 # water stairs (the steps themselves)
            if (x - gx_) ** 2 + (z - gz_) ** 2 < rr * rr: return False
        lx, lz = rot_y(x - sh_ent[0], z - sh_ent[1], -sh_ry)               # sea hall footprint
        if abs(lx) < 14 and -7 < lz < 37: return False
        return True
    patches = 0
    for k in range(500):
        if patches >= 50: break
        a = rng.uniform(0, 2 * math.pi); r_ = rng.uniform(80, 116)
        x, z = math.cos(a) * r_ * 1.05, math.sin(a) * r_
        if not clear_of_structures(x, z) or IS.ground(x, z) > -1.4: continue
        reef_patch(x, z, rng.integers(7, 14)); patches += 1
        if rng.random() < 0.35: fish(x + rng.normal() * 2, z + rng.normal() * 2)
    for k in range(12):          # lagoon between the House and the south beach
        x, z = rng.uniform(-50, 50), rng.uniform(-104, -78)
        if clear_of_structures(x, z) and IS.ground(x, z) < -1.4:
            reef_patch(x, z, rng.integers(6, 11))
            if k % 3 == 0: fish(x, z)
    for isl in IS.ISLANDS:
        name, (cx, cz), (rx, rz) = isl[0], isl[1], isl[2]
        if name.startswith('Isle_WingBar'): continue
        for k in range(9 if name not in ('Isle_Albatross', 'Isle_TowerShoal', 'Isle_CornerBar') else 5):
            a = rng.uniform(0, 2 * math.pi); f = rng.uniform(1.12, 1.45)
            lx, lz = math.cos(a) * rx * f, math.sin(a) * rz * f
            if len(isl) > 6 and isl[6]: lx, lz = rot_y(lx, lz, -isl[6])
            x, z = cx + lx, cz + lz
            if clear_of_structures(x, z) and IS.ground(x, z) < -1.4: reef_patch(x, z, rng.integers(6, 12), rad=3.5)
    # in front of both water stairs: coral among the broken stairs, and fish (redline 1)
    for (gxs, sgn) in ((90.0, 1), (-90.0, -1)):
        for k in range(7):
            x = gxs + sgn * rng.uniform(8.5, 15.0); z = rng.uniform(-11, 11)
            if IS.ground(x, z) < -1.3: reef_patch(x, z, rng.integers(6, 11), rad=3.0)
        for k in range(3):
            fish(gxs + sgn * rng.uniform(9, 14), rng.uniform(-8, 8), FISH[k])
    # round the tower base
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(9.5, 15)
        x, z = tp[0] + math.cos(a) * d, tcz + math.sin(a) * d
        if clear_of_structures(x, z) and IS.ground(x, z) < -1.3: reef_patch(x, z, rng.integers(6, 10), rad=3.0)
    for k in range(3):
        a = rng.uniform(0.5, 2.6) + (math.pi if k == 2 else 0); fish(tp[0] + math.cos(a) * 11, tcz + math.sin(a) * 11, FISH[k])
    wx, wz = -128.0, -118.0
    obj('Ship_Dutch', [wx, IS.ground(wx, wz) + 0.9, wz], e=[-4, 35, 24], col='none', name='Wreck of the Dutch ship', stat=True)
    for k in range(7):
        a = rng.uniform(0, 6.28); reef_patch(wx + math.cos(a) * 11, wz + math.sin(a) * 9, rng.integers(6, 11))
    fish(wx + 6, wz - 4, 'FishSchool_Tang'); fish(wx - 7, wz + 5, 'FishSchool_Chromis')
    fish(cb[0] + 14, cb[1] + 2, 'FishSchool_Reef'); fish(150 - 40, 40, 'FishSchool_Chromis'); fish(130, -30, 'FishSchool_Tang')

    # =========================================================== ivy, flowers and floating vines on the House
    by_name = {o_['name']: o_ for o_ in O if 'name' in o_}
    def follow(target, ivy, extra_r=0.0, local_off=None, floats=None, s=1.0):
        t = by_name.get(target)
        if t is None: return
        p = list(t['p'])
        if local_off is not None:
            lx, lz = rot_y(local_off[0], local_off[2], t['r']); p = [p[0] + lx, p[1] + local_off[1], p[2] + lz]
        obj(ivy, p, t['r'] + extra_r, name=f'Ivy ({target})', floats=floats, s=s)
    sides = info['sides']
    win_sides = [f'Vestibule_{n[0]}{n[1]}_{d}' for (n, d), k in sides.items() if k == 'window']
    blind_out = [f'Vestibule_{n[0]}{n[1]}_{d}' for (n, d), k in sides.items() if k == 'blind']
    for i, t in enumerate(win_sides):
        follow(t, f'Ivy_ExtWin_{i % 2}')
        follow(t, 'Ivy_WinIn')
        follow(t, f'Ivy_Float_{i % 2}', local_off=(0, 0, 0), floats=0.03)
    for i, t in enumerate(blind_out):
        if i % 3 != 2: follow(t, f'Ivy_ExtBlind_{i % 2}')
    win_halls = sorted({n for (n, d), k in sides.items() if k == 'window'})
    for n in win_halls:
        v = vpos(n); obj('Ivy_DomeTop', [v[0], 0, v[2]], rng.choice([0, 90, 180, 270]), name='Ivy and flowers (dome terrace)')
    for e_ in info['chosen']:
        nm = f"{'Nave' if e_ in info['naves'] else 'Arcade'}_{e_[0][0]}{e_[0][1]}_{e_[1][0]}{e_[1][1]}"
        t = by_name.get(nm)
        if t is None: continue
        if t['mesh'] == 'Nave': follow(nm, 'Ivy_NaveWin')
        elif t['mesh'] == 'Arcade_Win': follow(nm, 'Ivy_ArcadeWin3')
    for t in ['Vestibule_12_E', 'Vestibule_20_W', 'Vestibule_10_N']:
        follow(t, 'Ivy_VestInnerBlind')
    for t in ['Vestibule_01_W', 'Vestibule_11_W', 'Vestibule_21_E']:
        follow(t, 'Ivy_VestInnerOpen')
    for t in ['Vestibule_01_N', 'Vestibule_11_N', 'Vestibule_21_N', 'Vestibule_02_E']:
        follow(t, 'Ivy_HangLine_S', local_off=(0, 15.95, 9.8))
    for t in ['Vestibule_01_W', 'Vestibule_21_E']:     # curtains under the gate entablature (outside face)
        follow(t, 'Ivy_HangLine_L', extra_r=180, local_off=(0, 12.5, 13.15))
    for n in [(1, 1), (0, 0), (2, 2), (0, 2), (2, 0)]:
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
    L['wade'] = dict(y=-1.3, size=1500)
    L['handmenu'] = dict(audible='https://www.audible.com/pd/Piranesi-Audiobook/1526622416',
                         book='https://bookshop.org/p/books/piranesi-susanna-clarke/15861178')
    print(f'world3: boats {len(boats)}, crabs {len(crabs)}, seats {len(SE)}, objects {len(O)}')
