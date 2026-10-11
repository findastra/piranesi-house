"""v3 secret way and the bird stair: ledges up the Colossus, the Climb vine, the castellum and the roof aqueducts that run from
it to every exit (with the ride paths), the ride tube, the stone-jump bird tower with its marble nest and the egg, and the
encampment on the slide's sand bar. Run: python3 gen/kit3d.py [name ...]"""
import os, sys, json, math, numpy as np
from math import pi, sin, cos, sqrt, atan2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import K, AS, NA, bpy, reset, apply, mesh, prism_xz, prism_xy, recalc, cyl, ring_band, finish, balustrade_x, urn, rot_z, MAN, EXTRA, FLOW
from kit3b import worn_block, rock, sweep, uv_export, ribbon, disc_uv
from ivy import read_pms
import plan7 as PL
import islands as IS

rng = np.random.default_rng(4545)
B2U = lambda p: (p[0], p[2], p[1])        # Blender (x, y, z) <-> Unity (x, z, y)

# =====================================================================================================
# 1. ledges up the Colossus (statue-local Unity frame; built in Blender as (x, z, y))
# =====================================================================================================
def colossus_ledges():
    reset()
    P = read_pms('Colossus')[0]
    col = json.load(open(os.path.join(PL.HERE, '..', 'out', 'Data', 'Kit2Extra.json')))['colossus']
    palm = col['palm']
    th_palm = atan2(palm[2], palm[0])
    n = 36; step = math.radians(28); h0, h1 = 0.35, 12.0
    parts = []; ledges = []
    for k in range(n):
        h = h0 + (h1 - h0) * k / (n - 1)
        th = th_palm - step * (n - 1 - k)
        m = np.abs(P[:, 1] - h) < 0.45
        Q = P[m]
        ang = np.arctan2(Q[:, 2], Q[:, 0]); dang = (ang - th + pi) % (2 * pi) - pi
        sel = np.abs(dang) < math.radians(16)
        r = float(np.linalg.norm(Q[sel][:, [0, 2]], axis=1).max()) if sel.any() else 1.6
        if k == n - 1: r = max(r, float(np.hypot(palm[0], palm[2])) + 0.35)
        rc = r + 0.32
        x, z = rc * cos(th), rc * sin(th)
        b = worn_block((0, 0, 0), (0.86, 0.8, 0.24), 600 + k, 'Marble', wear=0.25, chips=2)
        b = apply(b, (0, 0, 0), (0, 0, th + pi / 2))
        parts.append(apply(b, (x, z, h - 0.12)))
        # a little carved bracket under each ledge, into the robe
        br = K.box(-0.18, 0.18, -0.3, 0.3, -0.55, -0.12, 'Marble', 'bracket')
        br = apply(br, (0, 0, 0), (0, 0, th + pi / 2))
        parts.append(apply(br, (x - cos(th) * 0.15, z - sin(th) * 0.15, h)))
        ledges.append([round(x, 3), round(h, 3), round(z, 3)])
    # steps up the back of the pedestal (statue-local -z), floor at y = -1.8
    for i in range(6):
        zf = -4.7 - (6 - i) * 0.36
        parts.append(K.box(-1.6, 1.6, zf, -4.69, -1.8, -1.8 + (i + 1) * 0.3, 'Marble', 'step'))
    finish(parts, 'Colossus_Ledges')
    EXTRA['colossus_ledges'] = ledges
    EXTRA['colossus_ledge_top'] = ledges[-1]
    print('ledges', len(ledges), 'top', ledges[-1])

# =====================================================================================================
# 2. the Climb vine: hangs from the oculus rim beside the raised palm (vine-local: anchor at origin, hangs to -length)
# =====================================================================================================
def climb_vine():
    import ivy3, ivy as IV
    rects = ivy3.leaf_rects()
    try: frects = ivy3.flower_atlas()
    except Exception: frects = [[0, 0, 0.3, 0.3]]
    L = 12.4
    pts = []
    for k in range(int(L / 0.06)):
        t = k * 0.06
        pts.append(np.array([0.05 * sin(t * 1.3), -t, 0.05 * cos(t * 0.9)]))
    main = dict(p=np.array(pts), n=np.tile(np.array([0, 0, -1.0]), (len(pts), 1)), att=np.zeros(len(pts), bool), gen=0, hang=True)
    tw = []
    for j in range(3):            # strands twisted round the main stem
        P = np.array([p + np.array([0.06 * cos(i * 0.21 + j * 2.1), 0, 0.06 * sin(i * 0.21 + j * 2.1)]) for i, p in enumerate(pts)])
        tw.append(dict(p=P, n=main['n'], att=main['att'], gen=1, hang=True))
    side = IV.hang([pts[i] for i in range(10, len(pts) - 20, 18)], rng, length=(0.4, 1.4), face=np.array([0, 0, -1.0]), sway=0.08)
    ivy3.export3('Vine_Climb', [main] + tw + side, rng, rects, frects, MAN, hanging=True,
                 flower_p=0.05, size=(0.08, 0.16), lod=False)
    EXTRA['vine_length'] = L

# =====================================================================================================
# 3. castellum + roof aqueducts to every exit, chutes, and the ride paths (world coords)
# =====================================================================================================
CH_FLOOR = 25.6; CH_W = 3.0; WATER = 26.0
def lat_world(p): return ((p[0] + 0.5 - PL.N // 2) * PL.G, (p[1] + 0.5 - PL.N // 2) * PL.G)

def gallery_hit(x, z, pad=11.5):
    """True if (x, z) lies over a gallery (between two connected halls) or a hall."""
    for (a, b) in PL.MAZE['edges']:
        ax, az = (a[0] - 3) * PL.G, (a[1] - 3) * PL.G; bx, bz = (b[0] - 3) * PL.G, (b[1] - 3) * PL.G
        if az == bz and min(ax, bx) - 1 <= x <= max(ax, bx) + 1 and abs(z - az) < pad: return True
        if ax == bx and min(az, bz) - 1 <= z <= max(az, bz) + 1 and abs(x - ax) < pad: return True
    for i in range(PL.N):
        for j in range(PL.N):
            if abs(x - (i - 3) * PL.G) < 13.5 and abs(z - (j - 3) * PL.G) < 13.5: return True
    return False

def exit_end(name):
    """(chute polyline in world (x, y, z) from the last lattice point, rider exit point, exit yaw)."""
    e = PL.EXITS[name]; c = e['cell']; side = e['side']
    cx, _, cz = PL.cell_pos(c)
    last = lat_world(TUBES[name][-1])
    H = PL.HALF
    if side in ('W', 'E'):
        sgn = -1 if side == 'W' else 1
        gz = cz; wx = sgn * (H + 6.0)
        mid = (last[0] + sgn * 10, WATER - 3, last[1] + (gz - last[1]) * 0.25)
        end = (sgn * (H + 30.0), 0.35, gz + (last[1] - gz) * 0.45)
        exitp = (sgn * (H + 7.0), 0.1, gz + (last[1] - gz) * 0.22); yaw = 90 if sgn > 0 else 270
    elif side == 'N':
        gx = cx
        mid = (last[0] + (gx - last[0]) * 0.25, WATER - 3, last[1] + 10)
        end = (gx + (last[0] - gx) * 0.45, 0.35, H + 30.0)
        exitp = (gx + (last[0] - gx) * 0.22, 0.1, H + 7.0); yaw = 0
    elif side == 'S':           # the tower door: land on the marble tower's pavilion terrace
        tx, tz = cx, -H - 6.5
        mid = ((last[0] + tx) / 2 + 4, 26.6, (last[1] + tz) / 2)
        end = (tx + 3.0, 27.45, tz - 1.0)
        exitp = (tx + 2.0, 27.1, tz - 2.5); yaw = 270
    elif side == 'SE':
        bar = [i for i in PL.ISLANDS if i[0] == 'Isle_CornerBar'][0][1]
        mid = (last[0] + 8, WATER - 4, last[1] - 8)
        end = (bar[0] + 9.0, 0.5, bar[1] - 9.0)
        exitp = (bar[0] + 3.0, IS.ground(bar[0] + 3.0, bar[1] - 3.0) + 0.05, bar[1] - 3.0); yaw = 135
    else:                       # NW: the albatross isle, at the foot of the stone-jump tower
        isl = [i for i in PL.ISLANDS if i[0] == 'Isle_Albatross'][0][1]
        mid = (last[0] - 8, WATER - 4, last[1] + 8)
        end = (isl[0] + 9.0, 1.2, isl[1] - 9.0)
        exitp = (isl[0] + 5.0, IS.ground(isl[0] + 5.0, isl[1] - 5.0) + 0.05, isl[1] - 5.0); yaw = 315
    start = (last[0], WATER, last[1])
    # smooth chute: quadratic through mid, sampled
    P0, P1, P2 = map(np.array, (start, mid, end))
    pts = [tuple((1 - t) ** 2 * P0 + 2 * (1 - t) * t * P1 + t * t * P2) for t in np.linspace(0, 1, 40)]
    return pts, exitp, yaw

TUBES = {k: [tuple(p) for p in v] for k, v in PL.MAZE['tubes'].items()}
def aqueducts():
    reset()
    parts = []
    # unique lattice segments
    segs = set()
    for n, pts in TUBES.items():
        for a, b in zip(pts, pts[1:]): segs.add(tuple(sorted((a, b))))
    for (a, b) in sorted(segs):
        (ax, az), (bx, bz) = lat_world(a), lat_world(b)
        along_x = az == bz
        L = abs(bx - ax) if along_x else abs(bz - az)
        x0 = min(ax, bx); z0 = min(az, bz)
        # arcade wall: Blender coords; local frame along +x from 0..L, then rotate/translate
        wall = K.box(0, L, -CH_W / 2 + 0.25, CH_W / 2 - 0.25, -3.0, CH_FLOOR, 'Wall', 'arcade')
        cuts = []
        t = 4.0
        while t < L - 3.0:
            wx, wz = (x0 + t, az) if along_x else (ax, z0 + t)
            if gallery_hit(wx, wz, pad=11.0):
                # one great arch over the gallery or hall in the way
                t2 = t
                while t2 < L - 1 and gallery_hit((x0 + t2, az)[0] if along_x else ax, az if along_x else z0 + t2, pad=11.0): t2 += 0.5
                span = t2 - t + 6.0
                cuts.append(K.arch_prism(span, max(2.0, 20.5 - span / 2), t + (t2 - t) / 2, -CH_W, CH_W, z0=-3.2, name='big'))
                t = t2 + 5.0
            else:
                cuts.append(K.arch_prism(6.4, 10.5, t + 3.2, -CH_W, CH_W, z0=-3.2, name='a1'))
                cuts.append(K.arch_prism(3.2, 18.0, t + 3.2, -CH_W, CH_W, z0=14.0, name='a2'))
                t += 8.8
        K.boolean(wall, cuts)
        seg_parts = [wall]
        seg_parts.append(K.box(-0.1, L + 0.1, -CH_W / 2, CH_W / 2, CH_FLOOR - 0.5, CH_FLOOR, 'Marble', 'course'))
        for sy in (-1, 1):
            seg_parts.append(K.box(-0.1, L + 0.1, sy * CH_W / 2 - (0.3 if sy > 0 else 0), sy * CH_W / 2 + (0.3 if sy < 0 else 0), CH_FLOOR, CH_FLOOR + 0.9, 'Stone', 'cwall'))
        for p_ in seg_parts:
            if along_x: parts.append(apply(p_, (x0, az, 0)))
            else: parts.append(apply(p_, (ax, z0, 0), (0, 0, pi / 2)))
        # pier caps at the lattice points
    for p in {q for s in segs for q in s}:
        x, z = lat_world(p)
        parts.append(K.box(x - CH_W / 2 - 0.3, x + CH_W / 2 + 0.3, z - CH_W / 2 - 0.3, z + CH_W / 2 + 0.3, -3.0, CH_FLOOR, 'Wall', 'pier'))
    # chutes from the last lattice point of each exit line
    rides = {}
    rr = 0.9
    prof = [(-rr - 0.18, 0.45), (-rr - 0.18, -0.65), (rr + 0.18, -0.65), (rr + 0.18, 0.45), (rr + 0.02, 0.45)]
    prof += [(rr * cos(a), rr * sin(a) * 0.8) for a in np.linspace(0, -pi, 13)] + [(-rr - 0.02, 0.45)]
    B = NA.Builder()
    for n, pts in TUBES.items():
        chute, exitp, yaw = exit_end(n)
        cb = [B2U(q) for q in chute]
        frames = []
        for i in range(len(cb)):
            tg = np.array(cb[min(i + 1, len(cb) - 1)]) - np.array(cb[max(i - 1, 0)]); tg /= np.linalg.norm(tg)
            sd = np.cross(tg, [0, 0, 1.0]); sd /= np.linalg.norm(sd) + 1e-9
            frames.append((sd, np.array([0, 0, 1.0])))
        parts.append(sweep([np.array(q) + np.array([0, 0, -0.05]) for q in cb], prof, 'Marble', 'chute', frames=frames))
        for i in range(0, len(cb) - 2, 4):
            q = cb[i]
            if q[2] < 3: continue
            parts.append(K.lathe([(0.22, -3.0), (0.22, q[2] - 0.75), (0.32, q[2] - 0.7)], 10, 'Marble', name='post'))
            parts[-1] = apply(parts[-1], (q[0], q[1], 0))
        ribbon(B, [np.array(q) + np.array([0, 0, -0.62]) for q in cb], 1.2, 'Flow', side=None, vscale=0.4)
        # ride path (Unity world): castellum basin -> lattice line -> chute
        lat = [lat_world(p) for p in pts]
        path = [(lat[0][0], WATER + 0.25, lat[0][1])]
        for (x, z) in lat[1:]:
            path.append((x, WATER + 0.22, z))
        path += [(q[0], max(q[1] - 0.45, 0.3), q[2]) for q in chute[1:]]
        rides[n] = dict(path=[[round(float(v), 3) for v in p] for p in path], exit=[round(float(v), 3) for v in exitp], exitR=yaw)
    # water in the channels
    for (a, b) in sorted(segs):
        (ax, az), (bx, bz) = lat_world(a), lat_world(b)
        ribbon(B, [B2U((ax, WATER, az)), B2U(((ax + bx) / 2, WATER, (az + bz) / 2)), B2U((bx, WATER, bz))], CH_W - 0.75, 'Flow', side=None, vscale=0.25)
    finish(parts, 'RoofAqueducts')
    uv_export(B, 'RoofAqueductsWater', {'Flow': FLOW})
    # castellum: the water-tower the climb vine brings you to (world position from the maze's castellum lattice point)
    reset()
    cx, cz = lat_world(PL.MAZE['castellum'])
    parts = []
    parts.append(K.lathe([(7.2, -3.0), (7.2, 1.4), (6.8, 1.6), (6.4, 24.6), (7.3, 25.0), (7.6, 25.6), (8.2, 25.75), (8.2, 26.2), (6.2, 26.2),
                          (6.2, 27.1), (5.6, 27.1), (5.6, 25.3), (0.001, 25.3)], 64, 'Wall', name='castellum', cap_bottom=True, cap_top=False))
    for k in range(12):
        a = 2 * pi * k / 12
        parts.append(apply(K.box(-0.45, 0.45, -0.25, 0.25, 1.6, 24.6, 'Marble', 'pil'), (6.6 * cos(a), 6.6 * sin(a), 0), (0, 0, a + pi / 2)))
        fr = K.arch_molding(1.6, 18.0, 0.0, 0.0, 0.1, 0.16, m='Marble', name='blind', legs_to=6.0)
        a2 = a + pi / 12
        parts.append(apply(fr, (6.55 * cos(a2), 6.55 * sin(a2), 0), (0, 0, a2 - pi / 2)))
    # walkway balustrade
    for k in range(24):
        a0 = 2 * pi * k / 24; a1 = a0 + 2 * pi / 24 * 0.8
        for a in np.linspace(a0, a1, 5): parts.append(K3.baluster(8.0 * cos(a), 8.0 * sin(a), 26.2, 0.75))
    parts.append(K.lathe([(7.8, 26.95), (8.2, 26.95), (8.2, 27.15), (7.8, 27.15)], 64, 'Marble', name='rail', cap_top=False, cap_bottom=False))
    finish([p for p in parts if p is not None], 'Castellum', export=False)
    ob = bpy.data.objects['Castellum']; apply(ob, (cx, cz, 0)); K.export_bytes(ob, 'Castellum')
    B = NA.Builder(); disc_uv(B, 0.0, 5.6, 26.75, 'Pool', seg=48, cx=cx, cy=cz)
    uv_export(B, 'CastellumPool', {'Pool': dict(shader='pool', alpha='BLEND')})
    # ride start: each tube waits in the basin near the outlet toward its line
    for n, r in rides.items():
        first = r['path'][1] if len(r['path']) > 1 else r['path'][0]
        d = np.array([first[0] - cx, first[2] - cz]); d /= np.linalg.norm(d) + 1e-9
        k = list(rides).index(n)
        off = np.array([-d[1], d[0]]) * (1.2 if k % 2 else -1.2)
        st = (cx + d[0] * 3.6 + off[0], 26.95, cz + d[1] * 3.6 + off[1])
        r['path'] = [[round(st[0], 3), 26.95, round(st[2], 3)], [round(cx + d[0] * 7.5, 3), WATER + 0.3, round(cz + d[1] * 7.5, 3)]] + r['path'][1:]
    EXTRA['rides'] = rides
    EXTRA['castellum'] = dict(p=[cx, 26.25, cz], walk=[round(cx + 6.9, 3), 26.25, round(cz, 3)])
    print('rides', {k: len(v['path']) for k, v in rides.items()})

def ride_tube():
    B = NA.Builder()
    R0, r0 = 0.52, 0.2; nu, nv = 24, 10
    rings = []; uvs = []
    for i in range(nu + 1):
        a = 2 * pi * i / nu; ring = []; uu = []
        for j in range(nv + 1):
            b = 2 * pi * j / nv
            ring.append(((R0 + r0 * cos(b)) * cos(a), (R0 + r0 * cos(b)) * sin(a), r0 * sin(b) + r0)); uu.append((i / nu * 4, j / nv))
        rings.append(ring); uvs.append(uu)
    B.quad_strip(rings, uvs, 'Tube')
    import kit2 as K2
    uv_export(B, 'RideTube', {'Tube': K2.M('LinenRed', smooth=0.5)})

# =====================================================================================================
# 4. the stone-jump bird tower with the marble nest and the egg (tower-local: base centre at origin, door on -y)
# =====================================================================================================
BT = dict(half=6.0, height=19.0)
def bird_tower():
    reset()
    h = BT['half']; H = BT['height']
    parts = []
    body = K.box(-h, h, -h, h, -2.0, H, 'Wall', 'tower')
    cuts = [K.box(-h + 1.0, h - 1.0, -h + 1.0, h - 1.0, 0.0, H + 0.2, 'Wall', 'core'), K.arch_prism(3.2, 3.6, 0, -h - 0.2, -h + 1.2, z0=0.0, name='door')]
    for ax in ('x', 'y'):
        for c in (-2.6, 2.6):
            for (z0, sp, w) in ((6.0, 9.0, 1.6), (12.0, 15.5, 1.6)):
                cuts.append(K.arch_prism(w, sp, c, -h - 0.2, h + 0.2, z0=z0, axis=ax, name='win'))
    K.boolean(body, cuts); parts.append(body)
    parts.append(K.box(-h + 1.0, h - 1.0, -h + 1.0, h - 1.0, -2.0, 0.0, 'Floor', 'floor'))
    # rusticated base, string courses, cornice, top terrace and parapet
    for (z0, z1, d) in ((0.0, 1.4, 0.25), (5.2, 5.6, 0.32), (11.2, 11.6, 0.32), (H - 0.9, H - 0.4, 0.38), (H - 0.4, H, 0.55)):
        parts.append(K.box(-h - d, h + d, -h - d, h + d, z0, z1, 'Marble' if z0 > 0 else 'Stone', 'band'))
    parts.append(K.box(-h + 1.0, h - 1.0, -h + 1.0, h - 1.0, H - 0.6, H, 'Floor', 'roof'))
    for k in range(4):
        for p in balustrade_x(-h + 0.4, h - 0.4, -h + 0.25, H, posts=[0.0], h=1.0):
            parts.append(apply(p, (0, 0, 0), (0, 0, k * pi / 2)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(K.box(sx * h - (0.6 if sx > 0 else 0), sx * h + (0.6 if sx < 0 else 0), sy * h - (0.6 if sy > 0 else 0), sy * h + (0.6 if sy < 0 else 0), H, H + 1.6, 'Marble', 'ped'))
    # the stone blocks: a jumping stair spiralling up round the outside, each block standing out from the wall on a bracket
    blocks = []
    per = 4 * 2 * h; n = int(H / 0.34) + 1
    s_step = 1.25
    for k in range(n):
        y = 0.45 + k * (H - 0.45) / (n - 1)
        s = (k * s_step) % per
        face = int(s // (2 * h)); u = s % (2 * h) - h
        u = max(-h + 0.7, min(h - 0.7, u))
        out = h + 0.55
        pos = {0: (u, -out), 1: (out, u), 2: (-u, out), 3: (-out, -u)}[face]
        yaw = face * pi / 2
        if k == n - 1: pos = (h - 0.9, -out); yaw = 0
        b = worn_block((0, 0, 0), (0.95, 0.9, 0.3), 1300 + k, 'Stone' if k % 3 else 'Marble', wear=0.3, chips=2)
        b = apply(b, (0, 0, 0), (0, 0, yaw))
        parts.append(apply(b, (pos[0], pos[1], y - 0.15)))
        blocks.append([round(pos[0], 3), round(y, 3), round(pos[1], 3)])
    # last step onto the parapet: a gap in the balustrade
    nest_z = H
    parts.append(K.lathe([(0.001, nest_z), (1.0, nest_z), (1.7, nest_z + 0.15), (2.05, nest_z + 0.55), (2.0, nest_z + 0.75), (1.6, nest_z + 0.62),
                          (1.0, nest_z + 0.4), (0.001, nest_z + 0.35)], 48, 'Marble', name='nest',
                         radial=lambda t, z, r: r * (1 + 0.05 * sin(t * 23 + z * 10) + 0.03 * sin(t * 61))))
    for k in range(40):            # marble twigs woven round the rim
        a = rng.uniform(0, 2 * pi); a2 = a + rng.uniform(0.3, 0.8)
        p0 = (1.95 * cos(a), 1.95 * sin(a), nest_z + 0.55 + rng.uniform(-0.1, 0.1)); p1 = (1.9 * cos(a2), 1.9 * sin(a2), nest_z + 0.6 + rng.uniform(-0.1, 0.15))
        m_ = ((p0[0] + p1[0]) / 2 * 1.08, (p0[1] + p1[1]) / 2 * 1.08, (p0[2] + p1[2]) / 2 + 0.06)
        parts.append(sweep([p0, m_, p1], [(cos(q) * 0.045, sin(q) * 0.045) for q in np.linspace(0, 2 * pi, 6, endpoint=False)], 'Marble', 'twig'))
    finish(parts, 'BirdTower')
    # the egg (smooth, pearly) as a UV mesh
    B = NA.Builder()
    rings = []; uvs = []
    for j in range(33):
        th = pi * j / 32; ring = []; uu = []
        for i in range(49):
            ph = 2 * pi * i / 48
            rz = 0.62 * (1 - 0.18 * cos(th))
            ring.append((rz * sin(th) * cos(ph), rz * sin(th) * sin(ph), 0.95 * (1 - cos(th)) - 0.05)); uu.append((i / 48, j / 32))
        rings.append(ring); uvs.append(uu)
    B.quad_strip(rings[::-1], uvs[::-1], 'Egg')
    uv_export(B, 'GiantEgg', {'Egg': dict(shader='prop', alpha='OPAQUE', albedo='Ivy/Flower_Albedo.png', tint=[1.0, 0.97, 0.9], smooth=1.0, metal=0.35)})
    EXTRA['bird_tower'] = dict(half=h, height=H, blocks=blocks, nest=[0.0, nest_z + 0.38, 0.0])
    print('bird tower blocks', len(blocks))

# =====================================================================================================
# 5. the encampment on the slide's sand bar: tents, a fire ring, log seats, cushions
# =====================================================================================================
def encampment():
    import kit2 as K2
    for nm, col in (('Tent_Cream', 'LinenCream'), ('Tent_Teal', 'LinenTeal')):
        B = NA.Builder()
        L, W, Ht = 3.2, 2.4, 1.9
        for s in (-1, 1):
            B.card((s * W / 2, -L / 2, 0), (s * W / 2, L / 2, 0), (0, L / 2, Ht), (0, -L / 2, Ht), (0, 0, 2, 1.5), col)
            B.card((0, -L / 2, Ht), (0, L / 2, Ht), (s * W / 2, L / 2, 0), (s * W / 2, -L / 2, 0), (0, 0, 2, 1.5), col)
        B.card((-W / 2, L / 2, 0), (W / 2, L / 2, 0), (0, L / 2, Ht), (0, L / 2, Ht), (0, 0, 1, 1), col)
        B.card((W / 2, L / 2, 0), (-W / 2, L / 2, 0), (0, L / 2, Ht), (0, L / 2, Ht), (0, 0, 1, 1), col)
        for y in (-L / 2 - 0.05, L / 2 + 0.05):
            rr = [[(0.03 * cos(a), y + 0.03 * sin(a), z) for a in np.linspace(0, 2 * pi, 6)] for z in (0, Ht + 0.25)]
            B.quad_strip(rr, [[(0, 0)] * 6, [(0, 2)] * 6], 'Planks')
        uv_export(B, nm, {col: K2.M(col, doubleSided=True), 'Planks': K2.M('Planks')})
    reset()
    parts = []
    for k in range(11):
        a = 2 * pi * k / 11
        parts.append(rock((0.8 * cos(a), 0.8 * sin(a), 0.1), (0.22, 0.18, 0.16), 1500 + k, 'Stone'))
    finish(parts, 'FireRing')
    B = NA.Builder()
    for k in range(3):        # logs to sit on
        a = 2 * pi * k / 3 + 0.4; cx_, cy_ = 2.4 * cos(a), 2.4 * sin(a); t = np.array([-sin(a), cos(a), 0])
        rr = [[(cx_ + t[0] * e + 0.22 * cos(q) * cos(a), cy_ + t[1] * e + 0.22 * cos(q) * sin(a), 0.22 + 0.22 * sin(q)) for q in np.linspace(0, 2 * pi, 9)] for e in (-0.9, 0.9)]
        B.quad_strip(rr, [[(q / 6.28, 0) for q in np.linspace(0, 2 * pi, 9)], [(q / 6.28, 2) for q in np.linspace(0, 2 * pi, 9)]], 'Planks')
    for k in range(5):        # firewood in the ring
        a = k * 1.25
        rr = [[(0.45 * cos(a) * e + 0.06 * cos(q) * sin(a), 0.45 * sin(a) * e - 0.06 * cos(q) * cos(a), 0.12 + 0.06 * sin(q) + 0.15 * (1 - abs(e))) for q in np.linspace(0, 2 * pi, 7)] for e in (-1, 1)]
        B.quad_strip(rr, [[(q / 6.28, 0) for q in np.linspace(0, 2 * pi, 7)], [(q / 6.28, 1) for q in np.linspace(0, 2 * pi, 7)]], 'Planks')
    for k in range(4):        # cushions
        a = 2 * pi * k / 4 + 1.1
        B.sphere((3.6 * cos(a), 3.6 * sin(a), 0.12), 0.32, ['LinenRed', 'LinenTeal', 'LinenCream', 'LinenRed'][k], seg=8)
    uv_export(B, 'CampLogs', {'Planks': K2.M('Planks'), 'LinenRed': K2.M('LinenRed'), 'LinenTeal': K2.M('LinenTeal'), 'LinenCream': K2.M('LinenCream')})
    EXTRA['camp'] = dict(logs=[[round(2.4 * cos(2 * pi * k / 3 + 0.4), 3), 0.44, round(2.4 * sin(2 * pi * k / 3 + 0.4), 3)] for k in range(3)])

BUILDERS = {'Ledges': colossus_ledges, 'Vine': climb_vine, 'Aqueducts': aqueducts, 'Tube': ride_tube, 'BirdTower': bird_tower, 'Camp': encampment}
if __name__ == '__main__':
    names = sys.argv[1:] or list(BUILDERS)
    for n in names:
        print('== kit3d', n, flush=True)
        BUILDERS[n]()
        json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1); json.dump(EXTRA, open(K3.EXP, 'w'), indent=1)
    print('kit3d done')
