"""Distant LODs for the heavy scanned props (corals, sponges, rocks, plants...): Blender collapse-decimation of the
PMS2 meshes, written as <Name>_LOD1 with the same submeshes/materials. The Unity builder wraps any mesh that has a
_LOD1 sibling in an LODGroup."""
import os, sys, json, struct, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import assets as AS

MESH = os.path.join(HERE, '..', 'out', 'Meshes')

def read(name):
    with open(os.path.join(MESH, name + '.bytes'), 'rb') as f:
        mg = f.read(4); nv, ns, fl = struct.unpack('<iii', f.read(12))
        P = np.frombuffer(f.read(nv * 12), '<f4').reshape(-1, 3); f.read(nv * 12); f.read(nv * 4)
        UV = np.frombuffer(f.read(nv * 8), '<f4').reshape(-1, 2) if mg == b'PMS2' else np.zeros((nv, 2), np.float32)
        subs = []
        for s in range(ns):
            ln = struct.unpack('<i', f.read(4))[0]; nm = f.read(ln).decode()
            ni = struct.unpack('<i', f.read(4))[0]; subs.append((nm, np.frombuffer(f.read(ni * 4), '<i4').reshape(-1, 3)))
    return mg, P, UV, subs

def lod(name, ratio):
    mg, P, UV, subs = read(name)
    if mg != b'PMS2': return None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new(name)
    faces = []; mi = []
    for k, (nm, idx) in enumerate(subs):
        faces += idx[:, [0, 2, 1]].tolist(); mi += [k] * len(idx)
        me.materials.append(bpy.data.materials.new(f'm{k}'))
    me.from_pydata(P[:, [0, 2, 1]].tolist(), [], faces)
    me.polygons.foreach_set('material_index', np.array(mi, np.int32))
    uvl = me.uv_layers.new(); lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    uvl.data.foreach_set('uv', UV[lv].astype(np.float32).ravel())
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    m = ob.modifiers.new('d', 'DECIMATE'); m.ratio = ratio; m.use_collapse_triangulate = True
    nv, nt, bb = AS.export_pms2(ob, name + '_LOD1', [nm for nm, _ in subs])
    return nt

if __name__ == '__main__':
    man = json.load(open(AS.MANIFEST))
    rules = [('Coral_', 0.12), ('Sponge_', 0.15), ('Boulder_', 0.1), ('Rock_Coast', 0.25), ('Rock_SandSmall', 0.2),
             ('Plant_Pachira_', 0.2), ('Plant_Periwinkle_', 0.25), ('Plant_Calathea_', 0.3), ('Clam_', 0.2), ('SeaStar_', 0.2),
             ('Treasure_', 0.15), ('Chess_', 0.1), ('Lion_', 0.15), ('Marble_Bust', 0.15), ('Barrels', 0.15), ('Ship_', 0.2),
             ('Basket_', 0.15), ('Horse_Statue', 0.15), ('Crab_', 0.15), ('Fruit_', 0.2), ('Goblets_', 0.2), ('Candleholders_', 0.25)]
    names = sorted(f[:-6] for f in os.listdir(MESH) if f.endswith('.bytes') and not f.endswith('_LOD1.bytes'))
    for n in names:
        r = next((r for p, r in rules if n.startswith(p)), None)
        if r is None or n not in man: continue
        nt = lod(n, r)
        if nt:
            man[n + '_LOD1'] = man[n]
            print(n, '->', nt, flush=True)
    json.dump(man, open(AS.MANIFEST, 'w'), indent=1)
