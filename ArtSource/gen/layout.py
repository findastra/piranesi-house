"""Lays out the House in Unity space (x right, y up, z forward). Writes out/Data/HouseLayout.json,
consumed by the Unity editor builder. Modules were exported with their long axis on +Z.

Plan: 3x3 grid of domed Vestibules 60 m apart. The central east-west row is joined by colonnaded
Naves; the remaining links are a maze of stone Arcades (spanning tree + one loop). Missing links
become blind niches holding colossal statues. The west-central Vestibule opens onto the Sea Gate."""
import json, math, os, random

OUT = os.path.join(os.path.dirname(__file__), '..', 'out', 'Data')
os.makedirs(OUT, exist_ok=True)
R = random.Random(9)
G = 60.0

objects, lights, shafts, emitters, probes, reverbs, statues, sounds = [], [], [], [], [], [], [], []

def rot_y(x, z, deg):
    a = math.radians(deg)
    return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)

def place(mesh, p, ry=0.0, s=(1, 1, 1), col='mesh', name=None, static=True, tag=''):
    objects.append(dict(name=name or mesh, mesh=mesh, p=[round(v, 4) for v in p], r=round(ry % 360, 3), s=list(s), col=col, stat=static, tag=tag))

def local(origin, ry, lx, ly, lz):
    x, z = rot_y(lx, lz, ry)
    return [origin[0] + x, origin[1] + ly, origin[2] + z]

# ---------------------------------------------------------------- statue registry (stand-ins for the book's statues)
REG = {
    'Statue_WingedFigure': 'Winged figure (stand-in; book: angel caught in a rose bush - TO CONFIRM placement)',
    'Statue_Beast': 'Stand-in for the Gorilla',
    'Statue_Horse': 'Horse',
    'Statue_Dragon': 'Dragon / strange beast',
    'Statue_Hare': 'Stand-in for the Fox teaching squirrels (animal group)',
    'Statue_SeatedSage': 'Seated figure (stand-in for the two Kings playing chess)',
    'Statue_Queen': 'Bust of a queen',
    'Statue_Child': 'Stand-in for the Boy playing cymbals',
    'Statue_Head': 'Colossal head (Drowned Halls)',
}
FULL = ['Statue_WingedFigure', 'Statue_Beast', 'Statue_SeatedSage', 'Statue_Horse', 'Statue_Dragon', 'Statue_Hare']
BUSTS = ['Statue_Queen', 'Statue_Child', 'Statue_Head']

def statue(mesh, p, ry, scale=1.0, role=None):
    statues.append(dict(mesh=mesh, p=[round(v, 4) for v in p], r=round(ry % 360, 3), s=scale, role=role or REG.get(mesh, '')))

# ---------------------------------------------------------------- maze
nodes = [(i, j) for i in range(3) for j in range(3)]
edges_all = []
for i in range(3):
    for j in range(3):
        if i < 2: edges_all.append(((i, j), (i + 1, j)))
        if j < 2: edges_all.append(((i, j), (i, j + 1)))
naves = {((0, 1), (1, 1)), ((1, 1), (2, 1))}
parent = {n: n for n in nodes}
def find(n):
    while parent[n] != n: n = parent[n]
    return n
chosen = set()
for e in naves:
    parent[find(e[0])] = find(e[1]); chosen.add(e)
pool = [e for e in edges_all if e not in naves]; R.shuffle(pool)
loops = 1
for e in pool:
    a, b = find(e[0]), find(e[1])
    if a != b:
        parent[a] = b; chosen.add(e)
    elif loops > 0:
        chosen.add(e); loops -= 1
print('galleries:', len(chosen), sorted(chosen))

def vpos(n): return [(n[0] - 1) * G, 0.0, (n[1] - 1) * G]

# side directions: name -> (ry, dx, dz)
DIRS = {'N': (0, 0, 1), 'E': (90, 1, 0), 'S': (180, 0, -1), 'W': (270, -1, 0)}
def neighbor(n, d):
    _, dx, dz = DIRS[d]
    return (n[0] + dx, n[1] + dz)

SEA_GATE = ((0, 1), 'W')
CASCADE = ((2, 2), 'N')

for n in nodes:
    o = vpos(n)
    vname = f'Vestibule_{n[0]}{n[1]}'
    place('Vest_Core', o, 0, name=vname + '_Core')
    probes.append(dict(p=[o[0], 8, o[2]], size=[20, 28, 20], name=vname))
    reverbs.append(dict(p=[o[0], 6, o[2]], minD=8, maxD=16, preset='Cave'))
    # oculus light shaft + seasonal fall-through + wind
    shafts.append(dict(p=[o[0], 26.6, o[2]], radius=2.9, height=26.6, kind='oculus'))
    emitters.append(dict(kind='season', p=[o[0], 26.0, o[2]], size=[5, 0.5, 5], fall=26))
    emitters.append(dict(kind='dust', p=[o[0], 8, o[2]], size=[18, 14, 18]))
    sounds.append(dict(clip='Wind_Loop', p=[o[0], 24, o[2]], vol=0.35, minD=4, maxD=45, spatial=1))
    for d, (ry, dx, dz) in DIRS.items():
        nb = neighbor(n, d)
        e = tuple(sorted([n, nb]))
        has_gallery = e in chosen
        is_gate = (n, d) == SEA_GATE
        side = 'Vest_SideOpen' if (has_gallery or is_gate) else 'Vest_SideBlind'
        place(side, o, ry, name=f'{vname}_{d}')
        # lunette light shaft (angled light through the round window)
        shafts.append(dict(p=local(o, ry, 0, 18.2, 10.6), radius=1.9, height=18.0, kind='window', face=ry + 180))
        if is_gate:
            place('SeaGate', o, ry, name='SeaGate')
            statue('Statue_Horse', local(o, ry, -9.2, 1.3, 23.8), ry + 90, 1.5, 'Horse of the Sea Gate')
            statue('Statue_Dragon', local(o, ry, 9.2, 1.3, 23.8), ry - 90, 1.4, 'Guardian beast of the Sea Gate')
            sounds.append(dict(clip='Ocean_Near_Loop', p=local(o, ry, 0, 0, 30), vol=1.0, minD=6, maxD=140, spatial=1))
            emitters.append(dict(kind='season', p=local(o, ry, 0, 30, 30), size=[60, 1, 40], fall=34))
            emitters.append(dict(kind='spray', p=local(o, ry, 0, -0.2, 30), size=[16, 0.2, 1]))
            # invisible barrier at the foot of the stairs (no swimming in the deep sea)
            objects.append(dict(name='SeaBarrier', mesh='', p=local(o, ry, 0, -1.0, 27.0), r=ry, s=[22, 4, 0.5], col='box', stat=True, tag='invisible'))
            objects.append(dict(name='SeaBarrier', mesh='', p=local(o, ry, -11.3, 1.0, 17.0), r=ry, s=[0.5, 4, 12], col='box', stat=True, tag='invisible'))
            objects.append(dict(name='SeaBarrier', mesh='', p=local(o, ry, 11.3, 1.0, 17.0), r=ry, s=[0.5, 4, 12], col='box', stat=True, tag='invisible'))
        elif not has_gallery:
            if (n, d) == CASCADE:
                place('Cascade', local(o, ry, 0, 0, 10.0), ry + 180, col='none', name='Cascade', static=False)
                emitters.append(dict(kind='splash', p=local(o, ry, 0, 0.3, 7.4), size=[3.5, 0.3, 1.0]))
                sounds.append(dict(clip='Cascade_Loop', p=local(o, ry, 0, 2, 7.5), vol=0.9, minD=3, maxD=50, spatial=1))
            else:
                place('Pedestal_Colossal', local(o, ry, 0, 0, 9.6), ry + 180, col='box', name='Colossus_Pedestal')
                big = R.choice(['Statue_WingedFigure', 'Statue_SeatedSage', 'Statue_Beast'])
                statue(big, local(o, ry, 0, 1.75, 9.6), ry + 180, 2.3 if big != 'Statue_SeatedSage' else 2.6)
            # outer-boundary blind sides hear the distant sea
            if not (0 <= nb[0] < 3 and 0 <= nb[1] < 3):
                sounds.append(dict(clip='Ocean_Far_Loop', p=local(o, ry, 0, 6, 13), vol=0.45, minD=5, maxD=40, spatial=1))
    # sand drifted into two corners of some vestibules
    if R.random() < 0.6:
        for k in range(R.choice([1, 2])):
            cx, cz = R.choice([(-8, -8), (8, -8), (-8, 8), (8, 8)])
            place('SandDrift', [o[0] + cx, 0, o[2] + cz], R.uniform(0, 360), (R.uniform(0.6, 0.9), R.uniform(0.6, 1.1), R.uniform(0.6, 0.9)), name='SandDrift')

# ---------------------------------------------------------------- galleries
for e in sorted(chosen):
    a, b = e
    pa, pb = vpos(a), vpos(b)
    c = [(pa[0] + pb[0]) / 2, 0.0, (pa[2] + pb[2]) / 2]
    along_x = a[1] == b[1]
    ry = 90 if along_x else 0
    kind = 'Nave' if e in naves else 'Arcade'
    gname = f'{kind}_{a[0]}{a[1]}_{b[0]}{b[1]}'
    place(kind, c, ry, name=gname)
    probes.append(dict(p=[c[0], 7, c[2]], size=[36, 22, 20] if along_x else [20, 22, 36], name=gname))
    reverbs.append(dict(p=[c[0], 5, c[2]], minD=10, maxD=20, preset='Auditorium' if kind == 'Nave' else 'StoneCorridor'))
    emitters.append(dict(kind='dust', p=local(c, ry, 0, 7, 0), size=[10, 12, 34] if kind == 'Nave' else [8, 10, 34], rot=ry))
    COL_Y = [-15.75 + 4.5 * k for k in range(8)]
    if kind == 'Nave':
        for sx in (-1, 1):
            for z in COL_Y:
                place('Column', local(c, ry, 6 * sx, 0, z), ry, col='capsule', name='Column')
            for k in range(7):
                z = (COL_Y[k] + COL_Y[k + 1]) / 2
                place('Plinth_Square', local(c, ry, 6 * sx, 0, z), ry, col='box', name='Plinth')
                st = FULL[(k + (3 if sx > 0 else 0)) % len(FULL)]
                sc = {'Statue_Dragon': 0.75, 'Statue_Horse': 0.75}.get(st, 0.95)
                statue(st, local(c, ry, 6 * sx, 1.3, z), ry - 90 * sx, sc)
                if k % 2 == 0:  # busts in the wall niches behind
                    statue(BUSTS[(k // 2 + (1 if sx > 0 else 0)) % 3], local(c, ry, 8.35 * sx, 0.6, z), ry - 90 * sx, 1.4)
        for zo in (-9.0, 9.0):
            shafts.append(dict(p=local(c, ry, 0, 20.5, zo), radius=1.5, height=20.5, kind='oculus'))
            emitters.append(dict(kind='season', p=local(c, ry, 0, 20.3, zo), size=[2.5, 0.4, 2.5], fall=20))
        for k in range(7):
            z = (COL_Y[k] + COL_Y[k + 1]) / 2
            for sx in (-1, 1):
                shafts.append(dict(p=local(c, ry, 6.3 * sx, 13.5, z), radius=1.1, height=13.5, kind='window', face=ry - 90 * sx, dim=0.5))
    else:
        bays = [-15.75 + 4.5 * k for k in range(8)]
        for sx in (-1, 1):
            for k, z in enumerate(bays):
                pick = R.random()
                if pick < 0.75:
                    st = R.choice(FULL + ['Statue_Queen'])
                    sc = {'Statue_Dragon': 0.7, 'Statue_Horse': 0.7, 'Statue_Queen': 1.6, 'Statue_SeatedSage': 1.0}.get(st, 1.0)
                    statue(st, local(c, ry, 5.45 * sx, 0.9, z), ry - 90 * sx, sc)
                # free-standing statues on stepped plinths along the corridor (every other bay, staggered)
                if (k + (sx > 0)) % 2 == 0:
                    zz = z + 2.25
                    if abs(zz) < 17:
                        place('Plinth_Round', local(c, ry, 3.2 * sx, 0, zz), R.uniform(0, 360), col='box', name='Plinth')
                        st = R.choice(FULL)
                        sc = {'Statue_Dragon': 0.6, 'Statue_Horse': 0.65}.get(st, 0.85)
                        statue(st, local(c, ry, 3.2 * sx, 1.25, zz), ry - 90 * sx + R.uniform(-25, 25), sc)
        # 3 lanterns per gallery, alternating sides (keeps every mesh under the per-object pixel-light limit)
        for zp, sx in ((-9.0, -1), (0.0, 1), (9.0, -1)):
            lp = local(c, ry, 4.58 * sx, 3.0, zp)
            place('Lantern', lp, ry - 90 * sx, col='none', name='Lantern', static=False)
            lights.append(dict(kind='lantern', p=local(c, ry, 3.95 * sx, 3.35, zp), range=7.0, intensity=1.5, color=[1.0, 0.68, 0.38]))
        for zo in (-9.0, 9.0):
            shafts.append(dict(p=local(c, ry, 0, 14.2, zo), radius=0.75, height=14.2, kind='skylight'))
            emitters.append(dict(kind='season', p=local(c, ry, 0, 14.0, zo), size=[1.4, 0.3, 1.4], fall=14))
    # fallen fragments + sand in some galleries
    for k in range(R.randint(1, 3)):
        m = R.choice(['Fragment_Drum', 'Fragment_Slab'])
        lx = R.uniform(-3, 3); lz = R.uniform(-14, 14)
        if m == 'Fragment_Drum':
            place(m, local(c, ry, lx, 0.42, lz), R.uniform(0, 360), name=m, col='box')
            objects[-1]['lie'] = True
        else:
            place(m, local(c, ry, lx, 0.0, lz), R.uniform(0, 360), (1, 1, 1), name=m, col='box')
    if kind == 'Arcade' and R.random() < 0.5:
        place('SandDrift', local(c, ry, R.choice([-3, 3]), 0, R.choice([-14, 14])), R.uniform(0, 360), (0.7, 0.8, 0.9), name='SandDrift')

# ---------------------------------------------------------------- distant wings of the House across the sea
for k, (dist, ang, w) in enumerate([(380, 200, 'Wing_1'), (520, 250, 'Wing_2'), (450, 300, 'Wing_3'), (650, 160, 'Wing_1'), (700, 320, 'Wing_2'), (600, 20, 'Wing_3'), (560, 110, 'Wing_2')]):
    a = math.radians(ang)
    place(w, [math.sin(a) * dist, -2, math.cos(a) * dist], ang + 90 + R.uniform(-20, 20), (1.6, 1.6, 1.6), col='none', name='DistantWing')

place('Seabed', [0, 0, 0], 0, col='mesh', name='Seabed_Sand')

# global sounds
sounds.append(dict(clip='House_Drone_Loop', p=[0, 0, 0], vol=0.18, spatial=0))
sounds.append(dict(clip='Ocean_Far_Loop', p=[0, 0, 0], vol=0.12, spatial=0))

spawn = dict(p=[vpos((1, 1))[0] - 2.0, 0.1, vpos((1, 1))[2]], r=270)
layout = dict(objects=objects, statues=statues, lights=lights, shafts=shafts, emitters=emitters, probes=probes,
              reverbs=reverbs, sounds=sounds, spawn=spawn, registry=REG,
              house_bounds=[-75, -75, 75, 75])
json.dump(layout, open(os.path.join(OUT, 'HouseLayout.json'), 'w'), indent=1)
print(f'objects {len(objects)}, statues {len(statues)}, lights {len(lights)}, shafts {len(shafts)}, emitters {len(emitters)}, probes {len(probes)}')
