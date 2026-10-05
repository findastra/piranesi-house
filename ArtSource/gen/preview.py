"""Assemble HouseLayout.json in Blender and render quick Cycles previews (sanity check before Unity)."""
import bpy, json, os, struct, numpy as np, math, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MESH = os.path.join(HERE, '..', 'out', 'Meshes')
L = json.load(open(os.path.join(HERE, '..', 'out', 'Data', 'HouseLayout.json')))
OUTP = sys.argv[1] if len(sys.argv) > 1 else '/tmp/preview.png'
VIEW = sys.argv[2] if len(sys.argv) > 2 else 'spawn'
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

COLORS = {'Floor': (0.8, 0.8, 0.78), 'Wall': (0.78, 0.72, 0.62), 'Marble': (0.88, 0.88, 0.86), 'Gold': (0.8, 0.6, 0.25),
          'Verde': (0.08, 0.2, 0.14), 'Iron': (0.05, 0.05, 0.05), 'Flame': (1, 0.6, 0.2), 'Sand': (0.75, 0.65, 0.5),
          'Glass': (0.7, 0.85, 1.0), 'Water': (0.8, 0.9, 1.0), 'Stone': (0.66, 0.66, 0.63), 'Statue': (0.9, 0.9, 0.88)}
mats = {}
def getmat(n):
    if n in mats: return mats[n]
    m = bpy.data.materials.new(n); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*COLORS.get(n, (0.8, 0.8, 0.8)), 1)
    b.inputs['Roughness'].default_value = 0.3
    if n == 'Gold': b.inputs['Metallic'].default_value = 1
    if n in ('Flame', 'Glass'):
        b.inputs['Emission Color'].default_value = (*COLORS[n], 1); b.inputs['Emission Strength'].default_value = 6 if n == 'Flame' else 3
    # vertex AO multiply
    attr = nt.nodes.new('ShaderNodeVertexColor'); attr.layer_name = 'Col'
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1
    mix.inputs['A'].default_value = (*COLORS.get(n, (0.8, 0.8, 0.8)), 1)
    nt.links.new(attr.outputs['Color'], mix.inputs['B']); nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
    mats[n] = m; return m

cache = {}
def load(name):
    if name in cache: return cache[name]
    with open(os.path.join(MESH, name + '.bytes'), 'rb') as f:
        assert f.read(4) == b'PMS1'
        nv, ns, _ = struct.unpack('<iii', f.read(12))
        P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3)
        N = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3)
        C = np.frombuffer(f.read(nv * 4), np.uint8).reshape(-1, 4)
        faces = []; fm = []; names = []
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln).decode()
            ni = struct.unpack('<i', f.read(4))[0]; idx = np.frombuffer(f.read(ni * 4), '<i4').reshape(-1, 3)
            faces.append(idx[:, [0, 2, 1]]); fm += [s] * len(idx); names.append(nm)
    F = np.concatenate(faces)
    me = bpy.data.meshes.new(name)
    me.from_pydata(P[:, [0, 2, 1]].tolist(), [], F.tolist())
    for nm in names: me.materials.append(getmat(nm))
    me.polygons.foreach_set('material_index', np.array(fm, np.int32))
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); ca.data.foreach_set('color', (C / 255.0).astype(np.float32).ravel())
    me.shade_smooth()
    me.normals_split_custom_set_from_vertices(N[:, [0, 2, 1]].tolist())
    cache[name] = me; return me

def inst(mesh, p, ry, s):
    me = load(mesh)
    ob = bpy.data.objects.new(mesh, me); sc.collection.objects.link(ob)
    ob.location = (p[0], p[2], p[1]); ob.rotation_euler = (0, 0, math.radians(-ry))
    ob.scale = (s[0], s[2], s[1])
    return ob

for o in L['objects']:
    if not o['mesh'] or o['mesh'] in ('Seabed',) or o['mesh'].startswith('Wing'): continue
    ob = inst(o['mesh'], o['p'], o['r'], o['s'])
    if o.get('lie'): ob.rotation_euler[0] = math.pi / 2
for s in L['statues']:
    inst(s['mesh'] + '_LOD1', s['p'], s['r'], [s['s']] * 3)
for l in L['lights']:
    bpy.ops.object.light_add(type='POINT', location=(l['p'][0], l['p'][2], l['p'][1]))
    lt = bpy.context.active_object.data; lt.energy = 250; lt.color = l['color']; lt.shadow_soft_size = 0.2
# water
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0.35))
w = bpy.context.active_object; wm = bpy.data.materials.new('W'); wm.use_nodes = True
b = wm.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.1, 0.5, 0.55, 1)
b.inputs['Roughness'].default_value = 0.02; b.inputs['Transmission Weight'].default_value = 0.85; b.inputs['IOR'].default_value = 1.33
w.data.materials.append(wm)
# sun + sky
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(35), math.radians(10), math.radians(40)))
bpy.context.active_object.data.energy = 4.0; bpy.context.active_object.data.angle = 0.02
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.45, 0.6, 0.75, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.2
# camera
cam = bpy.data.cameras.new('c'); cam.lens = 18
co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
sp = L['spawn']
if VIEW == 'spawn':
    co.location = (sp['p'][0], sp['p'][2], 1.7); co.rotation_euler = (math.radians(92), 0, math.radians(90))
elif VIEW == 'arcade':
    co.location = (-60 + 0, -30 + 16, 1.7); co.rotation_euler = (math.radians(95), 0, math.radians(180))
elif VIEW == 'aerial':
    cam.lens = 24; co.location = (-160, -120, 110); co.rotation_euler = (math.radians(58), 0, math.radians(-53))
elif VIEW == 'vault':
    co.location = (0, 0, 1.7); co.rotation_euler = (math.radians(150), 0, math.radians(90))
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('SAMPLES', 24)); sc.cycles.use_denoising = True
sc.render.resolution_x = 800; sc.render.resolution_y = 450
sc.cycles.max_bounces = 4
sc.render.filepath = OUTP
bpy.ops.render.render(write_still=True)
print('rendered', OUTP)
