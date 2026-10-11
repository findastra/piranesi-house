"""Render a composition of exported meshes (PMS1 + PMS2) with Cycles for checking.
usage: python3 look.py spec.json out.png
spec: {"objects":[{"mesh":..,"p":[x,y,z],"r":deg,"e":[x,y,z],"s":[sx,sy,sz]}], "layout": bool (include HouseLayout objects
within 'radius' of 'centre'), "centre":[x,z], "radius":r, "cam":{"loc":[x,y,z],"look":[x,y,z],"lens":24},
"res":[w,h], "samples":16, "water":y or null, "sun":[elev, azim]}  (Unity coordinates)"""
import bpy, json, os, sys, struct, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
MESH = os.path.join(ROOT, 'out', 'Meshes'); IMP = os.path.join(ROOT, 'out', 'Imported')
MAN = json.load(open(os.path.join(ROOT, 'out', 'Data', 'Materials.json')))
spec = json.load(open(sys.argv[1])); OUT = sys.argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
COL = {'Floor': (0.82, 0.8, 0.76), 'Wall': (0.78, 0.7, 0.58), 'Marble': (0.9, 0.9, 0.88), 'Gold': (0.85, 0.62, 0.28),
       'Verde': (0.1, 0.25, 0.18), 'Iron': (0.05, 0.05, 0.05), 'Flame': (1, 0.6, 0.2), 'Sand': (0.82, 0.7, 0.52),
       'Glass': (0.7, 0.85, 1.0), 'Glass2': (0.75, 0.88, 0.95), 'Water': (0.75, 0.9, 1.0), 'Stone': (0.66, 0.66, 0.63), 'Statue': (0.92, 0.92, 0.9)}
mats = {}
def stone(n):
    key = 'S_' + n
    if key in mats: return mats[key]
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    c = COL.get(n, (0.8, 0.8, 0.8))
    b.inputs['Roughness'].default_value = 0.45
    if n == 'Gold': b.inputs['Metallic'].default_value = 1
    if n in ('Glass', 'Glass2', 'Water'):
        b.inputs['Transmission Weight'].default_value = 0.9; b.inputs['Roughness'].default_value = 0.05
    if n == 'Flame':
        b.inputs['Emission Color'].default_value = (*c, 1); b.inputs['Emission Strength'].default_value = 8
    attr = nt.nodes.new('ShaderNodeVertexColor'); attr.layer_name = 'Col'
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1
    mix.inputs['A'].default_value = (*c, 1)
    nt.links.new(attr.outputs['Color'], mix.inputs['B']); nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
    mats[key] = m; return m
def manifest_mat(sub, e):
    if sub in mats: return mats[sub]
    m = bpy.data.materials.new(sub); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tint = e.get('tint', [1, 1, 1])
    b.inputs['Base Color'].default_value = (*tint, 1)
    b.inputs['Roughness'].default_value = 1 - e.get('smooth', 0.4)
    if e.get('shader') in ('flow', 'pool'):
        b.inputs['Base Color'].default_value = (0.6, 0.85, 0.95, 1); b.inputs['Transmission Weight'].default_value = 0.6
        b.inputs['Roughness'].default_value = 0.05
    if e.get('shader') == 'coral':
        b.inputs['Base Color'].default_value = (*e.get('tip', [0.9, 0.5, 0.6]), 1)
    alb = e.get('albedo')
    if alb:
        d = os.path.join(IMP, alb) if '/' in alb else None
        if d and os.path.exists(d):
            tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(d)
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1
            nt.links.new(tex.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = (*tint, 1)
            if e.get('vertexTint'):
                attr = nt.nodes.new('ShaderNodeVertexColor'); attr.layer_name = 'Col'
                mix2 = nt.nodes.new('ShaderNodeMix'); mix2.data_type = 'RGBA'; mix2.blend_type = 'MULTIPLY'; mix2.inputs['Factor'].default_value = 0.8
                nt.links.new(mix.outputs['Result'], mix2.inputs['A']); nt.links.new(attr.outputs['Color'], mix2.inputs['B'])
                nt.links.new(mix2.outputs['Result'], b.inputs['Base Color'])
            else:
                nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
            if e.get('alpha') in ('MASK', 'BLEND'):
                nt.links.new(tex.outputs['Alpha'], b.inputs['Alpha'])
    mats[sub] = m; return m
cache = {}
def load(name):
    if name in cache: return cache[name]
    p = os.path.join(MESH, name + '.bytes')
    if not os.path.exists(p): print('missing', name); cache[name] = None; return None
    with open(p, 'rb') as f:
        mg = f.read(4); nv, ns, _ = struct.unpack('<iii', f.read(12))
        P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3); N = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3)
        C = np.frombuffer(f.read(nv * 4), np.uint8).reshape(-1, 4)
        UV = np.frombuffer(f.read(nv * 8), '<f4').reshape(-1, 2) if mg == b'PMS2' else None
        faces = []; fm = []; names = []
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln).decode()
            ni = struct.unpack('<i', f.read(4))[0]; idx = np.frombuffer(f.read(ni * 4), '<i4').reshape(-1, 3)
            faces.append(idx[:, [0, 2, 1]]); fm += [s] * len(idx); names.append(nm)
    F = np.concatenate(faces)
    me = bpy.data.meshes.new(name)
    me.from_pydata(P[:, [0, 2, 1]].tolist(), [], F.tolist())
    ents = {e['sub']: e for e in MAN.get(name.replace('_LOD1', ''), [])}
    for nm in names:
        me.materials.append(manifest_mat(nm, ents[nm]) if nm in ents else stone(nm))
    me.polygons.foreach_set('material_index', np.array(fm, np.int32))
    if mg == b'PMS1':
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); ca.data.foreach_set('color', (C / 255.0).astype(np.float32).ravel())
    else:
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); cc = C[:, [1, 2, 3, 0]] / 255.0; cc[:, 3] = 1
        ca.data.foreach_set('color', cc.astype(np.float32).ravel())
        uvl = me.uv_layers.new(); lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
        uvl.data.foreach_set('uv', UV[lv].ravel())
    me.shade_smooth()
    try: me.normals_split_custom_set_from_vertices(N[:, [0, 2, 1]].tolist())
    except Exception: pass
    cache[name] = me; return me
def euler_unity(x, y, z):
    x, y, z = map(math.radians, (x, y, z))
    Rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz
from mathutils import Matrix
SW = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float)
def inst(o):
    me = load(o['mesh'])
    if me is None: return
    ob = bpy.data.objects.new(o['mesh'], me); sc.collection.objects.link(ob)
    e = o.get('e'); R = euler_unity(*e) if e else euler_unity(90 if o.get('lie') else 0, o.get('r', 0), 0)
    s = o.get('s', [1, 1, 1]); s = [s] * 3 if np.isscalar(s) else s
    Mu = R @ np.diag(s); Mb = SW @ Mu @ SW
    p = o['p']
    M = Matrix(((Mb[0, 0], Mb[0, 1], Mb[0, 2], p[0]), (Mb[1, 0], Mb[1, 1], Mb[1, 2], p[2]), (Mb[2, 0], Mb[2, 1], Mb[2, 2], p[1]), (0, 0, 0, 1)))
    ob.matrix_world = M
objs = list(spec.get('objects', []))
if spec.get('layout'):
    L = json.load(open(os.path.join(ROOT, 'out', 'Data', 'HouseLayout.json')))
    c = spec.get('centre', [0, 0]); rad = spec.get('radius', 1e9)
    for o in L['objects'] + [dict(mesh=s_['mesh'] + '_LOD1', p=s_['p'], r=s_['r'], s=[s_['s']] * 3) for s_ in L['statues']]:
        if not o.get('mesh') or o['mesh'] in spec.get('skip', []): continue
        if math.hypot(o['p'][0] - c[0], o['p'][2] - c[1]) > rad and not o['mesh'].startswith(('Isle_', 'Seabed', 'Slide')): continue
        objs.append(o)
for o in objs: inst(o)
wy = spec.get('water', 0.2)
if wy is not None:
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, wy))
    w = bpy.context.active_object; wm = bpy.data.materials.new('W'); wm.use_nodes = True
    b = wm.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.1, 0.45, 0.5, 1)
    b.inputs['Roughness'].default_value = 0.03; b.inputs['Transmission Weight'].default_value = 0.8; b.inputs['IOR'].default_value = 1.33
    w.data.materials.append(wm)
el, az = spec.get('sun', [40, 30])
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(90 - el), 0, math.radians(az)))
bpy.context.active_object.data.energy = 4.0; bpy.context.active_object.data.angle = 0.03
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.5, 0.65, 0.8, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
cam = bpy.data.cameras.new('c'); cam.lens = spec['cam'].get('lens', 24); cam.clip_end = 5000
co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
loc = spec['cam']['loc']; look = spec['cam']['look']
from mathutils import Vector
lb = Vector((loc[0], loc[2], loc[1])); tb = Vector((look[0], look[2], look[1]))
co.location = lb; co.rotation_euler = (tb - lb).to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'CYCLES'; sc.cycles.samples = spec.get('samples', 16); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3
res = spec.get('res', [960, 540]); sc.render.resolution_x, sc.render.resolution_y = res
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('rendered', OUT)
