"""Pure-numpy copies of the island and seabed height fields used by kit2.py, so the layout can put things on the
ground (and under the water) without Blender."""
import numpy as np

import math
# v3 (7 x 7 House): the islands sit beyond the exits; positions come from plan7.py
from plan7 import ISLANDS as _PL_ISLANDS, HALF as HOUSE_HALF
ISLANDS = [tuple(i) for i in _PL_ISLANDS]
# v3: the far wings of the House, each standing on its own sand bar with an entrance hall facing the House
# v3 (7 x 7): one far wing beyond each exit, straight out from its gate along the gate's own line (through its isle), so every road
# runs gate -> isle -> far bar -> far hall in one straight line. (distance of the near face from the House centre along the line,
# exit, wing mesh, end-on = the wing's short end faces the House)
from plan7 import EXITS as _EXITS, cell_pos as _cell_pos
_SIDE = {'W': (-1, 0), 'E': (1, 0), 'N': (0, 1), 'S': (0, -1), 'SE': (1, -1), 'NW': (-1, 1)}
def gate_line(exit_):
    """(point on the gate's centre line (x, z), unit outward direction) for an exit."""
    e = _EXITS[exit_]; c = _cell_pos(e['cell']); v = _SIDE[e['side']]; n = math.hypot(*v)
    return (c[0], c[2]), (v[0] / n, v[1] / n)
WINGS = [(440, 'Sea Gate', 'Wing_1', True), (450, 'East Water Stair', 'Wing_3', False), (420, 'Tower Door', 'Wing_2', False),
         (430, 'Aqueduct Arch', 'Wing_3', True), (440, 'Corner Passage', 'Wing_1', True), (430, 'Bird Stair', 'Wing_2', False)]
WING_LEN = {'Wing_1': 0.0, 'Wing_2': 0.0, 'Wing_3': 0.0}      # filled from the meshes (x extent)
WING_DEPTH = 30.0

def wing_frames(lengths):
    """per far wing: pos (wing centre), ry, d (unit vector from the wing toward the House), endon (short end faces the House),
    near (distance from the wing centre to its face toward the House), the sand bar under it, and the far hall in front:
    hall = entrance of the themed far hall (a Sea Hall shell) with its yaw (local +z away from the House)."""
    out = []
    for k, (dist, exit_, w, endon) in enumerate(WINGS):
        (gx, gz), (vx, vz) = gate_line(exit_)
        dx, dz = -vx, -vz; ang = math.degrees(math.atan2(vz, vx)) % 360
        L = lengths.get(w, 160.0)
        near = L / 2 if endon else WING_DEPTH / 2
        t = dist - (gx * vx + gz * vz) + near     # 'dist' is where the wing's near face stands (from the centre, along the line)
        px, pz = gx + vx * t, gz + vz * t
        ry_face = math.degrees(math.atan2(-dx, -dz)) % 360       # local +z away from the House
        ry = (ry_face + 90.0) % 360 if endon else ry_face        # end-on: the long (local x) axis points at the House
        hall_ent = (px + dx * (near + 36.0), pz + dz * (near + 36.0))
        bar_r = (L / 2 + 10.0, WING_DEPTH / 2 + 9.0)
        out.append(dict(pos=(px, pz), ry=ry, d=(dx, dz), bar=(px, pz), radii=bar_r, rot=-ry, mesh=w, name=f'Isle_WingBar_{k}',
                        exit=exit_, bearing=ang, dist=dist, endon=endon, near=near, hall=hall_ent, hall_ry=ry_face, length=L))
    return out

def add_wing_bars(lengths):
    """register the wing sand bars as islands (idempotent)."""
    have = {i[0] for i in ISLANDS}
    for k, f in enumerate(wing_frames(lengths)):
        if f['name'] in have: continue
        ISLANDS.append((f['name'], f['bar'], f['radii'], 0.9, 1.25, 40 + k, f['rot']))
    INDEX.clear(); INDEX.update({n[0]: i for i, n in enumerate(ISLANDS)})
INDEX = {n[0]: i for i, n in enumerate(ISLANDS)}

def _local(x, z, isl):
    cx, cz = isl[1]
    if len(isl) > 6 and isl[6]:
        t = math.radians(isl[6]); c, s = math.cos(t), math.sin(t)
        return (x - cx) * c + (z - cz) * s, -(x - cx) * s + (z - cz) * c
    return x - cx, z - cz

def island_height(x, z, ix):
    name, (cx, cz), (rx, rz), crest, inner, seed = ISLANDS[ix][:6]
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6, 4)
    lx, lz = _local(x, z, ISLANDS[ix])
    ang = np.arctan2(lz, lx)
    wob = 1 + 0.12 * np.sin(ang * 3 + ph[0]) + 0.07 * np.sin(ang * 5 + ph[1])
    d = np.sqrt((lx / (rx * wob)) ** 2 + (lz / (rz * wob)) ** 2)
    h = np.where(d < 1, crest + (inner - crest) * np.clip(1 - d, 0, 1) ** 0.7 * np.clip((1 - d) * 3, 0, 1), crest - (d - 1) * 9)
    h = h + 0.08 * np.sin(x * 0.7 + ph[2]) * np.sin(z * 0.6 + ph[3]) * (d < 1)
    return np.maximum(h, -4.0), d

def seabed_height(x, z):
    dh = np.maximum(np.abs(x), np.abs(z)) - HOUSE_HALF
    d = np.maximum(dh, 0)
    for ix, isl in enumerate(ISLANDS):
        _, (cx, cz), (rx, rz), *_ = isl
        lx, lz = _local(x, z, isl)
        di = np.sqrt((lx / rx) ** 2 + (lz / rz) ** 2) - 1
        d = np.minimum(d, np.maximum(di, 0) * min(rx, rz))
    shelf = -1.6 - 2.2 * np.clip(d / 30, 0, 1) - 10 * np.clip((d - 35) / 120, 0, 1) ** 1.4
    ripple = 0.25 * np.sin(x * 0.21 + np.sin(z * 0.05) * 3) * np.sin(z * 0.17)
    return shelf + ripple

def ground(x, z):
    """Highest solid surface at (x, z): island sand or seabed (the House footprint is not handled here)."""
    h = seabed_height(np.asarray(x, float), np.asarray(z, float))
    for ix in range(len(ISLANDS)):
        hi, d = island_height(np.asarray(x, float), np.asarray(z, float), ix)
        h = np.maximum(h, np.where(d < 1.45, hi, -99))
    return float(h) if np.ndim(h) == 0 else h

def island_d(x, z, name):
    return float(island_height(np.asarray(x, float), np.asarray(z, float), INDEX[name])[1])

def outline(ix, n=72):
    """the island's sand edge (d = 1 of its height field) as world (x, z) points."""
    name, (cx, cz), (rx, rz), crest, inner, seed = ISLANDS[ix][:6]
    r = np.random.default_rng(seed); ph = r.uniform(0, 6, 4)
    t = math.radians(ISLANDS[ix][6]) if len(ISLANDS[ix]) > 6 and ISLANDS[ix][6] else 0.0
    c, s = math.cos(t), math.sin(t)
    pts = []
    for a in np.linspace(0, 2 * math.pi, n, endpoint=False):
        wob = 1 + 0.12 * math.sin(a * 3 + ph[0]) + 0.07 * math.sin(a * 5 + ph[1])
        rr = 1.0 / math.sqrt((math.cos(a) / (rx * wob)) ** 2 + (math.sin(a) / (rz * wob)) ** 2)
        lx, lz = rr * math.cos(a), rr * math.sin(a)
        pts.append((cx + lx * c - lz * s, cz + lx * s + lz * c))
    return pts
