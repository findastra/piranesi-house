"""Textured preview of exported House props: loads PMS2 meshes (positions, normals, UVs, submeshes) back into Blender,
rebuilds each submesh's material from the manifest (albedo x tint, GL normal map, mask R smooth / G ao / B metal,
alpha clip, foliage translucency) and renders them in daylight with Cycles - so a prop is judged the way it will
look in the world, not as grey geometry.

    python3 gen/real/preview.py out.png WaterLily [WaterLily_Pink ...] [--water] [--table] [--cam ex,ey,ez:lx,ly,lz]
"""
import os, sys, json, math, struct
import numpy as np
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
MESH = os.path.join(ROOT, 'out', 'Meshes')
IMP = os.path.join(ROOT, 'out', 'Imported')
MAN = os.path.join(ROOT, 'out', 'Data', 'Materials.json')

def load_pms(name):
    """-> P (Blender space), N, UV, list of (sub name, tris)"""
    with open(os.path.join(MESH, name + '.bytes'), 'rb') as f:
        mg = f.read(4); nv, ns, fl = struct.unpack('<iii', f.read(12))
        P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3).astype(float)
        N = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3).astype(float)
        C = np.frombuffer(f.read(nv * 4), np.uint8).reshape(-1, 4)
        U = np.frombuffer(f.read(nv * 8), '<f4').reshape(-1, 2).astype(float) if mg == b'PMS2' else np.zeros((nv, 2))
        subs = []
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln).decode(); ni = struct.unpack('<i', f.read(4))[0]
            subs.append((nm, np.frombuffer(f.read(ni * 4), '<i4').reshape(-1, 3)[:, [0, 2, 1]]))
    # Unity (x, y up, z) -> Blender (x, y = Unity z, z up); the exporter swapped y/z and flipped winding
    return P[:, [0, 2, 1]], N[:, [0, 2, 1]], U, subs, C

def manifest():
    return json.load(open(MAN))

def _img(rel, linear=False):
    if not rel: return None
    p = rel if os.path.isabs(rel) else os.path.join(IMP, rel)
    if not os.path.exists(p): return None
    im = bpy.data.images.load(p, check_existing=True)
    if linear: im.colorspace_settings.name = 'Non-Color'
    return im

def make_material(mesh, e):
    m = bpy.data.materials.new(e['sub']); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bs = N['Principled BSDF']; out = N['Material Output']
    sh = e.get('shader', 'prop')
    d = e.get('dir') or mesh
    rel = lambda p: (p if (not p or '/' in p) else f'{d}/{p}')
    tint = list(e.get('tint', [1, 1, 1]))[:3] + [1]
    uv = N.new('ShaderNodeUVMap')
    alb = _img(rel(e.get('albedo')))
    tintn = N.new('ShaderNodeRGB'); tintn.outputs[0].default_value = tint
    if alb:
        t = N.new('ShaderNodeTexImage'); t.image = alb; L.new(uv.outputs[0], t.inputs[0])
        mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
        L.new(t.outputs['Color'], mul.inputs[6]); L.new(tintn.outputs[0], mul.inputs[7]); L.new(mul.outputs[2], bs.inputs['Base Color'])
        if e.get('alpha') in ('MASK', 'BLEND') or sh == 'foliage':
            L.new(t.outputs['Alpha'], bs.inputs['Alpha'])
    else:
        bs.inputs['Base Color'].default_value = tint
    sm = float(e.get('smooth', 0.45 if sh != 'foliage' else 0.6))
    mk = _img(rel(e.get('mask')), True)
    if mk:
        t = N.new('ShaderNodeTexImage'); t.image = mk; L.new(uv.outputs[0], t.inputs[0])
        sp = N.new('ShaderNodeSeparateColor'); L.new(t.outputs['Color'], sp.inputs[0])
        if sh == 'prop' and 'smooth' not in e: sm = 1.0
        mr = N.new('ShaderNodeMath'); mr.operation = 'MULTIPLY'; mr.inputs[1].default_value = sm; L.new(sp.outputs[0], mr.inputs[0])
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; L.new(mr.outputs[0], inv.inputs[1])
        L.new(inv.outputs[0], bs.inputs['Roughness'])
        metal = float(e.get('metal', 1.0 if sh == 'prop' else 0.0))
        mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = metal; L.new(sp.outputs[2], mm.inputs[0])
        L.new(mm.outputs[0], bs.inputs['Metallic'])
    else:
        bs.inputs['Roughness'].default_value = 1 - min(sm, 1.0)
        bs.inputs['Metallic'].default_value = float(e.get('metal', 0.0))
    nm = _img(rel(e.get('normal')), True)
    if nm:
        t = N.new('ShaderNodeTexImage'); t.image = nm; L.new(uv.outputs[0], t.inputs[0])
        nn = N.new('ShaderNodeNormalMap'); L.new(t.outputs['Color'], nn.inputs['Color']); L.new(nn.outputs[0], bs.inputs['Normal'])
    if sh == 'ivymat' and alb:
        vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
        mk2 = _img(rel(e.get('mask')), True)
        t2 = N.new('ShaderNodeTexImage'); t2.image = mk2; L.new(uv.outputs[0], t2.inputs[0])
        sp2 = N.new('ShaderNodeSeparateColor'); L.new(t2.outputs['Color'], sp2.inputs[0])
        thr = N.new('ShaderNodeMath'); thr.operation = 'MULTIPLY_ADD'      # (1 - cov) * 0.85 + 0.1
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; L.new(vc.outputs['Alpha'], inv.inputs[1])
        L.new(inv.outputs[0], thr.inputs[0]); thr.inputs[1].default_value = 0.85; thr.inputs[2].default_value = 0.1
        gt1 = N.new('ShaderNodeMath'); gt1.operation = 'GREATER_THAN'; L.new(sp2.outputs[2], gt1.inputs[0]); L.new(thr.outputs[0], gt1.inputs[1])
        a1 = [n for n in N if n.type == 'TEX_IMAGE' and n.image == alb][0]
        gt2 = N.new('ShaderNodeMath'); gt2.operation = 'GREATER_THAN'; gt2.inputs[1].default_value = 0.5; L.new(a1.outputs['Alpha'], gt2.inputs[0])
        both = N.new('ShaderNodeMath'); both.operation = 'MULTIPLY'; L.new(gt1.outputs[0], both.inputs[0]); L.new(gt2.outputs[0], both.inputs[1])
        trn = N.new('ShaderNodeBsdfTranslucent'); L.new(bs.inputs['Base Color'].links[0].from_socket, trn.inputs['Color'])
        mix = N.new('ShaderNodeMixShader'); mix.inputs[0].default_value = 0.15; L.new(bs.outputs[0], mix.inputs[1]); L.new(trn.outputs[0], mix.inputs[2])
        tp = N.new('ShaderNodeBsdfTransparent'); mx2 = N.new('ShaderNodeMixShader')
        L.new(both.outputs[0], mx2.inputs[0]); L.new(tp.outputs[0], mx2.inputs[1]); L.new(mix.outputs[0], mx2.inputs[2]); L.new(mx2.outputs[0], out.inputs[0])
        bs.inputs['Metallic'].default_value = 0.0
        if bs.inputs['Metallic'].links: nt.links.remove(bs.inputs['Metallic'].links[0])
        return m
    if sh == 'foliage':
        tr = float(e.get('translucency', 0.6))
        try:
            bs.inputs['Subsurface Weight'].default_value = min(0.5, tr * 0.3)
            bs.inputs['Subsurface Radius'].default_value = (0.01, 0.01, 0.004)
        except Exception: pass
        # thin translucent leaf: mix in a translucent BSDF tinted by the albedo
        trn = N.new('ShaderNodeBsdfTranslucent')
        if alb: L.new(bs.inputs['Base Color'].links[0].from_socket, trn.inputs['Color'])
        mix = N.new('ShaderNodeMixShader'); mix.inputs[0].default_value = min(0.45, tr * 0.25)
        L.new(bs.outputs[0], mix.inputs[1]); L.new(trn.outputs[0], mix.inputs[2])
        # alpha clip via a transparent mix
        if alb:
            tp = N.new('ShaderNodeBsdfTransparent'); mx2 = N.new('ShaderNodeMixShader')
            gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = float(e.get('cutoff', 0.45))
            L.new(bs.inputs['Alpha'].links[0].from_socket, gt.inputs[0]); L.new(gt.outputs[0], mx2.inputs[0])
            L.new(tp.outputs[0], mx2.inputs[1]); L.new(mix.outputs[0], mx2.inputs[2]); L.new(mx2.outputs[0], out.inputs[0])
        else:
            L.new(mix.outputs[0], out.inputs[0])
    elif e.get('alpha') == 'MASK' and alb:
        tp = N.new('ShaderNodeBsdfTransparent'); mx2 = N.new('ShaderNodeMixShader')
        gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5
        L.new(bs.inputs['Alpha'].links[0].from_socket, gt.inputs[0]); L.new(gt.outputs[0], mx2.inputs[0])
        L.new(tp.outputs[0], mx2.inputs[1]); L.new(bs.outputs[0], mx2.inputs[2]); L.new(mx2.outputs[0], out.inputs[0])
    if sh == 'coral':
        bs.inputs['Base Color'].default_value = list(e.get('base', [0.55, 0.35, 0.45])) + [1]
    return m

def add_prop(name, loc=(0, 0, 0), yaw=0.0, scale=1.0, man=None):
    man = man or manifest()
    P, Nn, U, subs, C = load_pms(name)
    F = np.concatenate([t for _, t in subs]); mi = np.concatenate([np.full(len(t), k) for k, (_, t) in enumerate(subs)])
    me = bpy.data.meshes.new(name); me.from_pydata(P.tolist(), [], F.tolist())
    uvl = me.uv_layers.new(name='UVMap')
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    uvl.data.foreach_set('uv', U[lv].astype(np.float32).ravel())
    ents = {e['sub']: e for e in man.get(name, [])}
    for nm, _ in subs:
        e = ents.get(nm, dict(sub=nm))
        me.materials.append(make_material(name, e))
    me.polygons.foreach_set('material_index', mi.astype(np.int32))
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', (C.astype(np.float32) / 255).ravel())
    me.shade_smooth()
    try:
        me.normals_split_custom_set_from_vertices(Nn.tolist())
    except Exception: pass
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (0, 0, math.radians(yaw)); ob.scale = (scale,) * 3
    return ob

def scene(samples=48, sun_elev=38, sun_az=140, exposure=0.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 12
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = exposure
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky')
    try:
        sky.sky_type = 'NISHITA'; sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_az)
        sky.sun_disc = False
    except Exception: pass
    bg = nt.nodes['Background']; bg.inputs['Strength'].default_value = 0.35
    nt.links.new(sky.outputs[0], bg.inputs[0])
    sd = bpy.data.lights.new('sun', 'SUN'); sd.energy = 4.0; sd.angle = math.radians(1.5)
    so = bpy.data.objects.new('sun', sd); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(90 - sun_elev), 0, math.radians(sun_az + 90))
    return sc

def ground(kind='marble', z=0.0, size=6):
    m = bpy.data.materials.new(kind); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    me = bpy.data.meshes.new(kind)
    s = size
    if kind == 'water':
        # a water surface with a pale stone floor 0.5 m below
        me.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
        b.inputs['Base Color'].default_value = (0.05, 0.16, 0.15, 1); b.inputs['Roughness'].default_value = 0.04
        b.inputs['IOR'].default_value = 1.33
        try: b.inputs['Transmission Weight'].default_value = 1.0
        except Exception: pass
        # ripples
        tex = m.node_tree.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 6
        bump = m.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08
        m.node_tree.links.new(tex.outputs[0], bump.inputs['Height']); m.node_tree.links.new(bump.outputs[0], b.inputs['Normal'])
        vol = m.node_tree.nodes.new('ShaderNodeVolumeAbsorption'); vol.inputs['Color'].default_value = (0.35, 0.75, 0.7, 1); vol.inputs['Density'].default_value = 1.2
        m.node_tree.links.new(vol.outputs[0], m.node_tree.nodes['Material Output'].inputs['Volume'])
        me.materials.append(m)
        ob = bpy.data.objects.new(kind, me); bpy.context.scene.collection.objects.link(ob)
        # closed water body so the absorption volume has an inside
        bm = bpy.data.meshes.new('wb'); d = 0.6
        bm.from_pydata([(-s, -s, z - d), (s, -s, z - d), (s, s, z - d), (-s, s, z - d)], [], [(3, 2, 1, 0)])
        bm.materials.append(m); bo = bpy.data.objects.new('wb', bm); bpy.context.scene.collection.objects.link(bo)
        fl = bpy.data.materials.new('floor'); fl.use_nodes = True
        fb = fl.node_tree.nodes['Principled BSDF']; fb.inputs['Base Color'].default_value = (0.62, 0.6, 0.55, 1); fb.inputs['Roughness'].default_value = 0.7
        fm = bpy.data.meshes.new('floor'); fm.from_pydata([(-s, -s, z - d - 0.01), (s, -s, z - d - 0.01), (s, s, z - d - 0.01), (-s, s, z - d - 0.01)], [], [(0, 1, 2, 3)])
        fm.materials.append(fl); fo = bpy.data.objects.new('floor', fm); bpy.context.scene.collection.objects.link(fo)
        return ob
    me.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    col = {'marble': (0.82, 0.8, 0.76, 1), 'sand': (0.72, 0.6, 0.42, 1), 'dark': (0.12, 0.12, 0.13, 1)}[kind]
    b.inputs['Base Color'].default_value = col; b.inputs['Roughness'].default_value = 0.35 if kind == 'marble' else 0.8
    me.materials.append(m)
    ob = bpy.data.objects.new(kind, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def camera(eye, target, lens=50, res=(900, 600)):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('cam'); cd.lens = lens; cd.clip_start = 0.005
    co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = res
    return co

def frame(objs, view=(0.0, -1.0, 0.6), lens=50, res=(900, 600), pad=1.15):
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for o in objs:
        for c in o.bound_box:
            p = np.array(o.matrix_world @ Vector(c)); lo = np.minimum(lo, p); hi = np.maximum(hi, p)
    c = (lo + hi) / 2; r = np.linalg.norm(hi - lo) / 2 * pad
    d = np.asarray(view, float); d /= np.linalg.norm(d)
    fov = 2 * math.atan(36 / 2 / lens) * min(1.0, res[1] / res[0]) if res[0] > res[1] else 2 * math.atan(36 / 2 / lens)
    dist = r / math.sin(fov / 2)
    return camera(tuple(c + d * dist), tuple(c), lens, res)

def render(path):
    bpy.context.scene.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
    return path

if __name__ == '__main__':
    args = sys.argv[1:]
    out = args[0]; names = [a for a in args[1:] if not a.startswith('--')]
    flags = [a for a in args[1:] if a.startswith('--')]
    scene(samples=int(next((f.split('=')[1] for f in flags if f.startswith('--samples=')), 40)))
    if '--water' in flags: ground('water')
    elif '--sand' in flags: ground('sand')
    else: ground('marble')
    man = manifest()
    obs = []; x = 0.0
    for n in names:
        o = add_prop(n, man=man)
        w = o.dimensions[0]
        o.location = (x + w / 2, 0, 0); x += w + 0.15 * max(w, 0.2)
        obs.append(o)
    cam = next((f for f in flags if f.startswith('--cam=')), None)
    res = tuple(int(v) for v in next((f.split('=')[1] for f in flags if f.startswith('--res=')), '900x600').split('x'))
    if cam:
        e, t = cam.split('=')[1].split(':'); camera(tuple(map(float, e.split(','))), tuple(map(float, t.split(','))), res=res)
    else:
        frame(obs, res=res)
    render(out)
