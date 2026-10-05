"""Import downloaded CC0 assets (Poly Haven glTF, Smithsonian draco GLB), decimate in Blender to VR budgets,
pack textures for the Piranesi shaders, and export PMS2 meshes (with UVs) + a material manifest.

Outputs:
  out/Meshes/<Name>.bytes            PMS2 mesh (Unity space)
  out/Imported/<Name>/*.png          albedo (RGBA), normal (GL), mask (R smooth, G ao, B 0, A 1)
  out/Data/Materials.json            {mesh: [{sub, shader, albedo, normal, mask, alphaClip, tint}]}
"""
import bpy, json, os, struct, sys, math, numpy as np
from PIL import Image
import DracoPy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'assets')
OUTM = os.path.join(ROOT, 'out', 'Meshes'); os.makedirs(OUTM, exist_ok=True)
OUTI = os.path.join(ROOT, 'out', 'Imported'); os.makedirs(OUTI, exist_ok=True)
MANIFEST = os.path.join(ROOT, 'out', 'Data', 'Materials.json')

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

def load_gltf(path):
    if path.endswith('.glb'):
        b = open(path, 'rb').read()
        off = 12; js = None; bins = []
        while off < len(b):
            ln, typ = struct.unpack('<II', b[off:off + 8])
            chunk = b[off + 8:off + 8 + ln]
            if typ == 0x4E4F534A: js = json.loads(chunk)
            else: bins.append(chunk)
            off += 8 + ln
        buffers = [bins[0] if bins else b'']
    else:
        js = json.load(open(path))
        d = os.path.dirname(path)
        buffers = [open(os.path.join(d, bf['uri']), 'rb').read() for bf in js['buffers']]
    return js, buffers, os.path.dirname(path)

def bview(js, buffers, i):
    bv = js['bufferViews'][i]
    o = bv.get('byteOffset', 0)
    return buffers[bv.get('buffer', 0)][o:o + bv['byteLength']], bv.get('byteStride')

def accessor(js, buffers, i):
    ac = js['accessors'][i]
    dt = COMP[ac['componentType']]; n = NCOMP[ac['type']]
    data, stride = bview(js, buffers, ac['bufferView'])
    off = ac.get('byteOffset', 0); count = ac['count']
    isz = np.dtype(dt).itemsize
    if stride and stride != n * isz:
        raw = np.frombuffer(data, np.uint8)
        arr = np.stack([np.frombuffer(raw[off + k * stride: off + k * stride + n * isz].tobytes(), dt) for k in range(count)])
    else:
        arr = np.frombuffer(data, dt, count * n, off).reshape(count, n)
    arr = arr.astype(np.float32) if dt != np.uint32 and dt != np.uint16 or ac.get('normalized') else arr
    if ac.get('normalized'):
        mx = {np.uint8: 255, np.uint16: 65535, np.int8: 127, np.int16: 32767}[dt]
        arr = arr.astype(np.float32) / mx
    return arr

def node_matrix(n):
    if 'matrix' in n: return np.array(n['matrix'], np.float64).reshape(4, 4).T
    t = n.get('translation', [0, 0, 0]); r = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
    x, y, z, w = r
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.array(s)[None, :]; M[:3, 3] = t
    return M

def save_image(js, buffers, base, tex_index, dest):
    if tex_index is None: return None
    tex = js['textures'][tex_index]
    src = tex.get('source')
    if src is None:
        for e in tex.get('extensions', {}).values(): src = e.get('source', src)
    img = js['images'][src]
    if 'uri' in img:
        im = Image.open(os.path.join(base, img['uri']))
    else:
        data, _ = bview(js, buffers, img['bufferView'])
        import io
        im = Image.open(io.BytesIO(data))
    im.load()
    return im

def gather(path):
    """Return list of primitives: (positions(gltf space), normals, uvs, indices, material index) with node transforms applied,
    plus (js, buffers, base)."""
    js, buffers, base = load_gltf(path)
    prims = []
    def visit(ni, parent):
        n = js['nodes'][ni]; M = parent @ node_matrix(n)
        if 'mesh' in n:
            for p in js['meshes'][n['mesh']]['primitives']:
                ext = p.get('extensions', {}).get('KHR_draco_mesh_compression')
                if ext:
                    data, _ = bview(js, buffers, ext['bufferView'])
                    m = DracoPy.decode(data)
                    P = np.asarray(m.points, np.float64); F = np.asarray(m.faces, np.int64).reshape(-1, 3)
                    N = np.asarray(m.normals, np.float64) if m.normals is not None and len(m.normals) else None
                    UV = np.asarray(m.tex_coord, np.float64) if m.tex_coord is not None and len(m.tex_coord) else None
                else:
                    at = p['attributes']
                    P = accessor(js, buffers, at['POSITION']).astype(np.float64)
                    N = accessor(js, buffers, at['NORMAL']).astype(np.float64) if 'NORMAL' in at else None
                    UV = accessor(js, buffers, at['TEXCOORD_0']).astype(np.float64) if 'TEXCOORD_0' in at else None
                    F = accessor(js, buffers, p['indices']).astype(np.int64).reshape(-1, 3) if 'indices' in p else np.arange(len(P)).reshape(-1, 3)
                P = (M[:3, :3] @ P.T).T + M[:3, 3]
                if N is not None:
                    Nm = np.linalg.inv(M[:3, :3]).T
                    N = (Nm @ N.T).T; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
                prims.append((P, N, UV, F, p.get('material', 0)))
        for c in n.get('children', []): visit(c, M)
    scene = js['scenes'][js.get('scene', 0)]
    for r in scene['nodes']: visit(r, np.eye(4))
    return prims, js, buffers, base

# ------------------------------------------------------------------ texture packing
def pack_material(js, buffers, base, mi, outdir, name, maxres, alpha_from_albedo=True):
    m = js['materials'][mi] if mi is not None and mi < len(js.get('materials', [])) else {}
    pbr = m.get('pbrMetallicRoughness', {})
    res = {}
    os.makedirs(outdir, exist_ok=True)
    alb = save_image(js, buffers, base, pbr.get('baseColorTexture', {}).get('index'), None)
    if alb is not None:
        alb = alb.convert('RGBA')
        if max(alb.size) > maxres: alb = alb.resize((maxres, maxres), Image.LANCZOS)
        alb.save(os.path.join(outdir, f'{name}_Albedo.png')); res['albedo'] = f'{name}_Albedo.png'
    nrm = save_image(js, buffers, base, m.get('normalTexture', {}).get('index'), None)
    if nrm is not None:
        nrm = nrm.convert('RGB')
        if max(nrm.size) > maxres: nrm = nrm.resize((maxres, maxres), Image.LANCZOS)
        nrm.save(os.path.join(outdir, f'{name}_Normal.png')); res['normal'] = f'{name}_Normal.png'
    if alb is None and m.get('occlusionTexture'):
        aoim = save_image(js, buffers, base, m['occlusionTexture']['index'], None).convert('RGBA')
        if max(aoim.size) > maxres: aoim = aoim.resize((maxres, maxres), Image.LANCZOS)
        aoim.save(os.path.join(outdir, f'{name}_Albedo.png')); res['albedo'] = f'{name}_Albedo.png'; alb = aoim
    mr = save_image(js, buffers, base, pbr.get('metallicRoughnessTexture', {}).get('index'), None)
    ao = save_image(js, buffers, base, m.get('occlusionTexture', {}).get('index'), None)
    size = (alb.size if alb is not None else (512, 512))
    if mr is not None or ao is not None:
        rough = np.full(size[::-1], pbr.get('roughnessFactor', 0.6), np.float32)
        metal = np.full(size[::-1], pbr.get('metallicFactor', 0.0), np.float32)
        occ = np.ones(size[::-1], np.float32)
        if mr is not None:
            a = np.asarray(mr.convert('RGB').resize(size, Image.BILINEAR), np.float32) / 255
            rough = a[..., 1] * pbr.get('roughnessFactor', 1.0); metal = a[..., 2] * pbr.get('metallicFactor', 1.0)
        if ao is not None:
            occ = np.asarray(ao.convert('RGB').resize(size, Image.BILINEAR), np.float32)[..., 0] / 255
        mask = np.stack([1 - rough, occ, metal, np.ones_like(rough)], -1)
        Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(outdir, f'{name}_Mask.png'))
        res['mask'] = f'{name}_Mask.png'
    else:
        res['smooth'] = 1 - pbr.get('roughnessFactor', 0.6)
        res['metal'] = pbr.get('metallicFactor', 0.0)
    if 'baseColorFactor' in pbr: res['tint'] = pbr['baseColorFactor'][:3]
    res['alpha'] = m.get('alphaMode', 'OPAQUE')
    res['doubleSided'] = bool(m.get('doubleSided', False))
    return res

# ------------------------------------------------------------------ blender mesh build / decimate / export
def build_object(prims, name, scale=1.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    V = []; Fs = []; UVs = []; NN = []; MI = []; vbase = 0
    mats = sorted(set(p[4] for p in prims))
    for P, N, UV, F, mi in prims:
        # glTF (x, y, z) Y-up  ->  Blender (x, -z, y) Z-up
        Pb = np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1) * scale
        V.append(Pb); Fs.append(F + vbase)
        uv = UV if UV is not None else np.zeros((len(P), 2))
        UVs.append(np.stack([uv[:, 0], 1 - uv[:, 1]], 1))
        NN.append(np.stack([N[:, 0], -N[:, 2], N[:, 1]], 1) if N is not None else None)
        MI.append(np.full(len(F), mats.index(mi)))
        vbase += len(P)
    V = np.concatenate(V); F = np.concatenate(Fs); UVv = np.concatenate(UVs); MI = np.concatenate(MI)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(len(F) * 3); me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
    me.polygons.add(len(F)); me.polygons.foreach_set('loop_start', np.arange(0, len(F) * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', UVv[F.ravel()].astype(np.float32).ravel())
    for k, mi in enumerate(mats):
        me.materials.append(bpy.data.materials.new(f'{name}_m{mi}'))
    me.polygons.foreach_set('material_index', MI.astype(np.int32))
    me.shade_smooth()
    if all(n is not None for n in NN):
        NV = np.concatenate(NN)
        me.normals_split_custom_set_from_vertices(NV.astype(np.float32).tolist())
    me.validate()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob, mats

def split_variants(ob):
    """Separate a multi-variant asset (several plants laid out in a row) into one object per variant:
    loose parts are grouped when their XY footprints overlap, then each group is re-centred on the origin."""
    for o in bpy.context.scene.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    boxes = []
    for o in objs:
        co = np.empty(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        boxes.append((co.min(0), co.max(0)))
    parent = list(range(len(objs)))
    def f(i):
        while parent[i] != i: i = parent[i]
        return i
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            a, b = boxes[i], boxes[j]
            if (a[0][0] <= b[1][0] + 0.02 and b[0][0] <= a[1][0] + 0.02 and a[0][1] <= b[1][1] + 0.02 and b[0][1] <= a[1][1] + 0.02):
                parent[f(i)] = f(j)
    groups = {}
    for i in range(len(objs)): groups.setdefault(f(i), []).append(objs[i])
    out = []
    for g in sorted(groups.values(), key=lambda g: -sum(len(o.data.vertices) for o in g)):
        if sum(len(o.data.polygons) for o in g) < 60: continue
        if len(g) > 1:
            for o in bpy.context.scene.objects: o.select_set(False)
            for o in g: o.select_set(True)
            bpy.context.view_layer.objects.active = g[0]
            bpy.ops.object.join()
        o = g[0]
        co = np.empty(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        lo, hi = co.min(0), co.max(0); c = (lo + hi) / 2; c[2] = lo[2]
        o.data.vertices.foreach_set('co', (co - c).ravel()); o.data.update()
        out.append(o)
    return out[:8]

def decimate(ob, target_tris):
    ob.data.calc_loop_triangles(); n = len(ob.data.loop_triangles)
    if n <= target_tris: return n
    mod = ob.modifiers.new('dec', 'DECIMATE'); mod.ratio = target_tris / n
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear(); old = ob.data; ob.data = me; bpy.data.meshes.remove(old)
    me.calc_loop_triangles(); return len(me.loop_triangles)

def export_pms2(ob, fname, sub_names, ao=None):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    nl = len(me.loops); nt = len(me.loop_triangles)
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    lv = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
    cn = np.empty(nl * 3, np.float32); me.corner_normals.foreach_get('vector', cn); cn = cn.reshape(-1, 3)
    uv = np.zeros((nl, 2), np.float32)
    if me.uv_layers.active:
        b = np.empty(nl * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', b); uv = b.reshape(-1, 2)
    tl = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', tl); tl = tl.reshape(-1, 3)
    tm = np.empty(nt, np.int32); me.loop_triangles.foreach_get('material_index', tm)
    key = np.concatenate([lv[:, None].astype(np.int64), np.round(cn * 500).astype(np.int64), np.round(uv * 8192).astype(np.int64)], 1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
    first = np.zeros(len(uniq), np.int64); first[inv[::-1]] = np.arange(nl)[::-1]
    P = co[lv[first]][:, [0, 2, 1]]; N = cn[first][:, [0, 2, 1]]; U = uv[first]
    C = np.full((len(P), 4), 255, np.uint8)
    if ao is not None:
        a = (np.clip(ao(P), 0, 1) * 255).astype(np.uint8); C[:, 0] = C[:, 1] = C[:, 2] = a
    tris = inv[tl][:, [0, 2, 1]]
    subs = []
    for mi, nm in enumerate(sub_names):
        sel = tris[tm == mi]
        if len(sel): subs.append((nm, sel.ravel().astype(np.int32)))
    with open(os.path.join(OUTM, fname + '.bytes'), 'wb') as f:
        f.write(b'PMS2'); f.write(struct.pack('<iii', len(P), len(subs), 1))
        f.write(P.astype('<f4').tobytes()); f.write(N.astype('<f4').tobytes()); f.write(C.tobytes()); f.write(U.astype('<f4').tobytes())
        for nm, idx in subs:
            bn = nm.encode(); f.write(struct.pack('<i', len(bn))); f.write(bn)
            f.write(struct.pack('<i', len(idx))); f.write(idx.astype('<i4').tobytes())
    ob.evaluated_get(dg).to_mesh_clear()
    bb = P.min(0), P.max(0)
    return len(P), len(tris), bb

# ------------------------------------------------------------------ asset table
# name: (source path, target tris, texture max res, shader, scale, extra)
PH = lambda id, res='2k': os.path.join(A, 'polyhaven', id, f'{id}_{res}.gltf')
SI = lambda t: os.path.join(A, 'smithsonian', t + '.glb')
ASSETS = {
    # garden table
    'Fruit_Apple': (PH('food_apple_01'), 3000, 1024, 'prop', 1, {}),
    'Fruit_Lime': (PH('food_lime_01'), 3000, 1024, 'prop', 1, {}),
    'Fruit_Pomegranate': (PH('food_pomegranate_01'), 3000, 1024, 'prop', 1, {}),
    'Fruit_Kiwi': (PH('food_kiwi_01'), 3000, 1024, 'prop', 1, {}),
    'Fruit_Lychee': (PH('food_lychee_01'), 3000, 1024, 'prop', 1, {}),
    'Fruit_Pears': (PH('food_pears_asian_01'), 5000, 1024, 'prop', 1, {}),
    'Fruit_Bananas': (PH('bananas'), 8000, 1024, 'prop', 1, {'split': True}),
    'Fruit_Lemon': (PH('lemon'), 3000, 1024, 'prop', 1, {}),
    'Bowl_Wood': (PH('wooden_bowl_01'), 4000, 1024, 'prop', 1, {}),
    'Goblets_Brass': (PH('brass_goblets'), 6000, 1024, 'prop', 1, {}),
    'Jug': (PH('jug_01'), 4000, 1024, 'prop', 1, {}),
    'Vase_Antique': (PH('antique_ceramic_vase_01'), 4000, 1024, 'prop', 1, {}),
    'Basket_Wicker': (PH('wicker_basket_01'), 8000, 1024, 'prop', 1, {}),
    'Candleholders': (PH('brass_candleholders'), 10000, 1024, 'prop', 1, {'split': True}),
    'Plate_Carved': (PH('carved_wooden_plate'), 2000, 1024, 'prop', 1, {}),
    # book statues / decor
    'Lion_Head': (PH('lion_head'), 12000, 2048, 'prop', 1, {}),
    'Chess_Set': (PH('chess_set'), 30000, 2048, 'prop', 1, {}),
    'Elephant_Carved': (PH('carved_wooden_elephant'), 6000, 2048, 'prop', 1, {}),
    'Shell_Lambis': (PH('lambis_shell'), 4000, 1024, 'prop', 1, {}),
    'Horse_Statue': (PH('horse_statue_01'), 15000, 2048, 'prop', 1, {}),
    'Marble_Bust': (PH('marble_bust_01'), 12000, 2048, 'prop', 1, {}),
    'Whale_Bronze': (PH('bronze_whale_statue'), 4000, 1024, 'prop', 1, {}),
    'Treasure_Chest': (PH('treasure_chest'), 15000, 2048, 'prop', 1, {}),
    'Lantern_Wood': (PH('wooden_lantern_01'), 5000, 1024, 'prop', 1, {}),
    'Bucket_Wood': (PH('wooden_bucket_01'), 3000, 1024, 'prop', 1, {}),
    # nature (1k)
    'Plant_Pachira': (PH('pachira_aquatica_01', '1k'), 40000, 1024, 'foliage', 1, {'split': True}),
    'Plant_Anthurium': (PH('anthurium_botany_01', '1k'), 5000, 1024, 'foliage', 1, {'split': True}),
    'Plant_Calathea': (PH('calathea_orbifolia_01', '1k'), 17000, 1024, 'foliage', 1, {'split': True}),
    'Plant_Fern': (PH('fern_02', '1k'), 7000, 1024, 'foliage', 1, {'split': True}),
    'Plant_Sorrel': (PH('shrub_sorrel_01', '1k'), 4000, 1024, 'foliage', 1, {'split': True}),
    'Plant_Periwinkle': (PH('periwinkle_plant', '1k'), 30000, 1024, 'foliage', 1, {'split': True}),
    'Rock_Coast': (PH('coast_rocks_01', '1k'), 30000, 1024, 'prop', 1, {}),
    'Rock_SandSmall': (PH('sand_rocks_small_01', '1k'), 30000, 1024, 'prop', 1, {}),
    'Rock_07': (PH('rock_07', '1k'), 8000, 1024, 'prop', 1, {}),
    'Rock_09': (PH('rock_09', '1k'), 8000, 1024, 'prop', 1, {}),
    'Boulder_01': (PH('boulder_01', '1k'), 12000, 1024, 'prop', 1, {}),
    'Pier_Kit': (PH('modular_wooden_pier', '1k'), 60000, 1024, 'prop', 1, {}),
    'Ship_Dutch': (PH('dutch_ship_medium', '1k'), 40000, 1024, 'prop', 1, {}),
    'Barrels': (PH('wooden_barrels_01', '1k'), 12000, 1024, 'prop', 1, {}),
    # reef (Smithsonian, CC0). museum specimens are bleached -> coral shader recolours
    'Coral_Staghorn': (SI('Acropora_cervicornis'), 9000, 1024, 'coral', 1, {'size': 1.3}),
    'Coral_Brain': (SI('Diploria_labyrinthiformis'), 9000, 1024, 'coral', 1, {'size': 1.0}),
    'Coral_BrainGrooved': (SI('Pseudodiploria_strigosa'), 9000, 1024, 'coral', 1, {'size': 0.9}),
    'Coral_Lobe': (SI('Porites_lobata_parvicalyx'), 8000, 1024, 'coral', 1, {'size': 1.1}),
    'Coral_Cauliflower': (SI('Pocillopora_meandrina'), 9000, 1024, 'coral', 1, {'size': 0.55}),
    'Coral_Lace': (SI('Pocillopora_damicornis'), 9000, 1024, 'coral', 1, {'size': 0.45}),
    'Coral_Maze': (SI('Meandrina_meandrites'), 8000, 1024, 'coral', 1, {'size': 0.8}),
    'Coral_Fire': (SI('Millepora_alcicornis'), 9000, 1024, 'coral', 1, {'size': 0.9}),
    'Coral_Lettuce': (SI('Agaricia_lamarcki'), 8000, 1024, 'coral', 1, {'size': 0.7}),
    'Coral_Lobo': (SI('Lobophyllia_wellsi'), 8000, 1024, 'coral', 1, {'size': 0.6}),
    'Coral_Cactus': (SI('Pavona_cactus'), 9000, 1024, 'coral', 1, {'size': 0.75}),
    'Coral_Montipora': (SI('Montipora_berryi'), 8000, 1024, 'coral', 1, {'size': 0.9}),
    'Coral_Mushroom': (SI('Fungia_discus'), 4000, 1024, 'coral', 1, {'size': 0.25, 'flat': True}),
    'Coral_Table': (SI('Acropora_valenciennesi'), 9000, 1024, 'coral', 1, {'size': 1.6}),
    'Coral_Honeycomb': (SI('Goniastrea_favulus'), 7000, 1024, 'coral', 1, {'size': 0.6}),
    'SeaStar_Blue': (SI('Linckia_laevigata'), 3000, 1024, 'prop', 1, {'size': 0.3, 'flat': True}),
    'SeaStar_Cushion': (SI('Culcita_novaeguineae'), 3000, 1024, 'prop', 1, {'size': 0.25, 'flat': True}),
    'SeaStar_Crown': (SI('Acanthaster_brevispinus'), 4000, 1024, 'prop', 1, {'size': 0.4, 'flat': True}),
    'Shell_ConeTextile': (SI('Conus_textile'), 2500, 1024, 'prop', 1, {'size': 0.11}),
    'Shell_ConeGlory': (SI('Conus_gloriamaris'), 2500, 1024, 'prop', 1, {'size': 0.12}),
    'Clam_Giant': (SI('Tridacna_Flodacna_squamosa'), 6000, 1024, 'prop', 1, {'size': 0.6}),
    'Crab_Blue': (SI('Blue_Crab'), 3500, 1024, 'prop', 1, {'size': 0.22, 'flat': True, 'override': {'shader': 'coral', 'base': [0.82, 0.8, 0.72], 'tip': [0.33, 0.36, 0.22], 'height': 0.12, 'detail': 0.9, 'glow': 0.0}}),
    'Sponge_Barrel': (SI('Xestospongia_rosariensis'), 7000, 1024, 'coral', 1, {'size': 1.0}),
    'Sponge_Grass': (SI('Spongia_graminea_tampa'), 6000, 1024, 'coral', 1, {'size': 0.5}),
}

if __name__ == '__main__':
    only = sys.argv[1:]
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    report = {}
    for name, (src, tris, maxres, shader, scale, extra) in ASSETS.items():
        if only and name not in only: continue
        if not os.path.exists(src):
            print('MISSING', name, src); continue
        prims, js, buffers, base = gather(src)
        ob, mats = build_object(prims, name, scale)
        if 'size' in extra:
            # normalise museum scans: centre on XY, rest on Z=0, scale largest dimension to real size
            me = ob.data
            co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
            lo, hi = co.min(0), co.max(0)
            c = (lo + hi) / 2; c[2] = lo[2]
            if extra.get('flat'):
                ax = int(np.argmin(hi - lo))
                if ax == 0: co = co[:, [2, 1, 0]] * np.array([-1, 1, 1])
                elif ax == 1: co = co[:, [0, 2, 1]] * np.array([1, -1, 1])
                lo, hi = co.min(0), co.max(0); c = (lo + hi) / 2; c[2] = lo[2]
            k = extra['size'] / float((hi - lo).max())
            co = (co - c) * k
            me.vertices.foreach_set('co', co.ravel()); me.update()
        parts = split_variants(ob) if extra.get('split') else [ob]
        if len(parts) > 1:
            for pi_, part in enumerate(parts):
                pname = f'{name}_{pi_}'
                decimate(part, max(1500, tris // len(parts)))
                subs = [f'{name}_{k}' for k in range(len(mats))]
                nv, nt, bb = export_pms2(part, pname, subs)
                manifest[pname] = None  # filled below with shared material entries
                report[pname] = (nv, nt, [round(float(x), 3) for x in bb[0]], [round(float(x), 3) for x in bb[1]])
                print(f'  {pname}: {nt} tris, bounds {report[pname][2]} .. {report[pname][3]}', flush=True)
            outdir = os.path.join(OUTI, name); entries = []
            for k, mi in enumerate(mats):
                info = pack_material(js, buffers, base, mi, outdir, f'{name}_{k}', maxres); info['sub'] = f'{name}_{k}'; info['shader'] = shader
                info['dir'] = name; entries.append(info)
            for pi_ in range(len(parts)): manifest[f'{name}_{pi_}'] = entries
            continue
        n = decimate(ob, tris)
        subs = []; entries = []
        outdir = os.path.join(OUTI, name)
        for k, mi in enumerate(mats):
            sub = f'{name}_{k}'
            info = pack_material(js, buffers, base, mi, outdir, sub, maxres)
            info['sub'] = sub; info['shader'] = shader; info['dir'] = name
            if 'override' in extra: info.update(extra['override'])
            entries.append(info); subs.append(sub)
        nv, nt, bb = export_pms2(ob, name, subs)
        manifest[name] = entries
        report[name] = (nv, nt, [round(float(x), 3) for x in bb[0]], [round(float(x), 3) for x in bb[1]])
        print(f'{name}: {nt} tris, bounds {report[name][2]} .. {report[name][3]}, mats {[(e["sub"], e.get("alpha")) for e in entries]}', flush=True)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    json.dump(manifest, open(MANIFEST, 'w'), indent=1)
    json.dump(report, open(os.path.join(ROOT, 'out', 'Data', 'AssetBounds.json'), 'w'), indent=1)
    print('assets done')
