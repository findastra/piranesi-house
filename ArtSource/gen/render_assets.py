"""Render a contact sheet of exported meshes (PMS1/PMS2) with their manifest textures (Cycles)."""
import bpy, os, sys, json, struct, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
MESH = os.path.join(ROOT, 'out', 'Meshes'); IMP = os.path.join(ROOT, 'out', 'Imported')
MAN = json.load(open(os.path.join(ROOT, 'out', 'Data', 'Materials.json')))

def read_pms(path):
    with open(path, 'rb') as f:
        magic = f.read(4); nv, ns, flags = struct.unpack('<iii', f.read(12))
        P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3); N = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3)
        C = np.frombuffer(f.read(nv * 4), np.uint8).reshape(-1, 4)
        UV = np.frombuffer(f.read(nv * 8), '<f4').reshape(-1, 2) if magic == b'PMS2' else np.zeros((nv, 2), np.float32)
        subs = []
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln).decode()
            ni = struct.unpack('<i', f.read(4))[0]; idx = np.frombuffer(f.read(ni * 4), '<i4').reshape(-1, 3)
            subs.append((nm, idx))
    return P, N, C, UV, subs

def material(sub, entry):
    m = bpy.data.materials.new(sub); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tint = entry.get('tint', [1, 1, 1]) if entry else [0.85, 0.85, 0.82]
    b.inputs['Base Color'].default_value = (*tint, 1)
    b.inputs['Roughness'].default_value = 1 - entry.get('smooth', 0.4) if entry else 0.5
    if entry and entry.get('albedo'):
        d = os.path.join(IMP, entry['albedo']) if '/' in entry['albedo'] else os.path.join(IMP, sub.rsplit('_', 1)[0], entry['albedo'])
        if os.path.exists(d):
            tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(d)
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1
            nt.links.new(tex.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = (*tint, 1)
            nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
            if entry.get('alpha') == 'MASK':
                nt.links.new(tex.outputs['Alpha'], b.inputs['Alpha'])
    if entry and entry.get('shader') == 'coral':
        b.inputs['Base Color'].default_value = (0.8, 0.5, 0.6, 1)
    return m

def load(name):
    P, N, C, UV, subs = read_pms(os.path.join(MESH, name + '.bytes'))
    entries = {e['sub']: e for e in MAN.get(name, [])}
    me = bpy.data.meshes.new(name)
    Pb = P[:, [0, 2, 1]]
    faces = []; mi = []
    for k, (nm, idx) in enumerate(subs):
        faces += idx[:, [0, 2, 1]].tolist(); mi += [k] * len(idx)
        me.materials.append(material(nm, entries.get(nm)))
    me.from_pydata(Pb.tolist(), [], faces)
    me.polygons.foreach_set('material_index', np.array(mi, np.int32))
    uvl = me.uv_layers.new(); lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    uvl.data.foreach_set('uv', UV[lv].ravel()); me.shade_smooth()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob, P

if __name__ == '__main__':
    out = sys.argv[1]; names = sys.argv[2:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    cols = int(math.ceil(math.sqrt(len(names) * 1.6)))
    for i, n in enumerate(names):
        ob, P = load(n)
        size = float((P.max(0) - P.min(0)).max()) or 1
        ob.scale = (1.6 / size,) * 3
        c = (P.max(0) + P.min(0)) / 2 / size * 1.6
        ob.location = ((i % cols) * 2.2 - c[0], -(i // cols) * 2.2 - c[2], -P.min(0)[1] / size * 1.6)
        bpy.ops.object.text_add(location=((i % cols) * 2.2 - 0.9, -(i // cols) * 2.2 - 1.05, 0.01))
        t = bpy.context.active_object; t.data.body = n; t.data.size = 0.16
    bpy.ops.object.light_add(type='SUN', rotation=(0.7, 0.2, 0.8)); bpy.context.active_object.data.energy = 3.5
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.001))
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'
    rows = (len(names) + cols - 1) // cols
    cam.ortho_scale = max(cols, rows * 1.0) * 2.25
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = ((cols - 1) * 1.1, -(rows - 1) * 1.1 - 4.5, 7); co.rotation_euler = (math.radians(38), 0, 0)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.cycles.use_denoising = True
    sc.render.resolution_x = 1400; sc.render.resolution_y = int(1400 * rows / cols * 0.9)
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print('rendered', out)
