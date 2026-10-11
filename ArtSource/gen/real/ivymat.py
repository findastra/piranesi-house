"""Ivy mantle: the dense ivy that covers the House's roofs and outer walls.

1. Texture (rendered in Blender): about a thousand scanned English-ivy leaves (the same ambientCG scans as the climbing
   ivy) are laid in overlapping layers over a 1.5 m tile, tips hanging down, with old woody stems beneath, wrapped so
   the tile repeats without a seam. Orthographic renders give the albedo + alpha, the leaves' normals, contact
   occlusion, and a per-leaf 'rank' (higher for leaves on top) that lets the shader thin the mantle leaf by leaf
   toward its edges.
2. Mantles (see mantle.py): offset shells over the real roof and wall geometry, carrying that texture, with a
   coverage value per vertex.

    python3 gen/real/ivymat.py
"""
import os, sys, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import bpy
from mathutils import Vector

ROOT = os.path.join(HERE, '..', '..')
IMP = os.path.join(ROOT, 'out', 'Imported')
OUT = os.path.join(IMP, 'IvyMat')
T = 1.5            # tile size (m)
RES = 2048

def leaf_rects():
    from scipy import ndimage
    a = np.asarray(Image.open(os.path.join(IMP, 'Ivy', 'Ivy_Albedo.png')))[..., 3]
    small = np.asarray(Image.fromarray(a).resize((512, 256)), np.float32) / 255 > 0.4
    lab, n = ndimage.label(small)
    rects = []
    for sl in ndimage.find_objects(lab):
        y0, y1 = sl[0].start, sl[0].stop; x0, x1 = sl[1].start, sl[1].stop
        if (y1 - y0) > 30 and (x1 - x0) > 30:
            rects.append([(x0 - 1) / 512, 1 - (y1 + 1) / 256, (x1 + 1) / 512, 1 - (y0 - 1) / 256])
    return rects

def nrm(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-12)

def build_carpet(seed=7, n_leaves=1150):
    r = np.random.default_rng(seed)
    rects = leaf_rects()
    V = []; UV = []; F = []; COL = []; RANK = []; MAT = []
    def leaf(c, size, ang, tilt, rect, tint, rank):
        # leaf frame: tip direction t in the plane (rotated by ang from -y), tilted up out of the plane by `tilt`
        t = np.array([math.sin(ang), -math.cos(ang), 0.0])
        t = nrm(t * math.cos(tilt) + np.array([0, 0, 1.0]) * math.sin(tilt))
        right = nrm(np.cross(np.array([0, 0, 1.0]), t)); n = nrm(np.cross(t, right))
        asp = (rect[2] - rect[0]) * 2048 / ((rect[3] - rect[1]) * 1024)
        h = size; w = size * asp
        fold = 0.14 * size; droop = r.uniform(0.04, 0.16) * h
        base = c - t * h * 0.15
        um = (rect[0] + rect[2]) / 2
        P = [base - right * w / 2, base + n * fold, base + right * w / 2,
             base + t * h - right * w / 2 - n * droop, base + t * h + n * fold - n * droop, base + t * h + right * w / 2 - n * droop]
        U = [(rect[0], rect[1]), (um, rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (um, rect[3]), (rect[2], rect[3])]
        b = len(V)
        V.extend(P); UV.extend(U); COL.extend([tint] * 6); RANK.extend([rank] * 6)
        for f in ((0, 1, 4, 3), (1, 2, 5, 4)): F.append(tuple(b + i for i in f)); MAT.append(0)
    leaves = []
    for k in range(n_leaves):
        layer = r.random() ** 0.8                                   # 0 bottom .. 1 top
        z = 0.005 + 0.075 * layer
        size = r.uniform(0.055, 0.1) * (0.8 + 0.45 * layer)
        ang = r.normal(0, 0.75) + (math.pi if r.random() < 0.06 else 0)   # tips mostly hanging down
        tilt = math.radians(r.uniform(6, 34))
        rect = rects[r.integers(len(rects))]
        dark = 0.62 + 0.38 * layer
        if r.random() < 0.025: tint = (1.0 * dark, 0.72 * dark, 0.45 * dark)      # a bronze leaf
        elif r.random() < 0.06: tint = (1.05, 1.12, 0.8)                          # young lime leaf
        else:
            v = r.uniform(0.88, 1.06); tint = (dark * v, dark * v * r.uniform(0.97, 1.04), dark * v * 0.95)
        rank = float(np.clip(0.25 + 0.7 * layer + r.normal(0, 0.06), 0.2, 1.0))
        leaves.append((np.array([r.uniform(0, T), r.uniform(0, T), z]), size, ang, tilt, rect, tint, rank))
    leaves.sort(key=lambda L: L[0][2])
    for (c, size, ang, tilt, rect, tint, rank) in leaves:
        for dx in (-T, 0, T):
            for dy in (-T, 0, T):
                cc = c + np.array([dx, dy, 0])
                if -0.2 < cc[0] < T + 0.2 and -0.2 < cc[1] < T + 0.2:
                    leaf(cc, size, ang, tilt, rect, tint, rank)
    # woody stems meandering under the leaves (wrapped)
    S = []
    for k in range(26):
        p = np.array([r.uniform(0, T), r.uniform(0, T), 0.004]); d = nrm(np.array([r.normal() * 0.6, r.choice([-1, 1]), 0]))
        pts = [p.copy()]
        for j in range(int(r.uniform(0.8, 2.2) / 0.03)):
            d = nrm(d + np.array([r.normal() * 0.25, r.normal() * 0.25, 0])); d[2] = 0
            p = p + d * 0.03; pts.append(p.copy())
        S.append((np.array(pts), r.uniform(0.003, 0.007)))
    for (P, rad) in S:
        for dx in (-T, 0, T):
            for dy in (-T, 0, T):
                Q = P + np.array([dx, dy, 0])
                if Q[:, 0].max() < -0.1 or Q[:, 0].min() > T + 0.1 or Q[:, 1].max() < -0.1 or Q[:, 1].min() > T + 0.1: continue
                for i in range(len(Q) - 1):
                    a, b = Q[i], Q[i + 1]
                    tg = nrm(b - a); sd = nrm(np.cross(np.array([0, 0, 1.0]), tg)) * rad
                    bi = len(V)
                    V.extend([a - sd, a + sd + np.array([0, 0, rad]), b + sd + np.array([0, 0, rad]), b - sd])
                    UV.extend([(0.99, 0.99)] * 4); COL.extend([(0.38, 0.3, 0.22)] * 4); RANK.extend([0.55] * 4)
                    F.append((bi, bi + 1, bi + 2, bi + 3)); MAT.append(1)
    print(f'  carpet: {len(leaves)} leaves (+ wrap copies), {len(F)} faces', flush=True)
    return np.array(V), np.array(UV), F, np.array(COL), np.array(RANK), MAT

def scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = 24; sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 2; sc.cycles.transparent_max_bounces = 64
    sc.render.film_transparent = True
    sc.render.filter_size = 0.8
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.color_mode = 'RGBA'; sc.render.image_settings.color_depth = '16'
    sc.render.resolution_x = sc.render.resolution_y = RES
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = T
    co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
    co.location = (T / 2, T / 2, 2.0); co.rotation_euler = (0, 0, 0)
    return sc

def make_mesh(V, UV, F, COL, RANK, MAT):
    me = bpy.data.meshes.new('carpet'); me.from_pydata(V.tolist(), [], [list(f) for f in F])
    uvl = me.uv_layers.new(name='UVMap')
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    uvl.data.foreach_set('uv', UV[lv].astype(np.float32).ravel())
    ca = me.color_attributes.new('tint', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.concatenate([COL, np.ones((len(COL), 1))], 1).astype(np.float32).ravel())
    ra = me.color_attributes.new('rank', 'FLOAT_COLOR', 'POINT')
    ra.data.foreach_set('color', np.stack([RANK] * 3 + [np.ones(len(RANK))], 1).astype(np.float32).ravel())
    me.polygons.foreach_set('material_index', np.array(MAT, np.int32))
    me.shade_smooth()
    ob = bpy.data.objects.new('carpet', me); bpy.context.scene.collection.objects.link(ob)
    return ob

def set_material(ob, mode):
    """mode: albedo | normal | rank | ao | smooth -> an emission shader that writes that quantity, clipped by the leaf alpha."""
    me = ob.data
    me.materials.clear()
    alb = bpy.data.images.load(os.path.join(IMP, 'Ivy', 'Ivy_Albedo.png'), check_existing=True)
    nim = bpy.data.images.load(os.path.join(IMP, 'Ivy', 'Ivy_Normal.png'), check_existing=True); nim.colorspace_settings.name = 'Non-Color'
    mim = bpy.data.images.load(os.path.join(IMP, 'Ivy', 'Ivy_Mask.png'), check_existing=True); mim.colorspace_settings.name = 'Non-Color'
    for which in ('leaf', 'stem'):
        m = bpy.data.materials.new(f'{mode}_{which}'); m.use_nodes = True
        nt = m.node_tree; N = nt.nodes; L = nt.links
        for nd in list(N): N.remove(nd)
        out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.0
        uv = N.new('ShaderNodeUVMap')
        ta = N.new('ShaderNodeTexImage'); ta.image = alb; ta.interpolation = 'Cubic'; L.new(uv.outputs[0], ta.inputs[0])
        tint = N.new('ShaderNodeVertexColor'); tint.layer_name = 'tint'
        rank = N.new('ShaderNodeVertexColor'); rank.layer_name = 'rank'
        if mode == 'albedo':
            if which == 'leaf':
                mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
                L.new(ta.outputs['Color'], mul.inputs[6]); L.new(tint.outputs['Color'], mul.inputs[7]); L.new(mul.outputs[2], em.inputs['Color'])
            else:
                L.new(tint.outputs['Color'], em.inputs['Color'])
        elif mode == 'normal':
            vm = N.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY_ADD'
            vm.inputs[1].default_value = (0.5, 0.5, 0.5); vm.inputs[2].default_value = (0.5, 0.5, 0.5)
            if which == 'leaf':
                tn = N.new('ShaderNodeTexImage'); tn.image = nim; L.new(uv.outputs[0], tn.inputs[0])
                nm = N.new('ShaderNodeNormalMap'); L.new(tn.outputs['Color'], nm.inputs['Color'])
                L.new(nm.outputs[0], vm.inputs[0])
            else:
                geo = N.new('ShaderNodeNewGeometry'); L.new(geo.outputs['Normal'], vm.inputs[0])
            L.new(vm.outputs[0], em.inputs['Color'])
        elif mode == 'rank':
            L.new(rank.outputs['Color'], em.inputs['Color'])
        elif mode == 'ao':
            ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 16; ao.inputs['Distance'].default_value = 0.06
            L.new(ao.outputs['AO'], em.inputs['Color'])
        elif mode == 'smooth':
            if which == 'leaf':
                tm = N.new('ShaderNodeTexImage'); tm.image = mim; L.new(uv.outputs[0], tm.inputs[0])
                sp = N.new('ShaderNodeSeparateColor'); L.new(tm.outputs['Color'], sp.inputs[0])
                L.new(sp.outputs[0], em.inputs['Color'])
            else:
                em.inputs['Color'].default_value = (0.2, 0.2, 0.2, 1)
        if which == 'leaf':
            gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5
            L.new(ta.outputs['Alpha'], gt.inputs[0])
            tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
            L.new(gt.outputs[0], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
            L.new(mx.outputs[0], out.inputs[0])
        else:
            L.new(em.outputs[0], out.inputs[0])
        me.materials.append(m)

def render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    a = np.asarray(Image.open(path), np.float32)
    a = a / (65535.0 if a.max() > 255 else 255.0)
    return a

def main():
    os.makedirs(OUT, exist_ok=True)
    V, UV, F, COL, RANK, MAT = build_carpet()
    tmp = os.path.join(OUT, '_tmp'); os.makedirs(tmp, exist_ok=True)
    sc = scene(); ob = make_mesh(V, UV, F, COL, RANK, MAT)
    res = {}
    for mode in ('albedo', 'normal', 'rank', 'ao', 'smooth'):
        set_material(ob, mode)
        sc.view_settings.view_transform = 'Standard'
        if mode != 'albedo':
            sc.display_settings.display_device = 'sRGB'; sc.view_settings.view_transform = 'Raw'
        sc.cycles.samples = 32 if mode == 'ao' else 16
        res[mode] = render(os.path.join(tmp, f'{mode}.png'))
        print('  rendered', mode, flush=True)
    A = res['albedo']; alpha = A[..., 3]
    un = lambda x: x[..., :3]                                          # Blender writes PNGs with straight alpha
    from scipy import ndimage
    solid = alpha > 0.5
    idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
    fill = lambda x: x[idx[0], idx[1]]
    col = fill(un(A)); nm = fill(un(res['normal'])); rk = fill(un(res['rank']))[..., 0]
    ao = fill(un(res['ao']))[..., 0]; sm = fill(un(res['smooth']))[..., 0]
    # albedo: written in display space by the 'Standard' transform already
    Image.fromarray((np.concatenate([np.clip(col, 0, 1), alpha[..., None]], -1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'IvyMat_Albedo.png'))
    nmv = nm * 2 - 1; nmv /= np.linalg.norm(nmv, axis=-1, keepdims=True) + 1e-6
    Image.fromarray(((nmv * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, 'IvyMat_Normal.png'))
    ao = 0.45 + 0.55 * np.clip(ao, 0, 1)
    mk = np.stack([np.clip(sm * 0.9, 0, 1), ao, np.clip(rk, 0, 1), np.ones_like(ao)], -1)
    Image.fromarray((mk * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'IvyMat_Mask.png'))
    print('ivy mantle texture written; coverage', round(float(solid.mean()), 3))

if __name__ == '__main__':
    main()
