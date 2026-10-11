"""Everything outside the 7 x 7 House (called from layout7.py): the island and building beyond each exit, the far bar,
far hall and far wing beyond it on the same straight line (with mooring poles, painted in the road's colour, marking the wade).
Every place along one road is named for it (plan7.CHAINS) and grouped under it. Also the spawn camp, Ruin Isle's comforts and
the Lived-in Hall, the Marble Tower's slide, the Bird Tower with the albatross and the egg, the Corner Hall, reefs, wreck and
fish, ivy and flowers, creatures, and the Stormscape (dead-end tally, storm, Astra's Infinite Pole and its endless stair)."""
import os, json, math, numpy as np
import islands as IS
import plan7 as PL
import ruin as RU
from ivy import euler, read_pms

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'out', 'Data')
EX = json.load(open(os.path.join(DATA, 'Kit2Extra.json')))
EX3 = json.load(open(os.path.join(DATA, 'Kit3Extra.json')))
rng = np.random.default_rng(7171)
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
EXIT_ISLE = {c['exit']: c['isle'] for c in PL.CHAINS}

def wing_lengths():
    return {w: float(bounds(w)[1][0] - bounds(w)[0][0]) for w in ('Wing_1', 'Wing_2', 'Wing_3')}

def build(L, info):
    IS.add_wing_bars(wing_lengths())
    vpos, local, sides = info['vpos'], info['local'], info['sides']
    O = L['objects']; ST = L['statues']; LI = L['lights']; SH = L['shafts']; EM = L['emitters']; SO = L['sounds']; SE = L['seats']
    PR = L['probes']; RV = L['reverbs']
    boats = []; crabs = []; variants = [dict(name=k, base=v[0], tip=v[1], glow=v[2]) for k, v in VARIANTS.items()]
    H = PL.HALF

    GRP = [None]            # the road (chain) being built: every object it places is grouped under it in the hierarchy
    def road(exit_): GRP[0] = PL.CHAIN[exit_]['group'] if exit_ else None
    def obj(mesh, p, r=0.0, e=None, s=1.0, col='none', name=None, stat=True, mv=None, noshadow=False, spin=None, tag='', floats=None):
        d = dict(name=name or mesh, mesh=mesh, p=R3(p), r=round(float(r) % 360, 3), s=[float(s)] * 3 if np.isscalar(s) else [float(v) for v in s],
                 col=col, stat=stat, tag=tag)
        if GRP[0]: d['group'] = GRP[0]
        if e is not None: d['e'] = [float(v) for v in e]
        if mv: d['mv'] = mv
        if noshadow: d['noshadow'] = True
        if spin: d['spin'] = list(spin)
        if floats is not None: d['floats'] = True; d['fy'] = float(floats); d['stat'] = False
        O.append(d); return d

    def box(name, p, size, r=0.0, tag=''):
        O.append(dict(name=name, mesh='', p=R3(p), r=round(float(r) % 360, 3), s=list(size), col='box', stat=True, tag=tag))

    def gy(x, z): return IS.ground(x, z)

    def lantern(p, rng_=6.0, inten=1.4, mesh=True, r=0.0, color=(1.0, 0.66, 0.36)):
        if mesh: obj('Lantern_Wood', p, r, col='none', stat=False)
        LI.append(dict(kind='lantern', p=R3([p[0], p[1] + 0.32, p[2]]), range=rng_, intensity=inten, color=list(color)))

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
        for t in np.linspace(0, 160, 3201):
            x, z = x0 + dx * t, z0 + dz * t
            if IS.island_d(x, z, name) >= d_want: return (x, z)
        return (x0, z0)

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
        obj('DockPiles', [p[0], 0.0, p[2]], yaw, col='none', name=name + ' piles')
        obj('DockDeck', [p[0], 0.2 + FREE, p[2]], yaw, col='mesh', name=name, floats=FREE)

    def fountain(c, s=1.0, ry=0.0, name='Fountain'):
        obj('HallFountain', c, ry, s=s, col='mesh', name=name)
        obj('HallFountainPool', c, ry, s=s, noshadow=True, stat=False, name=name + ' (pool)')
        obj('HallFountainWater', c, ry, s=s, noshadow=True, stat=False, name=name + ' (water)')
        SO.append(dict(clip='Cascade_Loop', p=R3([c[0], c[1] + 1.5, c[2]]), vol=0.32 * s, minD=1.5, maxD=16 * s, spatial=1))

    def isle_hall(entrance, ry, s=1.0, name='Isle Hall', statues_=('Statue_Hare', 'Statue_SeatedSage', 'Statue_Queen', 'Statue_Head')):
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
        for k in range(2):
            lx = (-1) ** k * Wd * 0.28; lz = Ln * 0.5
            x, z = rot_y(lx, lz, ry)
            p = [entrance[0] + x, fy, entrance[1] + z]
            obj('Plinth_Square', p, ry, s=s, col='box', name='Plinth')
            st = statues_[rng.integers(len(statues_))]
            ST.append(dict(mesh=st, p=R3([p[0], fy + 1.3 * s, p[2]]), r=round((ry + (90 if k else 270)) % 360, 2), s=0.9 * s, role=f'Statue of {name}'))
        x, z = rot_y(0, Ln / 2, ry)
        SH.append(dict(p=R3([entrance[0] + x, fy + 11.0 * s, entrance[1] + z]), radius=0.8 * s, height=10.5 * s, kind='window', face=ry + 90, dim=0.5))
        PR.append(dict(p=R3([entrance[0] + x, fy + 6 * s, entrance[1] + z]), size=[Wd - 2, 14 * s, Ln - 2] if ry % 180 == 0 else [Ln - 2, 14 * s, Wd - 2],
                       name=name.replace(' ', '_'), res=64))
        RV.append(dict(p=R3([entrance[0] + x, fy + 4, entrance[1] + z]), minD=6 * s, maxD=12 * s, preset='StoneCorridor'))
        return fy

    def road_statue(p, yaw, fam, name, k=1.0):
        """the road's own statue on a plinth ringed in the road's colour: stands at every building along that road, so the
        isle building and the far hall can be told apart from the others at a glance (the colour key, no writing)."""
        p = [p[0], gy(p[0], p[2]) - 0.05, p[2]]                # stands on the sand (or the seabed, on a taller plinth)
        sc = PL.FAM_BASE[fam] * k; ext = PL.FAM_EXT[fam]
        pk = max((max(ext) * sc + 0.45) / 1.36, 0.85); hk = 1.0 if p[1] > -0.3 else 1.0 + (-p[1] + 0.15) / 1.3
        obj('Plinth_Square', p, yaw, s=(pk, hk, pk), col='box', name=f'Plinth ({fam}, {name})')
        obj('NeonRing', [p[0], p[1] + 0.02, p[2]], yaw, s=(1.36 * pk + 0.12, 2.0, 1.36 * pk + 0.12), col='none', mv=fam, noshadow=True,
            name=f'Neon ring ({fam})')
        d = dict(mesh=PL.FAM_MESH[fam], p=R3([p[0], p[1] + 1.3 * hk, p[2]]), r=round(yaw % 360, 2), s=round(sc, 3), role=f'{fam} - {name}')
        if GRP[0]: d['group'] = GRP[0]
        ST.append(d)

    def palm(x, z, tall, s=None):
        m = f'Palm_Tall_{rng.integers(3)}' if tall else f'Palm_{rng.integers(3)}'
        obj(m, [x, gy(x, z) - 0.05, z], rng.uniform(0, 360), s=s or rng.uniform(0.88, 1.12), col='none', stat=False)
        box('Palm Trunk', [x, gy(x, z) + 1.5, z], [0.5, 3.0, 0.5])
        if rng.random() < 0.6:
            a = rng.uniform(0, 6.28); d = rng.uniform(0.8, 2.2)
            cx2, cz2 = x + math.cos(a) * d, z + math.sin(a) * d
            obj('Coconuts', [cx2, gy(cx2, cz2) - 0.02, cz2], rng.uniform(0, 360), s=rng.uniform(0.9, 1.15), stat=False, noshadow=True)

    def dress_isle(name, avoid, palms=6, flowers=8, grass=6, plants=6, shells=16, crabs_=3, boulders=0, tall_every=2):
        for i, (x, z) in enumerate(sample_isle(name, 0.2, 0.82, palms, avoid=avoid, minsep=6)):
            palm(x, z, tall=(i % tall_every == 0))
        for (x, z) in sample_isle(name, 0.2, 0.85, flowers, avoid=avoid, minsep=3):
            obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.2), stat=False)
        for (cx_, cz_) in sample_isle(name, 0.1, 0.7, grass, avoid=avoid, minsep=7):
            for (x, z) in sample_isle(name, 0.0, 0.9, int(rng.integers(5, 9)), avoid=avoid, minsep=0.8, near=(cx_, cz_, 1.5)):
                obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.35), stat=False, noshadow=True)
        for (x, z) in sample_isle(name, 0.2, 0.7, plants, avoid=avoid, minsep=2):
            obj(PLANTS[rng.integers(len(PLANTS))], [x, gy(x, z) - 0.02, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.4), stat=False)
        for (x, z) in sample_isle(name, 0.88, 1.03, shells, avoid=avoid, minsep=1.0):
            m = STARS[rng.integers(3)] if rng.random() < 0.4 else SHELLS[rng.integers(3)]
            obj(m, [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.3), stat=False, noshadow=True)
        for (x, z) in sample_isle(name, 0.92, 1.12, boulders, avoid=avoid, minsep=12):
            obj('Boulder_01', [x, gy(x, z) - 0.25, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.6), col='mesh')
        for (x, z) in sample_isle(name, 0.8, 0.97, crabs_, avoid=avoid, minsep=4):
            crabs.append(dict(p=R3([x, gy(x, z), z]), r=round(rng.uniform(0, 360), 1)))

    def isle_c(name): return IS.ISLANDS[IS.INDEX[name]][1]

    # ---------------------------------------------------------------- comforts: the spawn camp, the pergolas, the lived-in hall
    def feast_pergola(c):
        g = max(gy(c[0] + dx, c[1] + dz) for dx in (-4.5, 0, 4.5) for dz in (-2.7, 2.7))
        obj('VinePergola', [c[0], g, c[1]], 0, col='mesh', name='Vine pergola (the feast)')
        obj('Ivy_Pergola', [c[0], g, c[1]], 0, name='Vine canopy (shade)')
        T = np.array([c[0], g, c[1]]); top = g + 0.82
        obj('GardenTable', T, 0, col='mesh', name='Marble table')
        for yaw in (0, 180):
            obj('ExedraBench', T, yaw, col='mesh', name='Marble bench')
            for a_ in (-28, 0, 28):
                aa = math.radians(a_); lx, lz = 2.0 * math.cos(aa), 2.0 * math.sin(aa)
                wx, wz = rot_y(lx, lz, yaw)
                SE.append(dict(p=R3([T[0] + wx, T[1] + 0.46, T[2] + wz]), r=yaw_to(-wx, -wz), kind='bench', text='Sit at the marble table',
                               exit=R3([T[0] + wx * 1.35, T[1] + 0.05, T[2] + wz * 1.35]), size=[0.6, 0.4, 0.6]))
        def on_table(m, lx, lz, yaw=None, s=1.0, dy=0.0):
            obj(m, [T[0] + lx, top + dy, T[2] + lz], rng.uniform(0, 360) if yaw is None else yaw, s=s, stat=False)
        on_table('Bowl_Wood', 0, 0, s=1.6)
        for k, m in enumerate(['Fruit_Apple', 'Fruit_Apple', 'Fruit_Lemon', 'Fruit_Lime', 'Fruit_Pomegranate', 'Fruit_Kiwi', 'Fruit_Apple', 'Fruit_Lemon']):
            a_ = k * 2.4; r_ = 0.09 if k < 6 else 0.03
            on_table(m, math.cos(a_) * r_, math.sin(a_) * r_, dy=0.03 + (0.07 if k >= 6 else 0))
        for k in range(5): on_table('Fruit_Lychee', 0.12 + rng.normal() * 0.03, -0.42 + rng.normal() * 0.03)
        on_table('Fruit_Bananas', 0.38, -0.2, yaw=30); on_table('Fruit_Pears', -0.3, 0.38)
        for k, a_ in enumerate((45, 135, 225, 315)):
            aa = math.radians(a_); on_table('Plate_Carved', math.cos(aa) * 0.6, math.sin(aa) * 0.6)
        on_table('Goblets_Brass', -0.5, -0.12, yaw=80); on_table('Jug', 0.12, 0.52, yaw=200); on_table('WineBottle', -0.62, 0.2)
        on_table('WineBottle', 0.66, -0.35); on_table('Vase_Antique', 0.55, 0.25); on_table('Candleholders_0', -0.22, -0.4, yaw=10)
        LI.append(dict(kind='lantern', p=R3([T[0] - 0.22, top + 0.95, T[2] - 0.4]), range=5.0, intensity=1.1, color=[1.0, 0.7, 0.4]))
        for k in range(10):
            a_ = rng.uniform(0, 2 * math.pi); x, z = c[0] + math.cos(a_) * rng.uniform(5.0, 7.0), c[1] + math.sin(a_) * rng.uniform(3.6, 5.0)
            obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.3), stat=False)
    def daybed_pergola(c):
        g = max(gy(c[0] + dx, c[1] + dz) for dx in (-4.5, 0, 4.5) for dz in (-2.7, 2.7))
        obj('VinePergola', [c[0], g, c[1]], 90, col='mesh', name='Vine pergola (daybeds)')
        obj('Ivy_Pergola', [c[0], g, c[1]], 90, name='Vine canopy (shade)')
        for k, lz in enumerate((-2.6, 0.0, 2.6)):
            p_ = [c[0] - 1.0, g, c[1] + lz]
            obj('MarbleBed', p_, 90, col='box', name='Marble daybed'); obj(f'BedLinen_{k % 3}', p_, 90, stat=False, name='Bedding')
            SE.append(dict(p=R3([p_[0] + 0.9, g + 0.75, p_[2]]), r=90, kind='bench', text='Lie down in the shade',
                           exit=R3([p_[0] - 0.6, g + 0.05, p_[2] + 0.9]), size=[0.9, 0.5, 1.6]))
        obj('Hammock_Vine', [c[0] + 2.6, g + 1.3, c[1]], 0, stat=False, name='Vine hammock')
        SE.append(dict(p=R3([c[0] + 2.6, g + 0.9, c[1]]), r=90, kind='hammock', text='Rest in the hammock', exit=R3([c[0] + 3.8, g + 0.05, c[1]]), size=[1.2, 0.4, 0.8]))
        obj('Basket_Wicker', [c[0] + 1.0, g, c[1] - 2.2], 30, s=1.4, stat=False)
        for k, m in enumerate(['Fruit_Apple', 'Fruit_Lemon', 'Fruit_Lime', 'Fruit_Pears']):
            obj(m, [c[0] + 1.0 + 0.08 * math.cos(k * 1.6), g + 0.05, c[1] - 2.2 + 0.08 * math.sin(k * 1.6)], rng.uniform(0, 360), stat=False)
        obj('Jug', [c[0] + 1.3, g, c[1] + 2.1], 0, stat=False); obj('Goblets_Brass', [c[0] + 1.1, g, c[1] + 2.4], 0, stat=False)
        for k in range(8):
            a_ = rng.uniform(0, 2 * math.pi); x, z = c[0] + math.cos(a_) * rng.uniform(3.6, 5.0), c[1] + math.sin(a_) * rng.uniform(5.0, 7.0)
            obj(f'Hibiscus_{["Red", "Pink", "Orange"][rng.integers(3)]}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.9, 1.3), stat=False)
    def living_hall(ent, ry, rc):
        """the hall behind the spawn as somewhere people stuck here would really live: bedrooms with marble beds and linen
        curtains, a marble bar with wine and fruit, a hearth, a washing basin, rugs, flowers and vines."""
        hs = [gy(ent[0] + x, ent[1] + z) for lx in (-10, 0, 10) for lz in (0, 12, 24, 34) for x, z in [rot_y(lx, lz, ry)]]
        fy = max(0.2, max(hs) + 0.05); O_ = [ent[0], fy, ent[1]]
        Hp = lambda lx, ly, lz: local(O_, ry, lx, ly, lz)
        obj('SeaHall', O_, ry, col='mesh', name='The Lived-in Hall (Ruin Isle)')
        obj('Ivy_SeaHall', O_, ry, name='Ivy (the Lived-in Hall)')
        for sx in (-1, 1): road_statue(Hp(7.6 * sx, 0.0, -2.6), ry + 180, 'Gorilla', 'the Lived-in Hall', k=0.8)
        SH.append(dict(p=R3(Hp(0, 31.4, 17.0)), radius=1.7, height=31.4, kind='oculus'))
        PR.append(dict(p=R3(Hp(0, 8, 17.0)), size=[22, 18, 34] if ry % 180 == 0 else [34, 18, 22], name='LivedInHall', res=128))
        RV.append(dict(p=R3(Hp(0, 4, 17.0)), minD=8, maxD=18, preset='Room'))
        # bedrooms on the left wall: marble beds, partitions of slabs, linen curtains, a side table, a candle, a rug
        for k, lz in enumerate((5.5, 13.0, 20.5, 28.0)):
            b = Hp(-8.35, 0, lz)
            obj('MarbleBed', b, ry + 270, col='box', name='Marble bed'); obj(f'BedLinen_{k % 3}', b, ry + 270, stat=False, name='Bedding')
            SE.append(dict(p=R3(Hp(-9.4, 0.72, lz)), r=(ry + 90) % 360, kind='bench', text='Lie down', exit=R3(Hp(-6.6, 0.05, lz)), size=[1.4, 0.5, 1.0]))
            st_ = Hp(-10.0, 0, lz + 1.15); obj('MarbleStool', st_, 0, col='box', name='Side table')
            obj('Candleholders_1', [st_[0], fy + 0.7, st_[2]], rng.uniform(0, 360), stat=False)
            LI.append(dict(kind='lantern', p=R3([st_[0], fy + 1.05, st_[2]]), range=4.0, intensity=0.75, color=[1.0, 0.62, 0.32]))
            obj(f'Rug_{k % 2}', Hp(-6.6, 0, lz), ry + 90, col='none', stat=False, name='Rug')
            if k < 3: obj('MarbleSlab', Hp(-9.2, 2.2, lz + 3.75), ry, s=(3.6, 2.2, 0.3), col='box', name='Partition (marble slabs)')
            obj('ScreenPosts', Hp(-6.1, 0, lz + 1.5), ry + 90, col='none', name='Curtain posts')
            obj('LinenScreen', Hp(-6.1, 0, lz + 1.5), ry + 90, col='none', stat=False, name='Linen curtain')
            obj(f'Hibiscus_{["Red", "Pink", "Orange"][k % 3]}', Hp(-10.5, 0, lz - 1.4), rng.uniform(0, 360), s=0.8, stat=False)
        # the bar on the right wall, its stools, its shelves of wine
        bc = Hp(7.6, 0, 10.0)
        obj('MarbleBar', bc, ry + 90, col='mesh', name='The marble bar')
        bt = EX3.get('bar', dict(top=1.12, shelf=[1.63, 2.33], shelf_y=1.22))
        for j, dz in enumerate((-1.9, -0.65, 0.65, 1.9)):
            sp = Hp(6.25, 0, 10.0 + dz); obj('MarbleStool', sp, 0, col='box', name='Bar stool')
            SE.append(dict(p=R3([sp[0], fy + 0.71, sp[2]]), r=(ry + 90) % 360, kind='bench', text='Sit at the bar', exit=R3(Hp(5.2, 0.05, 10.0 + dz)), size=[0.5, 0.4, 0.5]))
        for j in range(9):
            dz = -2.0 + j * 0.5; q = Hp(7.6, bt['top'], 10.0 + dz)
            m = ['WineBottle', 'Goblets_Brass', 'Jug', 'WineBottle', 'Bowl_Wood', 'Goblets_Brass', 'WineBottle', 'Candleholders_2', 'Plate_Carved'][j]
            obj(m, q, rng.uniform(0, 360), stat=False)
        for sh_ in bt['shelf']:
            for j in range(10):
                q = Hp(7.6 + bt['shelf_y'], sh_ + 0.01, 10.0 - 2.1 + j * 0.47)
                obj(['WineBottle', 'WineBottle', 'Jug', 'Vase_Antique', 'WineBottle'][j % 5], q, rng.uniform(0, 360), stat=False)
        bowl = Hp(7.6, bt['top'], 8.0)
        for k, m in enumerate(['Fruit_Apple', 'Fruit_Lemon', 'Fruit_Pomegranate', 'Fruit_Lime', 'Fruit_Pears']):
            obj(m, [bowl[0] + 0.07 * math.cos(k * 1.3), bowl[1] + 0.05, bowl[2] + 0.07 * math.sin(k * 1.3)], rng.uniform(0, 360), stat=False)
        for dz in (-1.5, 1.5):
            q = Hp(6.9, 2.9, 10.0 + dz); obj('Lantern', q, ry + 90, col='none', stat=False)
            LI.append(dict(kind='lantern', p=R3(q), range=6.0, intensity=1.2, color=[1.0, 0.66, 0.36]))
        obj('Rug_0', Hp(4.6, 0, 10.0), ry, col='none', stat=False, name='Rug')
        # the hearth and kitchen corner
        hc = Hp(6.8, 0, 24.5)
        obj('FireRing', hc, 0, col='box', name='Hearth'); LI.append(dict(kind='torch', p=R3([hc[0], fy + 0.55, hc[2]]), range=9.0, intensity=1.6, color=[1.0, 0.56, 0.24]))
        obj('CampLogs', hc, ry, col='mesh', name='Logs round the hearth')
        obj('Barrels', Hp(9.6, 0, 30.5), ry, col='box'); obj('Bucket_Wood', Hp(8.6, 0, 31.4), 0, stat=False)
        obj('Basket_Wicker', Hp(9.8, 0, 21.0), 0, s=1.4, stat=False)
        obj('MarbleSlab', Hp(10.2, 0.9, 27.0), ry, s=(1.6, 0.9, 3.0), col='box', name='Kitchen table')
        for j, m in enumerate(['Plate_Carved', 'Bowl_Wood', 'Jug', 'Fruit_Bananas', 'Plate_Carved']):
            obj(m, Hp(10.2, 0.92, 25.8 + j * 0.6), rng.uniform(0, 360), stat=False)
        # the washing basin at the back, flowers and plants along the walls, vines hanging inside
        obj('HallFountain', Hp(0, 0, 30.5), 0, s=0.6, col='mesh', name='Washing basin'); obj('HallFountainPool', Hp(0, 0, 30.5), 0, s=0.6, noshadow=True, stat=False)
        obj('HallFountainWater', Hp(0, 0, 30.5), 0, s=0.6, noshadow=True, stat=False)
        for k in range(14):
            sx = rng.choice([-1, 1]); q = Hp(sx * 10.6, 0, rng.uniform(2, 32))
            obj(PLANTS[rng.integers(len(PLANTS))] if k % 2 else f'Hibiscus_{["Red", "Pink", "Orange"][k % 3]}', q, rng.uniform(0, 360), s=rng.uniform(0.9, 1.3), stat=False)
        for lz in (8.0, 17.0, 26.0):
            obj('Ivy_HangLine_L', Hp(0, 9.5, lz), ry + 90, name='Vines hung across the hall')
        obj('Rug_1', Hp(0, 0, 17.0), ry, col='none', stat=False, name='Rug')
        obj('GardenTable', Hp(0, 0, 17.0), ry, col='mesh', name='Marble table (in the hall)')
        for yaw in (0, 180): obj('ExedraBench', Hp(0, 0, 17.0), ry + yaw, col='mesh', name='Marble bench')
        for k, m in enumerate(['Bowl_Wood', 'WineBottle', 'Goblets_Brass', 'Vase_Antique']):
            obj(m, Hp(-0.4 + k * 0.3, 0.82, 17.0 + (0.2 if k % 2 else -0.2)), rng.uniform(0, 360), s=1.4 if m == 'Bowl_Wood' else 1.0, stat=False)
    def spawn_camp():
        """the camp on the terrace of the East Water Stair, where you arrive, facing the way in."""
        sp = L['spawn']['p']
        fire = [sp[0] - 0.5, 0.0, sp[2] + 6.5]
        obj('FireRing', fire, rng.uniform(0, 360), col='box', name='Fire ring (the camp)')
        LI.append(dict(kind='torch', p=R3([fire[0], 0.55, fire[2]]), range=10.0, intensity=1.9, color=[1.0, 0.56, 0.24]))
        obj('CampLogs', fire, 0, col='mesh', name='Log seats round the fire')
        for k, lg in enumerate(EX3['camp']['logs']):
            lp = [fire[0] + lg[0], 0.0, fire[2] + lg[2]]; face = yaw_to(fire[0] - lp[0], fire[2] - lp[2])
            SE.append(dict(p=R3([lp[0], lg[1] + 0.02, lp[2]]), r=face, kind='bench', text='Sit by the fire',
                           exit=R3([lp[0] - (fire[0] - lp[0]) * 0.4, 0.05, lp[2] - (fire[2] - lp[2]) * 0.4]), size=[0.7, 0.4, 0.7]))
        for tm, p_, face in (('Tent_Cream', (sp[0] - 4.9, sp[2] + 8.3), 135.0), ('Tent_Teal', (sp[0] - 4.9, sp[2] - 8.2), 45.0)):
            obj(tm, [p_[0], -0.02, p_[1]], face, col='box', name=f'Tent ({tm[5:].lower()})')
        for (x, z) in ((sp[0] + 1.6, sp[2] + 4.0), (sp[0] - 2.2, sp[2] - 5.2)):
            lantern([x, 0.0, z], rng_=5.0, inten=1.0)
        obj('Basket_Wicker', [fire[0] + 2.8, 0.0, fire[2] + 1.6], 40, s=1.3, stat=False)
        for k, m in enumerate(['Fruit_Apple', 'Fruit_Lemon', 'Fruit_Pomegranate']):
            obj(m, [fire[0] + 2.8 + 0.07 * math.cos(k * 2), 0.06, fire[2] + 1.6 + 0.07 * math.sin(k * 2)], rng.uniform(0, 360), stat=False)
        obj('Jug', [fire[0] - 2.6, 0.0, fire[2] - 1.0], 0, stat=False)
    def gate_world(name):
        e = PL.EXITS[name]; o = vpos(e['cell'])
        v = {'W': (-1, 0), 'E': (1, 0), 'N': (0, 1), 'S': (0, -1), 'SE': (1, -1), 'NW': (-1, 1)}[e['side']]
        return o, v

    # =========================================================== sand: every island and wing bar
    WB = {f['name']: f['exit'] for f in IS.wing_frames(wing_lengths())}
    for isl in IS.ISLANDS:
        name, (cx, cz) = isl[0], isl[1]
        if name in PL.SAND_NAMES: label, ex_ = PL.SAND_NAMES[name]
        elif name in WB: ex_ = WB[name]; label = PL.CHAIN[ex_]['bar_name']
        else: label, ex_ = name, None
        road(ex_)
        obj(name, [cx, 0, cz], 0, col='mesh', name=f'Sand: {label}', tag='terrain')
    road(None)
    exit_docks = {}

    # ---------------- Tower Door (Boy with Cymbals road): the Marble Tower and its slide on Tower Shoal, then Beach Isle and its hall
    road('Tower Door')
    tw = [o_ for o_ in O if o_.get('name') == 'Marble Tower'][0]
    tp, tr_ = tw['p'], tw['r']
    obj('Tower3SlideWater', tp, tr_, noshadow=True, stat=False, name='Slide water')
    obj('Ivy_Tower3', tp, tr_, name='Ivy (Marble Tower)')
    ride = [local(tp, tr_, q[0], q[2], q[1]) for q in EX3['tower3_ride']]
    end = ride[-1]
    ex_p = (end[0] - 0.4, end[2] - 4.6)
    L['slide'] = dict(exit=R3([ex_p[0], gy(ex_p[0], ex_p[1]) + 0.05, ex_p[1]]), exitR=float(tr_ % 360), path=[round(float(v), 3) for pt in ride for v in pt])
    EM.append(dict(kind='spray', p=R3([end[0], 0.3, end[2]]), size=[3, 0.2, 3]))
    SO.append(dict(clip='Cascade_Loop', p=R3([tp[0], 8.0, tp[2] - 6.5]), vol=0.35, minD=3, maxD=25, spatial=1))
    PR.append(dict(p=R3([tp[0], 13.0, tp[2] - 6.5]), size=[13, 27, 13], name='MarbleTower', res=128))
    tcz = tp[2] - 6.5
    for k in range(9):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(8.0, 12.0)
        x, z = tp[0] + math.cos(a) * d, tcz + math.sin(a) * d
        if z > tcz - 1.0 or abs(x - end[0]) < 4: continue            # keep the house side and the slide run-out clear
        g = gy(x, z)
        if rng.random() < 0.5:
            obj('Fragment_Drum', [x, g + 0.32, z], rng.uniform(0, 360), e=[90 + rng.uniform(-8, 8), rng.uniform(0, 360), rng.uniform(-8, 8)], col='box', name='Fallen column drum')
        else:
            y = g - 0.15
            for j in range(int(rng.integers(1, 4))):
                obj('Fragment_Drum', [x + rng.normal() * 0.05, y, z + rng.normal() * 0.05], rng.uniform(0, 360), col='box', name='Broken column'); y += 0.9
        if rng.random() < 0.6:
            obj('Ivy_Column_1', [x, g - 0.2, z], rng.uniform(0, 360), s=0.6, name='Ivy (broken column)')
    TS = 'Isle_TowerShoal'
    dress_isle(TS, avoid=[(end[0], end[2], 4.0), (ex_p[0], ex_p[1], 2.5)], palms=2, flowers=6, grass=2, plants=0, shells=10, crabs_=1, tall_every=1)
    SB = 'Isle_SouthBeach'; sbc = isle_c(SB)
    hall_sb = PL.CHAIN['Tower Door']['bpos']
    dk = shore_point(SB, sbc[0] + 30.0, sbc[1], 0, 1, 0.9)
    hm = (sbc[0] + 10.0, sbc[1] + 6.0)
    sb_avoid = [(hm[0], hm[1], 3.0), (dk[0], dk[1] + 4, 4.0), (hall_sb[0], hall_sb[1] - 11, 15.0)]
    obj('Hammock_Vine', [hm[0], gy(hm[0], hm[1]) + 1.3, hm[1]], 90, stat=False, name='Vine hammock')
    SE.append(dict(p=R3([hm[0], gy(hm[0], hm[1]) + 0.9, hm[1]]), r=0, kind='hammock', text='Rest in the hammock',
                   exit=R3([hm[0], gy(hm[0], hm[1] - 1.6) + 0.05, hm[1] - 1.6]), size=[1.2, 0.4, 0.8]))
    sb_fy = isle_hall(hall_sb, 180.0, name='Beach Isle Hall')
    road_statue(local([hall_sb[0], sb_fy, hall_sb[1]], 180.0, -5.6, 0, -3.2), 0.0, 'Boy with Cymbals', 'Beach Isle Hall')
    dress_isle(SB, avoid=sb_avoid, palms=24, flowers=16, grass=9, plants=12, shells=34, crabs_=10, boulders=5, tall_every=3)
    dock([dk[0], 0, dk[1] - 1.0], 0, 'Dock (Beach Isle)')
    gondola([dk[0] + 2.8, 0, dk[1] + 8.0], 0); exit_docks['Tower Door'] = dk
    SO.append(dict(clip='Ocean_Near_Loop', p=R3([sbc[0], 1, sbc[1] + 24]), vol=0.8, minD=8, maxD=90, spatial=1))
    SO.append(dict(clip='Wind_Loop', p=R3([sbc[0], 6, sbc[1]]), vol=0.35, minD=10, maxD=70, spatial=1))
    EM.append(dict(kind='season', p=R3([sbc[0], 16, sbc[1]]), size=[110, 1, 44], fall=15))

    # ---------------- East Water Stair (Gorilla road): the Causeway to Ruin Isle (arch ruins, drapes, hammocks, the table, paths,
    # shards, the pergolas) and the Lived-in Hall
    road('East Water Stair')
    RI = 'Isle_Ruin'; rc = isle_c(RI)
    g0 = gy(rc[0], rc[1]); RO = np.array([rc[0], g0, rc[1]])
    for (x, z) in RU.COLUMNS:
        obj('Column', RO + [x, RU.BASE_Y, z], 0, col='capsule', name='Ruin Column')
    obj('ArchRuin', RO, 0, col='mesh', name='Arch ruins over the colonnade')
    obj('Ivy_Ruin3', RO, 0, name='Ivy and vine drapes (Ruin)')
    for (x, z) in RU.STUMPS:
        y = RU.BASE_Y + 0.1
        for k in range(int(rng.integers(2, 4))):
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
    obj('Fragment_Drum', T + [0.0, -0.3, -2.45], 0, col='box', name='Chess Drum')
    obj('Chess_Set', T + [0.0, 0.64, -2.45], 12, s=1.2, stat=False)
    cxp, czp = T[0] + 1.25, T[2] - 2.9
    obj('Treasure_Chest', [cxp, gy(cxp, czp) - 0.02, czp], 300, col='box', name='Treasure Chest (beside the chess drum)')
    obj('Plinth_Round', RO + [-12.6, gy(rc[0] - 12.6, rc[1] - 1.0) - g0 - 0.1, -1.0], 0, col='box')
    obj('Whale_Bronze', RO + [-12.6, gy(rc[0] - 12.6, rc[1] - 1.0) - g0 + 1.15, -1.0], 120, s=1.2, col='none')
    obj('Lion_Head', RO + [9.2, RU.BASE_Y + 0.1 + 0.92 * 2 - 0.02, -3.5], 200, s=1.5, col='none', name='Lion head on the broken column')
    for (x, z) in [(-6.9, -5.0), (6.9, 5.0), (2.3, 5.2), (-2.3, -5.2)]:
        lantern(RO + [x, gy(rc[0] + x, rc[1] + z) - g0, z], rng_=5.0, inten=1.1, r=rng.uniform(0, 360))
    obj('RuinPaths', [0, 0, 0], 0, col='mesh', name='Eroded marble paths', noshadow=True, tag='terrain')
    for k in range(48):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(3.2, 17.0)
        x, z = rc[0] + math.cos(a) * d * 1.2, rc[1] + math.sin(a) * d * 0.8
        if abs(x - T[0]) < 2.5 and abs(z - T[2]) < 3.4: continue
        obj(f'Shard_{rng.integers(4)}', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.7, 1.4), stat=False, noshadow=True, name='Marble shard')
    for (x, z) in RU.COLUMNS + RU.STUMPS:
        for k in range(int(rng.integers(1, 3))):
            a = rng.uniform(0, 6.28); r_ = rng.uniform(1.0, 1.6)
            px, pz = x + math.cos(a) * r_, z + math.sin(a) * r_
            if abs(pz) < 3.2 and abs(px) < 3.0: continue
            obj(PLANTS[rng.integers(len(PLANTS))], RO + [px, gy(rc[0] + px, rc[1] + pz) - g0 - 0.02, pz], rng.uniform(0, 360), s=rng.uniform(1.0, 1.5), stat=False)
    hall_ri = PL.CHAIN['East Water Stair']['bpos']
    living_hall(hall_ri, 90.0, rc)
    pA = (rc[0] - 22.0, rc[1] + 14.0); pB = (rc[0] - 20.0, rc[1] - 15.0)
    feast_pergola(pA); daybed_pergola(pB)
    ravoid = [(rc[0], rc[1], 14.0), (hall_ri[0] + 17, hall_ri[1], 19.0), (pA[0], pA[1], 7.0), (pB[0], pB[1], 7.0)]
    dress_isle(RI, avoid=ravoid, palms=14, flowers=46, grass=0, plants=22, shells=16, crabs_=4)
    for (cx_, cz_) in sample_isle(RI, 0.08, 0.5, 14, avoid=[(T[0], T[2], 3.2), (hall_ri[0], hall_ri[1] + 11, 12.0)], minsep=4.5):
        for (x, z) in sample_isle(RI, 0.0, 0.62, int(rng.integers(6, 11)), avoid=[(T[0], T[2], 2.6)], minsep=0.55, near=(cx_, cz_, 1.3)):
            obj('BeachGrass', [x, gy(x, z) - 0.03, z], rng.uniform(0, 360), s=rng.uniform(0.85, 1.35), stat=False, noshadow=True)
    for (x, z) in sample_isle(RI, 0.86, 1.02, 16, minsep=1.2, near=(rc[0] - 33, rc[1] - 4, 7.0)):
        obj(STARS[rng.integers(3)], [x, gy(x, z) + 0.005, z], rng.uniform(0, 360), s=rng.uniform(1.0, 1.5), stat=False, noshadow=True, name='Starfish')
    rd = shore_point(RI, rc[0], rc[1] + 2.0, -1, 0, 0.9)
    dock([rd[0] + 1.0, 0, rc[1] + 2.0], 270, 'Dock (Ruin Isle)')
    gondola([rd[0] - 8.0, 0, rc[1] + 4.8], 270); exit_docks['East Water Stair'] = rd
    lantern([rd[0] + 2.5, gy(rd[0] + 2.5, rc[1]), rc[1]])
    SO.append(dict(clip='Ocean_Near_Loop', p=R3([rd[0], 1, rc[1] + 2]), vol=0.7, minD=6, maxD=60, spatial=1))
    SO.append(dict(clip='Wind_Loop', p=R3(RO + [0, 8, 0]), vol=0.3, minD=6, maxD=50, spatial=1))
    EM.append(dict(kind='season', p=R3(RO + [0, 14, 0]), size=[30, 1, 20], fall=14))
    EM.append(dict(kind='dust', p=R3(RO + [0, 5, 0]), size=[22, 9, 10]))

    spawn_camp()
    road(None)

    # ---------------- Aqueduct Arch (Angel road): Pump Isle straight out from the arch; the Pump House at its east end works the
    # noria and the aqueduct that feed the cascade and the roof channels
    road('Aqueduct Arch')
    AQ_Y = -0.5
    cas = vpos(PL.CASCADE[0]); ax, az0 = cas[0], cas[2] + 12.0
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
    PI = 'Isle_Pump'; pc = isle_c(PI)
    (agx, _), _v = IS.gate_line('Aqueduct Arch')
    hall_pi = PL.CHAIN['Aqueduct Arch']['bpos']
    pi_fy = isle_hall(hall_pi, 90.0, name='The Pump House')
    road_statue(local([hall_pi[0], pi_fy, hall_pi[1]], 90.0, 5.6, 0, -3.2), 270.0, 'Angel', 'the Pump House')
    bx0, bz0 = pc[0] + 38.0, pc[1] - 5.0
    obj('Barrels', [bx0, gy(bx0, bz0) - 0.04, bz0], 30, col='box')
    for k in range(2):
        bx2, bz2 = bx0 - 1.5, bz0 - 1.6 + k * 0.6
        obj('Bucket_Wood', [bx2, gy(bx2, bz2), bz2], rng.uniform(0, 360), stat=False)
    lantern([bx0 + 0.3, gy(bx0 + 0.3, bz0 - 2.4), bz0 - 2.4])
    pd = shore_point(PI, agx + 9.0, pc[1], 0, -1, 0.9)                # the south shore, beside the line from the arch
    pavoid = [(hall_pi[0] + 11, hall_pi[1], 12.0), (nxp, nz, 9.0), (bx0, bz0, 3.0), (agx, pc[1], 3.5), (pd[0], pd[1] + 2, 4.0)]
    dress_isle(PI, avoid=pavoid, palms=9, flowers=8, grass=7, plants=5, shells=16, crabs_=3, tall_every=2)
    dock([pd[0], 0, pd[1] + 1.0], 180, 'Dock (Pump Isle)')
    gondola([pd[0] + 2.8, 0, pd[1] - 8.0], 180); exit_docks['Aqueduct Arch'] = (agx, pd[1])
    road(None)

    # ---------------- Sea Gate (Elephant road): West Isle and West Isle Hall (the wreck lies off to the south)
    road('Sea Gate')
    WI = 'Isle_West'; wc = isle_c(WI)
    hall_w = PL.CHAIN['Sea Gate']['bpos']
    w_fy = isle_hall(hall_w, 270.0, name='West Isle Hall', statues_=('Statue_Head', 'Statue_SeatedSage', 'Statue_Queen'))
    road_statue(local([hall_w[0], w_fy, hall_w[1]], 270.0, -5.6, 0, -3.2), 90.0, 'Elephant', 'West Isle Hall', k=0.8)
    dress_isle(WI, avoid=[(hall_w[0] - 11, hall_w[1], 13.0)], palms=8, flowers=6, grass=6, plants=4, shells=18, crabs_=4, boulders=3)
    wd = shore_point(WI, wc[0], wc[1] - 6.0, 1, 0, 0.9)
    dock([wd[0] - 1.0, 0, wc[1] - 6.0], 90, 'Dock (West Isle)')
    gondola([wd[0] + 8.0, 0, wc[1] - 9.0], 90); exit_docks['Sea Gate'] = wd
    lantern([wd[0] - 2.5, gy(wd[0] - 2.5, wc[1] - 4.0), wc[1] - 4.0])
    SO.append(dict(clip='Wind_Loop', p=R3([wc[0], 6, wc[1]]), vol=0.3, minD=6, maxD=50, spatial=1))
    road(None)

    # ---------------- Bird Stair (Albatross road): the Bird Tower (a stone-jump climb) on Albatross Isle, the marble nest, the
    # albatross and the egg
    road('Bird Stair')
    AI = 'Isle_Albatross'; ac = isle_c(AI)
    bt = EX3['bird_tower']; bry = PL.CHAIN['Bird Stair']['bry']          # door (local -z) toward the House
    btg = max(gy(ac[0] + dx, ac[1] + dz) for dx in (-6, 0, 6) for dz in (-6, 0, 6))
    obj('BirdTower', [ac[0], btg, ac[1]], bry, col='mesh', name='The Bird Tower (Albatross Isle)')
    nest = [ac[0], btg + bt['nest'][1], ac[1]]
    obj('GiantEgg', nest, rng.uniform(0, 360), col='box', name='The giant egg (in the marble nest)')
    ax_, az_ = rot_y(1.25, 0.6, bry)
    obj('Albatross', [nest[0] + ax_, nest[1] + 0.05, nest[2] + az_], bry + 200, s=1.2, col='none', name='The albatross')
    EM.append(dict(kind='glint', p=R3([nest[0], nest[1] + 1.0, nest[2]]), size=[1.4, 1.8, 1.4]))
    EM.append(dict(kind='sparkle', p=R3([nest[0], nest[1] + 1.0, nest[2]]), size=[2.4, 2.2, 2.4]))
    LI.append(dict(kind='spot', p=R3([nest[0] + 2.0, nest[1] + 7.0, nest[2] - 2.0]), dir=R3(np.array([-2.0, -6.2, 2.0]) / np.linalg.norm([-2.0, -6.2, 2.0])),
                   angle=16, range=12, intensity=3.2, color=[1.0, 0.95, 0.85], name='Light on the egg'))
    SO.append(dict(clip='Wind_Loop', p=R3([ac[0], 20, ac[1]]), vol=0.45, minD=5, maxD=50, spatial=1))
    dress_isle(AI, avoid=[(ac[0], ac[1], 9.5)], palms=2, flowers=3, grass=4, plants=0, shells=10, crabs_=3, boulders=3, tall_every=1)
    exit_docks['Bird Stair'] = shore_point(AI, ac[0], ac[1], -0.7071, 0.7071, 0.9)
    bdx, bdz = rot_y(0, -1.0, bry); bsp = [ac[0] + bdx * 9.0 - bdz * 3.5, 0, ac[1] + bdz * 9.0 + bdx * 3.5]
    road_statue(bsp, yaw_to(-ac[0], -ac[1]), 'Albatross', 'the Bird Tower')
    road(None)

    # ---------------- Corner Passage (Minotaur road): Corner Isle and the Corner Hall standing in the sea beside it
    road('Corner Passage')
    CB = 'Isle_CornerBar'; cb = isle_c(CB)
    dress_isle(CB, avoid=[(cb[0] + 3, cb[1] - 3, 2.5)], palms=3, flowers=0, grass=2, plants=0, shells=12, crabs_=1, tall_every=1)
    gondola([cb[0] + 9.0, 0, cb[1] + 7.0], 225)
    lantern([cb[0] + 2.0, gy(cb[0] + 2.0, cb[1] - 2.0), cb[1] - 2.0])
    sh_ent = PL.CORNER_HALL['entrance']; sh_ry = PL.CORNER_HALL['ry']
    obj('SeaHall', [sh_ent[0], 0.0, sh_ent[1]], sh_ry, col='mesh', name='The Corner Hall')
    obj('Ivy_SeaHall', [sh_ent[0], 0.0, sh_ent[1]], sh_ry, name='Ivy (the Corner Hall)')
    shc = local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 0, 17.0)
    fountain(shc, 1.0, name='Fountain (the Corner Hall)')
    for sx in (-1, 1):
        road_statue(local([sh_ent[0], 0, sh_ent[1]], sh_ry, 7.6 * sx, 0.0, -2.6), sh_ry + 180, 'Minotaur', 'the Corner Hall', k=0.85)
    for k, lz in enumerate((7.0, 12.0, 22.0, 27.0)):
        for sx in (-1, 1):
            p = local([sh_ent[0], 0, sh_ent[1]], sh_ry, 6.4 * sx, 0, lz)
            obj('Plinth_Square', p, sh_ry, col='box', name='Plinth')
            st = ['Statue_Dragon', 'Statue_Head', 'Statue_SeatedSage', 'Statue_Dragon'][(k + (sx > 0)) % 4]
            ST.append(dict(mesh=st, p=R3([p[0], 1.3, p[2]]), r=round((sh_ry - 90 * sx) % 360, 2), s=0.55 if st == 'Statue_Dragon' else 1.0, role='Statue of the Corner Hall'))
    for lz in (10.0, 24.0):
        for sx in (-1, 1):
            SH.append(dict(p=R3(local([sh_ent[0], 0, sh_ent[1]], sh_ry, 9.0 * sx, 17.5, lz)), radius=1.2, height=15.0, kind='window', face=sh_ry - 90 * sx, dim=0.4))
    SH.append(dict(p=R3(local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 31.4, 17.0)), radius=1.7, height=31.4, kind='oculus'))
    PR.append(dict(p=R3(local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 11, 17.0)), size=[30, 30, 30], name='CornerHall', res=128))
    RV.append(dict(p=R3(local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 6, 17.0)), minD=10, maxD=22, preset='Auditorium'))
    EM.append(dict(kind='dust', p=R3(local([sh_ent[0], 0, sh_ent[1]], sh_ry, 0, 9, 17.0)), size=[16, 16, 28], rot=sh_ry))
    SO.append(dict(clip='Ocean_Near_Loop', p=R3([cb[0], 1, cb[1]]), vol=0.6, minD=5, maxD=50, spatial=1))
    exit_docks['Corner Passage'] = (sh_ent[0] + 20, sh_ent[1] - 20)
    road(None)

    # =========================================================== the far wings: one beyond each exit, on the same line, each
    # fronted by a themed far hall (a Sea Hall shell) built from the book (rudimentary but walkable and working)
    floods = []; offerings = []; quests = []
    QI = {q['exit']: k for k, q in enumerate(PL.QUESTS)}
    def prize(exit_, mesh, p, yaw, s=1.0, extra=None):
        k = QI[exit_]; q = PL.QUESTS[k]
        o_ = obj(mesh, p, yaw, s=s, col='none', stat=False, noshadow=True, name=f"Quest prize {k + 1}: {q['prize']}")
        EM.append(dict(kind='glint', p=R3([p[0], p[1] + 0.35, p[2]]), size=[0.7, 0.6, 0.7]))
        LI.append(dict(kind='lantern', p=R3([p[0], p[1] + 0.9, p[2]]), range=3.5, intensity=0.9, color=[1.0, 0.85, 0.55]))
        d = dict(index=k, name=o_['name'], p=R3([p[0], p[1] + 0.3, p[2]]), size=[1.2, 1.2, 1.2], text=f"Take {q['prize'][0].lower() + q['prize'][1:]}")
        if extra: d.update(extra)
        quests.append(d)
        return o_
    def far_hall(f):
        exit_ = f['exit']; theme = PL.WING_IDEAS[exit_]; ent = f['hall']; ry = f['hall_ry']
        drowned = exit_ == 'Sea Gate'
        if drowned: fy = -1.15
        else:
            hs = [gy(ent[0] + x, ent[1] + z) for lx in (-10, 0, 10) for lz in (0, 12, 24, 34) for x, z in [rot_y(lx, lz, ry)]]
            fy = max(0.15, max(hs) + 0.05)
        O_ = [ent[0], fy, ent[1]]
        Hp = lambda lx, ly, lz: local(O_, ry, lx, ly, lz)
        ch = PL.CHAIN[exit_]
        obj('SeaHall', O_, ry, col='mesh', name=f"{theme} (far hall, {ch['road']})")
        obj('Ivy_SeaHall', O_, ry, name=f'Ivy ({theme})')
        for sx in (-1, 1):                                  # the road's statue again at the far door, as at the gate
            road_statue(Hp(7.6 * sx, 0.0, -2.6), ry + 180, ch['family'], theme, k=0.85)
        SH.append(dict(p=R3(Hp(0, 31.4, 17.0)), radius=1.7, height=31.4, kind='oculus'))
        for lz in (10.0, 24.0):
            for sx in (-1, 1):
                SH.append(dict(p=R3(Hp(9.0 * sx, 17.5, lz)), radius=1.2, height=15.0, kind='window', face=ry - 90 * sx, dim=0.4))
        PR.append(dict(p=R3(Hp(0, 11, 17.0)), size=[30, 30, 30] if ry % 180 == 0 else [30, 30, 30], name=theme.replace(' ', '_'), res=128))
        RV.append(dict(p=R3(Hp(0, 6, 17.0)), minD=10, maxD=22, preset='Auditorium'))
        for sx in (-1, 1):
            lantern(Hp(sx * 4.2, 0.02, 1.2), rng_=6.0, inten=1.1)
        face_in = lambda sx: ry - 90 * sx               # a figure on the side sx faces the middle of the hall
        back = (ry + 180) % 360                            # faces the entrance
        if exit_ == 'Sea Gate':                             # ------------- the Drowned Halls
            for sx in (-1, 1):
                ST.append(dict(mesh='Statue_WingedFigure', p=R3(Hp(7.4 * sx, 0, 9.0)), r=round(face_in(sx) % 360, 2), s=3.0, role='Colossus of the Drowned Halls'))
                ST.append(dict(mesh='Statue_SeatedSage', p=R3(Hp(7.4 * sx, 0, 24.0)), r=round(face_in(sx) % 360, 2), s=3.4, role='Seated giant of the Drowned Halls'))
            ST.append(dict(mesh='Statue_Head', p=R3(Hp(0, -1.4, 30.0)), r=round(back, 2), s=8.0, role='A drowned colossal head'))
            for (x, z) in [(rng.uniform(-9.5, 9.5), rng.uniform(2.5, 31)) for _ in range(70)]:
                if abs(abs(x) - 7.4) < 2.2 and (abs(z - 9) < 2.4 or abs(z - 24) < 2.4): continue
                if abs(x) < 3.2 and z > 27: continue
                q = Hp(x, 0, z)
                lily_n = globals().setdefault('_lily_n', [0]); lily_n[0] += 1
                lm = ('WaterLily_Pads', 'WaterLily', 'WaterLily_Pads', 'WaterLily_Pink', 'WaterLily_Pads')[lily_n[0] % 5]
                obj(lm, [q[0], 0.0, q[2]], rng.uniform(0, 360), s=rng.uniform(0.8, 1.7), stat=False, noshadow=True, name='Water lily', floats=0.02)
            for k, fz in enumerate((12.0, 20.0)):
                q = Hp(rng.uniform(-3, 3), 0, fz); obj(FISH[k], [q[0], -0.7, q[2]], rng.uniform(0, 360), noshadow=True, stat=False, tag='reef', name='Fish school')
            SO.append(dict(clip='Ocean_Near_Loop', p=R3(Hp(0, 1, 17)), vol=0.45, minD=4, maxD=30, spatial=1))
            EM.append(dict(kind='dust', p=R3(Hp(0, 6, 17)), size=[16, 10, 28], rot=ry))
            obj('MarbleSlab', Hp(0, 1.3, 32.2), ry, s=(4.0, 2.5, 2.6), col='box', name='Dry step above the water')
            lp = Hp(0, 1.3, 32.4); obj('Lectern', lp, back, col='box', name='Lectern')
            pg = local(lp, back, 0, 1.08, 0.0)
            prize('Sea Gate', 'JournalPage', pg, back)
        elif exit_ == 'East Water Stair':                   # ------------- the Derelict Halls
            obj('DerelictLedge', Hp(0, 0, 24.5), ry, col='mesh', name='Broken upper floor (Derelict Halls)')
            top = EX3.get('derelict_ledge_top', 7.7)
            for k in range(16):                             # a rubble slope up to the broken floor
                t = k / 15.0
                lx = -7.6 + 4.4 * t + 0.4 * math.sin(k * 1.7); lz = 8.0 + 18.0 * t
                h = 0.48 * (k + 1)
                obj('MarbleSlab', Hp(lx, h, lz), ry + rng.uniform(-14, 14), s=(1.9, h, 1.6), col='box', name='Rubble (climb)')
            for k, (m_, lx, lz, e0) in enumerate((('Statue_Horse', 5.5, 10.0, 90), ('Statue_WingedFigure', 4.5, 19.0, 85), ('Statue_SeatedSage', -2.0, 6.0, 70))):
                q = Hp(lx, 0.45, lz); obj(m_, q, e=[e0, (ry + 30 + 70 * k) % 360, 0], s=1.2, col='box', name='Toppled statue')
            for k in range(8):
                q = Hp(rng.uniform(-8, 8), 0, rng.uniform(3, 31))
                obj('Fragment_Drum', [q[0], fy + 0.42, q[2]], rng.uniform(0, 360), e=[90, rng.uniform(0, 360), 0], col='box', name='Fallen drum')
            for k in range(2):
                q = Hp(rng.uniform(3, 8), 0, 5 + 12 * k); obj('BrokenStairs', [q[0], fy, q[2]], rng.uniform(0, 360), col='none', name='Broken stairs (Derelict Halls)')
            for k in range(4):
                SH.append(dict(p=R3(Hp(rng.uniform(-7, 7), 21.0, rng.uniform(6, 30))), radius=rng.uniform(0.8, 1.6), height=21.0, kind='window', face=ry + rng.uniform(-40, 40), dim=0.6))
            prize('East Water Stair', 'GoldShard', Hp(2.2, top + 0.02, 26.4), rng.uniform(0, 360))
            seat = Hp(0, top + 0.02, 25.4)
            SE.append(dict(p=R3(seat), r=back, kind='bench', text='Sit on the broken floor and look back toward the House',
                           exit=R3(Hp(0, top + 0.05, 27.0)), size=[0.8, 0.5, 0.8]))
            EM.append(dict(kind='dust', p=R3(Hp(0, 8, 17)), size=[18, 14, 30], rot=ry))
        elif exit_ == 'Tower Door':                         # ------------- the Ninth Vestibule
            obj('GrandStair', Hp(0, 0, 14.0), ry, col='mesh', name='The great staircase (centre)')
            obj('MarbleSlab', Hp(0, 6.0, 29.0), ry, s=(21.0, 1.0, 10.0), col='box', name='Landing of the three staircases')
            for sx in (-1, 1):
                obj('GrandStair', Hp(8.0 * sx, 0, 4.0), ry, s=(0.95, 1, 1), col='mesh', name='A great staircase (side)')
                obj('MarbleSlab', Hp(8.0 * sx, 6.0, 19.0), ry, s=(5.0, 1.0, 10.0), col='box', name='Side gallery')
            wb = Hp(0, 6.0, 31.0); wyaw = back
            ST.append(dict(mesh='Statue_WingedFigure', p=R3(wb), r=round(wyaw, 2), s=5.0, role='The Woman Carrying a Beehive (stand-in)'))
            hx, hz = rot_y(-0.19 * 5.0, 0.1 * 5.0, wyaw)
            hive = [wb[0] + hx, wb[1] + 2.3 * 5.0 - 0.35, wb[2] + hz]
            obj('Beehive', hive, rng.uniform(0, 360), s=2.2, col='none', name='The beehive')
            obj('Plinth_Low', Hp(1.6, 6.0, 27.0), back, col='box', name='Plinth (the honeycomb)')
            prize('Tower Door', 'Honeycomb', Hp(1.6, 6.62, 27.0), rng.uniform(0, 360), s=1.4)
            EM.append(dict(kind='glint', p=R3([hive[0], hive[1] + 1.4, hive[2]]), size=[3.0, 2.6, 3.0]))
            fl = obj('FloodWater', Hp(0, -0.35, 1.0), ry, col='none', stat=False, noshadow=True, name='The Joining of the Three Tides (flood water)')
            floods.append(dict(name=fl['name'], low=round(fy - 0.4, 3), high=round(fy + 1.25, 3), period=420.0, rise=24.0, hold=40.0,
                               sound=R3(Hp(0, 1.5, 6))))
            for sx in (-1, 0, 1):
                EM.append(dict(kind='spray', p=R3(Hp(10.5 * sx if sx else 0, 0.4, 2.0 if sx == 0 else 16.0)), size=[3, 0.2, 3]))
        elif exit_ == 'Aqueduct Arch':                      # ------------- the Upper Halls
            EM.append(dict(kind='clouds', p=R3(Hp(0, 3.6, 17.0)), size=[18, 4.0, 30], rot=ry))
            EM.append(dict(kind='rainzone', p=R3(Hp(0, 19.5, 17.0)), size=[17, 0.5, 29], fall=19))
            for sx in (-1, 1):
                for lz in (6.0, 28.0):
                    q = Hp(6.5 * sx, 0, lz)
                    obj('HallFountain', q, 0, s=0.75, col='mesh', name='Rain basin'); obj('HallFountainPool', q, 0, s=0.75, noshadow=True, stat=False, name='Rain basin (water)')
            obj('GrandStair', Hp(0, 0, 9.0), ry, col='mesh', name='Stair up through the cloud')
            obj('MarbleSlab', Hp(0, 6.0, 24.0), ry, s=(10.0, 1.0, 10.0), col='box', name='Platform above the cloud')
            SE.append(dict(p=R3(Hp(0, 6.02, 27.5)), r=back, kind='bench', text='Sit above the cloud', exit=R3(Hp(0, 6.05, 25.5)), size=[0.8, 0.5, 0.8]))
            obj('Plinth_Low', Hp(2.2, 6.0, 25.0), back, col='box', name='Plinth (the cloud jar)')
            jp = Hp(2.2, 6.62, 25.0); prize('Aqueduct Arch', 'CloudJar', jp, 0, s=1.5)
            EM.append(dict(kind='jar', p=R3([jp[0], jp[1] + 0.25, jp[2]]), size=[0.24, 0.3, 0.24]))
            SO.append(dict(clip='Rain_Loop', p=R3(Hp(0, 4, 17)), vol=0.6, minD=4, maxD=28, spatial=1))
            LI.append(dict(kind='lantern', p=R3(Hp(0, 12, 17)), range=16, intensity=0.6, color=[0.75, 0.82, 1.0]))
        elif exit_ == 'Corner Passage':                     # ------------- the Hall of the Minotaurs
            horns = EX3.get('beast_head', [-0.1, 1.84, -0.17])
            for sx in (-1, 1):
                for lz in (6.0, 13.0, 20.0, 27.0):
                    q = Hp(7.6 * sx, 0, lz)
                    obj('Plinth_Square', q, ry, s=(1.7, 1.0, 1.7), col='box', name='Plinth')
                    yaw = face_in(sx); sc = 2.4
                    ST.append(dict(mesh='Statue_Beast', p=R3([q[0], fy + 1.3, q[2]]), r=round(yaw % 360, 2), s=sc, role='A Minotaur (stand-in)'))
                    hx, hz = rot_y(horns[0] * sc, horns[2] * sc, yaw)
                    obj('BullHorns', [q[0] + hx, fy + 1.3 + horns[1] * sc, q[2] + hz], yaw, s=sc, col='none', name='Horns of the Minotaur')
            fq = Hp(0, 0, 31.6)
            obj('Plinth_Square', fq, back, col='box', name='Plinth (the Faun)')
            ST.append(dict(mesh='Statue_SeatedSage', p=R3([fq[0], fy + 1.3, fq[2]]), r=round(back, 2), s=1.25, role='The Faun (stand-in)'))
            bq = Hp(0, 0, 29.6)
            prize('Corner Passage', 'ThreadSpool', Hp(0.9, 0.0, 30.6), rng.uniform(0, 360), s=1.6, extra=dict(thread='ThreadLines'))
            obj('BlockSeat_1', bq, back, col='box', name="A stone at the Faun's feet")
            SE.append(dict(p=R3([bq[0], fy + EX3['block_seat_h'] + 0.01, bq[2]]), r=back, kind='bench', text="Sit at the Faun's feet",
                           exit=R3(Hp(0, 0.05, 27.6)), size=[0.6, 0.4, 0.6]))
            dw = rot_y(0, 1, ry); dv = np.array([dw[0] * 0.85, -0.5, dw[1] * 0.85]); dv /= np.linalg.norm(dv)
            LI.append(dict(kind='spot', p=R3(Hp(0, 18.0, 1.0)), dir=R3(dv), angle=34, range=40, intensity=2.2, color=[1.0, 0.72, 0.45], name='Evening light'))
        elif exit_ == 'Bird Stair':                         # ------------- the Alcove of the Dead
            for sx in (-1, 1):
                for lz in (6.0, 12.0, 22.0, 28.0):
                    q = Hp(8.6 * sx, 0, lz)
                    obj('Plinth_Round', q, ry, s=0.8, col='box', name='Plinth (one of the Dead)')
                    obj('Bundle', [q[0], fy + 1.0 + 0.16, q[2]], e=[90, (ry + 90) % 360, 0], col='none', name='A bundle tied with seaweed twine')
                    for k in range(2):
                        m = SHELLS[rng.integers(3)]
                        obj(m, [q[0] + rng.uniform(-0.3, 0.3), fy + 1.0, q[2] + rng.uniform(-0.3, 0.3)], rng.uniform(0, 360), s=0.9, stat=False, noshadow=True)
            bq = Hp(-8.6, 0, 17.0)
            obj('Plinth_Square', bq, ry, col='box', name='The empty niche')
            obj('BiscuitBox', [bq[0], fy + 1.3, bq[2]], ry + 15, s=1.4, col='box', name='The red biscuit box')
            for k, (lx, lz) in enumerate(((-4.5, 4.0), (4.5, 4.0), (-4.5, 30.0), (4.5, 30.0), (8.6, 17.0))):
                q = Hp(lx, 0, lz)
                obj('Candleholders', [q[0], fy, q[2]], rng.uniform(0, 360), s=1.6, stat=False, name='Candles')
                LI.append(dict(kind='lantern', p=R3([q[0], fy + 1.2, q[2]]), range=4.5, intensity=0.8, color=[1.0, 0.62, 0.32]))
            oq = Hp(0, 0, 17.0)
            obj('Plinth_Round', oq, ry, col='box', name='Offering plinth')
            lil = []
            for k in range(36):
                a = 2 * math.pi * k / 12 + (k // 12) * 0.26; rr = 0.35 + 0.12 * (k // 12)
                if k < 12: p_ = [oq[0] + math.cos(a) * rr * 0.6, fy + 1.27, oq[2] + math.sin(a) * rr * 0.6]
                else: p_ = [oq[0] + math.cos(a) * (1.4 + 0.5 * (k // 12)), fy + 0.02, oq[2] + math.sin(a) * (1.4 + 0.5 * (k // 12))]
                nm = f'Offered lily {k + 1}'
                obj('WaterLily', p_, rng.uniform(0, 360), s=0.8, stat=False, noshadow=True, name=nm)
                lil.append(nm)
            offerings.append(dict(name='Offering plinth', p=R3([oq[0], fy + 1.0, oq[2]]), size=[2.4, 2.2, 2.4], lilies=lil,
                                  text='Leave a water lily for the Dead'))
            cq = Hp(1.1, 0, 17.6)
            obj('Candleholders_0', [cq[0], fy + 1.25, cq[2]], 0, s=1.4, stat=False, name='The candle lit for you')
            quests.append(dict(index=QI['Bird Stair'], name='Offering plinth', p=R3([oq[0], fy + 1.0, oq[2]]), size=[2.4, 2.2, 2.4],
                               text='Leave a water lily for the Dead', offering=True, candle=R3([cq[0], fy + 1.75, cq[2]])))
            EM.append(dict(kind='dust', p=R3(Hp(0, 5, 17)), size=[16, 9, 28], rot=ry))
        return fy

    for f in IS.wing_frames(wing_lengths()):
        px, pz = f['pos']; dx, dz = f['d']; ch = PL.CHAIN[f['exit']]; road(f['exit'])
        obj(f['mesh'], [px, 0.0, pz], f['ry'], col='none', name=f"Far wing of {ch['hall']} (on {ch['bar_name']})", noshadow=True)
        far_hall(f)
        for k in range(int(rng.integers(4, 8))):              # palms along the sand bar
            lx = rng.uniform(-0.9, 0.9) * f['radii'][0]; lz = rng.choice([-1, 1]) * rng.uniform(0.55, 0.85) * f['radii'][1]
            x, z = rot_y(lx, lz, f['ry']); x += px; z += pz
            if IS.island_d(x, z, f['name']) < 0.85: palm(x, z, tall=True)
        # mooring poles (briccole) marking the wade from the exit's island to the far hall: painted with a band of the road's
        # colour near the top, as Venetian paline are painted in their house's colours, so each wade can be told from the others
        start = np.array(exit_docks.get(f['exit'], isle_c(EXIT_ISLE[f['exit']])), float)
        stop = np.array(f['hall'], float) - np.array([dx, dz]) * 4.0
        seg = stop - start; L_ = float(np.linalg.norm(seg)); u = seg / max(L_, 1e-6); side = np.array([-u[1], u[0]])
        for t in np.arange(10.0, L_ - 4.0, 15.0):
            for sgn in (-1, 1):
                q = start + u * t + side * 3.2 * sgn
                if gy(q[0], q[1]) > -0.6: continue
                by = gy(q[0], q[1]) - 0.4; yaw_b = rng.uniform(0, 360)
                obj('Briccola', [q[0], by, q[1]], yaw_b, col='capsule', name=f"Mooring pole ({ch['road']}, to {ch['hall']})")
                for hb in (4.9, 5.6):
                    obj('NeonRing', [q[0], by + hb, q[1]], yaw_b, s=(1.02, 3.0, 1.02), col='none', mv=ch['family'], noshadow=True,
                        name=f"Painted band ({ch['family']})")
            if int(t) % 60 == 10:
                q = start + u * t + side * 3.2
                LI.append(dict(kind='lantern', p=R3([q[0], 6.3, q[1]]), range=6.0, intensity=0.9, color=[1.0, 0.7, 0.4]))
        road(None)
    L['floods'] = floods; L['offerings'] = offerings; L['quests'] = quests
    L['questUi'] = dict(counts=info['quest_counts'], shelf=info['quest_shelf'], thread="Ariadne's golden thread (hidden until the quest)",
                        candle='The candle lit for you')
    obj('ThreadLines', [0, 0, 0], 0, col='none', stat=False, noshadow=True, name="Ariadne's golden thread (hidden until the quest)")

    # =========================================================== boats at the water stairs, broken stairs, coral and fish
    gates = [(n, e) for n, e in PL.EXITS.items() if e['side'] in ('W', 'N')]
    for n, e in gates:
        road(n); g = vpos(e['cell']); ryg = {'E': 90, 'W': 270, 'N': 0, 'S': 180}[e['side']]
        gondola(local(g, ryg, 3.6, 0, 27.5), ryg)
        bp = local(g, ryg, 0.0, 0.0, 38.5)
        obj('BrokenStairs', [bp[0], gy(bp[0], bp[2]) + 0.05, bp[2]], ryg + rng.uniform(-12, 12), col='none', name=f'Broken stairs ({n})')
    road(None)

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
        for k in range(int(rng.integers(1, 3))):
            x, z = cx + rng.normal() * rad * 0.7, cz + rng.normal() * rad * 0.7; g = IS.ground(x, z)
            m = ['Sponge_Barrel', 'Sponge_Grass'][rng.integers(2)]
            if -0.9 - g > 0.5: obj(m, [x, g - 0.05, z], rng.uniform(0, 360), s=rng.uniform(0.8, 1.4), stat=False, noshadow=True, tag='reef')
        for k in range(int(rng.integers(1, 4))):
            x, z = cx + rng.normal() * rad, cz + rng.normal() * rad; g = IS.ground(x, z)
            m = STARS[rng.integers(3)] if rng.random() < 0.8 else 'Clam_Giant'
            if g < -0.9: obj(m, [x, g + 0.01, z], rng.uniform(0, 360), s=rng.uniform(1.0, 1.5), stat=False, noshadow=True, tag='reef')

    def fish(x, z, kind=None, depth=None):
        g = IS.ground(x, z)
        top = -1.15
        if g > top - 1.0: return
        y = (top + g) / 2 if depth is None else max(g + 0.7, min(top - 0.4, depth))
        obj(kind or FISH[rng.integers(3)], [x, y, z], rng.uniform(0, 360), s=rng.uniform(0.85, 1.2), noshadow=True, stat=False, tag='reef', name='Fish school')

    def clear_of_structures(x, z):
        if abs(x) < H + 6 and abs(z) < H + 6: return False
        if abs(x - nxp) < 9 and az0 - 2 < z < nz + 10: return False
        if abs(x - tp[0]) < 9 and tcz - 13 < z < -H: return False
        for n, e in gates:
            g = vpos(e['cell']); ryg = {'E': 90, 'W': 270, 'N': 0, 'S': 180}[e['side']]
            gp = local(g, ryg, 0, 0, 27)
            if (x - gp[0]) ** 2 + (z - gp[2]) ** 2 < 120: return False
        lx, lz = rot_y(x - sh_ent[0], z - sh_ent[1], -sh_ry)
        if abs(lx) < 14 and -7 < lz < 37: return False
        if (x - ac[0]) ** 2 + (z - ac[1]) ** 2 < 100: return False
        return True
    patches = 0
    for k in range(900):
        if patches >= 70: break
        a = rng.uniform(0, 2 * math.pi); r_ = rng.uniform(H + 12, H + 70)
        x, z = math.cos(a) * r_, math.sin(a) * r_
        if not clear_of_structures(x, z) or IS.ground(x, z) > -1.4: continue
        reef_patch(x, z, int(rng.integers(7, 14))); patches += 1
        if rng.random() < 0.3: fish(x + rng.normal() * 2, z + rng.normal() * 2)
    for isl in IS.ISLANDS:
        name, (cx, cz), (rx, rz) = isl[0], isl[1], isl[2]
        if name.startswith('Isle_WingBar'): continue
        for k in range(9 if name not in ('Isle_Albatross', 'Isle_TowerShoal', 'Isle_CornerBar') else 5):
            a = rng.uniform(0, 2 * math.pi); f_ = rng.uniform(1.12, 1.45)
            lx, lz = math.cos(a) * rx * f_, math.sin(a) * rz * f_
            if len(isl) > 6 and isl[6]: lx, lz = rot_y(lx, lz, -isl[6])
            x, z = cx + lx, cz + lz
            if clear_of_structures(x, z) and IS.ground(x, z) < -1.4: reef_patch(x, z, int(rng.integers(6, 12)), rad=3.5)
    for n, e in gates:                    # in front of every water stair: coral among the broken stairs, and fish
        g = vpos(e['cell']); ryg = {'E': 90, 'W': 270, 'N': 0, 'S': 180}[e['side']]
        for k in range(7):
            q = local(g, ryg, rng.uniform(-11, 11), 0, rng.uniform(42.0, 50.0))
            if IS.ground(q[0], q[2]) < -1.3: reef_patch(q[0], q[2], int(rng.integers(6, 11)), rad=3.0)
        for k in range(3):
            q = local(g, ryg, rng.uniform(-8, 8), 0, rng.uniform(43, 48)); fish(q[0], q[2], FISH[k])
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(9.5, 15)
        x, z = tp[0] + math.cos(a) * d, tcz + math.sin(a) * d
        if clear_of_structures(x, z) and IS.ground(x, z) < -1.3: reef_patch(x, z, int(rng.integers(6, 10)), rad=3.0)
    wx, wz = PL.WRECK
    obj('Ship_Dutch', [wx, IS.ground(wx, wz) + 0.9, wz], e=[-4, 35, 24], col='none', name='Wreck of the Dutch ship', stat=True)
    for k in range(7):
        a = rng.uniform(0, 6.28); reef_patch(wx + math.cos(a) * 11, wz + math.sin(a) * 9, int(rng.integers(6, 11)))
    fish(wx + 6, wz - 4, 'FishSchool_Tang'); fish(wx - 7, wz + 5, 'FishSchool_Chromis')
    fish(cb[0] + 14, cb[1] + 2, 'FishSchool_Reef')

    # =========================================================== ivy, flowers and floating vines on the House
    by_name = {o_['name']: o_ for o_ in O if 'name' in o_}
    def follow(target, ivy, extra_r=0.0, local_off=None, floats=None, s=1.0):
        t = by_name.get(target)
        if t is None: return
        p = list(t['p'])
        if local_off is not None:
            lx, lz = rot_y(local_off[0], local_off[2], t['r']); p = [p[0] + lx, p[1] + local_off[1], p[2] + lz]
        obj(ivy, p, t['r'] + extra_r, name=f'Ivy ({target})', floats=floats, s=s)
    win_sides = [(n, d) for (n, d), k in sides.items() if k == 'window']
    outer_win = [(n, d) for (n, d) in win_sides if not (0 <= n[0] + {'E': 1, 'W': -1}.get(d, 0) < PL.N and 0 <= n[1] + {'N': 1, 'S': -1}.get(d, 0) < PL.N)]
    blind = [(n, d) for (n, d), k in sides.items() if k == 'blind']
    vn = lambda n, d: f'Vestibule_{n[0]}{n[1]}_{d}'
    for i, (n, d) in enumerate(win_sides):
        if i % 2 == 0 or (n, d) in outer_win: follow(vn(n, d), f'Ivy_ExtWin_{i % 2}')
        if i % 3 == 0 and (n, d) not in outer_win: follow(vn(n, d), 'Ivy_WinIn')
    for i, (n, d) in enumerate(outer_win):
        if i % 2 == 0: follow(vn(n, d), f'Ivy_Float_{i % 2}', local_off=(0, 0, 0), floats=0.03)
    for i, (n, d) in enumerate(blind):
        if i % 3 == 0: follow(vn(n, d), f'Ivy_ExtBlind_{i % 2}')
        elif i % 3 == 1 and i % 2 == 0: follow(vn(n, d), 'Ivy_VestInnerBlind')
    for n in sorted({n for (n, d) in outer_win}):
        if (n[0] + n[1]) % 2 == 0:
            v = vpos(n); obj('Ivy_DomeTop', [v[0], 0, v[2]], [0, 90, 180, 270][int(rng.integers(4))], name='Ivy and flowers (dome terrace)')
    gal = [(n, d) for (n, d), k in sides.items() if k == 'gallery']
    for i, (n, d) in enumerate(gal):
        if i % 9 == 0: follow(vn(n, d), 'Ivy_VestInnerOpen')
        if i % 13 == 4: follow(vn(n, d), 'Ivy_HangLine_S', local_off=(0, 15.95, 9.8))
    for (n, e) in gates:
        ryg = {'E': 'E', 'W': 'W', 'N': 'N'}[e['side']]
        follow(vn(tuple(e['cell']), ryg), 'Ivy_HangLine_L', extra_r=180, local_off=(0, 12.5, 13.15))
    for n in [(PL.N // 2, PL.N // 2), (0, 0), (6, 6), (0, 6), (6, 0), (2, 4), (4, 2)]:
        v = vpos(n); obj('Ivy_HangRing', [v[0], 26.35, v[2]], rng.uniform(0, 360), name='Ivy (oculus)')
    # ---- vine-bloomer: the ivy mantle over every roof and outer wall (gen/real/mantle.py)
    MANTLES = {'Vest_Dome': [('Dome', 3), ('CoreTop', 1)], 'ArcadeExt': [('Arcade', 2)], 'NaveExt': [('Nave', 2)],
               'Arcade': [('GalArcade', 2)], 'Arcade_Win': [('GalArcadeWin', 2)], 'Nave': [('GalNave', 2)],
               'Vest_SideWindow': [('SideWindow', 2)], 'Vest_SideWindow_CutL': [('SideWindow_CutL', 1)], 'Vest_SideWindow_CutR': [('SideWindow_CutR', 1)],
               'Vest_SideBlind': [('SideBlind', 2)], 'Vest_SideOpen': [('SideOpen', 2)], 'Vest_SideGate': [('SideGate', 1)],
               'SeaHall': [('SeaHall', 1)], 'IsleHall': [('IsleHall', 1)]}
    for k_ in ('Window', 'Window_CutL', 'Window_CutR', 'Blind', 'Gallery', 'Gate', 'Tower', 'Cascade'):
        MANTLES['VestExt_' + k_] = [('Ext' + k_, 1 if k_ in ('Gate', 'Tower', 'Cascade', 'Window_CutL', 'Window_CutR') else 2)]
    mantle_src = [o_ for o_ in O if o_.get('mesh') in MANTLES]
    for i_, o_ in enumerate(mantle_src):
        for (mn, nv) in MANTLES[o_['mesh']]:
            if not os.path.exists(os.path.join(HERE, '..', 'out', 'Meshes', f'IvyMantle_{mn}_0.bytes')): continue
            obj(f'IvyMantle_{mn}_{(i_ * 7 + len(o_.get("name", ""))) % nv}', o_['p'], o_['r'], s=o_.get('s', 1.0), noshadow=True,
                name=f"Ivy mantle ({o_.get('name', o_['mesh'])})")
    for k, c_ in enumerate([o_ for o_ in O if o_.get('mesh') == 'Column' and o_.get('name') == 'Column']):
        if k % 4 == 0:
            obj(f'Ivy_Column_{(k // 4) % 2}', c_['p'], rng.uniform(0, 360), name='Ivy (Nave column)')
    for o_ in O:                          # big terrain-like meshes: keep the lanterns off them (see the builder)
        if o_.get('mesh', '').startswith(('Wing_', 'Isle_')) and not o_.get('tag'): o_['tag'] = 'terrain'

    # =========================================================== the Stormscape (see HouseStorm.cs)
    lt = info['ledge_top']; pal = info['palm']
    ang = math.atan2(lt[2] - pal[2], lt[0] - pal[0])
    L['storm'] = dict(
        axis=R3([pal[0], 0.0, pal[2]]), base=round(lt[1], 3), theta0=round(ang, 4),
        pitch=6.4, steps=40, rise=0.16, inner=2.8, outer=5.8, turns=11, topTurns=55,          # Astra's Infinite Spiral: 40 steps of 0.16 m per turn
        pole=R3([pal[0], pal[1], pal[2]]),
        white=[40.0, 120.0], stars=[200.0, 300.0], grow=12.0, growDelay=5.0,
        rosette=info['rosette'], tally=info['tally'], deadends=L['deadends'], spawn=L['spawn'],
        openDome=['Vestibule_33_Core', 'Vestibule_33_Dome'], openMeshes=['Vest_Core_Open', 'Vest_Dome_Open'], hideInStorm=['The Climb vine'],
        meteors=12.0, diveTime=9.0, blackout=[0.6, 2.2, 1.8])

    # =========================================================== creatures, wading floor, hand menu
    L['boats'] = boats
    L['crabs'] = crabs
    L['dolphins'] = dict(period=110.0, duration=22.0, routes=PL.DOLPHINS)
    L['variants'] = variants
    L['wade'] = dict(y=-1.3, size=1500)
    L['handmenu'] = dict(audible='https://www.audible.com/pd/Piranesi-Audiobook/1526622416',
                         book='https://bookshop.org/p/books/piranesi-susanna-clarke/15861178')
    print(f'world7: boats {len(boats)}, crabs {len(crabs)}, seats {len(SE)}, objects {len(O)}')
