"""Blender (bpy) architecture + prop kit for the House.
Every module is modelled in Blender space (Z up, gallery long axis = +Y), then exported to a compact
binary mesh (.bytes) already converted to Unity space (x, z, y; winding flipped). A .blend with all
modules is saved for hand-editing.

Run:  python3 gen/kit.py
"""
import bpy, bmesh, numpy as np, os, struct, math, sys
from math import pi, sin, cos, sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MESH = os.path.join(HERE, '..', 'out', 'Meshes')
OUT_BLEND = os.path.join(HERE, '..', 'out', 'Blender')
os.makedirs(OUT_MESH, exist_ok=True); os.makedirs(OUT_BLEND, exist_ok=True)
rng = np.random.default_rng(42)

# ------------------------------------------------------------------ scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
COLL = bpy.context.scene.collection

def mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        col = {'Floor': (0.85, 0.85, 0.82), 'Wall': (0.85, 0.78, 0.66), 'Marble': (0.92, 0.92, 0.9),
               'Gold': (0.83, 0.62, 0.25), 'Verde': (0.1, 0.25, 0.18), 'Iron': (0.08, 0.08, 0.08),
               'Flame': (1.0, 0.6, 0.2), 'Sand': (0.8, 0.7, 0.55), 'Glass': (0.6, 0.75, 0.85),
               'Water': (0.3, 0.6, 0.7), 'Stone': (0.6, 0.6, 0.58)}.get(name, (0.8, 0.8, 0.8))
        m.diffuse_color = (*col, 1)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (*col, 1)
            bsdf.inputs['Roughness'].default_value = 0.35
            if name == 'Gold': bsdf.inputs['Metallic'].default_value = 1.0
            if name == 'Flame':
                bsdf.inputs['Emission Color'].default_value = (1, 0.55, 0.2, 1)
                bsdf.inputs['Emission Strength'].default_value = 8
    return m

def obj_from(verts, faces, matname, smooth=False, ao=None, name='part', sharp_angle=40):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in faces])
    me.validate(clean_customdata=False)
    me.materials.append(mat(matname))
    if smooth:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp_angle))
    else:
        me.shade_flat()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    a = np.ones(len(me.vertices), np.float32) if ao is None else np.asarray(ao, np.float32)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    c = np.repeat(a[:, None], 4, 1); c[:, 3] = 1
    ca.data.foreach_set('color', c.ravel())
    return ob

def box(x0, x1, y0, y1, z0, z1, m, name='box'):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return obj_from(v, f, m, name=name)

def grid_faces(nu, nv, wrap_u=False):
    """faces for a (nu x nv) vertex grid, u fastest."""
    f = []
    uu = nu if wrap_u else nu - 1
    for j in range(nv - 1):
        for i in range(uu):
            a = j * nu + i; b = j * nu + (i + 1) % nu
            f.append((a, b, b + nu, a + nu))
    return f

def lathe(profile, seg=48, m='Marble', radial=None, name='lathe', ao=None, cap_top=True, cap_bottom=True):
    """profile: list of (r, z) bottom->top. radial(theta, z, r) -> r' optional displacement."""
    prof = np.asarray(profile, float)
    th = np.linspace(0, 2 * pi, seg, endpoint=False)
    V = []; A = []
    for k, (r, z) in enumerate(prof):
        for t in th:
            rr = radial(t, z, r) if radial else r
            V.append((rr * cos(t), rr * sin(t), z))
    F = grid_faces(seg, len(prof), wrap_u=True)
    nv = len(V)
    if cap_bottom:
        V.append((0, 0, prof[0, 1])); c = len(V) - 1
        F += [(c, (i + 1) % seg, i) for i in range(seg)]
    if cap_top:
        V.append((0, 0, prof[-1, 1])); c = len(V) - 1
        base = (len(prof) - 1) * seg
        F += [(c, base + i, base + (i + 1) % seg) for i in range(seg)]
    aov = None
    if ao is not None:
        aov = np.ones(len(V)); aov[:nv] = ao
    return obj_from(V, F, m, smooth=True, ao=aov, name=name)

def arch_prism(width, spring, x_center, y0, y1, z0=0.0, seg=32, axis='x', name='cut'):
    """Round-arched opening prism (rect up to `spring`, semicircle above) spanning y0..y1.
    axis='x': opening lies in the XZ plane (wall runs along X), extruded along Y."""
    r = width / 2.0
    pts = [(x_center - r, z0)]
    for i in range(seg + 1):
        a = pi - pi * i / seg
        pts.append((x_center + r * cos(a), spring + r * sin(a)))
    pts.append((x_center + r, z0))
    n = len(pts)
    V = [(p[0], y0, p[1]) for p in pts] + [(p[0], y1, p[1]) for p in pts]
    if axis == 'y':
        V = [(v[1], v[0], v[2]) for v in V]
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, j + n, i + n))
    return obj_from(V, F, 'Wall', name=name)

def boolean(target, cutters, op='DIFFERENCE'):
    for c in cutters:
        mod = target.modifiers.new('b', 'BOOLEAN')
        mod.operation = op; mod.object = c
        try: mod.solver = 'EXACT'
        except Exception: pass
    dg = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    target.modifiers.clear()
    old = target.data; target.data = me
    bpy.data.meshes.remove(old)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)
    me.shade_flat()
    return target

def join(parts, name):
    parts = [p for p in parts if p is not None]
    with bpy.context.temp_override(active_object=parts[0], selected_editable_objects=parts, object=parts[0]):
        bpy.ops.object.join()
    ob = parts[0]; ob.name = name; ob.data.name = name
    return ob

def sweep_profile_x(profile, x0, x1, name, m):
    """extrude a 2D profile (y,z) along X from x0..x1 (closed polygon)."""
    p = np.asarray(profile, float); n = len(p)
    V = [(x0, y, z) for y, z in p] + [(x1, y, z) for y, z in p]
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n; F.append((i, j, j + n, i + n))
    return obj_from(V, F, m, name=name)

def sweep_profile_y(profile, y0, y1, name, m):
    p = np.asarray(profile, float); n = len(p)
    V = [(x, y0, z) for x, z in p] + [(x, y1, z) for x, z in p]
    F = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n; F.append((j, i, i + n, j + n))
    return obj_from(V, F, m, name=name)

def arch_molding(width, spring, xc, yface, depth, thick, seg=40, m='Marble', name='archivolt', legs_to=0.0):
    """Molding band following an arch outline on a wall face (wall runs along X, face at y=yface,
    molding protrudes toward -y by `depth`)."""
    r = width / 2.0
    path = [(xc - r, legs_to)] + [(xc + r * cos(pi - pi * i / seg), spring + r * sin(pi - pi * i / seg)) for i in range(seg + 1)] + [(xc + r, legs_to)]
    V = []; F = []
    # quad strip: inner edge (on outline) and outer edge (offset outward by thick), front and back
    def outward(i):
        x, z = path[i]
        if z <= spring + 1e-6 and (i == 0 or i == len(path) - 1 or abs(x - xc) >= r - 1e-6):
            return (-1 if x < xc else 1, 0)
        dx, dz = x - xc, z - spring; l = sqrt(dx * dx + dz * dz) + 1e-9
        return (dx / l, dz / l)
    n = len(path)
    for i in range(n):
        x, z = path[i]; ox, oz = outward(i)
        for (yy, off) in [(yface, 0), (yface - depth, 0), (yface - depth, thick), (yface, thick)]:
            V.append((x + ox * off, yy, z + oz * off))
    for i in range(n - 1):
        a = i * 4; b = (i + 1) * 4
        for k in range(4):
            k2 = (k + 1) % 4
            F.append((a + k, a + k2, b + k2, b + k))
    F.append((0, 1, 2, 3)); e = (n - 1) * 4; F.append((e + 3, e + 2, e + 1, e))
    return obj_from(V, F, m, name=name)

# ================================================================== exporter
def export_bytes(ob, fname):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    nl = len(me.loops); nt = len(me.loop_triangles)
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    lv = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
    cn = np.empty(nl * 3, np.float32); me.corner_normals.foreach_get('vector', cn); cn = cn.reshape(-1, 3)
    tl = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', tl); tl = tl.reshape(-1, 3)
    tm = np.empty(nt, np.int32); me.loop_triangles.foreach_get('material_index', tm)
    col = np.ones((len(me.vertices), 4), np.float32)
    ca = me.color_attributes.get('Col')
    if ca is not None:
        buf = np.empty(len(ca.data) * 4, np.float32); ca.data.foreach_get('color', buf); buf = buf.reshape(-1, 4)
        if ca.domain == 'POINT': col = buf
        else:
            col = np.ones((len(me.vertices), 4), np.float32); col[lv] = buf
    # unique (vertex, quantized normal)
    key = np.concatenate([lv[:, None].astype(np.int64), np.round(cn * 1000).astype(np.int64)], 1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    first = np.zeros(len(uniq), np.int64); first[inv[::-1]] = np.arange(nl)[::-1]
    P = co[lv[first]]; N = cn[first]; C = col[lv[first]]
    # to Unity space
    P = P[:, [0, 2, 1]]; N = N[:, [0, 2, 1]]
    tris = inv[tl][:, [0, 2, 1]]
    names = [m.name if m else 'Default' for m in me.materials] or ['Default']
    subs = []
    for mi, nm in enumerate(names):
        sel = tris[tm == mi]
        if len(sel): subs.append((nm, sel.ravel().astype(np.int32)))
    C8 = (np.clip(C, 0, 1) * 255).astype(np.uint8)
    with open(os.path.join(OUT_MESH, fname + '.bytes'), 'wb') as f:
        f.write(b'PMS1'); f.write(struct.pack('<iii', len(P), len(subs), 0))
        f.write(P.astype('<f4').tobytes()); f.write(N.astype('<f4').tobytes()); f.write(C8.tobytes())
        for nm, idx in subs:
            b = nm.encode(); f.write(struct.pack('<i', len(b))); f.write(b)
            f.write(struct.pack('<i', len(idx))); f.write(idx.astype('<i4').tobytes())
    ev.to_mesh_clear()
    print(f'  {fname}: {len(P)} verts, {len(tris)} tris, mats={[s[0] for s in subs]}')

MODULES = {}
def module(name, ob):
    ob.name = name
    MODULES[name] = ob
    export_bytes(ob, name)
    # park modules in a row in the .blend for browsing
    ob.location.x = 40 * (len(MODULES) - 1)
    return ob

# ================================================================== column (Corinthian-ish), 10.6 m
def make_column(height_scale=1.0, name='Column'):
    parts = []
    parts.append(box(-0.6, 0.6, -0.6, 0.6, 0, 0.25, 'Marble', 'plinth'))
    base_prof = [(0.58, 0.25), (0.6, 0.3), (0.6, 0.34), (0.56, 0.39), (0.5, 0.42), (0.49, 0.47), (0.53, 0.5), (0.54, 0.54), (0.5, 0.58), (0.47, 0.6)]
    parts.append(lathe(base_prof, 64, 'Marble', name='base', cap_bottom=False, cap_top=False))
    # fluted shaft
    z0, z1 = 0.6, 9.2
    zs = np.concatenate([[z0, z0 + 0.06, z0 + 0.15, z0 + 0.4], np.linspace(z0 + 1.2, z1 - 1.2, 7), [z1 - 0.4, z1 - 0.15, z1 - 0.06, z1]])
    nfl = 24; segs_per = 6; seg = nfl * segs_per
    def r_at(z):
        t = (z - z0) / (z1 - z0)
        return 0.45 - 0.07 * t ** 1.6
    def flute(t, z, r):
        if z < z0 + 0.12 or z > z1 - 0.12: return r
        ph = (t * nfl / (2 * pi)) % 1.0
        w = 0.78  # flute width fraction (rest is fillet)
        if ph > w: return r
        u = (ph / w) * 2 - 1
        d = sqrt(max(0, 1 - u * u))
        fade = min(1, (z - z0 - 0.12) / 0.25, (z1 - 0.12 - z) / 0.25)
        return r - 0.04 * d * fade
    prof = [(r_at(z), z) for z in zs]
    th = np.linspace(0, 2 * pi, seg, endpoint=False)
    ao_shaft = []
    for r, z in prof:
        for t in th:
            ao_shaft.append(1 - 0.55 * (r - flute(t, z, r)) / 0.04)
    parts.append(lathe(prof, seg, 'Marble', radial=flute, name='shaft', ao=ao_shaft, cap_bottom=False, cap_top=False))
    # astragal + bell with two rows of acanthus
    parts.append(lathe([(0.38, 9.2), (0.43, 9.24), (0.43, 9.31), (0.38, 9.35)], 64, 'Marble', name='astragal', cap_bottom=False, cap_top=False))
    zb = np.linspace(9.35, 10.35, 22)
    def bell_r(z):
        t = (z - 9.35) / 1.0
        return 0.38 + 0.14 * t ** 1.5
    def leaves(t, z, r):
        tt = (z - 9.35) / 1.0
        d = 0
        # row 1 (short), row 2 (tall, offset)
        for row, (h, off, amp) in enumerate([(0.45, 0, 0.13), (0.8, pi / 8, 0.11)]):
            if tt < h:
                s = tt / h
                lobe = max(0.0, cos(8 * (t - off))) ** 0.6
                curl = sin(pi * s) ** 0.8 + 0.6 * s ** 4
                serr = 0.85 + 0.15 * cos(40 * (t - off))
                d = max(d, amp * lobe * curl * serr)
        return r + d
    ao_b = []
    thb = np.linspace(0, 2 * pi, 96, endpoint=False)
    for z in zb:
        for t in thb:
            ao_b.append(0.55 + 0.45 * min(1, (leaves(t, z, bell_r(z)) - bell_r(z)) / 0.09))
    parts.append(lathe([(bell_r(z), z) for z in zb], 96, 'Marble', radial=leaves, name='bell', ao=ao_b, cap_bottom=False, cap_top=False))
    # volutes at 4 corners (small curls)
    for k in range(4):
        a = pi / 4 + k * pi / 2
        bpy.ops.mesh.primitive_torus_add(major_radius=0.09, minor_radius=0.035, major_segments=24, minor_segments=10,
                                         location=(0.55 * cos(a), 0.55 * sin(a), 10.22), rotation=(pi / 2, 0, a + pi / 2))
        v = bpy.context.active_object; v.data.materials.append(mat('Marble'))
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        ca = v.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set('color', np.tile([0.8, 0.8, 0.8, 1], len(v.data.vertices)).astype(np.float32))
        v.data.shade_smooth(); parts.append(v)
    # abacus: concave-sided plate
    n = 64; V = []; zA, zB = 10.35, 10.6
    for z in (zA, zB):
        for i in range(n):
            t = 2 * pi * i / n
            # superellipse-ish square with concave sides
            c, s = cos(t), sin(t)
            rr = 0.66 / (abs(c) ** 4 + abs(s) ** 4) ** 0.25
            rr -= 0.06 * abs(cos(2 * t)) ** 0 * (1 - abs(sin(2 * t))) * 0 + 0.07 * (1 - abs(sin(2 * t)))
            V.append((rr * c, rr * s, z))
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    parts.append(obj_from(V, F, 'Marble', smooth=True, name='abacus', sharp_angle=50))
    ob = join(parts, name)
    if height_scale != 1.0:
        ob.scale.z = height_scale
        with bpy.context.temp_override(active_object=ob, selected_editable_objects=[ob], object=ob):
            bpy.ops.object.transform_apply(scale=True)
    return ob

# ================================================================== vault helpers
def _samples(L, cell, offs, extra, base_step):
    pts = set(np.round(np.arange(0, L + 1e-6, base_step), 4).tolist()); pts.add(round(L, 4))
    if cell:
        ncell = int(round(L / cell)); cell = L / ncell
        for k in range(ncell):
            for o in offs:
                for v in (k * cell + o, (k + 1) * cell - o):
                    if 0 <= v <= L: pts.add(round(v, 4))
            pts.add(round((k + 0.5) * cell, 4))
    for e in extra:
        if 0 <= e <= L: pts.add(round(e, 4))
    return np.array(sorted(pts))

def barrel_vault(half_w, spring, y0, y1, m, coffer=True, ribs=(), oculi=(), name='vault', sky_holes=(), base_step=0.5, extrados=True):
    """Semicircular barrel vault across X (radius half_w), along Y. Normals face inward (down).
    Sample lines are placed exactly on coffer/rib edges so recesses are crisp at low vertex counts."""
    R = half_w
    L_arc = pi * R
    ncof_u = max(6, int(round(L_arc / 1.55)))
    offs = [0.14, 0.19, 0.32, 0.37]
    margin = 0.12 * R
    su = _samples(L_arc, L_arc / ncof_u if coffer else 0, offs, [margin, L_arc - margin], base_step if not coffer else 0.6)
    ey = []
    for (yr, w) in ribs:
        ey += [yr - y0 - w / 2 - 0.12, yr - y0 - w / 2 - 0.01, yr - y0 - w / 2, yr - y0 + w / 2, yr - y0 + w / 2 + 0.01, yr - y0 + w / 2 + 0.12]
    for (yo, w2) in sky_holes:
        ey += [yo - y0 - w2, yo - y0 + w2]
    sv = _samples(y1 - y0, 1.5 if coffer else 0, offs, ey, base_step if not coffer else 0.75)
    angs = su / R; ys = y0 + sv
    nu, nv = len(angs), len(ys)
    V = []; AO = []; keep = np.ones((nv, nu), bool)
    cu = L_arc / ncof_u
    for j, y in enumerate(ys):
        for i, a in enumerate(angs):
            d = 0.0; ao = 1.0
            if coffer:
                sarc = a * R
                fu = (sarc / cu) % 1.0
                fv = ((y - y0) / 1.5) % 1.0
                e = min(min(fu, 1 - fu) * cu, min(fv, 1 - fv) * 1.5)
                rec = 0.12 * np.clip((e - 0.14) / 0.05, 0, 1) + 0.1 * np.clip((e - 0.32) / 0.05, 0, 1)
                if sarc < margin - 1e-4 or sarc > L_arc - margin + 1e-4: rec = 0
                d = rec
                ao = 1 - 0.45 * float(0.13 < e < 0.2) - 0.35 * float(0.31 < e < 0.38) if rec > 0 else 1.0
            for (yr, w) in ribs:
                if abs(y - yr) < w / 2 - 0.005:
                    d = -0.28; ao = 1.0
                elif abs(y - yr) < w / 2 + 0.13:
                    ao = min(ao, 0.55)
            rr = R + d
            x = -rr * cos(a); z = spring + rr * sin(a)
            for (yo, ro) in oculi:
                if (y - yo) ** 2 + x ** 2 < ro * ro: keep[j, i] = False
            for (yo, w2) in sky_holes:
                if abs(y - yo) < w2 - 1e-3 and abs(x) < w2 - 1e-3: keep[j, i] = False
            V.append((x, y, z)); AO.append(ao)
    F = []
    for j in range(nv - 1):
        for i in range(nu - 1):
            if keep[j, i] and keep[j, i + 1] and keep[j + 1, i] and keep[j + 1, i + 1]:
                a0 = j * nu + i
                F.append((a0, a0 + nu, a0 + nu + 1, a0 + 1))
    ob = obj_from(V, F, m, smooth=True, ao=AO, name=name, sharp_angle=35)
    parts = [ob]
    if extrados:
        # coarse outer roof shell (seen only from outside / courtyards)
        Ro = R + 0.9; na = 25
        Vo = []
        for y in (y0, y1):
            for k in range(na):
                a = pi * k / (na - 1)
                Vo.append((-Ro * cos(a), y, spring + Ro * sin(a)))
        Fo = [(k, k + 1, na + k + 1, na + k) for k in range(na - 1)]
        parts.append(obj_from(Vo, Fo, 'Wall', smooth=True, name=name + '_roof'))
    return join(parts, name) if len(parts) > 1 else ob

def oculus_ring(r, z_center, y_center=0, m='Marble', name='ring', axis_z=True):
    prof = [(r, -0.25), (r + 0.18, -0.25), (r + 0.22, -0.15), (r + 0.4, -0.1), (r + 0.45, 0.0), (r, 0.0)]
    ob = lathe([(a, b + z_center) for a, b in prof], 64, m, name=name, cap_top=False, cap_bottom=False)
    ob.location.y = y_center
    with bpy.context.temp_override(active_object=ob, selected_editable_objects=[ob], object=ob):
        bpy.ops.object.transform_apply(location=True)
    return ob

# ================================================================== VESTIBULE (20x20 inner, sail vault, oculus)
def make_vestibule_core():
    parts = []
    parts.append(box(-12, 12, -12, 12, -8, 0, 'Floor', 'floor'))
    R2 = 200.0; S = 13.0; n = 121
    xs = np.linspace(-10, 10, n)
    V = []; AO = []; keep = np.ones((n, n), bool)
    for j, y in enumerate(xs):
        for i, x in enumerate(xs):
            r2 = x * x + y * y
            zc = sqrt(max(R2 - r2, 0.0))
            # spherical coffers
            psi = math.acos(min(1, zc / sqrt(R2)))
            phi = math.atan2(y, x)
            nphi = 32
            fphi = (phi / (2 * pi) * nphi) % 1.0
            band = math.degrees(psi)
            ring_w = 7.5; fr = ((band - 13) / ring_w)
            d = 0; ao = 1
            if fr > 0.15 and band < 78:
                f2 = fr % 1.0
                rr = sqrt(R2) * sin(psi)
                e_phi = min(fphi, 1 - fphi) * (2 * pi * rr / nphi)
                e_rng = min(f2, 1 - f2) * math.radians(ring_w) * sqrt(R2)
                e = min(e_phi, e_rng)
                d = 0.12 * np.clip((e - 0.12) / 0.05, 0, 1) + 0.1 * np.clip((e - 0.3) / 0.05, 0, 1)
                ao = 1 - 0.45 * np.clip(1 - abs(e - 0.33) / 0.18, 0, 1) * (d > 0.05)
            rad = sqrt(R2) + d
            k = rad / sqrt(R2)
            z = S + zc * k
            px, py = x * k if r2 > 0 else x, y * k if r2 > 0 else y
            # keep the vault boundary on the wall planes
            if abs(x) >= 9.999: px = x
            if abs(y) >= 9.999: py = y
            if r2 < 3.0 ** 2: keep[j, i] = False
            V.append((px, py, z)); AO.append(ao)
    F = []
    for j in range(n - 1):
        for i in range(n - 1):
            if keep[j, i] and keep[j, i + 1] and keep[j + 1, i] and keep[j + 1, i + 1]:
                a0 = j * n + i
                F.append((a0, a0 + n, a0 + n + 1, a0 + 1))
    v = obj_from(V, F, 'Marble', smooth=True, ao=AO, name='sailvault', sharp_angle=35)
    parts.append(v)
    # exterior: square roof ring at wall-top (z=24) + spherical cap dome with a drum around the oculus
    Rs = 14.6; a0 = math.asin(11.0 / Rs)
    capr = Rs * cos(a0)
    a1 = math.acos(3.6 / Rs)
    prof = [(capr * 1.0 + 0.4, 24.0), (capr, 24.0)] + [(Rs * cos(a), 13.0 + Rs * sin(a)) for a in np.linspace(a0, a1, 10)]
    zt = 13.0 + Rs * sin(a1)
    prof += [(3.6, zt + 0.7), (3.0, zt + 0.7)]
    parts.append(lathe(prof, 48, 'Wall', name='dome_ext', cap_top=False, cap_bottom=False))
    nth = 64; Vr = []; Fr = []
    for k in range(nth):
        t = 2 * pi * k / nth
        c, s_ = cos(t), sin(t)
        m_ = max(abs(c), abs(s_))
        Vr.append((capr * c, capr * s_, 24.0)); Vr.append((12.0 * c / m_, 12.0 * s_ / m_, 24.0))
    for k in range(nth):
        a = 2 * k; b = 2 * ((k + 1) % nth)
        Fr.append((a, a + 1, b + 1, b))
    parts.append(obj_from(Vr, Fr, 'Wall', name='roofring'))
    zc = S + sqrt(R2 - 9.0)
    parts.append(oculus_ring(3.0, zc, 0, 'Gold', 'oculus_ring'))
    # cornice ring at springing on all 4 sides (inner faces)
    prof = [(0, 12.6), (-0.25, 12.6), (-0.3, 12.75), (-0.45, 12.85), (-0.5, 13.0), (0, 13.0)]
    for k in range(4):
        c = sweep_profile_x([(10 + yy, z) for yy, z in [(-a, b) for a, b in [(p[0] * -1, p[1]) for p in prof]]], -10, 10, f'cornice{k}', 'Marble')
        # place cornice on side k: built along X at y = 10 (protruding toward center: y<10)
        c.rotation_euler.z = k * pi / 2
        with bpy.context.temp_override(active_object=c, selected_editable_objects=[c], object=c):
            bpy.ops.object.transform_apply(rotation=True)
        parts.append(c)
    gold = []
    for k in range(4):
        g = box(-10, 10, 9.92, 10.0, 12.3, 12.6, 'Gold', f'goldband{k}')
        g.rotation_euler.z = k * pi / 2
        with bpy.context.temp_override(active_object=g, selected_editable_objects=[g], object=g):
            bpy.ops.object.transform_apply(rotation=True)
        parts.append(g)
    return join([p for p in parts if p is not None], 'Vest_Core')

def make_vestibule_side(open_=True):
    """Wall on +Y side: inner face y=10, outer y=12, x in [-12,12], z 0..24."""
    wall = box(-12, 12, 10, 12, 0, 24, 'Wall', 'wall')
    cut = [arch_prism(10, 7, 0, 9.9 if open_ else 9.9, 12.1 if open_ else 11.3, name='arch')]
    # lunette window
    th = np.linspace(0, 2 * pi, 40, endpoint=False)
    rw = 2.2; zw = 18.2
    pts = [(rw * cos(t), zw + rw * sin(t)) for t in th]
    n = len(pts)
    Vc = [(p[0], 9.9, p[1]) for p in pts] + [(p[0], 12.1, p[1]) for p in pts]
    Fc = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    cut.append(obj_from(Vc, Fc, 'Wall', name='win'))
    boolean(wall, cut)
    parts = [wall]
    parts.append(arch_molding(10, 7, 0, 10.0, 0.25, 0.55, m='Marble', name='archivolt_in'))
    if open_:
        parts.append(arch_molding(10, 7, 0, 12.25, 0.25, 0.55, m='Marble', name='archivolt_out'))
        parts.append(box(-0.5, 0.5, 9.7, 12.3, 11.7, 12.9, 'Gold', 'keystone'))
    else:
        parts.append(box(-0.5, 0.5, 9.7, 10.05, 11.7, 12.9, 'Gold', 'keystone'))
    # window ring
    ring = lathe([(2.2, -0.0), (2.55, 0.0), (2.6, 0.15), (2.2, 0.15)], 48, 'Marble', name='winring', cap_top=False, cap_bottom=False)
    ring.rotation_euler.x = pi / 2; ring.location = (0, 10.0, zw)
    with bpy.context.temp_override(active_object=ring, selected_editable_objects=[ring], object=ring):
        bpy.ops.object.transform_apply(location=True, rotation=True)
    parts.append(ring)
    # mullion cross in window
    parts.append(box(-0.06, 0.06, 10.8, 11.0, zw - 2.2, zw + 2.2, 'Iron', 'mull1'))
    parts.append(box(-2.2, 2.2, 10.8, 11.0, zw - 0.06, zw + 0.06, 'Iron', 'mull2'))
    # pilasters flanking arch
    for sx in (-1, 1):
        x0 = sx * 7.2
        parts.append(box(x0 - 0.7, x0 + 0.7, 9.65, 10.0, 0, 11.8, 'Marble', 'pil'))
        parts.append(box(x0 - 0.85, x0 + 0.85, 9.55, 10.0, 0, 0.5, 'Marble', 'pilbase'))
        parts.append(box(x0 - 0.85, x0 + 0.85, 9.5, 10.0, 11.8, 12.3, 'Marble', 'pilcap'))
    return join(parts, 'Vest_SideOpen' if open_ else 'Vest_SideBlind')

# ================================================================== NAVE (colonnade gallery, 36 m)
COL_Y = [-15.75 + 4.5 * k for k in range(8)]
def end_caps(half_w, top, opening_w=10, spring=7, name='caps', m='Wall'):
    caps = []
    for sy in (-1, 1):
        y0, y1 = (17.4, 18.0) if sy > 0 else (-18.0, -17.4)
        c = box(-half_w, half_w, y0, y1, 0, top, m, 'cap')
        boolean(c, [arch_prism(opening_w, spring, 0, y0 - 0.1, y1 + 0.1, name='capcut')])
        caps.append(c)
    return caps

def make_nave():
    parts = [box(-10, 10, -18, 18, -8, 0, 'Floor', 'floor')]
    for sx in (-1, 1):
        w = box(8 if sx > 0 else -10, 10 if sx > 0 else -8, -18, 18, 0, 16.5, 'Wall', 'wall')
        cuts = []
        for k in range(7):
            yc = (COL_Y[k] + COL_Y[k + 1]) / 2
            c = arch_prism(2.0, 4.0, yc, 7.9 if sx > 0 else -8.9, 8.9 if sx > 0 else -7.9, z0=0.6, axis='y', name='niche')
            cuts.append(c)
        boolean(w, cuts)
        parts.append(w)
        # aisle ceiling slab
        parts.append(box(6.45 if sx > 0 else -8, 8 if sx > 0 else -6.45, -18, 18, 10.6, 12.4, 'Marble', 'aisleceil'))
        # entablature: architrave, gold frieze, cornice (stepped)
        x_in = 5.45 if sx > 0 else -6.55
        sgn = sx
        def bx(a, b, z0, z1, m, nm):
            lo, hi = (a, b) if sx > 0 else (-b, -a)
            return box(lo, hi, -18, 18, z0, z1, m, nm)
        parts.append(bx(5.45, 6.55, 10.6, 10.85, 'Marble', 'arch1'))
        parts.append(bx(5.38, 6.55, 10.85, 11.25, 'Marble', 'arch2'))
        parts.append(bx(5.42, 6.55, 11.25, 11.85, 'Gold', 'frieze'))
        parts.append(bx(5.2, 6.55, 11.85, 12.0, 'Marble', 'corn1'))
        parts.append(bx(4.95, 6.55, 12.0, 12.25, 'Marble', 'corn2'))
        parts.append(bx(4.85, 6.55, 12.25, 12.4, 'Gold', 'corn3'))
        # attic with clerestory windows (glass)
        att = bx(6.0, 6.55, 12.4, 14.6, 'Wall', 'attic')
        wcuts = []
        for k in range(7):
            yc = (COL_Y[k] + COL_Y[k + 1]) / 2
            wcuts.append(box(5.9 if sx > 0 else -6.65, 6.65 if sx > 0 else -5.9, yc - 1.3, yc + 1.3, 12.8, 14.25, 'Wall', 'wcut'))
        boolean(att, wcuts)
        parts.append(att)
        for k in range(7):
            yc = (COL_Y[k] + COL_Y[k + 1]) / 2
            parts.append(bx(6.4, 6.45, 12.8, 14.25, 'Glass', 'glass') if False else None)
            lo, hi = (6.35, 6.4) if sx > 0 else (-6.4, -6.35)
            parts.append(box(lo, hi, yc - 1.3, yc + 1.3, 12.8, 14.25, 'Glass', 'glass'))
            # mullions
            parts.append(box(lo - 0.03, hi + 0.03, yc - 0.05, yc + 0.05, 12.8, 14.25, 'Iron', 'm'))
        parts.append(bx(5.85, 6.55, 14.4, 14.6, 'Marble', 'springcourse'))
    ribs = [(y, 0.7) for y in COL_Y]
    parts.append(barrel_vault(6.0, 14.6, -18, 18, 'Marble', coffer=True, ribs=ribs, oculi=[(-9.0, 1.6), (9.0, 1.6)], name='vault'))
    for yo in (-9.0, 9.0):
        parts.append(oculus_ring(1.6, 14.6 + 6.0 - 0.02, yo, 'Gold', 'ocring'))
    parts += end_caps(10, 21.5)
    return join([p for p in parts if p is not None], 'Nave')

# ================================================================== ARCADE (stone vaulted corridor, 36 m)
def make_arcade():
    parts = [box(-7, 7, -18, 18, -8, 0, 'Floor', 'floor')]
    bays = [-15.75 + 4.5 * k for k in range(8)]
    for sx in (-1, 1):
        w = box(5 if sx > 0 else -7, 7 if sx > 0 else -5, -18, 18, 0, 15.5, 'Wall', 'wall')
        cuts = [arch_prism(2.4, 4.2, yc, 4.9 if sx > 0 else -6.0, 6.0 if sx > 0 else -4.9, z0=0.9, axis='y', name='niche') for yc in bays]
        boolean(w, cuts)
        parts.append(w)
        def bx(a, b, y0, y1, z0, z1, m, nm):
            lo, hi = (a, b) if sx > 0 else (-b, -a)
            return box(lo, hi, y0, y1, z0, z1, m, nm)
        # continuous ledge/bench
        parts.append(bx(4.35, 5.0, -18, 18, 0, 0.75, 'Stone', 'ledge'))
        parts.append(bx(4.25, 5.0, -18, 18, 0.75, 0.9, 'Stone', 'ledgecap'))
        for k in range(1, 8):
            yp = -18 + 4.5 * k
            parts.append(bx(4.6, 5.0, yp - 0.45, yp + 0.45, 0.9, 8.5, 'Stone', 'pil'))
            parts.append(bx(4.45, 5.0, yp - 0.6, yp + 0.6, 8.5, 8.85, 'Stone', 'pilcap'))
        # niche arch moldings
        for yc in bays:
            m = arch_molding(2.4, 4.2, 0, 0.0, 0.12, 0.22, m='Stone', name='nm', legs_to=0.9)
            # built in XZ plane facing -y; rotate to face inward along x
            m.rotation_euler.z = (pi / 2 if sx > 0 else -pi / 2)
            m.location = (5.0 * sx, yc, 0)
            with bpy.context.temp_override(active_object=m, selected_editable_objects=[m], object=m):
                bpy.ops.object.transform_apply(location=True, rotation=True)
            parts.append(m)
        parts.append(bx(4.4, 5.0, -18, 18, 8.85, 9.3, 'Stone', 'cornice'))
    ribs = [(-13.5, 0.9), (-4.5, 0.9), (4.5, 0.9), (13.5, 0.9)]
    parts.append(barrel_vault(5.0, 9.3, -18, 18, 'Wall', coffer=False, ribs=ribs, sky_holes=[(-9.0, 0.8), (9.0, 0.8)], base_step=0.3, name='vault'))
    parts += end_caps(7, 15.5)
    return join(parts, 'Arcade')

# ================================================================== props
def make_plinth_round():
    prof = [(1.1, 0), (1.1, 0.22), (0.98, 0.25), (0.98, 0.42), (0.86, 0.45), (0.8, 0.5), (0.74, 0.55), (0.74, 1.05), (0.8, 1.08), (0.86, 1.12), (0.88, 1.25)]
    return lathe(prof, 64, 'Marble', name='Plinth_Round')

def make_plinth_square():
    parts = [box(-0.68, 0.68, -0.68, 0.68, 0, 0.2, 'Marble', 'b1'), box(-0.6, 0.6, -0.6, 0.6, 0.2, 0.3, 'Marble', 'b2'),
             box(-0.5, 0.5, -0.5, 0.5, 0.3, 1.1, 'Verde', 'die'),
             box(-0.6, 0.6, -0.6, 0.6, 1.1, 1.2, 'Marble', 'c1'), box(-0.66, 0.66, -0.66, 0.66, 1.2, 1.3, 'Marble', 'c2')]
    return join(parts, 'Plinth_Square')

def make_pedestal_colossal():
    parts = [box(-1.8, 1.8, -1.8, 1.8, 0, 0.4, 'Marble', 'b1'), box(-1.5, 1.5, -1.5, 1.5, 0.4, 1.5, 'Verde', 'die'),
             box(-1.7, 1.7, -1.7, 1.7, 1.5, 1.75, 'Marble', 'c1'), box(-1.55, 1.55, -1.55, 1.55, 0.4, 0.5, 'Gold', 'g')]
    return join(parts, 'Pedestal_Colossal')

def make_lantern():
    parts = []
    parts.append(box(-0.04, 0.04, 0, 0.55, 0.62, 0.68, 'Iron', 'arm'))           # bracket arm (wall at y=0, out to +y)
    parts.append(box(-0.12, 0.12, 0, 0.04, 0.45, 0.8, 'Iron', 'plate'))
    cage = lathe([(0.001, 0.0), (0.14, 0.05), (0.16, 0.1), (0.16, 0.5), (0.2, 0.55), (0.05, 0.68), (0.001, 0.7)], 6, 'Iron', name='cage')
    cage.location = (0, 0.55, -0.1)
    with bpy.context.temp_override(active_object=cage, selected_editable_objects=[cage], object=cage):
        bpy.ops.object.transform_apply(location=True)
    cage.data.shade_flat()
    parts.append(cage)
    glow = lathe([(0.001, 0.0), (0.135, 0.0), (0.135, 0.42), (0.001, 0.42)], 6, 'Flame', name='glow')
    glow.location = (0, 0.55, 0.0)
    with bpy.context.temp_override(active_object=glow, selected_editable_objects=[glow], object=glow):
        bpy.ops.object.transform_apply(location=True)
    parts.append(glow)
    return join(parts, 'Lantern')

def make_fragment_drum():
    def flute(t, z, r):
        ph = (t * 24 / (2 * pi)) % 1.0
        return r - 0.035 * sqrt(max(0, 1 - ((ph / 0.78) * 2 - 1) ** 2)) if ph < 0.78 else r
    zs = np.linspace(0, 0.9, 10)
    ob = lathe([(0.43, z) for z in zs], 96, 'Marble', radial=flute, name='Fragment_Drum')
    # jagged top
    me = ob.data
    for v in me.vertices:
        if v.co.z > 0.85:
            v.co.z += rng.uniform(-0.25, 0.05) * (0.5 + 0.5 * sin(atan2c(v.co.y, v.co.x) * 3))
    return ob

def atan2c(y, x): return math.atan2(y, x)

def make_fragment_slab():
    V = []; F = []
    ob = box(-1.1, 1.1, -0.7, 0.7, 0, 0.25, 'Floor', 'Fragment_Slab')
    sub = ob.modifiers.new('s', 'SUBSURF'); sub.levels = 2; sub.subdivision_type = 'SIMPLE'
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); ob.modifiers.clear()
    ob.data = me
    for v in me.vertices:
        if abs(v.co.x) > 1.0 or abs(v.co.y) > 0.6:
            v.co.x *= 1 + rng.uniform(-0.12, 0.05); v.co.y *= 1 + rng.uniform(-0.12, 0.05)
    me.shade_flat()
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); ca.data.foreach_set('color', np.ones(len(me.vertices) * 4, np.float32))
    return ob

def make_sand_drift(size=10.0, n=64, peak=0.9, seed=3):
    r = np.random.default_rng(seed)
    xs = np.linspace(-size / 2, size / 2, n)
    V = []
    ph = r.uniform(0, 6, 6)
    for y in xs:
        for x in xs:
            d = sqrt((x / (size / 2)) ** 2 + (y / (size / 2)) ** 2)
            hgt = peak * max(0, 1 - d) ** 1.6
            hgt *= 0.8 + 0.2 * sin(x * 1.3 + ph[0]) * cos(y * 1.1 + ph[1])
            hgt += 0.04 * sin(x * 6 + y * 2 + ph[2]) * max(0, 1 - d)
            V.append((x, y, hgt - 0.03))
    F = grid_faces(n, n)
    F = [(a, b, c, d) for (a, b, c, d) in F]
    return obj_from(V, F, 'Sand', smooth=True, name='SandDrift')

def make_seagate():
    """Terrace + grand stairs descending into the sea. Local: starts at y=12 (outside a vestibule side wall)."""
    parts = [box(-11, 11, 12, 22, -8, 0, 'Floor', 'terrace')]
    steps = 18; rise = 0.25; run = 0.55
    for i in range(steps):
        y0 = 22 + i * run; z1 = -rise * (i + 1)
        parts.append(box(-8, 8, y0, y0 + run, -8, z1 + 0.0 if i else -rise, 'Stone', 'step'))
    # side walls / balustrade cheeks
    for sx in (-1, 1):
        parts.append(box(8 * sx - (0 if sx > 0 else 1.2), 8 * sx + (1.2 if sx > 0 else 0), 22, 22 + steps * run, -8, 0.9, 'Wall', 'cheek'))
        parts.append(box(11 * sx - (0 if sx > 0 else 0.6), 11 * sx + (0.6 if sx > 0 else 0), 12, 22, 0, 0.9, 'Wall', 'parapet'))
        parts.append(box(9.2 * sx - 1.6, 9.2 * sx + 1.6, 22.2, 25.4, 0.9, 1.3, 'Marble', 'capstone'))
    return join(parts, 'SeaGate')

def make_cascade_ribbon(width=3.2, top=16.0, n=40):
    """falling water sheet: starts at window bottom (y=0 plane) and arcs out into the room (+y)."""
    V = []
    for j in range(n):
        t = j / (n - 1)
        z = top * (1 - t)
        y = 0.4 + 2.2 * t ** 0.5
        w = width * (1 + 0.25 * t)
        for i in range(9):
            u = i / 8 - 0.5
            V.append((u * w, y + 0.12 * cos(u * 6), z))
    F = grid_faces(9, n)
    ob = obj_from(V, F, 'Water', smooth=True, name='Cascade')
    return ob

def make_ocean_floor():
    n = 160; L = 900.0
    xs = np.linspace(-L / 2, L / 2, n)
    V = []
    for y in xs:
        for x in xs:
            # house footprint roughly [-80, 80] (Unity x/z). deepen away from house
            d = max(0, max(abs(x), abs(y)) - 75)
            z = -2.5 - min(d, 60) * 0.25 - 0.002 * d * d
            z += 0.8 * sin(x * 0.05) * cos(y * 0.043)
            V.append((x, y, z))
    return obj_from(V, grid_faces(n, n), 'Sand', smooth=True, name='Seabed')

def make_distant_wing(seed):
    """Low-detail silhouette of other wings of the House (seen in fog across the sea)."""
    r = np.random.default_rng(seed)
    parts = []
    L = r.uniform(120, 260); H = r.uniform(30, 55)
    parts.append(box(-L / 2, L / 2, -14, 14, -10, H, 'Wall', 'block'))
    cuts = []
    nb = int(L / 9)
    for k in range(nb):
        x = -L / 2 + (k + 0.5) * L / nb
        for tier, (z0, sp, w) in enumerate([(0.5, 6.0, 5.0), (H * 0.45, H * 0.45 + 5, 4.0), (H * 0.72, H * 0.72 + 3, 3.0)]):
            if z0 + w > H - 3: continue
            c = arch_prism(w, sp, x, -14.2, -11.5, z0=z0, name='a')
            cuts.append(c)
    boolean(parts[0], cuts)
    # pediment / attic
    parts.append(box(-L / 2 - 1, L / 2 + 1, -15, 15, H, H + 2, 'Marble', 'cornice'))
    for k in range(r.integers(1, 3)):
        x = r.uniform(-L / 3, L / 3)
        dome = lathe([(12 * cos(a), H + 2 + 10 * sin(a)) for a in np.linspace(0, pi / 2, 12)] + [(0.001, H + 12.01)], 32, 'Marble', name='dome')
        dome.location.x = x
        with bpy.context.temp_override(active_object=dome, selected_editable_objects=[dome], object=dome):
            bpy.ops.object.transform_apply(location=True)
        parts.append(dome)
    return join(parts, f'Wing_{seed}')

# ================================================================== build all
if __name__ == '__main__':
    only = sys.argv[1:]  # optional subset
    builders = [
        ('Column', make_column), ('Vest_Core', make_vestibule_core),
        ('Vest_SideOpen', lambda: make_vestibule_side(True)), ('Vest_SideBlind', lambda: make_vestibule_side(False)),
        ('Nave', make_nave), ('Arcade', make_arcade),
        ('Plinth_Round', make_plinth_round), ('Plinth_Square', make_plinth_square), ('Pedestal_Colossal', make_pedestal_colossal),
        ('Lantern', make_lantern), ('Fragment_Drum', make_fragment_drum), ('Fragment_Slab', make_fragment_slab),
        ('SandDrift', make_sand_drift), ('SeaGate', make_seagate), ('Cascade', make_cascade_ribbon),
        ('Seabed', make_ocean_floor), ('Wing_1', lambda: make_distant_wing(1)), ('Wing_2', lambda: make_distant_wing(2)),
        ('Wing_3', lambda: make_distant_wing(3)),
    ]
    for name, fn in builders:
        if only and name not in only: continue
        print('building', name, flush=True)
        module(name, fn())
    if not only:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_BLEND, 'House_Kit.blend'))
    print('kit done')
