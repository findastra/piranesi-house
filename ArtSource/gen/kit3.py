"""House v3 kit (redlines 1): richer exterior, tall window halls, gates with sunburst windows and gauntlet torches,
roof water channels and hall fountains, the open marble slide tower, corner exit, isle halls and the sea hall,
the ruin's arches and seats, eroded water stairs, plaques.

Stone parts are modelled in Blender space (Z up) like kit.py and exported as PMS1 (triplanar stone shaders).
Water ribbons are PMS2 with 'flow' manifest entries. Run:  python3 gen/kit3.py [name ...]"""
import os, sys, json, math, numpy as np
from math import pi, sin, cos, sqrt, atan2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit as K
import assets as AS
import nature as NA
import bpy

ROOT = os.path.join(HERE, '..')
DATA = os.path.join(ROOT, 'out', 'Data')
MAN = json.load(open(AS.MANIFEST)) if os.path.exists(AS.MANIFEST) else {}
EXP = os.path.join(DATA, 'Kit3Extra.json')
EXTRA = json.load(open(EXP)) if os.path.exists(EXP) else {}
rng = np.random.default_rng(303)
FLOW = dict(shader='flow', alpha='BLEND')

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def apply(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    ob.location = loc; ob.rotation_euler = rot
    if scale is not None: ob.scale = scale
    with bpy.context.temp_override(active_object=ob, selected_editable_objects=[ob], object=ob):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob

def mesh(V, F, m, name='part', smooth=False, ao=None, sharp=40):
    return K.obj_from(V, F, m, smooth=smooth, ao=ao, name=name, sharp_angle=sharp)

def prism_xz(pts, y0, y1, m, name='prism'):
    """closed polygon in the XZ plane (list of (x, z)), extruded along Y from y0 to y1."""
    p = np.asarray(pts, float); n = len(p)
    V = [(x, y0, z) for x, z in p] + [(x, y1, z) for x, z in p]
    area = sum(p[i, 0] * p[(i + 1) % n, 1] - p[(i + 1) % n, 0] * p[i, 1] for i in range(n))
    a = list(range(n)); b = list(range(n, 2 * n))
    if area > 0: F = [tuple(a), tuple(reversed(b))]
    else: F = [tuple(reversed(a)), tuple(b)]
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, j + n, i + n) if area > 0 else (j, i, i + n, j + n))
    ob = mesh(V, F, m, name)
    ob.data.validate(); ob.data.update()
    # make normals consistent and outward
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
    return ob

def prism_xy(pts, z0, z1, m, name='prism'):
    """closed polygon in the XY plane, extruded along Z."""
    ob = prism_xz(pts, z0, z1, m, name)
    # prism_xz built (x, y, z) = (px, extrude, pz); swap y/z
    for v in ob.data.vertices:
        x, y, z = v.co; v.co = (x, z, y)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
    return ob

def recalc(ob):
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
    return ob

def cyl(x, y, z0, z1, r, m, seg=24, name='cyl'):
    ob = K.lathe([(r, z0), (r, z1)], seg, m, name=name)
    return apply(ob, (x, y, 0))

def arch_outline(w, spring, xc=0.0, z0=0.0, seg=24):
    r = w / 2
    pts = [(xc - r, z0)] + [(xc + r * cos(pi - pi * i / seg), spring + r * sin(pi - pi * i / seg)) for i in range(seg + 1)] + [(xc + r, z0)]
    return pts

def ring_band(cx, cz, r0, r1, a0, a1, y0, y1, m, seg=32, name='band', wobble=None):
    """annular sector in the XZ plane (centre cx, cz), radii r0 < r1, angles a0..a1, extruded y0..y1."""
    th = np.linspace(a0, a1, seg + 1)
    outer = []
    for t in th:
        rr = r1 + (wobble(t) if wobble else 0.0)
        outer.append((cx + rr * cos(t), cz + rr * sin(t)))
    inner = [(cx + r0 * cos(t), cz + r0 * sin(t)) for t in th[::-1]]
    return prism_xz(outer + inner, y0, y1, m, name)

LOD = [False]          # when True, balustrades are solid parapets (distant LOD meshes)

def baluster(x, y, z0, h, m='Marble', seg=6):
    prof = [(0.11, 0), (0.11, 0.06), (0.07, 0.1), (0.06, 0.16), (0.1, 0.3), (0.13, 0.42), (0.1, 0.55), (0.055, 0.66),
            (0.06, 0.7), (0.09, 0.74), (0.09, 0.8)]
    s = h / 0.8
    ob = K.lathe([(r, z * s + z0) for r, z in prof], seg, m, name='bal')
    return apply(ob, (x, y, 0))

def balustrade_x(x0, x1, y, z, m='Marble', depth=0.42, h=1.05, spacing=0.36, posts=()):
    """balustrade running along X centred on y, base at z."""
    parts = [K.box(x0, x1, y - depth / 2, y + depth / 2, z, z + 0.18, m, 'plinth')]
    hb = h - 0.18 - 0.16
    n = max(1, int((x1 - x0 - 0.3) / spacing))
    if LOD[0]:
        parts.append(K.box(x0, x1, y - depth / 2 + 0.08, y + depth / 2 - 0.08, z + 0.18, z + h - 0.16, m, 'solid'))
        n = 0
    for i in range(n):
        x = x0 + 0.15 + (i + 0.5) * (x1 - x0 - 0.3) / n
        if any(abs(x - p) < 0.45 for p in posts): continue
        parts.append(baluster(x, y, z + 0.18, hb, m))
    parts.append(K.box(x0, x1, y - depth / 2 - 0.04, y + depth / 2 + 0.04, z + h - 0.16, z + h, m, 'rail'))
    for p in posts:
        parts.append(K.box(p - 0.28, p + 0.28, y - depth / 2 - 0.05, y + depth / 2 + 0.05, z, z + h + 0.06, m, 'post'))
    return parts

def urn(x, y, z, s=1.0, m='Marble'):
    prof = [(0.22, 0), (0.22, 0.08), (0.12, 0.14), (0.1, 0.22), (0.24, 0.42), (0.3, 0.62), (0.26, 0.82), (0.18, 0.92),
            (0.22, 0.98), (0.12, 1.06), (0.06, 1.2), (0.001, 1.28)]
    ob = K.lathe([(r * s, z + h * s) for r, h in prof], 20, m, name='urn')
    return apply(ob, (x, y, 0))

def half_column(x, y, z0, z1, r, m='Marble', facing=1, seg=24):
    """engaged column (full lathe; the back half hides in the wall), base + shaft + capital."""
    parts = [K.box(x - r * 1.35, x + r * 1.35, y - r * 1.35, y + r * 1.35, z0, z0 + 0.22, m, 'cplinth')]
    parts.append(K.lathe([(r * 1.2, z0 + 0.22), (r * 1.2, z0 + 0.3), (r * 1.05, z0 + 0.38), (r, z0 + 0.45), (r * 0.86, z1 - 0.55),
                          (r * 0.95, z1 - 0.5), (r * 0.9, z1 - 0.45), (r * 1.1, z1 - 0.2), (r * 1.25, z1 - 0.12)], seg, m, name='col'))
    parts[-1] = apply(parts[-1], (x, y, 0))
    parts.append(K.box(x - r * 1.4, x + r * 1.4, y - r * 1.4, y + r * 1.4, z1 - 0.12, z1, m, 'abacus'))
    return parts

def dentils(x0, x1, y, z0, z1, m='Marble', step=0.3, w=0.16, d=0.18):
    out = []
    n = int((x1 - x0) / step)
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        out.append(K.box(x - w / 2, x + w / 2, y, y + d, z0, z1, m, 'dentil'))
    return out

def finish(parts, name, export=True):
    parts = [p for p in parts if p is not None]
    ob = K.join(parts, name)
    if export: K.export_bytes(ob, name)
    return ob

# =====================================================================================================
# 1. window hall wall: three tall windows (redlines 5, 9)
# =====================================================================================================
WIN = [(-3.6, 1.9, 11.0), (0.0, 2.2, 13.0), (3.6, 1.9, 11.0)]      # (x, width, spring) ; sill 0.55

def corner_cutter(end, w=2.6, spring=4.2, z0=0.0):
    """diagonal passage through the corner block at the +x (end=+1) or -x (end=-1) end of a side wall (inner corner
    (10e, 10), outer corner (12e, 12)); width w measured across the passage."""
    c = K.arch_prism(w, spring, 0.0, -4.0, 4.0, z0=z0, name='cornercut')
    # passage axis: Y; rotate so it points along (e, 1)/sqrt2, centred on the corner diagonal
    ang = -pi / 4 * end
    return apply(c, (11.0 * end, 11.0, 0), (0, 0, ang))

def vest_side_window3(name='Vest_SideWindow', cut=0):
    reset()
    wall = K.box(-12, 12, 10, 12, 0, 24, 'Wall', 'wall')
    cuts = [K.arch_prism(w, sp, x, 9.9, 12.1, z0=0.55, name='win') for (x, w, sp) in WIN]
    th = np.linspace(0, 2 * pi, 40, endpoint=False); rw = 2.2; zw = 18.2
    cuts.append(prism_xz([(rw * cos(t), zw + rw * sin(t)) for t in th], 9.9, 12.1, 'Wall', 'lun'))
    if cut: cuts.append(corner_cutter(cut))
    K.boolean(wall, cuts)
    parts = [wall]
    for (x, w, sp) in WIN:
        # inner + outer architraves, sill seat, glazing with leaded mullions
        parts.append(K.arch_molding(w, sp, x, 10.0, 0.18, 0.3, m='Marble', name='av_in', legs_to=0.55))
        parts.append(K.arch_molding(w, sp, x, 12.2, 0.2, 0.32, m='Marble', name='av_out', legs_to=0.55))
        parts.append(K.box(x - w / 2 + 0.02, x + w / 2 - 0.02, 9.92, 11.6, 0.42, 0.58, 'Marble', 'seat'))
        parts.append(K.box(x - w / 2, x + w / 2, 11.55, 11.95, 0.58, 0.82, 'Marble', 'sill'))
        parts.append(K.box(x - w / 2 - 0.3, x + w / 2 + 0.3, 12.0, 12.32, 0.3, 0.55, 'Marble', 'sill_out'))
        top = sp + w / 2
        parts.append(K.box(x - 0.035, x + 0.035, 11.8, 11.9, 0.82, top, 'Iron', 'mv'))
        for z in np.arange(2.2, sp, 1.45):
            parts.append(K.box(x - w / 2, x + w / 2, 11.8, 11.9, z - 0.03, z + 0.03, 'Iron', 'mh'))
        # tracery ring in the arch head
        parts.append(ring_band(x, sp + 0.05, w * 0.22, w * 0.22 + 0.06, 0, 2 * pi, 11.8, 11.9, 'Iron', 24, 'trac'))
        gl = K.arch_prism(w, sp, x, 11.84, 11.86, z0=0.82, name='glass')
        gl.data.materials.clear(); gl.data.materials.append(K.mat('Glass2')); parts.append(gl)
    # centre window: pediment (both faces) ; side windows: sloping hoods falling away from the centre (sketch)
    for (yf, yb) in ((12.0, 12.42), (9.58, 10.0)):
        parts.append(prism_xz([(-1.9, 14.55), (1.9, 14.55), (0.0, 15.75)], yf, yb, 'Marble', 'ped'))
        parts.append(K.box(-1.95, 1.95, yf - (0.05 if yf > 11 else 0), yb + (0.05 if yf > 11 else 0), 14.35, 14.55, 'Marble', 'pedbase'))
        for sx in (-1, 1):
            x = 3.6 * sx; hi, lo = 12.55, 12.0
            xin, xout = x - 1.35 * sx, x + 1.35 * sx
            parts.append(prism_xz([(xin, hi), (xin, hi + 0.22), (xout, lo + 0.22), (xout, lo)], yf, yb, 'Marble', 'hood'))
    parts.append(K.box(-0.32, 0.32, 9.75, 10.05, 13.7, 14.3, 'Gold', 'key'))
    # lunette ring + cross, pilasters (inner face)
    ring = K.lathe([(2.2, 0.0), (2.55, 0.0), (2.6, 0.15), (2.2, 0.15)], 48, 'Marble', name='winring', cap_top=False, cap_bottom=False)
    parts.append(apply(ring, (0, 10.0, zw), (pi / 2, 0, 0)))
    parts.append(K.box(-0.06, 0.06, 10.8, 11.0, zw - 2.2, zw + 2.2, 'Iron', 'mull1'))
    parts.append(K.box(-2.2, 2.2, 10.8, 11.0, zw - 0.06, zw + 0.06, 'Iron', 'mull2'))
    for sx in (-1, 1):
        x0 = sx * 7.2
        if cut == sx: continue          # the corner passage replaces this pilaster's neighbourhood
        parts.append(K.box(x0 - 0.7, x0 + 0.7, 9.65, 10.0, 0, 11.8, 'Marble', 'pil'))
        parts.append(K.box(x0 - 0.85, x0 + 0.85, 9.5, 10.0, 11.8, 12.3, 'Marble', 'pilcap'))
    if cut > 0:                       # one frame per corner (the -x variant shares the same corner)
        parts += corner_portal_inner(cut)
    finish(parts, name)
    EXTRA['window_seats'] = [[x, 0.58, 10.75] for (x, w, sp) in WIN]

def corner_portal_inner(end):
    """moulded frame around the diagonal corner passage, on the inner (room) side."""
    parts = []
    fr = K.arch_molding(2.6, 4.2, 0.0, 0.0, 0.18, 0.32, m='Marble', name='cfr', legs_to=0.0)
    # arch_molding builds on y=0 face protruding -y: rotate to face the room diagonal
    ang = -pi / 4 * end
    d = np.array([end, 1.0]) / sqrt(2)
    c = np.array([10.0 * end, 10.0]) - d * 0.02
    parts.append(apply(fr, (c[0], c[1], 0), (0, 0, ang)))
    key = K.box(-0.28, 0.28, -0.3, 0.05, 5.15, 5.75, 'Gold', 'ckey')
    parts.append(apply(key, (c[0], c[1], 0), (0, 0, ang)))
    return parts

# =====================================================================================================
# 2. gate side: grand sunburst window, scalloped trim, aedicule (redlines 1, 7)
# =====================================================================================================
def scallop_arch(w, spring, r_in, r_out, amp, lobes, yface, depth, m='Marble', legs_to=1.2, seg=96):
    """arch-following band whose outer edge is scalloped (cusped lobes), with plain legs."""
    r = w / 2
    pts_out = []; pts_in = []
    # left leg (bottom -> spring), arc, right leg
    for z in np.linspace(legs_to, spring, 6):
        pts_out.append((-r - r_out, z)); pts_in.append((-r - r_in, z))
    for i in range(seg + 1):
        t = pi - pi * i / seg
        lob = amp * abs(sin(lobes * (pi - t) / 2 * 2)) ** 0.6
        pts_out.append(((r + r_out + lob) * cos(t), spring + (r + r_out + lob) * sin(t)))
        pts_in.append(((r + r_in) * cos(t), spring + (r + r_in) * sin(t)))
    for z in np.linspace(spring, legs_to, 6):
        pts_out.append((r + r_out, z)); pts_in.append((r + r_in, z))
    poly = pts_out + pts_in[::-1]
    return prism_xz(poly, yface, yface + depth, m, 'scallop')

def vest_side_gate():
    reset()
    wall = K.box(-12, 12, 10, 12, 0, 24, 'Wall', 'wall')
    zc, R = 14.4, 4.6
    win = [(-R, zc)] + [(R * cos(pi - pi * i / 40), zc + R * sin(pi - pi * i / 40)) for i in range(41)] + [(R, zc)]
    cuts = [K.arch_prism(10, 7, 0, 9.9, 12.1, name='arch'), prism_xz(win, 9.9, 12.1, 'Wall', 'sun')]
    K.boolean(wall, cuts)
    parts = [wall]
    # inner face (as the plain open side)
    parts.append(K.arch_molding(10, 7, 0, 10.0, 0.25, 0.55, m='Marble', name='archivolt_in'))
    parts.append(K.box(-0.5, 0.5, 9.7, 12.3, 11.7, 12.9, 'Gold', 'keystone'))
    for sx in (-1, 1):
        x0 = sx * 7.2
        parts.append(K.box(x0 - 0.7, x0 + 0.7, 9.65, 10.0, 0, 11.8, 'Marble', 'pil'))
        parts.append(K.box(x0 - 0.85, x0 + 0.85, 9.55, 10.0, 0, 0.5, 'Marble', 'pilbase'))
        parts.append(K.box(x0 - 0.85, x0 + 0.85, 9.5, 10.0, 11.8, 12.3, 'Marble', 'pilcap'))
    # sunburst window: spokes, inner fan ring, frame rings (both faces)
    for k in range(1, 10):
        a = pi * k / 10
        L = R - 0.1
        sp = K.box(1.65, L, -0.25, 0.25, -0.09, 0.09, 'Marble', 'spoke')
        parts.append(apply(sp, (0, 11.0, zc), (0, -a, 0)))
    parts.append(ring_band(0, zc, 1.55, 1.75, 0, pi, 10.9, 11.1, 'Marble', 32, 'fan'))
    parts.append(K.box(-R, R, 10.0, 12.0, zc - 0.2, zc + 0.05, 'Marble', 'sill'))
    for (y0, y1) in ((12.0, 12.35), (9.65, 10.0)):
        parts.append(ring_band(0, zc, R, R + 0.55, 0, pi, y0, y1, 'Marble', 40, 'wframe'))
    gl = prism_xz(win, 11.4, 11.42, 'Glass2', 'sunglass'); parts.append(gl)
    # outside: sunburst glory of gilded rays around the frame
    for k in range(1, 18):
        a = pi * k / 18
        L = 1.4 if k % 2 else 2.3
        ray = prism_xz([(R + 0.6, -0.12), (R + 0.6 + L, 0.0), (R + 0.6, 0.12)], 12.0, 12.12, 'Gold', 'ray')
        parts.append(apply(ray, (0, 0, zc), (0, -a, 0)))
    # scalloped 'fancy trim' around the arch + plain archivolt + great keystone
    parts.append(scallop_arch(10, 7, 0.0, 0.95, 0.32, 9, 12.0, 0.26, 'Marble', legs_to=1.0))
    parts.append(K.arch_molding(10, 7, 0, 12.48, 0.22, 0.38, m='Marble', name='archivolt_out', legs_to=1.0))
    parts.append(prism_xz([(-0.55, 11.6), (0.55, 11.6), (0.8, 13.2), (-0.8, 13.2)], 12.0, 12.75, 'Gold', 'bigkey'))
    # aedicule: paired engaged columns on pedestals, entablature
    for sx in (-1, 1):
        for xc in (6.45, 8.65):
            x = xc * sx
            parts.append(K.box(x - 0.75, x + 0.75, 12.0, 12.95, 0.0, 1.25, 'Marble', 'ped'))
            parts.append(K.box(x - 0.82, x + 0.82, 12.0, 13.02, 1.15, 1.32, 'Marble', 'pedcap'))
            parts += half_column(x, 12.45, 1.32, 12.55, 0.48, 'Marble')
    parts.append(K.box(-9.55, 9.55, 12.0, 13.05, 12.55, 13.05, 'Marble', 'architrave'))
    parts.append(K.box(-9.55, 9.55, 12.0, 12.98, 13.05, 13.55, 'Gold', 'frieze'))
    parts.append(K.box(-9.75, 9.75, 12.0, 13.25, 13.55, 13.75, 'Marble', 'cornice1'))
    parts.append(K.box(-9.95, 9.95, 12.0, 13.45, 13.75, 14.0, 'Marble', 'cornice2'))
    parts += dentils(-9.5, 9.5, 13.05, 13.4, 13.55, 'Marble', 0.32, 0.16, 0.18)
    finish(parts, 'Vest_SideGate')
    EXTRA['gate_torches'] = [[7.55 * s, 5.0, 12.0] for s in (-1, 1)]      # unity local (x, y, z) on the outer face

def gate_torch():
    """bronze gauntlet holding a torch out from the wall. Local: wall at y=0, projecting +y; flame tip near z=1.15."""
    reset()
    parts = [K.box(-0.18, 0.18, 0.0, 0.06, -0.3, 0.3, 'Gold', 'plate')]
    # forearm (tapered, angled up 25 deg), cuff ring
    arm = K.lathe([(0.075, 0.0), (0.09, 0.05), (0.085, 0.3), (0.07, 0.48), (0.075, 0.52)], 12, 'Gold', name='arm')
    parts.append(apply(arm, (0, 0.04, -0.05), (-pi / 2 + 0.44, 0, 0)))
    cuff = K.lathe([(0.11, 0.0), (0.12, 0.02), (0.12, 0.08), (0.1, 0.1)], 12, 'Gold', name='cuff')
    parts.append(apply(cuff, (0, 0.06, -0.04), (-pi / 2 + 0.44, 0, 0)))
    # fist gripping the shaft (a squashed sphere with knuckle bumps)
    fist = K.lathe([(0.001, -0.08), (0.07, -0.07), (0.1, -0.02), (0.1, 0.04), (0.07, 0.08), (0.001, 0.09)], 12, 'Gold', name='fist')
    parts.append(apply(fist, (0, 0.5, 0.18)))
    for k in range(4):
        kn = K.lathe([(0.001, -0.03), (0.03, -0.02), (0.03, 0.02), (0.001, 0.03)], 8, 'Gold', name='kn')
        parts.append(apply(kn, (-0.06 + k * 0.04, 0.58, 0.2 + 0.01 * (k % 2))))
    # torch shaft + cup
    parts.append(cyl(0, 0.5, -0.25, 0.62, 0.035, 'Iron', 10, 'shaft'))
    cup = K.lathe([(0.04, 0.6), (0.12, 0.72), (0.15, 0.8), (0.13, 0.82), (0.08, 0.74), (0.001, 0.74)], 14, 'Gold', name='cup')
    parts.append(apply(cup, (0, 0.5, 0)))
    parts.append(cyl(0, 0.5, 0.74, 0.8, 0.11, 'Iron', 10, 'coals'))
    finish(parts, 'GateTorch')
    EXTRA['torch_flame'] = [0.0, 0.95, 0.5]   # unity local (x, y, z)

# =====================================================================================================
# 3. exterior decor for vestibule faces: rustication, pilasters, string course, cornice, balustrade, urns
# =====================================================================================================
def vest_ext(kind, cut=0):
    """outer face at y=12 (Blender). kind: window | blind | gallery | gate | tower | cascade."""
    reset()
    parts = []
    full = kind in ('window', 'blind', 'cascade')
    gap = {'window': [(-4.75, 4.75)], 'cascade': [(-1.9, 1.9)], 'tower': [(-6.9, 6.9)]}.get(kind, [])
    def runs(x0, x1, gaps):
        segs = [(x0, x1)]
        for g0, g1 in gaps:
            nxt = []
            for a, b in segs:
                if g1 <= a or g0 >= b: nxt.append((a, b)); continue
                if g0 > a: nxt.append((a, g0))
                if g1 < b: nxt.append((g1, b))
            segs = nxt
        return [(a, b) for a, b in segs if b - a > 0.3]
    lo_gap = [(-10.4, 10.4)] if kind == 'gallery' else gap
    if kind == 'gate': lo_gap = [(-9.9, 9.9)]
    if kind == 'tower': lo_gap = [(-6.9, 6.9)]
    if cut: lo_gap = lo_gap + [((8.0 if cut > 0 else -12.5), (12.5 if cut > 0 else -8.0))]
    # rusticated base with banded joints
    for a, b in runs(-12.0, 12.0, lo_gap):
        parts.append(K.box(a, b, 12.0, 12.28, 0.0, 1.55, 'Stone', 'rust'))
        parts.append(K.box(a, b, 12.0, 12.36, 1.55, 1.78, 'Marble', 'rustcap'))
        for z in (0.5, 1.02):
            parts.append(K.box(a, b, 12.0, 12.31, z - 0.03, z + 0.03, 'Stone', 'band'))
    # string course at the arch-head level
    if kind in ('window', 'blind', 'cascade'):
        sc_gap = [(-2.9, 2.9)]          # the lunette window (r 2.2 + ring) sits right above
        for a, b in runs(-12.0, 12.0, sc_gap):
            parts.append(K.box(a, b, 12.0, 12.24, 15.9, 16.25, 'Marble', 'string'))
            parts.append(K.box(a, b, 12.0, 12.32, 16.25, 16.4, 'Marble', 'string2'))
    # giant pilasters (full height at the corners; mid pair where nothing else is)
    pil = [-11.4, 11.4]
    if kind in ('window', 'blind', 'cascade'): pil += [-6.6, 6.6]
    if cut: pil = [p for p in pil if not (p * cut > 0 and abs(p) > 10)]
    for x in pil:
        z0 = 1.78 if (kind not in ('gallery', 'gate', 'tower') or abs(x) > 11) else 17.8
        parts.append(K.box(x - 0.55, x + 0.55, 12.0, 12.3, z0, 22.3, 'Marble', 'pil'))
        parts.append(K.box(x - 0.68, x + 0.68, 12.0, 12.4, z0, z0 + 0.35, 'Marble', 'pilbase'))
        parts.append(K.box(x - 0.68, x + 0.68, 12.0, 12.42, 21.95, 22.35, 'Marble', 'pilcap'))
        parts.append(K.box(x - 0.6, x + 0.6, 12.0, 12.36, 21.6, 21.95, 'Gold', 'pilneck'))
    # panels and medallion on blind faces
    if kind == 'blind':
        for (x0, x1, z0, z1) in ((-4.6, 4.6, 3.2, 13.6), (-10.1, -7.6, 3.2, 13.6), (7.6, 10.1, 3.2, 13.6)):
            for (a, b, c, d) in ((x0, x1, z0, z0 + 0.2), (x0, x1, z1 - 0.2, z1), (x0, x0 + 0.2, z0, z1), (x1 - 0.2, x1, z0, z1)):
                parts.append(K.box(a, b, 12.0, 12.14, c, d, 'Marble', 'panel'))
        parts.append(ring_band(0, 9.5 - 1.2, 1.5, 1.85, 0, 2 * pi, 12.0, 12.2, 'Marble', 40, 'medal'))
        parts.append(ring_band(0, 9.5 - 1.2, 0.0, 1.5, 0, 2 * pi, 12.0, 12.06, 'Gold', 40, 'medalc'))
    # cornice: architrave, frieze, dentils, corona, cyma
    for a, b in runs(-12.25, 12.25, [(-6.9, 6.9)] if kind == 'tower' else []):
        parts.append(K.box(a, b, 12.0, 12.2, 22.35, 22.85, 'Marble', 'arch'))
        parts.append(K.box(a, b, 12.0, 12.12, 22.85, 23.3, 'Wall', 'frieze'))
        parts += dentils(a + 0.1, b - 0.1, 12.12, 23.3, 23.5, 'Marble', 0.34, 0.17, 0.22)
        parts.append(K.box(a, b, 12.0, 12.5, 23.5, 23.72, 'Marble', 'corona'))
        parts.append(K.box(a, b, 12.0, 12.7, 23.72, 24.0, 'Marble', 'cyma'))
        # balustrade on the parapet
        posts = [p for p in (-11.4, -6.6, 6.6, 11.4) if a + 0.3 < p < b - 0.3]
        parts += balustrade_x(a + 0.05, b - 0.05, 12.2, 24.0, posts=posts)
    # urn finials on the posts (corner urn only at the +x end so corners are not doubled)
    for p in ((-6.6, 6.6) if kind not in ('tower', 'gallery', 'gate') else ()) + ((11.6,) if not cut > 0 else ()):
        parts.append(urn(p, 12.2, 25.11, 0.9))
    ob = finish(parts, 'tmp', export=False)
    if cut:
        K.boolean(ob, [corner_cutter(cut, w=2.6, spring=4.2)])
    return ob

def all_vest_ext():
    for lod in (False, True):
        LOD[0] = lod; sfx = '_LOD1' if lod else ''
        for kind in ('window', 'blind', 'gallery', 'gate', 'tower', 'cascade'):
            ob = vest_ext(kind); nm = 'VestExt_' + kind.capitalize() + sfx; ob.name = nm; K.export_bytes(ob, nm)
        for cut, suf in ((1, 'CutR'), (-1, 'CutL')):
            ob = vest_ext('window', cut); nm = 'VestExt_Window_' + suf + sfx; ob.name = nm; K.export_bytes(ob, nm)
    LOD[0] = False

# =====================================================================================================
# 4. drum + ribbed dome + oculus well + lantern (replaces the low saucer from outside)
# =====================================================================================================
def vest_dome(rtop=3.4, lantern=True, name='Vest_Dome'):
    reset()
    parts = []
    Rd = 10.4; zb = 24.0; zt = 29.2
    # drum with blind arcades and pilasters
    drum = K.lathe([(Rd, zb), (Rd, zt)], 64, 'Wall', name='drum', cap_top=False, cap_bottom=False)
    parts.append(drum)
    parts.append(K.lathe([(Rd + 0.35, zb), (Rd + 0.35, zb + 0.6), (Rd + 0.15, zb + 0.75), (Rd, zb + 0.75)], 64, 'Marble', name='drumbase', cap_top=False, cap_bottom=False))
    parts.append(K.lathe([(Rd, zt - 0.6), (Rd + 0.3, zt - 0.5), (Rd + 0.5, zt - 0.2), (Rd + 0.5, zt), (Rd - 0.2, zt)], 64, 'Marble', name='drumcorn', cap_top=False, cap_bottom=False))
    nb = 16
    for k in range(nb):
        a = 2 * pi * k / nb
        p = K.box(-0.32, 0.32, -0.12, 0.25, zb + 0.75, zt - 0.6, 'Marble', 'dpil')
        parts.append(apply(p, (Rd * cos(a), Rd * sin(a), 0), (0, 0, a + pi / 2)))
        # recessed arch panel between pilasters (applied frame)
        a2 = a + pi / nb
        fr = K.arch_molding(1.7, zb + 2.6, 0.0, 0.0, 0.1, 0.16, m='Marble', name='dfr', legs_to=zb + 0.9)
        parts.append(apply(fr, (Rd * cos(a2), Rd * sin(a2), 0), (0, 0, a2 - pi / 2)))
    # ribbed dome (spherical cap) from the drum top to the oculus well
    Rs = 12.0; zc0 = zt - sqrt(Rs ** 2 - (Rd - 0.2) ** 2)
    a0 = math.asin((zt - zc0) / Rs)
    a1 = math.acos(rtop / Rs)
    prof = [((Rs) * cos(a), zc0 + Rs * sin(a)) for a in np.linspace(a0, a1, 18)]
    ztop = prof[-1][1]
    parts.append(K.lathe(prof, 64, 'Wall', name='dome', cap_top=False, cap_bottom=False))
    # ribs
    for k in range(16):
        a = 2 * pi * k / 16
        V = []; F = []
        pts = [((Rs + 0.22) * cos(t), zc0 + (Rs + 0.22) * sin(t)) for t in np.linspace(a0, a1, 16)]
        for (r, z) in pts:
            for (dr, dw) in ((-0.3, -0.2), (0.0, -0.2), (0.0, 0.2), (-0.3, 0.2)):
                V.append(((r + dr) * cos(a) - dw * sin(a), (r + dr) * sin(a) + dw * cos(a), z))
        n = len(pts)
        for i in range(n - 1):
            for j in range(4):
                aa = i * 4 + j; bb = i * 4 + (j + 1) % 4
                F.append((aa, bb, bb + 4, aa + 4))
        F.append((3, 2, 1, 0)); F.append(((n - 1) * 4, (n - 1) * 4 + 1, (n - 1) * 4 + 2, (n - 1) * 4 + 3))
        parts.append(recalc(mesh(V, F, 'Marble', 'rib')))
    # oculus well (open to the sky) from the inner oculus up through the dome, and a colonnetted lantern ring
    well_r = 3.0 if lantern else rtop - 0.4
    parts.append(K.lathe([(well_r, 26.75 if lantern else ztop - 1.2), (well_r, ztop + 0.1)], 40, 'Marble', name='well', cap_top=False, cap_bottom=False))
    if lantern:
        parts.append(K.lathe([(3.0, ztop + 0.1), (rtop + 0.6, ztop + 0.1), (rtop + 0.6, ztop + 0.45), (3.0, ztop + 0.45)], 40, 'Marble', name='lring', cap_top=False, cap_bottom=False))
        for k in range(12):
            a = 2 * pi * k / 12
            parts.append(cyl((rtop + 0.25) * cos(a), (rtop + 0.25) * sin(a), ztop + 0.45, ztop + 2.0, 0.13, 'Marble', 10, 'colonnette'))
        parts.append(K.lathe([(3.0, ztop + 2.0), (rtop + 0.75, ztop + 2.0), (rtop + 0.75, ztop + 2.35), (3.0, ztop + 2.35)], 40, 'Marble', name='lcap', cap_top=False, cap_bottom=False))
        parts.append(K.lathe([(rtop + 0.6, ztop + 2.35), (rtop + 0.45, ztop + 2.6), (3.0, ztop + 2.6)], 40, 'Gold', name='lcrown', cap_top=False, cap_bottom=False))
    else:                                  # broken open to the sky (the Stormscape): a plain lip round the hole
        parts.append(K.lathe([(well_r, ztop + 0.1), (rtop + 0.4, ztop + 0.1), (rtop + 0.4, ztop + 0.4), (well_r, ztop + 0.4)], 48, 'Marble', name='lip', cap_top=False, cap_bottom=False))
    # roof terrace between drum and parapet (covers the old square roof ring)
    nth = 64; Vr = []; Fr = []
    for k in range(nth):
        t = 2 * pi * k / nth; c, s_ = cos(t), sin(t); m_ = max(abs(c), abs(s_))
        Vr.append((Rd * c, Rd * s_, zb + 0.02)); Vr.append((12.0 * c / m_, 12.0 * s_ / m_, zb + 0.02))
    for k in range(nth):
        a = 2 * k; b = 2 * ((k + 1) % nth); Fr.append((a, a + 1, b + 1, b))
    parts.append(mesh(Vr, Fr, 'Floor', 'terrace'))
    finish(parts, name)
    if lantern: EXTRA['dome_top'] = ztop + 2.6


# =====================================================================================================
# 5. galleries: nave with tall windows + open oculi, exterior decor, flat arcade roof, roof water channels
# =====================================================================================================
def rot_z(ob, a):
    return apply(ob, (0, 0, 0), (0, 0, a))

def along_y(parts_fn):
    """build with a function that works along X at y, then rotate 90 deg so it runs along Y (x -> y, y -> -x)."""
    ps = parts_fn()
    return [rot_z(p, pi / 2) for p in ps]

NAVE_WIN = dict(z0=5.8, spring=9.55, w=1.3)
def nave3():
    reset()
    COL_Y = K.COL_Y
    bays = [(COL_Y[k] + COL_Y[k + 1]) / 2 for k in range(7)]
    parts = [K.box(-10, 10, -18, 18, -8, 0, 'Floor', 'floor')]
    for sx in (-1, 1):
        w = K.box(8 if sx > 0 else -10, 10 if sx > 0 else -8, -18, 18, 0, 16.5, 'Wall', 'wall')
        cuts = []
        for yc in bays:
            cuts.append(K.arch_prism(2.0, 4.0, yc, 7.9 if sx > 0 else -8.9, 8.9 if sx > 0 else -7.9, z0=0.6, axis='y', name='niche'))
            cuts.append(K.arch_prism(NAVE_WIN['w'], NAVE_WIN['spring'], yc, 7.9 if sx > 0 else -10.1, 10.1 if sx > 0 else -7.9, z0=NAVE_WIN['z0'], axis='y', name='win'))
        K.boolean(w, cuts); parts.append(w)
        parts.append(K.box(6.45 if sx > 0 else -8, 8 if sx > 0 else -6.45, -18, 18, 10.6, 12.4, 'Marble', 'aisleceil'))
        def bx(a, b, z0, z1, m, nm):
            lo, hi = (a, b) if sx > 0 else (-b, -a)
            return K.box(lo, hi, -18, 18, z0, z1, m, nm)
        parts.append(bx(5.45, 6.55, 10.6, 10.85, 'Marble', 'arch1'))
        parts.append(bx(5.38, 6.55, 10.85, 11.25, 'Marble', 'arch2'))
        parts.append(bx(5.42, 6.55, 11.25, 11.85, 'Gold', 'frieze'))
        parts.append(bx(5.2, 6.55, 11.85, 12.0, 'Marble', 'corn1'))
        parts.append(bx(4.95, 6.55, 12.0, 12.25, 'Marble', 'corn2'))
        parts.append(bx(4.85, 6.55, 12.25, 12.4, 'Gold', 'corn3'))
        att = bx(6.0, 6.55, 12.4, 14.6, 'Wall', 'attic')
        K.boolean(att, [K.box(5.9 if sx > 0 else -6.65, 6.65 if sx > 0 else -5.9, yc - 1.3, yc + 1.3, 12.8, 14.25, 'Wall', 'wcut') for yc in bays])
        parts.append(att)
        for yc in bays:
            lo, hi = (6.35, 6.4) if sx > 0 else (-6.4, -6.35)
            parts.append(K.box(lo, hi, yc - 1.3, yc + 1.3, 12.8, 14.25, 'Glass', 'glass'))
            parts.append(K.box(lo - 0.03, hi + 0.03, yc - 0.05, yc + 0.05, 12.8, 14.25, 'Iron', 'm'))
            # tall aisle window: glazing near the outer face, leaded bars, inner + outer mouldings
            xg = 9.82 * sx
            g = K.arch_prism(NAVE_WIN['w'], NAVE_WIN['spring'], yc, xg - 0.01, xg + 0.01, z0=NAVE_WIN['z0'] + 0.15, axis='y', name='glass2')
            g.data.materials.clear(); g.data.materials.append(K.mat('Glass2')); parts.append(g)
            parts.append(K.box(xg - 0.04, xg + 0.04, yc - 0.03, yc + 0.03, NAVE_WIN['z0'] + 0.15, NAVE_WIN['spring'] + 0.65, 'Iron', 'wmv'))
            for z in (7.0, 8.3):
                parts.append(K.box(xg - 0.04, xg + 0.04, yc - 0.65, yc + 0.65, z - 0.03, z + 0.03, 'Iron', 'wmh'))
            for (xf, d) in ((8.0, 0.14), (10.16, 0.16)):
                mo = K.arch_molding(NAVE_WIN['w'], NAVE_WIN['spring'], 0, 0.0, d, 0.24, m='Marble', name='wm', legs_to=NAVE_WIN['z0'])
                mo = apply(mo, (xf * sx, yc, 0), (0, 0, pi / 2 if sx > 0 else -pi / 2))
                parts.append(mo)
            parts.append(K.box(min(8.0, 10.3) * sx if sx > 0 else -10.3, 10.3 if sx > 0 else -8.0, yc - 0.85, yc + 0.85, NAVE_WIN['z0'] - 0.18, NAVE_WIN['z0'], 'Marble', 'wsill'))
        parts.append(bx(5.85, 6.55, 14.4, 14.6, 'Marble', 'springcourse'))
    ribs = [(y, 0.7) for y in COL_Y]
    parts.append(K.barrel_vault(6.0, 14.6, -18, 18, 'Marble', coffer=True, ribs=ribs, oculi=[(-9.0, 1.6), (9.0, 1.6)], name='vault', extrados=False))
    for yo in (-9.0, 9.0):
        parts.append(K.oculus_ring(1.6, 14.6 + 6.0 - 0.02, yo, 'Gold', 'ocring'))
    # outer roof shell with the two oculi open to the sky (+ short light wells and curbs)
    Ro = 6.9; nu = 33; ys = np.linspace(-18, 18, 49)
    V = []; keep = []
    for y in ys:
        for k in range(nu):
            a = pi * k / (nu - 1); x = -Ro * cos(a); z = 14.6 + Ro * sin(a)
            V.append((x, y, z)); keep.append(not any((y - yo) ** 2 + x * x < 1.75 ** 2 for yo in (-9.0, 9.0)))
    keep = np.array(keep).reshape(len(ys), nu)
    F = [(j * nu + i, j * nu + i + 1, (j + 1) * nu + i + 1, (j + 1) * nu + i) for j in range(len(ys) - 1) for i in range(nu - 1)
         if keep[j, i] and keep[j, i + 1] and keep[j + 1, i] and keep[j + 1, i + 1]]
    parts.append(mesh(V, F, 'Wall', 'roof', smooth=True))
    for yo in (-9.0, 9.0):
        parts.append(K.lathe([(1.6, 20.5), (1.6, 21.9)], 32, 'Marble', name='well', cap_top=False, cap_bottom=False))
        parts[-1] = apply(parts[-1], (0, yo, 0))
        parts.append(apply(K.lathe([(1.6, 21.9), (2.3, 21.9), (2.3, 22.35), (1.6, 22.35)], 32, 'Marble', name='curb', cap_top=False, cap_bottom=False), (0, yo, 0)))
    parts += K.end_caps(10, 21.5)
    finish(parts, 'Nave')

def gallery_ext(kind):
    """kind 'nave' (walls x=+-10, top 16.5) or 'arcade' (walls x=+-7, top 15.5)."""
    reset()
    X = 10.0 if kind == 'nave' else 7.0; TOP = 16.5 if kind == 'nave' else 15.5
    pil_y = list(K.COL_Y) if kind == 'nave' else [-18 + 4.5 * k for k in range(1, 8)]
    parts = []
    for sx in (-1, 1):
        def bx(a, b, y0, y1, z0, z1, m, nm):
            lo, hi = (X + a, X + b) if sx > 0 else (-X - b, -X - a)
            return K.box(lo, hi, y0, y1, z0, z1, m, nm)
        rz = 1.55 if kind == 'nave' else 0.66          # arcades: stay under the window-bay sills (z 0.9)
        parts.append(bx(0, 0.28, -18, 18, 0.0, rz, 'Stone', 'rust'))
        parts.append(bx(0, 0.36, -18, 18, rz, rz + 0.2, 'Marble', 'rustcap'))
        for z in ((0.5, 1.02) if kind == 'nave' else (0.33,)): parts.append(bx(0, 0.31, -18, 18, z - 0.03, z + 0.03, 'Stone', 'band'))
        for y in pil_y:
            pz = 1.78 if kind == 'nave' else 0.86
            parts.append(bx(0, 0.28, y - 0.45, y + 0.45, pz, TOP - 1.25, 'Marble', 'pil'))
            parts.append(bx(0, 0.38, y - 0.58, y + 0.58, pz, pz + 0.32, 'Marble', 'pilb'))
            parts.append(bx(0, 0.4, y - 0.58, y + 0.58, TOP - 1.6, TOP - 1.25, 'Marble', 'pilc'))
        # cornice + dentils
        parts.append(bx(0, 0.18, -18, 18, TOP - 1.25, TOP - 0.8, 'Marble', 'arch'))
        parts.append(bx(0, 0.1, -18, 18, TOP - 0.8, TOP - 0.42, 'Wall', 'frieze'))
        for k in range(int(36 / 0.34)):
            y = -18 + (k + 0.5) * 36 / int(36 / 0.34)
            parts.append(bx(0.1, 0.3, y - 0.085, y + 0.085, TOP - 0.42, TOP - 0.24, 'Marble', 'dent'))
        parts.append(bx(0, 0.5, -18, 18, TOP - 0.24, TOP - 0.05, 'Marble', 'corona'))
        parts.append(bx(0, 0.62, -18, 18, TOP - 0.05, TOP + 0.12, 'Marble', 'cyma'))
        # balustrade along the wall top (built along X then turned)
        bal = balustrade_x(-18, 18, 0.0, TOP + 0.12, posts=[y for y in pil_y if abs(y) < 17.5])
        for b_ in bal:
            b_ = rot_z(b_, pi / 2)
            parts.append(apply(b_, ((X - 0.3) * sx, 0, 0)))
    if kind == 'nave':
        for sx in (-1, 1):
            parts.append(K.box(6.6 if sx > 0 else -X, X if sx > 0 else -6.6, -18, 18, TOP - 0.06, TOP + 0.04, 'Floor', 'roofslab'))
    else:
        slab = K.box(-X, X, -18, 18, TOP - 0.1, TOP + 0.02, 'Floor', 'roofslab')
        K.boolean(slab, [K.box(-0.9, 0.9, yo - 0.9, yo + 0.9, TOP - 0.5, TOP + 0.5, 'Floor', 'hole') for yo in (-9.0, 9.0)])
        parts.append(slab)
        for yo in (-9.0, 9.0):
            for (a, b, c, d) in ((-1.1, 1.1, yo - 1.1, yo - 0.9), (-1.1, 1.1, yo + 0.9, yo + 1.1), (-1.1, -0.9, yo - 0.9, yo + 0.9), (0.9, 1.1, yo - 0.9, yo + 0.9)):
                parts.append(K.box(a, b, c, d, TOP, TOP + 0.45, 'Marble', 'curb'))
    # the roof water channel: a stone trough on brackets, off the oculi
    cx = 8.3 if kind == 'nave' else 4.0; zb = TOP + 0.04
    parts.append(K.box(cx - 0.5, cx + 0.5, -18, 18, zb, zb + 0.16, 'Stone', 'trough'))
    for sgn in (-1, 1):
        parts.append(K.box(cx + sgn * 0.5 - (0.12 if sgn > 0 else 0), cx + sgn * 0.5 + (0 if sgn > 0 else 0.12), -18, 18, zb + 0.16, zb + 0.52, 'Stone', 'twall'))
    for y in np.arange(-16.5, 17, 3.0):
        parts.append(K.box(cx - 0.62, cx + 0.62, y - 0.18, y + 0.18, zb, zb + 0.58, 'Stone', 'clamp'))
    nm = 'NaveExt' if kind == 'nave' else 'ArcadeExt'
    finish(parts, nm + ('_LOD1' if LOD[0] else ''))
    if not LOD[0]:
        B = NA.Builder()
        rings = [[(cx - 0.38, y, zb + 0.4), (cx + 0.38, y, zb + 0.4)] for y in np.linspace(-18, 18, 37)]
        uvs = [[(0, (y + 18) / 2.0), (1, (y + 18) / 2.0)] for y in np.linspace(-18, 18, 37)]
        B.quad_strip(rings, uvs, 'Flow')
        ob = B.build(nm + 'Water'); AS.export_pms2(ob, nm + 'Water', [nm + 'Water_Flow']); MAN[nm + 'Water'] = [dict(sub=nm + 'Water_Flow', **FLOW)]
        EXTRA[nm + '_channel'] = [cx, zb + 0.4]

def galleries():
    nave3()
    for lod in (False, True):
        LOD[0] = lod
        gallery_ext('nave'); gallery_ext('arcade')
    LOD[0] = False

# =====================================================================================================
BUILDERS = {}
def builder(name):
    def deco(fn):
        BUILDERS[name] = fn; return fn
    return deco

builder('Vest_SideWindow')(lambda: vest_side_window3())
builder('Vest_SideWindow_CutR')(lambda: vest_side_window3('Vest_SideWindow_CutR', cut=1))
builder('Vest_SideWindow_CutL')(lambda: vest_side_window3('Vest_SideWindow_CutL', cut=-1))
builder('Vest_SideGate')(vest_side_gate)
builder('GateTorch')(gate_torch)
builder('VestExt')(all_vest_ext)
builder('Vest_Dome')(vest_dome)
builder('Galleries')(galleries)

def save():
    json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1)
    json.dump(EXTRA, open(EXP, 'w'), indent=1)

if __name__ == '__main__':
    names = sys.argv[1:] or list(BUILDERS)
    for n in names:
        print('== building', n, flush=True)
        BUILDERS[n]()
        save()
    print('kit3 done')
