"""Bring a statue finished in Blender (a real museum scan, re-worked and weathered by hand, exported as OBJ with its
baked textures) into the House: PMS2 mesh + LOD1 with the scan's UVs, the baked marble albedo, the scan's normal map,
and a mask of smoothness (from the baked roughness) and occlusion (from the scan).

    python3 gen/real/scan_statue.py Colossus <out_dir> <normal.png> <occlusion.png> <height_m>
"""
import os, sys, math, json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mesh as MK
import bpy

def bring(name, src, normal_png, occl_png, height, lod_tris=7000):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=os.path.join(src, name + '.obj'), forward_axis='Y', up_axis='Z')
    ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    V = np.array([v.co for v in ob.data.vertices])
    z0 = V[:, 2].min(); H = V[:, 2].max() - z0
    feet = V[V[:, 2] < z0 + 0.08 * H]
    cx, cy = (feet[:, 0].min() + feet[:, 0].max()) / 2, (feet[:, 1].min() + feet[:, 1].max()) / 2
    s = height / H
    # base centre to the origin, scale to size, and turn 180 deg so she faces +z in Unity (a rotation, never a mirror)
    for v in ob.data.vertices:
        x, y, z = v.co.x - cx, v.co.y - cy, v.co.z - z0
        v.co = (-x * s, -y * s, z * s)
    ob.data.update()
    ob.data.materials.clear(); ob.data.materials.append(bpy.data.materials.new('Marble'))
    sub = f'{name}_Marble'
    MK.AS.export_pms2(ob, name, [sub])
    # LOD1: a decimated copy keeps its UVs
    n = MK.AS.decimate(ob, lod_tris)
    MK.AS.export_pms2(ob, name + '_LOD1', [sub])
    print(f'  {name}: {len(V)} verts, height {height} m; LOD1 {n} tris', flush=True)
    # textures
    d = os.path.join(MK.OUTI, name); os.makedirs(d, exist_ok=True)
    Image.open(os.path.join(src, f'{name}_Albedo.png')).convert('RGB').save(os.path.join(d, f'{name}_Albedo.png'))
    Image.open(normal_png).convert('RGB').resize((2048, 2048), Image.LANCZOS).save(os.path.join(d, f'{name}_Normal.png'))
    rough = np.asarray(Image.open(os.path.join(src, f'{name}_Roughness.png')).convert('L').resize((2048, 2048)), np.float32) / 255
    occ = np.asarray(Image.open(occl_png).convert('L').resize((2048, 2048)), np.float32) / 255
    MK.save_rgb(MK.mask(1 - rough, 0.35 + 0.65 * occ), os.path.join(d, f'{name}_Mask.png'))
    entry = dict(sub=sub, shader='prop', albedo=f'{name}/{name}_Albedo.png', normal=f'{name}/{name}_Normal.png',
                 mask=f'{name}/{name}_Mask.png', alpha='OPAQUE', smooth=1.0, metal=0.0, doubleSided=False)
    man = MK.load_manifest(); man[name] = [entry]; man[name + '_LOD1'] = [entry]; MK.save_manifest(man)
    # hand back the final Unity-space vertices for the climb planning
    P = np.array([v.co for v in bpy.data.objects[ob.name].data.vertices])
    return np.stack([P[:, 0], P[:, 2], P[:, 1]], 1)

if __name__ == '__main__':
    name, src, nrm_png, occ_png, h = sys.argv[1:6]
    Vu = bring(name, src, nrm_png, occ_png, float(h))
    np.save(sys.argv[6] if len(sys.argv) > 6 else f'{name}_unity.npy', Vu)
