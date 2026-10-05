"""The Colossus: MakeHuman CC0 base mesh posed with its CC0 skeleton/weights (pure numpy linear-blend
skinning), right palm raised up into the oculus light, robe draped from the waist, smoothed + AO baked
in Blender, exported as PMS1 with the palm seat position for the layout."""
import os, sys, json, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import kit as K
import statues as ST

MH = os.path.join(HERE, '..', 'src', 'mh')
DATA = os.path.join(HERE, '..', 'out', 'Data')
HEIGHT = 13.0
HAND = 2.1

def load_obj():
    V = []; F = []; grp = None
    for line in open(os.path.join(MH, 'base.obj')):
        if line.startswith('v '): V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('g '): grp = line.split()[1].strip()
        elif line.startswith('f ') and grp == 'body':
            F.append([int(p.split('/')[0]) - 1 for p in line.split()[1:]])
    return np.array(V), F

def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = np.dot(a, b)
    if np.linalg.norm(v) < 1e-8: return np.eye(3) if c > 0 else -np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))

def axis_angle(axis, ang):
    axis = axis / np.linalg.norm(axis); x, y, z = axis; c, s = math.cos(ang), math.sin(ang); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s], [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])

def T(R, h):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = h - R @ h; return M

def main():
    V, F = load_obj()
    skel = json.load(open(os.path.join(MH, 'default.mhskel')))
    W = json.load(open(os.path.join(MH, 'default_weights.mhw')))['weights']
    J = {k: V[v].mean(0) for k, v in skel['joints'].items()}
    bones = skel['bones']
    head = {b: J[d['head']] for b, d in bones.items()}; tail = {b: J[d['tail']] for b, d in bones.items()}
    sR = np.sign(head['clavicle.R'][0]); sL = -sR
    # palm normal at rest from thumb/pinky bases
    def palm_frame(Mw):
        wh = (Mw @ np.append(head['wrist.R'], 1))[:3]
        th = (Mw @ np.append(head['finger1-1.R'], 1))[:3]; pk = (Mw @ np.append(head['finger5-1.R'], 1))[:3]; md = (Mw @ np.append(head['finger3-1.R'], 1))[:3]
        hd = md - wh; hd /= np.linalg.norm(hd); lat = th - pk; lat /= np.linalg.norm(lat)
        n = np.cross(hd, lat); n /= np.linalg.norm(n)
        return wh, md, hd, n
    _, _, _, n_rest = palm_frame(np.eye(4))
    flip = 1.0 if n_rest[1] < 0 else -1.0      # relaxed A-pose palms face down/in: make n point out of the palm
    targets = {
        'spine01': np.array([sR * 0.04, 1.0, -0.04]),
        'upperarm01.R': np.array([sR * 0.32, 0.9, 0.28]),
        'lowerarm01.R': np.array([sR * 0.35, 0.62, 0.7]),
        'wrist.R': np.array([sR * 0.25, 0.08, 0.96]),
        'upperarm01.L': np.array([sL * 0.17, -0.97, 0.12]),
        'lowerarm01.L': np.array([sL * 0.08, -0.82, 0.55]),
        'neck01': np.array([sR * 0.08, 0.95, -0.2]),
        'head': np.array([sR * 0.2, 0.75, -0.55]),
    }
    order = []
    def visit(b):
        if b in order: return
        p = bones[b]['parent']
        if p: visit(p)
        order.append(b)
    for b in bones: visit(b)
    M = {}
    for b in order:
        p = bones[b]['parent']; Mp = M[p] if p else np.eye(4)
        h = (Mp @ np.append(head[b], 1))[:3]; t = (Mp @ np.append(tail[b], 1))[:3]
        R = np.eye(3)
        if b in targets: R = rot_between(t - h, targets[b])
        M[b] = T(R, h) @ Mp
        if b == 'wrist.R':
            # roll the hand about its own axis so the palm faces the sky
            wh, md, hd, n = palm_frame(M[b]); n = n * flip
            proj = np.array([0, 1.0, 0]) - hd * hd[1]; proj /= np.linalg.norm(proj)
            ang = math.atan2(np.dot(np.cross(n, proj), hd), np.dot(n, proj))
            M[b] = T(axis_angle(hd, ang), wh) @ M[b]
            S = np.eye(4); S[:3, :3] *= HAND; S[:3, 3] = wh - HAND * wh      # oversized offering hand (a seat for a person)
            M[b] = S @ M[b]
    # sculpted hair cap: push the scalp out along the rest normals with wavy locks (classical marble hair)
    V = V.copy()
    Nr = np.zeros_like(V)
    for f in F:
        for a, b, c in ((f[0], f[1], f[2]), (f[0], f[2], f[3])) if len(f) == 4 else ((f[0], f[1], f[2]),):
            n_ = np.cross(V[b] - V[a], V[c] - V[a]); Nr[[a, b, c]] += n_
    Nr /= np.linalg.norm(Nr, axis=1, keepdims=True) + 1e-12
    hw = np.zeros(len(V))
    for i, w in W.get('head', []): hw[i] = w
    eye = (J['eye.L____head'] + J['eye.R____head']) / 2
    hc = np.array([eye[0], eye[1], J['head____head'][2] if 'head____head' in J else eye[2] - 0.9])
    rel = V - hc
    zf = np.clip((rel[:, 2] - (eye[2] - hc[2]) * 0.35) / (-(eye[2] - hc[2]) * 1.2), 0, 1)
    zf = zf * zf * (3 - 2 * zf)                                 # 0 at the forehead, 1 at the back of the head
    thr = eye[1] + 0.55 - 1.45 * zf
    feather = np.clip((V[:, 1] - thr) / 0.18, 0, 1) * np.clip((hw - 0.35) / 0.4, 0, 1)
    ang = np.arctan2(rel[:, 0], rel[:, 2])
    locks = 0.5 + 0.5 * np.sin(ang * 14 + rel[:, 1] * 9 + np.sin(rel[:, 1] * 5) * 1.5)
    curls = 0.5 + 0.5 * np.sin(rel[:, 0] * 23 + rel[:, 2] * 19) * np.sin(rel[:, 1] * 21)
    disp = feather * (0.09 + 0.07 * locks + 0.04 * curls)
    V = V + Nr * disp[:, None]
    # arm/hand vertices (excluded from the drapery envelope)
    armw = np.zeros(len(V))
    for b, lst in W.items():
        if any(s in b for s in ('arm', 'wrist', 'finger', 'metacarpal', 'hand', 'clavicle', 'shoulder')):
            for i, w in lst: armw[i] += w
    Vh = np.c_[V, np.ones(len(V))]
    # linear blend skinning
    nV = len(V); acc = np.zeros((nV, 3)); wsum = np.zeros(nV)
    for b, lst in W.items():
        if b not in M: continue
        idx = np.array([i for i, w in lst]); w = np.array([w for i, w in lst])
        acc[idx] += (Vh[idx] @ M[b].T)[:, :3] * w[:, None]; wsum[idx] += w
    P = np.where(wsum[:, None] > 0, acc / np.maximum(wsum[:, None], 1e-9), V)
    wh, md, hd, n = palm_frame(M['wrist.R']); n = n * flip
    palm = wh + (md - wh) * 0.5 + n * 0.14 * HAND
    used = sorted(set(i for f in F for i in f))
    remap = {o: k for k, o in enumerate(used)}
    Pb = P[used]; Fb = [[remap[i] for i in f] for f in F]
    return Pb, Fb, palm, n, J, sR, armw[used] > 0.3

def robe(P, J, arm):
    """Himation wrapped around the hips and falling to the floor (MakeHuman units, decimetres). The surface
    follows the per-angle envelope of the hips/legs (arms excluded), so it hugs at the waist and flares below,
    with hanging folds that deepen toward the hem and a rolled band at the top."""
    hipL, hipR = J['upperleg01.L____head'], J['upperleg01.R____head']
    waist = (hipL + hipR) / 2
    floor = P[:, 1].min()
    y0 = waist[1] + 0.9; y1 = floor - 0.05
    cx, cz = waist[0], waist[2]
    Q = P[~arm]
    ny = 34; nt = 96
    A = np.linspace(0, 2 * math.pi, nt, endpoint=False)
    env = np.zeros((ny + 1, nt))
    qa = np.arctan2(Q[:, 2] - cz, Q[:, 0] - cx) % (2 * math.pi)
    qr = np.sqrt((Q[:, 0] - cx) ** 2 + (Q[:, 2] - cz) ** 2)
    for j in range(ny + 1):
        t = j / ny; y = y0 + (y1 - y0) * t
        m = np.abs(Q[:, 1] - y) < 0.45
        for i, a in enumerate(A):
            d = np.abs((qa[m] - a + math.pi) % (2 * math.pi) - math.pi) < 0.2
            env[j, i] = qr[m][d].max() if d.any() else 0.0
    # fill gaps (between the legs) and smooth around + down the robe
    for j in range(ny + 1):
        row = env[j]; mx = row.max()
        row[row < 0.3] = mx * 0.8
        for _ in range(6): row[:] = np.maximum(row, 0.5 * (np.roll(row, 1) + np.roll(row, -1)))
        for _ in range(4): row[:] = (np.roll(row, 1) + 2 * row + np.roll(row, -1)) / 4
    for j in range(1, ny + 1): env[j] = np.maximum(env[j], env[j - 1] * 0.97)    # no waisting below the hips
    rings = []
    for j in range(ny + 1):
        t = j / ny; y = y0 + (y1 - y0) * t
        flare = 0.03 + 1.15 * t ** 1.7
        amp = 0.04 + 0.42 * t ** 1.3
        ring = []
        for i, a in enumerate(A):
            fold = 0.55 * math.cos(a * 9 + 0.6 * math.sin(a * 2) + t * 0.8) + 0.3 * math.cos(a * 15 - t * 1.7) + 0.15 * math.cos(a * 23 + 1.3)
            swag = 0.18 * (1 - t) ** 2 * math.cos(a * 3 + 2.0 + t * 4)      # diagonal pull toward the knot near the top
            r = env[j, i] + flare + amp * fold + swag
            yy = y + (0.25 * t ** 3 * math.cos(a * 9 + 0.6 * math.sin(a * 2)) if j == ny else 0)
            ring.append((cx + r * math.cos(a), yy, cz + r * math.sin(a)))
        rings.append(ring)
    V = [p for r in rings for p in r]
    Fq = [[j * nt + i, j * nt + (i + 1) % nt, (j + 1) * nt + (i + 1) % nt, (j + 1) * nt + i] for j in range(ny) for i in range(nt)]
    # rolled band: a tube following the top ring, sunk into the body so no gap shows from above
    top = np.array(rings[0]); nb = 10; base = len(V)
    for i in range(nt):
        p = top[i]; c = np.array([cx, p[1], cz]); out = p - c; out[1] = 0; out /= np.linalg.norm(out) + 1e-9
        rr = 0.15 + 0.035 * math.sin(i / nt * 2 * math.pi * 7)
        for k in range(nb):
            b = 2 * math.pi * k / nb
            V.append(tuple(p - out * 0.09 + out * math.cos(b) * rr + np.array([0, 1.0, 0]) * math.sin(b) * rr * 0.8))
    for i in range(nt):
        for k in range(nb):
            a = base + i * nb + k; b = base + i * nb + (k + 1) % nb
            c = base + ((i + 1) % nt) * nb + (k + 1) % nb; d = base + ((i + 1) % nt) * nb + k
            Fq.append([a, d, c, b])
    return np.array(V), Fq

if __name__ == '__main__':
    P, F, palm, n, J, sR, arm = main()
    RV, RF = robe(P, J, arm)
    height = P[:, 1].max() - P[:, 1].min()
    k = HEIGHT / height                                   # statue height (m) per MH unit
    floor = P[:, 1].min()
    def to_unity(X): X = (X - [0, floor, 0]) * k; X = X.copy(); X[:, 0] *= -1; return X
    PU = to_unity(P); RU = to_unity(RV); palmU = to_unity(palm[None])[0]; nU = n.copy(); nU[0] *= -1
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def mk(Vu, Fs, name, subdiv):
        Vb = Vu[:, [0, 2, 1]]             # unity -> blender (mirror already applied keeps winding consistent)
        me = bpy.data.meshes.new(name); me.from_pydata(Vb.tolist(), [], [list(reversed(f)) for f in Fs]); me.validate(); me.shade_smooth()
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        if subdiv:
            m = ob.modifiers.new('s', 'SUBSURF'); m.levels = subdiv
            dg = bpy.context.evaluated_depsgraph_get(); me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); ob.modifiers.clear(); ob.data = me2
        return ob
    body = mk(PU, F, 'body', 1)
    rb = mk(RU, RF, 'robe', 1)
    for o in bpy.context.scene.objects: o.select_set(o.type == 'MESH')
    bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
    ob = bpy.context.active_object
    me = ob.data; me.calc_loop_triangles(); print('tris before', len(me.loop_triangles))
    mod = ob.modifiers.new('d', 'DECIMATE'); mod.ratio = min(1.0, 90000 / len(me.loop_triangles))
    dg = bpy.context.evaluated_depsgraph_get(); me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); ob.modifiers.clear(); ob.data = me2
    me2.shade_smooth()
    co = np.empty(len(me2.vertices) * 3, np.float32); me2.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    me2.calc_loop_triangles()
    tri = np.empty(len(me2.loop_triangles) * 3, np.int32); me2.loop_triangles.foreach_get('vertices', tri); tri = tri.reshape(-1, 3)
    # AO bake via the statue pipeline (Unity coords in, AO per vertex out)
    VU = co[:, [0, 2, 1]]; FU = tri[:, [0, 2, 1]]
    ao = 0.3 + 0.7 * ST.ao_bake(VU, FU)
    import trimesh
    N = -np.asarray(trimesh.Trimesh(VU, FU, process=False).vertex_normals)
    ST.write_bytes('Colossus', VU, FU, N, ao)
    # pedestal (stone kit)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ped = K.lathe([(4.7, 0), (4.7, 0.35), (4.4, 0.4), (4.4, 0.75), (4.1, 0.8), (4.0, 0.9), (3.9, 1.5), (4.05, 1.55), (4.2, 1.7), (4.2, 1.8)], 64, 'Marble', name='Colossus_Pedestal')
    K.export_bytes(ped, 'Colossus_Pedestal')
    ex = json.load(open(os.path.join(DATA, 'Kit2Extra.json'))) if os.path.exists(os.path.join(DATA, 'Kit2Extra.json')) else {}
    ex['colossus'] = dict(palm=palmU.round(3).tolist(), palm_normal=(nU / np.linalg.norm(nU)).round(3).tolist(), height=HEIGHT, pedestal=1.8)
    json.dump(ex, open(os.path.join(DATA, 'Kit2Extra.json'), 'w'), indent=1)
    print('colossus palm', palmU.round(2), 'normal', nU.round(2))
