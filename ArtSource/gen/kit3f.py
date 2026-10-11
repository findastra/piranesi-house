"""v3 book statues for the roads: the Elephant Carrying a Castle (from the carved elephant, subdivided and turned to marble,
with a little castle on its back) and the Minotaur (the beast figure crowned with bull's horns); sea-worn copies of these
and of the Boy (Statue_Child), plus LOD1s. Statues face +z, base at y = 0 (Unity). Run: python3 gen/kit3f.py"""
import os, sys, json, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import K, bpy, reset, apply, finish
from kit3c import write_pms1, read_full, vertex_normals, noise3, MESH
from math import pi

def ob_arrays(ob):
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); me = ev.to_mesh()
    me.calc_loop_triangles()
    P = np.array([v.co[:] for v in me.vertices], np.float64)
    F = np.array([t.vertices[:] for t in me.loop_triangles], np.int64)
    ev.to_mesh_clear()
    return P, F

def elephant():
    reset()
    bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, '..', 'assets', 'polyhaven', 'carved_wooden_elephant', 'carved_wooden_elephant_2k.gltf'))
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ob = obs[0]
    for o in obs[1:]: o.select_set(True)
    m = ob.modifiers.new('sub', 'SUBSURF'); m.levels = 2; m.render_levels = 2
    bpy.context.view_layer.objects.active = ob
    P, F = ob_arrays(ob)
    # Blender (z up) -> Unity (x, z, y); the elephant's long axis to +z, trunk forward, base on the ground
    P = P @ np.array(ob.matrix_world)[:3, :3].T
    U = np.stack([P[:, 0], P[:, 2], P[:, 1]], 1)
    # long axis -> z (principal axis in the ground plane), centred, base on the ground
    xz = U[:, [0, 2]] - U[:, [0, 2]].mean(0)
    feet = xz[U[:, 1] < U[:, 1].min() + 0.06 * np.ptp(U[:, 1])]                # the four feet set the body's axis
    w, V = np.linalg.eigh(np.cov((feet if len(feet) > 20 else xz).T)); ax = V[:, np.argmax(w)]
    ang = math.atan2(ax[0], ax[1])
    c, s_ = math.cos(-ang), math.sin(-ang)
    x2 = xz[:, 0] * c - xz[:, 1] * s_; z2 = xz[:, 0] * s_ + xz[:, 1] * c
    U = np.stack([x2, U[:, 1], z2], 1)
    U -= np.array([U[:, 0].mean(), U[:, 1].min(), U[:, 2].mean()])
    # the head end stands taller (ears and brow) than the rump: point it to +z
    zr = np.ptp(U[:, 2]); front = U[U[:, 2] > U[:, 2].max() - zr / 3]; rear = U[U[:, 2] < U[:, 2].min() + zr / 3]
    if np.percentile(rear[:, 1], 99) > np.percentile(front[:, 1], 99): U[:, 2] *= -1; U[:, 0] *= -1
    s = 2.2 / np.ptp(U[:, 2]); U *= s                                            # 2.2 m long at scale 1
    F = F[:, [0, 2, 1]]
    # a little castle (howdah tower) on its back
    top = U[np.abs(U[:, 2]) < 0.25]
    back_y = float(np.percentile(top[:, 1], 96)) if len(top) else float(U[:, 1].max())
    reset()
    parts = [K.box(-0.32, 0.32, -0.34, 0.34, 0.0, 0.42, 'Statue', 'keep'), K.box(-0.36, 0.36, -0.38, 0.38, 0.42, 0.5, 'Statue', 'corbel')]
    for k in range(12):                                                          # crenellations
        a = 2 * pi * k / 12
        x, y = 0.3 * math.cos(a), 0.32 * math.sin(a)
        if k % 2 == 0: parts.append(K.box(x - 0.06, x + 0.06, y - 0.06, y + 0.06, 0.5, 0.64, 'Statue', 'merlon'))
    parts.append(K.box(-0.4, 0.4, -0.42, 0.42, -0.06, 0.0, 'Statue', 'saddle'))
    cast = finish(parts, 'castle', export=False)
    C, CF = ob_arrays(cast)
    C = np.stack([C[:, 0], C[:, 2], C[:, 1]], 1); CF = CF[:, [0, 2, 1]]
    C[:, 1] += back_y - 0.04
    P2 = np.vstack([U, C]); F2 = np.vstack([F, CF + len(U)])
    N2 = vertex_normals(P2, F2); Cc = np.full((len(P2), 4), 255, np.uint8)
    write_pms1('Statue_Elephant', P2, N2, Cc, [('Statue', F2)])
    write_pms1('Statue_Elephant_LOD1', P2, N2, Cc, [('Statue', F2)])
    print('Statue_Elephant', len(P2), np.ptp(P2, axis=0).round(2))

def minotaur():
    mg, P, N, C, U, subs = read_full('Statue_Beast')
    F = np.concatenate([s[1] for s in subs])
    mg2, Ph, Nh, Ch, Uh, subs_h = read_full('BullHorns')
    Fh = np.concatenate([s[1] for s in subs_h])
    head = np.array([-0.1, 1.84, -0.17])
    P2 = np.vstack([P, Ph + head]); F2 = np.vstack([F, Fh + len(P)])
    N2 = vertex_normals(P2, F2); C2 = np.vstack([C, Ch])
    write_pms1('Statue_Minotaur', P2, N2, C2, [('Statue', F2)])
    if os.path.exists(os.path.join(MESH, 'Statue_Beast_LOD1.bytes')):
        mgl, Pl, Nl, Cl, Ul, subs_l = read_full('Statue_Beast_LOD1')
        Fl = np.concatenate([s[1] for s in subs_l])
        P3 = np.vstack([Pl, Ph + head]); F3 = np.vstack([Fl, Fh + len(Pl)])
        write_pms1('Statue_Minotaur_LOD1', P3, vertex_normals(P3, F3), np.vstack([Cl, Ch]), [('Statue', F3)])
    print('Statue_Minotaur', len(P2))

def worn(names):
    for st in names:
        mg, P, N, C, U, subs = read_full(st)
        F = np.concatenate([s[1] for s in subs])
        h = P[:, 1].max() - P[:, 1].min()
        n = noise3(P / h, [(9, 1.0), (23, 0.5), (51, 0.25)], sum(map(ord, st)))
        bite = np.clip(n - 0.15, 0, None) * 0.11 * h
        smooth = 0.012 * h * (1 + noise3(P / h, [(4, 1.0)], 7))
        Pw = P - N * (bite + smooth)[:, None]
        top = (P[:, 1] - P[:, 1].min()) / h
        Pw[:, 1] -= np.clip(n * 0.03 * h, 0, None) * top
        Nw = vertex_normals(Pw, F)
        Cw = C.copy(); ao = C[:, 0].astype(np.float64) / 255 * np.clip(1.0 - bite / (0.05 * h + 1e-6) * 0.5, 0.45, 1.0)
        Cw[:, 0] = Cw[:, 1] = Cw[:, 2] = (np.clip(ao, 0, 1) * 255).astype(np.uint8)
        write_pms1(st + '_Worn', Pw, Nw, Cw, [('Statue', F)])
        src = os.path.join(MESH, st + '_LOD1.bytes')
        if os.path.exists(src):
            import shutil; shutil.copy(src, os.path.join(MESH, st + '_Worn_LOD1.bytes'))
        print(st + '_Worn', len(Pw))

if __name__ == '__main__':
    elephant(); minotaur(); worn(['Statue_Elephant', 'Statue_Minotaur', 'Statue_Child'])
    print('kit3f done')
