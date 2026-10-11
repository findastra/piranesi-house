"""The 7 x 7 House (the Cross of the Four Winds) in Unity space (x right, y up, z north; metres, degrees). Writes
out/Data/HouseLayout.json for the Unity builder. The labyrinth comes from maze/final.json via plan7.py; world7.py adds
everything outside the House (islands, exit buildings, far wings, reefs, ivy) and the Stormscape.

Hints: every road has a family of statues; in each hall the family figure stands at the mouth of the gallery that carries
its road on, facing into it, on a pedestal sized by tier (colossal by the Colossus, plinth, small, sea-worn at the exit),
with a gold plaque counting the halls left (VII ... I). Dead ends hold one court figure each, with blue lanterns.
"""
import json, math, os, random
import numpy as np
import plan7 as PL
import islands as IS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', 'Data')
EX2 = json.load(open(os.path.join(OUT, 'Kit2Extra.json')))
EX3 = json.load(open(os.path.join(OUT, 'Kit3Extra.json')))
R = random.Random(77)
G = PL.G; N = PL.N; C = N // 2
M = PL.MAZE

objects, lights, shafts, emitters, probes, reverbs, statues, sounds, seats = [], [], [], [], [], [], [], [], []

def R3(p): return [round(float(v), 4) for v in p]
def rot_y(x, z, deg):
    a = math.radians(deg)
    return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
def local(o, ry, lx, ly, lz):
    x, z = rot_y(lx, lz, ry)
    return [o[0] + x, o[1] + ly, o[2] + z]
def yaw_to(dx, dz): return math.degrees(math.atan2(dx, dz)) % 360

def place(mesh, p, ry=0.0, s=(1, 1, 1), col='mesh', name=None, static=True, tag='', **kw):
    d = dict(name=name or mesh, mesh=mesh, p=R3(p), r=round(ry % 360, 3), s=[float(v) for v in s] if not np.isscalar(s) else [float(s)] * 3,
             col=col, stat=static, tag=tag)
    d.update(kw); objects.append(d); return d

def statue(mesh, p, ry, scale=1.0, role=''):
    statues.append(dict(mesh=mesh, p=R3(p), r=round(ry % 360, 3), s=round(float(scale), 4), role=role))

def vpos(c): return [(c[0] - C) * G, 0.0, (c[1] - C) * G]
DIRS = {'N': (0, 0, 1), 'E': (90, 1, 0), 'S': (180, 0, -1), 'W': (270, -1, 0)}
def nbr(c, d): return (c[0] + DIRS[d][1], c[1] + DIRS[d][2])
def E(a, b): return tuple(sorted((tuple(a), tuple(b))))
def inside(c): return 0 <= c[0] < N and 0 <= c[1] < N

EDGES = {E(a, b) for a, b in M['edges']}
NAVES = {E(a, b) for a, b in M['naves']}
SCREENS = {E(a, b) for a, b in M['screens']}
HALLS = {tuple(map(int, k.split(','))): v for k, v in M['halls'].items()}
DEAD = [tuple(c) for c in M['dead']]
COURT = {tuple(map(int, k.split(','))): v for k, v in M['court'].items()}
GATES = {}; CORNERS = {}
for e in M['exits']:
    c = tuple(e['cell'])
    if e['side'] in DIRS: GATES[(c, e['side'])] = e
    else: CORNERS[c] = ({'SE': (1, -1), 'NW': (-1, 1)}[e['side']], e)
CASCADE = (tuple(PL.CASCADE[0]), PL.CASCADE[1])
COLOSSUS = (C, C)
TREVI = ((C, C - 1), 'W')            # first hall south of the Colossus, its blind west wall

# tree depth from the Colossus (roof channels flow outward, toward the exits)
depth = {COLOSSUS: 0}; frontier = [COLOSSUS]
while frontier:
    nxt = []
    for n_ in frontier:
        for (a, b) in EDGES:
            if n_ in (a, b):
                m_ = b if a == n_ else a
                if m_ not in depth: depth[m_] = depth[n_] + 1; nxt.append(m_)
    frontier = nxt
assert len(depth) == N * N, 'labyrinth is not connected'
DEAD_EDGES = {e for e in EDGES if e[0] in DEAD or e[1] in DEAD}

def plaque(mesh, p, yaw, role):
    place(mesh, p, yaw, col='none', name=f'Plaque {mesh[7:]} - {role}', noshadow=True)

# ---------------------------------------------------------------- families: statue mesh and base scale (size 1 = human scale,
# capped so a colossal figure's footprint stays about 4.4 m)
FAM_MESH, FAM_BASE, FAM_EXT = PL.FAM_MESH, PL.FAM_BASE, PL.FAM_EXT      # (width x, length z) at scale 1
ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
PED = {'colossal': ('Pedestal_Colossal', 3.6, 1.75), 'plinth': ('Plinth_Square', 1.36, 1.3), 'small': ('Plinth_Low', 1.1, 0.6),
       'eroded': ('Plinth_Broken', 1.0, 0.63)}

# corners of a hall in world-axis signs; side d with local end sx maps to a corner
def corner_of(d, sx):
    ry = DIRS[d][0]
    x, z = rot_y(sx * 1.0, 1.0, ry)
    return (int(round(np.sign(x))), int(round(np.sign(z))))

def hint_statue(o, d, sx, f, cname):
    """family figure f in the hall at o, by the opening on side d (sx = -1 left / +1 right end), facing into the gallery."""
    ry = DIRS[d][0]
    fam = f['family']; tier = f['tier']
    sc = FAM_BASE[fam] * f['size']
    ext = FAM_EXT[fam]
    pm, pw, ph = PED[tier]
    foot = max(ext[0], ext[1]) * sc + 0.45
    k = max(foot / pw, 0.85) if tier in ('colossal', 'plinth') else 1.0
    hk = 0.8 if tier == 'colossal' else 1.0
    half = pw * k / 2
    xc = sx * max(6.4, 5.4 + half); zc = min(6.9, 9.4 - half)
    gaze = math.degrees(math.atan2(-xc, 22.0 - zc))
    top = ph * hk
    place(pm, local(o, ry, xc, 0, zc), ry, s=(k, hk, k), col='box', name=f'Pedestal ({fam}, {tier})')
    neon(local(o, ry, xc, 0.02, zc), ry, pw * k + 0.12, fam)
    worn = tier == 'eroded' or f['wear'] >= 0.3
    mesh = FAM_MESH[fam] + ('_Worn' if worn else '')
    statue(mesh, local(o, ry, xc, top, zc), ry + gaze, sc, f"{fam} ({tier}) - road to the {f['exit']}, {cname}")
    if f['left'] > 0:
        plaque('Plaque_' + ROMAN[f['left']], local(o, ry, xc, top * 0.55, zc - half - 0.012), ry, f"{fam}: {ROMAN[f['left']]} to the {f['exit']}")

def neon(p, yaw, width, fam):
    """the colour key: a neon band round the foot of a family pedestal, in that road's colour."""
    place('NeonRing', p, yaw, s=(width, 2.0, width), col='none', name=f'Neon ring ({fam})', mv=fam, noshadow=True, static=False)

def corner_statue(o, diag, f, cname):
    """the sea-worn figure in a corner exit hall, facing the diagonal passage."""
    fam = f['family']; sc = FAM_BASE[fam] * f['size']
    p = [o[0] + diag[0] * 5.9, 0.0, o[2] + diag[1] * 5.9]
    yaw = yaw_to(diag[0], diag[1])
    place('Plinth_Broken', p, yaw, col='box', name=f'Broken plinth ({fam}, the last)')
    neon([p[0], 0.02, p[2]], yaw, 1.15, fam)
    statue(FAM_MESH[fam] + '_Worn', [p[0], 0.63, p[2]], yaw, sc, f'{fam} (sea-worn) - the {f["exit"]} is here, {cname}')

# ---------------------------------------------------------------- the high-tide shelter (hidden egg): every outer window bay holds
# a marble daybed whose top is just above the highest tide, piled with linen, with wine, fruit, flowers and vines
WIN3 = [(-3.6, 1.9), (0.0, 2.2), (3.6, 1.9)]
DBT = EX3.get('window_daybed', dict(top=1.0, front=8.3))['top']
def window_beds(o, ry, cname, cut):
    for k, (wx, ww) in enumerate(WIN3):
        if cut and ((cut > 0 and wx > 0) or (cut < 0 and wx < 0)): continue       # the corner passage takes that bay
        place('WindowDaybed', local(o, ry, wx, 0, 0), ry, s=(ww - 0.04, 1, 1), col='mesh', name=f'Window daybed ({cname})')
        place(f'DaybedLinen_{R.randint(0, 2)}', local(o, ry, wx + R.uniform(-0.03, 0.03), 0, R.uniform(-0.05, 0.05)), ry + R.uniform(-1.5, 1.5),
              s=((ww - 0.1) / 0.92, 1, 1), col='none', name='Bedding', static=False)
        r = R.random()
        if r < 0.45:                                   # wine
            place('WineBottle', local(o, ry, wx + R.uniform(-0.35, 0.35), DBT + 0.17, 8.55 + R.uniform(0, 0.25)), R.uniform(0, 360), col='none', static=False, name='Wine')
            place('Goblets_Brass', local(o, ry, wx + R.uniform(-0.4, 0.4), DBT + 0.17, 8.6 + R.uniform(0, 0.3)), R.uniform(0, 360), col='none', static=False)
        elif r < 0.8:                                  # fruit
            b = local(o, ry, wx + R.uniform(-0.3, 0.3), DBT + 0.17, 8.7 + R.uniform(0, 0.2))
            place('Bowl_Wood', b, R.uniform(0, 360), s=1.3, col='none', static=False)
            for j, m in enumerate(['Fruit_Pomegranate', 'Fruit_Apple', 'Fruit_Lemon', 'Fruit_Pears', 'Fruit_Lime'][:R.randint(3, 5)]):
                a = j * 2.2; place(m, [b[0] + math.cos(a) * 0.07, b[1] + 0.04, b[2] + math.sin(a) * 0.07], R.uniform(0, 360), col='none', static=False)
        if R.random() < 0.5:                           # flowers at the foot
            place(f'Hibiscus_{R.choice(["Red", "Pink", "Orange"])}', local(o, ry, wx + R.choice([-1, 1]) * (ww / 2 + 0.35), 0, 8.6), R.uniform(0, 360),
                  s=R.uniform(0.7, 1.0), col='none', static=False)
        if k == 1 or R.random() < 0.34:                # sit on the edge with your feet over the floor (in the water at high tide)
            seats.append(dict(p=R3(local(o, ry, wx, DBT + 0.16, 8.75)), r=(ry + 180) % 360, kind='window',
                              text='Shelter in the window (feet in the water at high tide)',
                              exit=R3(local(o, ry, wx, 0.05, 7.3)), size=[0.9, 0.5, 0.9]))
    place('Ivy_WinIn', o, ry, col='none', name=f'Ivy (window, {cname})')
    if R.random() < 0.5:
        place('Lantern_Wood', local(o, ry, 0, 0.02, 8.0), ry, col='none', static=False)
        lights.append(dict(kind='lantern', p=R3(local(o, ry, 0, 0.34, 8.0)), range=5.0, intensity=0.8, color=[1.0, 0.68, 0.4]))

# ---------------------------------------------------------------- halls
SIDES = {}
occupied = {}                          # cell -> set of corners used (statues, Trevi, Colossus)
occupied[TREVI[0]] = {corner_of(TREVI[1], -1), corner_of(TREVI[1], 1)}
spray_count = 0
for i in range(N):
    for j in range(N):
        c = (i, j); o = vpos(c); cname = f"hall {'ABCDEFG'[i]}{j + 1}"
        vname = f'Vestibule_{i}{j}'
        place('Vest_Core', o, 0, name=vname + '_Core')
        place('Vest_Dome', o, 0, name=vname + '_Dome')
        probes.append(dict(p=[o[0], 8, o[2]], size=[20, 28, 20], name=vname, res=128))
        reverbs.append(dict(p=[o[0], 6, o[2]], minD=8, maxD=16, preset='Cave'))
        shafts.append(dict(p=[o[0], 26.6, o[2]], radius=2.9, height=26.6, kind='oculus'))
        emitters.append(dict(kind='season', p=[o[0], 26.0, o[2]], size=[5, 0.5, 5], fall=26))
        emitters.append(dict(kind='dust', p=[o[0], 8, o[2]], size=[14, 10, 14]))
        if (i + j) % 2 == 0:
            sounds.append(dict(clip='Wind_Loop', p=[o[0], 24, o[2]], vol=0.35, minD=4, maxD=55, spatial=1))
        corner_exit = CORNERS.get(c)
        for d, (ry, dx, dz) in DIRS.items():
            nb = nbr(c, d); e = E(c, nb)
            outer = not inside(nb)
            gate = GATES.get((c, d))
            if e in EDGES: kind = 'gallery'
            elif gate is not None: kind = 'tower' if gate['name'] == 'Tower Door' else 'gate'
            elif (c, d) == CASCADE: kind = 'cascade'
            elif outer or e in SCREENS: kind = 'window'
            else: kind = 'blind'
            SIDES[(c, d)] = kind
            cut = 0
            if corner_exit and outer and kind == 'window':
                diag = corner_exit[0]
                lx, lz = rot_y(1.0, 0.0, ry)
                if lx * diag[0] + lz * diag[1] > 0.5: cut = 1
                elif lx * diag[0] + lz * diag[1] < -0.5: cut = -1
                # only the two sides that meet at that corner get the passage
                if not ((d in ('E', 'W') and np.sign(dx) == diag[0]) or (d in ('N', 'S') and np.sign(dz) == diag[1])): cut = 0
            sfx = {1: '_CutR', -1: '_CutL', 0: ''}[cut]
            side = {'gate': 'Vest_SideGate', 'tower': 'Vest_SideOpen', 'gallery': 'Vest_SideOpen', 'window': 'Vest_SideWindow' + sfx}.get(kind, 'Vest_SideBlind')
            place(side, o, ry, name=f'{vname}_{d}')
            ext = {'gate': 'Gate', 'tower': 'Tower', 'gallery': 'Gallery', 'cascade': 'Cascade', 'window': 'Window' + sfx, 'blind': 'Blind'}[kind]
            place('VestExt_' + ext, o, ry, name=f'{vname}_{d}_Exterior')
            if kind == 'gate':
                place('SeaGate3', o, ry, name=f"Water stair ({gate['name']})")
                for tp_ in EX3['gate_torches']:
                    place('GateTorch', local(o, ry, tp_[0], tp_[1], tp_[2]), ry, col='none', name='Gauntlet torch')
                    fl = EX3['torch_flame']
                    lights.append(dict(kind='torch', p=R3(local(o, ry, tp_[0] + fl[0], tp_[1] + fl[1], tp_[2] + fl[2])), range=9.0, intensity=1.7, color=[1.0, 0.58, 0.26]))
                # sea-worn guardians of this gate's family on the capstones, looking out to sea
                fam = gate['family']; fm = FAM_MESH[fam] + '_Worn'
                for sx in (-1, 1):
                    statue(fm, local(o, ry, 9.2 * sx, 1.3, 23.8), ry, FAM_BASE[fam] * 0.9, f"{fam} guardian of the {gate['name']}")
                sounds.append(dict(clip='Ocean_Near_Loop', p=R3(local(o, ry, 0, 0, 30)), vol=1.0, minD=6, maxD=140, spatial=1))
                emitters.append(dict(kind='spray', p=R3(local(o, ry, 0, -0.2, 30)), size=[16, 0.2, 1]))
                shafts.append(dict(p=R3(local(o, ry, 0, 18.2, 10.6)), radius=1.9, height=18.0, kind='window', face=ry + 180))
            elif kind == 'tower':
                place('Tower3', local(o, ry, 0, 0, 12.0), ry, name='Marble Tower')
                sounds.append(dict(clip='Ocean_Far_Loop', p=R3(local(o, ry, 0, 6, 13)), vol=0.45, minD=5, maxD=40, spatial=1))
            elif kind == 'cascade':
                place('Cascade', local(o, ry, 0, 0, 10.0), ry + 180, col='none', name='Cascade', static=False)
                emitters.append(dict(kind='splash', p=R3(local(o, ry, 0, 0.3, 7.4)), size=[3.5, 0.3, 1.0]))
                sounds.append(dict(clip='Cascade_Loop', p=R3(local(o, ry, 0, 2, 7.5)), vol=0.9, minD=3, maxD=50, spatial=1))
            elif kind == 'window':
                shafts.append(dict(p=R3(local(o, ry, 0.0, 13.0 + 1.1, 11.2)), radius=1.1, height=14.1, kind='window', face=ry + 180, dim=0.3))
                if outer:
                    sounds.append(dict(clip='Ocean_Far_Loop', p=R3(local(o, ry, 0, 6, 13)), vol=0.45, minD=5, maxD=40, spatial=1))
                    window_beds(o, ry, cname, cut)
        # fountain in every hall but the Colossus' and the Trevi's
        if c not in (COLOSSUS, TREVI[0]):
            place('HallFountain', o, 0, col='mesh', name=f'Fountain ({cname})')
            place('HallFountainPool', o, 0, col='none', static=False, name=f'Fountain ({cname}) pool', noshadow=True)
            place('HallFountainWater', o, 0, col='none', static=False, name=f'Fountain ({cname}) water', noshadow=True)
            sounds.append(dict(clip='Cascade_Loop', p=[o[0], 1.5, o[2]], vol=0.3, minD=1.5, maxD=15, spatial=1))
        # family statues (hint figures)
        h = HALLS.get(c, {})
        used = occupied.setdefault(c, set())
        if corner_exit is not None:
            used.add(corner_exit[0])
        fams = h.get('fam', [])
        groups = {}
        for f in fams:
            if f['to'] is not None:
                t = tuple(f['to']); dd = [d for d in DIRS if nbr(c, d) == t][0]
            elif f['out'] in DIRS: dd = f['out']
            else: dd = f['out']                 # SE / NW corner exit
            groups.setdefault(dd, []).append(f)
        for dd, fs in groups.items():
            if dd in ('SE', 'NW'):
                for f in fs: corner_statue(o, corner_exit[0], f, cname)
                continue
            for f in fs:
                choice = None
                for sx in ((-1, 1) if R.random() < 0.5 else (1, -1)):
                    cn = corner_of(dd, sx)
                    if cn not in used: choice = sx; break
                if choice is None:
                    raise RuntimeError(f'no free corner for {f["family"]} in {cname}')
                used.add(corner_of(dd, choice))
                hint_statue(o, dd, choice, f, cname)
        # sand drifted into a corner now and then
        if c not in (COLOSSUS, TREVI[0]) and R.random() < 0.45:
            free = [cn for cn in ((1, 1), (1, -1), (-1, 1), (-1, -1)) if cn not in used]
            if free:
                cn = R.choice(free)
                place('SandDrift', [o[0] + cn[0] * 8, 0, o[2] + cn[1] * 8], R.uniform(0, 360), (R.uniform(0.6, 0.9), R.uniform(0.6, 1.0), R.uniform(0.6, 0.9)),
                      name='SandDrift')

# ---------------------------------------------------------------- the court of dead ends (one unique figure each, blue lanterns)
BLUE = [0.45, 0.62, 1.0]; GOLD = [1.0, 0.68, 0.38]
deadends = []
for k, c in enumerate(DEAD):
    o = vpos(c); name = COURT[c]
    entry = [d for d in DIRS if E(c, nbr(c, d)) in EDGES][0]
    opp = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}[entry]
    ry = DIRS[opp][0]
    p = local(o, ry, 0, 0, 6.4)
    place('Court_' + name, p, ry + 180, col='box', name=f'The {name} (dead end)')
    for sx in (-1, 1):
        lp = local(o, ry, 3.2 * sx, 3.0, 9.55)
        place('Lantern', lp, ry + 180, col='none', name='Lantern (blue)', static=False)
    lights.append(dict(kind='lantern', p=R3(local(o, ry, 0, 4.2, 7.6)), range=9.0, intensity=1.3, color=BLUE))
    deadends.append(dict(name=name, p=R3([o[0], 2.0, o[2]]), size=[19.5, 4.0, 19.5], burst=R3([p[0], 3.0, p[2]])))

# ---------------------------------------------------------------- galleries
FULL_NEUTRAL = ['Statue_Head', 'Statue_SeatedSage', 'Statue_Queen']
for e in sorted(EDGES):
    a, b = e
    if depth[a] > depth[b]: a, b = b, a                   # a: nearer the Colossus
    pa, pb = vpos(a), vpos(b)
    c = [(pa[0] + pb[0]) / 2, 0.0, (pa[2] + pb[2]) / 2]
    along_x = a[1] == b[1]
    ry = 90 if along_x else 0
    nave = e in NAVES
    dead = e in DEAD_EDGES
    gname = f"{'Nave' if nave else 'Arcade'}_{a[0]}{a[1]}_{b[0]}{b[1]}"
    perim = (not nave) and ((along_x and abs(c[2]) > 170) or (not along_x and abs(c[0]) > 170))
    win = False
    if not nave:
        off = c[2] if along_x else c[0]
        if abs(off) > 1:                                   # window wall (local +x) faces away from the Colossus
            ox, oz = (0.0, math.copysign(1, off)) if along_x else (math.copysign(1, off), 0.0)
            ry = round(math.degrees(math.atan2(-oz, ox))) % 360
            win = True
    place('Arcade_Win' if win else ('Nave' if nave else 'Arcade'), c, ry, name=gname)
    fry = yaw_to(pb[0] - pa[0], pb[2] - pa[2])            # roof channel water runs outward (from a to b)
    place('NaveExt' if nave else 'ArcadeExt', c, fry, name=gname + '_Exterior')
    place('NaveExtWater' if nave else 'ArcadeExtWater', c, fry, col='none', name=gname + '_RoofChannelWater', static=False)
    probes.append(dict(p=[c[0], 7, c[2]], size=[36, 22, 20] if along_x else [20, 22, 36], name=gname, res=128 if nave else 64))
    reverbs.append(dict(p=[c[0], 5, c[2]], minD=10, maxD=20, preset='Auditorium' if nave else 'StoneCorridor'))
    if nave:
        emitters.append(dict(kind='dust', p=R3(local(c, ry, 0, 7, 0)), size=[10, 12, 34], rot=ry))
        # nave statues: the families of this arm, facing outward along the nave (the gaze points to the gates)
        arm_fams = sorted({f['family'] for f in HALLS.get(b, {}).get('fam', [])})
        COL_Y = [-15.75 + 4.5 * k for k in range(8)]
        outward = 1 if rot_y(0, 1, ry)[0] * (pb[0] - pa[0]) + rot_y(0, 1, ry)[1] * (pb[2] - pa[2]) > 0 else -1
        for sx in (-1, 1):
            for z in COL_Y:
                place('Column', local(c, ry, 6 * sx, 0, z), ry, col='capsule', name='Column')
            for k in range(7):
                z = (COL_Y[k] + COL_Y[k + 1]) / 2
                place('Plinth_Square', local(c, ry, 6 * sx, 0, z), ry, col='box', name='Plinth')
                fam = arm_fams[(k + (sx > 0)) % len(arm_fams)]
                neon(local(c, ry, 6 * sx, 0.02, z), ry, 1.48, fam)
                t = (z * outward + 18) / 36                    # 0 at the Colossus end, 1 at the far end
                sc = FAM_BASE[fam] * (1.25 - 0.25 * t) * (0.62 if fam == 'Elephant' else 0.85)
                statue(FAM_MESH[fam], local(c, ry, 6 * sx, 1.3, z), ry + (0 if outward > 0 else 180) - 12 * sx * outward, sc,
                       f'{fam} of the nave (looking toward its gate)')
                if k % 3 == 1:
                    statue(FULL_NEUTRAL[(k // 3 + (sx > 0)) % 3], local(c, ry, 8.35 * sx, 0.6, z), ry - 90 * sx, 1.4, 'Bust in a nave niche')
        for zo in (-9.0, 9.0):
            shafts.append(dict(p=R3(local(c, ry, 0, 20.5, zo)), radius=1.5, height=20.5, kind='oculus'))
            emitters.append(dict(kind='season', p=R3(local(c, ry, 0, 20.3, zo)), size=[2.5, 0.4, 2.5], fall=20))
        for k in (1, 5):
            z = (COL_Y[k] + COL_Y[k + 1]) / 2
            for sx in (-1, 1):
                shafts.append(dict(p=R3(local(c, ry, 6.3 * sx, 13.5, z)), radius=1.1, height=13.5, kind='window', face=ry - 90 * sx, dim=0.5))
    else:
        bays = [-15.75 + 4.5 * k for k in range(8)]
        wall_sx = -1 if win else (1 if R.random() < 0.5 else -1)     # busts on the blind wall only
        for k, z in enumerate(bays):
            if k % 2 == 0 and R.random() < 0.7:
                st = R.choice(FULL_NEUTRAL)
                statue(st, local(c, ry, 5.45 * wall_sx, 0.9, z), ry - 90 * wall_sx, {'Statue_Queen': 1.6, 'Statue_SeatedSage': 1.0}.get(st, 1.3), 'Bust in a gallery niche')
            if perim and win and k in (2, 5):
                seats.append(dict(p=R3(local(c, ry, 5.6, 1.0, z)), r=ry + 90, kind='window', text='Sit in the window',
                                  exit=R3(local(c, ry, 3.9, 0.05, z)), size=[1.2, 0.5, 0.9]))
        col = BLUE if dead else GOLD
        for zp, sx in ((-8.0, -1), (8.0, 1)):
            lsx = -1 if win else sx                       # lanterns hang on the blind wall
            place('Lantern', local(c, ry, 4.58 * lsx, 3.0, zp), ry - 90 * lsx, col='none', name='Lantern' + (' (blue)' if dead else ''), static=False)
            lights.append(dict(kind='lantern', p=R3(local(c, ry, 3.95 * lsx, 3.35, zp)), range=7.0, intensity=1.5, color=col))
        shafts.append(dict(p=R3(local(c, ry, 0, 14.2, 0)), radius=0.75, height=14.2, kind='skylight'))
        emitters.append(dict(kind='season', p=R3(local(c, ry, 0, 14.0, 0)), size=[1.4, 0.3, 1.4], fall=14))
    for k in range(R.randint(0, 2)):
        m = R.choice(['Fragment_Drum', 'Fragment_Slab'])
        lx = R.uniform(-2.6, 2.6); lz = R.uniform(-14, 14)
        if m == 'Fragment_Drum':
            place(m, local(c, ry, lx, 0.42, lz), R.uniform(0, 360), name=m, col='box', lie=True)
        else:
            place(m, local(c, ry, lx, 0.0, lz), R.uniform(0, 360), name=m, col='box')

# ---------------------------------------------------------------- the Colossus (centre hall): ledges, the glittering hand,
# the Climb vine (teleport to the castellum), the plaque, the secret rosette, spawn and its stand
o = vpos(COLOSSUS); col = EX2['colossus']; palm = col['palm']; ped = col['pedestal']
cry = 180.0
ox, oz = rot_y(palm[0], palm[2], cry)
base = [o[0] - ox, 0.0, o[2] - oz]
place('Colossus_Pedestal', base, cry, col='mesh', name='Colossus Pedestal')
statue('Colossus', [base[0], ped, base[2]], cry, 1.0, 'The Colossus: a sea-worn marble giant (rest on her shoulder)')
platforms = []                                         # invisible footholds spiralling up round her to the palm
for k, pl in enumerate(EX3.get('colossus_platforms', [])):
    lx, lz = rot_y(pl['p'][0], pl['p'][2], cry)
    platforms.append(dict(name=f'Invisible foothold {k + 1}', p=R3([base[0] + lx, ped + pl['p'][1], base[2] + lz]), size=pl['size'], r=round((cry + pl['r']) % 360, 2)))
fx, fz = rot_y(0, 4.71, cry)
place('Plaque_ClimbToTheLight', [base[0] + fx, 1.0, base[2] + fz], cry + 180, col='none', name='Plaque - Climb to the light', noshadow=True)
rx_, rz_ = rot_y(-1.25, 4.72, cry)
rosette = place('SecretRosette', [base[0] + rx_, 1.48, base[2] + rz_], cry + 180, col='none', name='Secret rosette (starts the Stormscape)', static=False)
pw = [o[0], ped + palm[1], o[2]]
nrm = col['palm_normal']; nx, nz = rot_y(nrm[0], nrm[2], cry)
seat_p = [pw[0] + nx * 0.06, pw[1] + nrm[1] * 0.06, pw[2] + nz * 0.06]
seats.append(dict(p=R3(seat_p), r=cry, kind='palm', text="Rest on the Colossus' shoulder", exit=R3([base[0], 0.05, base[2] - 6.2]),
                  size=[0.9, 0.5, 0.9], trigger=dict(p=R3([base[0], 1.0, base[2] - 4.75]), size=[3.4, 2.0, 0.6])))
# the light on the hand: the oculus spot plus a narrow golden one, and two layers of glitter
lights.append(dict(kind='spot', p=R3([o[0], 26.2, o[2]]), dir=[0, -1, 0], angle=20, range=16, intensity=3.0, color=[1.0, 0.95, 0.86]))
lights.append(dict(kind='spot', p=R3([o[0] + 1.6, 26.0, o[2] - 1.2]), dir=R3(np.array([-1.6, pw[1] - 26.0, 1.2]) / np.linalg.norm([-1.6, pw[1] - 26.0, 1.2])),
                   angle=9, range=18, intensity=5.0, color=[1.0, 0.88, 0.62]))
emitters.append(dict(kind='sparkle', p=R3([pw[0], pw[1] + 0.6, pw[2]]), size=[1.8, 1.6, 1.8]))
emitters.append(dict(kind='glint', p=R3([pw[0], pw[1] + 0.35, pw[2]]), size=[1.1, 0.8, 1.1]))
shafts.append(dict(p=R3([o[0], 26.6, o[2]]), radius=0.9, height=26.6 - pw[1], kind='palm', face=0))
# the Climb vine hangs from the oculus rim right beside the top ledge
lt = EX3['colossus_ledge_top']
tx, tz = rot_y(lt[0], lt[2], cry); top = [base[0] + tx, ped + lt[1], base[2] + tz]
u = np.array([top[0] - o[0], top[2] - o[2]]); u /= np.linalg.norm(u)
vine = [o[0] + u[0] * 2.45, 26.6, o[2] + u[1] * 2.45]
place('Vine_Climb', vine, R.uniform(0, 360), col='none', name='The Climb vine', static=False, noshadow=True)
castle = EX3['castellum']
teleports = [dict(name='The Climb vine', p=R3([vine[0], top[1] + 1.3, vine[2]]), size=[0.9, 2.6, 0.9], text='Climb',
                  target=castle['walk'], targetR=270.0, near=R3(pw), nearR=2.4)]          # the prompt shows only within 2.4 m of the palm
# spawn and its stand (SPAWN, the dead-end tally)
spawn = dict(p=R3([o[0] + PL.SPAWN['p'][0], 0.1, o[2] + PL.SPAWN['p'][2]]), r=PL.SPAWN['r'])
fwd = (math.sin(math.radians(spawn['r'])), math.cos(math.radians(spawn['r']))); left = (-fwd[1], fwd[0])
stand = [spawn['p'][0] + fwd[0] * 1.7 + left[0] * 1.3, 0.0, spawn['p'][2] + fwd[1] * 1.7 + left[1] * 1.3]
syaw = yaw_to(-(spawn['p'][0] - stand[0]), -(spawn['p'][2] - stand[2]))
place('SpawnStand', stand, syaw, col='box', name='Spawn stand')
ss = EX3['spawn_stand']
place('Plaque_Spawn', local(stand, syaw, 0, ss['spawn_y'], ss['face'] - 0.004), syaw, col='none', name='Plaque - SPAWN', noshadow=True)
place('Plaque_DeadEnds', local(stand, syaw, 0, ss['title_y'], ss['face'] - 0.004), syaw, col='none', name='Plaque - DEAD ENDS FOUND', noshadow=True)
tally = []
for n_ in range(6):
    nm = f'Tally plaque {n_}/5'
    place(f'Plaque_Count{n_}', local(stand, syaw, 0, ss['count_y'], ss['face'] - 0.004), syaw, col='none', name=nm, noshadow=True, static=False)
    tally.append(nm)
# the quest stand on the other side (FAR HALL QUESTS 0/6 .. 6/6, wider for the longer plaque) and the prize shelf at the south
# edge of the terrace: each Far Hall Quest's twin appears on it, above its role plaque, when you bring it back
stand2 = [spawn['p'][0] + fwd[0] * 1.7 - left[0] * 1.3, 0.0, spawn['p'][2] + fwd[1] * 1.7 - left[1] * 1.3]
syaw2 = yaw_to(-(spawn['p'][0] - stand2[0]), -(spawn['p'][2] - stand2[2]))
place('SpawnStand', stand2, syaw2, s=(1.35, 1, 1), col='box', name='Quest stand')
place('Plaque_Quests', local(stand2, syaw2, 0, ss['title_y'], ss['face'] - 0.004), syaw2, col='none', name='Plaque - FAR HALL QUESTS', noshadow=True)
quest_counts = []
for n_ in range(7):
    nm = f'Quest plaque {n_}/6'
    place(f'Plaque_Quest{n_}', local(stand2, syaw2, 0, ss['count_y'], ss['face'] - 0.004), syaw2, col='none', name=nm, noshadow=True, static=False)
    quest_counts.append(nm)
shelf_c = [spawn['p'][0] + left[0] * 9.4 + fwd[0] * 0.2, 0.0, spawn['p'][2] + left[1] * 9.4 + fwd[1] * 0.2]
shelf_yaw = yaw_to(shelf_c[0] - spawn['p'][0], shelf_c[2] - spawn['p'][2])        # local -z (the plaques' side) faces the camp
place('MarbleSlab', [shelf_c[0], 0.85, shelf_c[2]], shelf_yaw, s=(4.0, 0.85, 0.55), col='box', name='Prize shelf (marble)')
TWIN = [('JournalPage', 1.0, 0.0), ('GoldShard', 0.8, 0.0), ('Honeycomb', 1.2, 0.0), ('CloudJar', 1.0, 0.0), ('ThreadSpool', 1.6, 0.0),
        ('Candleholders_0', 0.6, 0.0)]
quest_shelf = []
for k_, (m_, sc_, _) in enumerate(TWIN):
    x_ = (k_ - 2.5) * 0.64
    q_ = PL.QUESTS[k_]
    place(f'Plaque_Role{k_}', local(shelf_c, shelf_yaw, x_, 0.48, -0.275 - 0.004), shelf_yaw, s=(0.66, 0.66, 1.0), col='none',
          name=f"Plaque - {q_['role'].upper()}", noshadow=True)
    nm = f"Prize shelf {k_ + 1}: {q_['prize']}"
    place(m_, local(shelf_c, shelf_yaw, x_, 0.851, 0.02), shelf_yaw + 180, s=sc_, col='none', name=nm, noshadow=True, static=False)
    quest_shelf.append(nm)
probes.append(dict(p=[o[0], 12, o[2]], size=[22, 26, 22], name='Colossus', res=256))

# ---------------------------------------------------------------- the Trevi on the blind west wall of the first hall south
to = vpos(TREVI[0]); sry = DIRS[TREVI[1]][0]; tr = EX3['trevi']
for m in ('Trevi', 'TreviShell'):
    place(m, to, sry, col='mesh' if m == 'Trevi' else 'none', name='Trevi fountain' if m == 'Trevi' else 'Trevi shell')
place('TreviPool', to, sry, col='none', static=False, name='Trevi (pool)', noshadow=True)
place('TreviWater', to, sry, col='none', static=False, name='Trevi (water)', noshadow=True)
statue('Statue_SeatedSage', local(to, sry, tr['statue'][0], tr['statue'][1], tr['statue'][2]), sry + 180, 1.35, 'Oceanus in the Trevi niche (no road family here, so it is no hint)')
for hp in tr['horses']:             # busts, not family figures, so the fountain gives no false hint
    statue('Statue_Head', local(to, sry, hp[0], hp[1] + 0.2, hp[2]), sry + 180 + (25 if hp[0] < 0 else -25), 1.6, 'Bust of the Trevi')
sounds.append(dict(clip='Cascade_Loop', p=R3(local(to, sry, 0, 1.5, 8.0)), vol=0.7, minD=2.5, maxD=30, spatial=1))
emitters.append(dict(kind='splash', p=R3(local(to, sry, 0, 0.45, 7.3)), size=[2.4, 0.2, 0.6]))
emitters.append(dict(kind='spray', p=R3(local(to, sry, 0, 0.5, 7.0)), size=[8, 0.2, 2.4]))

# ---------------------------------------------------------------- roof: aqueducts, castellum, rides
place('RoofAqueducts', [0, 0, 0], 0, col='mesh', name='Roof aqueducts', tag='terrain')
place('RoofAqueductsWater', [0, 0, 0], 0, col='none', static=False, name='Roof aqueducts (water)', noshadow=True)
place('Castellum', [0, 0, 0], 0, col='mesh', name='Castellum (water tower of the roofs)')
place('CastellumPool', [0, 0, 0], 0, col='none', static=False, name='Castellum (basin)', noshadow=True)
sounds.append(dict(clip='Cascade_Loop', p=R3([castle['p'][0], 27, castle['p'][2]]), vol=0.6, minD=3, maxD=40, spatial=1))
rides = []
for n_, r_ in EX3['rides'].items():
    fam = PL.EXITS[n_]['family']
    rides.append(dict(name=n_, path=[round(float(v), 3) for pt in r_['path'] for v in pt], exit=r_['exit'], exitR=r_['exitR'],
                      text=f'Ride the aqueduct to the {n_}', family=fam, color=PL.rgb(PL.FAMILY_COLORS[fam])))

place('Seabed3', [0, 0, 0], 0, col='mesh', name='Sand_Seabed', tag='terrain')
place('SeabedFar', [0, 0, 0], 0, col='mesh', name='Sand_Seabed (far)', tag='terrain')
sounds.append(dict(clip='House_Drone_Loop', p=[0, 0, 0], vol=0.18, spatial=0))
sounds.append(dict(clip='Ocean_Far_Loop', p=[0, 0, 0], vol=0.12, spatial=0))

palette = [dict(name=k, color=PL.rgb(v)) for k, v in PL.FAMILY_COLORS.items()]
layout = dict(palette=palette, objects=objects, statues=statues, lights=lights, shafts=shafts, emitters=emitters, probes=probes, reverbs=reverbs,
              sounds=sounds, spawn=spawn, seats=seats, teleports=teleports, rides=rides, deadends=deadends, platforms=platforms,
              house_bounds=[-PL.HALF, -PL.HALF, PL.HALF, PL.HALF])
info = dict(sides=SIDES, edges=EDGES, naves=NAVES, vpos=vpos, local=local, tally=tally, rosette=rosette['name'], palm=pw,
            ledge_top=top, colossus_base=base, quest_counts=quest_counts, quest_shelf=quest_shelf)

CALM_MESHES = ('SeaHall', 'IsleHall', 'BirdTower', 'Wing_1', 'Wing_2', 'Wing_3', 'SeaGate3')

def calm_zones(objs, pad=1.5, fall=25.0):
    """calm water in the lee of every building that stands out on the sea (far halls, wings, isle halls, the Bird Tower,
    the water-stair terraces with the spawn camp): one rotated box per building, from its mesh footprint. The House itself
    is calm already (the sea shader's _HouseHalf)."""
    import struct
    import numpy as np
    foot = {}
    for m in CALM_MESHES:
        with open(os.path.join(OUT, '..', 'Meshes', m + '.bytes'), 'rb') as f:
            f.read(4); nv, _, _ = struct.unpack('<iii', f.read(12))
            P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3)
        foot[m] = (float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 2].min()), float(P[:, 2].max()))
    zones = []
    for o in objs:
        if o['mesh'] not in foot: continue
        x0, x1, z0, z1 = foot[o['mesh']]
        sx, sz = o['s'][0], o['s'][2]
        cx, cz = rot_y((x0 + x1) * 0.5 * sx, (z0 + z1) * 0.5 * sz, o['r'])
        zones.append(dict(name=o['name'], c=[round(o['p'][0] + cx, 2), round(o['p'][2] + cz, 2)], r=o['r'],
                          h=[round((x1 - x0) * 0.5 * sx + pad, 2), round((z1 - z0) * 0.5 * sz + pad, 2)], fall=fall))
    return zones

if __name__ == '__main__':
    import world7
    world7.build(layout, info)
    layout['calm'] = calm_zones(layout['objects'])
    assert len(layout['calm']) <= 24, f"{len(layout['calm'])} calm zones; the sea shader takes 24"
    json.dump(layout, open(os.path.join(OUT, 'HouseLayout.json'), 'w'), indent=1)
    print(f"objects {len(objects)}, statues {len(statues)}, lights {len(lights)}, shafts {len(shafts)}, emitters {len(emitters)}, "
          f"probes {len(probes)}, seats {len(seats)}, rides {len(rides)}, sounds {len(sounds)}")
