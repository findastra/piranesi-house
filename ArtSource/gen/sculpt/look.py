"""Preview renders of a sculpt (Cycles, CPU): a marble figure lit like a gallery, seen from several sides, tiled into
one PNG so a statue can be judged at a glance."""
import math, os
import numpy as np
import bpy
from PIL import Image

def _scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 20
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.cycles.max_bounces = 4
    sc.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.32, 0.33, 0.36, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
    return sc

def _marble():
    m = bpy.data.materials.new('marble'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.86, 0.84, 0.8, 1)
    b.inputs['Roughness'].default_value = 0.42
    try:
        b.inputs['Subsurface Weight'].default_value = 0.12
        b.inputs['Subsurface Radius'].default_value = (0.02, 0.016, 0.012)
    except Exception: pass
    return m

def render(V, F, path, views=(0, 35, 90, 180), res=(420, 640), samples=20, focus=None, zoom=1.0, extra=None, elev=0.12, floor=True):
    """V,F in Blender coords (z up, figure facing -y). views = yaw angles of the camera round the figure (0 = front).
    focus = (centre, half-height) to frame a detail instead of the whole figure."""
    sc = _scene(); sc.cycles.samples = samples
    me = bpy.data.meshes.new('fig'); me.from_pydata(np.asarray(V).tolist(), [], np.asarray(F).tolist()); me.shade_smooth()
    ob = bpy.data.objects.new('fig', me); sc.collection.objects.link(ob); me.materials.append(_marble())
    if extra:
        for (V2, F2) in extra:
            m2 = bpy.data.meshes.new('x'); m2.from_pydata(np.asarray(V2).tolist(), [], np.asarray(F2).tolist()); m2.shade_smooth()
            o2 = bpy.data.objects.new('x', m2); sc.collection.objects.link(o2); m2.materials.append(ob.data.materials[0])
    V = np.asarray(V)
    lo, hi = V.min(0), V.max(0)
    if focus is None:
        c = (lo + hi) / 2; half = max(hi[2] - lo[2], (max(hi[0] - lo[0], hi[1] - lo[1])) * res[1] / res[0]) / 2 * 1.08
    else:
        c, half = np.asarray(focus[0], float), focus[1]
    half /= zoom
    # floor
    fm = bpy.data.meshes.new('floor'); s = 50
    fm.from_pydata([(-s, -s, lo[2]), (s, -s, lo[2]), (s, s, lo[2]), (-s, s, lo[2])], [], [(0, 1, 2, 3)])
    fo = bpy.data.objects.new('floor', fm)
    if floor: sc.collection.objects.link(fo)
    fmat = bpy.data.materials.new('f'); fmat.use_nodes = True; fmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.3, 0.3, 0.32, 1)
    fm.materials.append(fmat)
    # lights: key high front-left, rim back-right, soft fill
    H = hi[2] - lo[2]
    for loc, en, size in [((-1.2, -1.6, 1.9), 260, 1.0), ((1.6, 1.4, 1.4), 120, 1.0), ((1.8, -1.2, 0.6), 40, 2.5)]:
        ld = bpy.data.lights.new('l', 'AREA'); ld.energy = en * H ** 2; ld.size = size * H / 2
        lo_ = bpy.data.objects.new('l', ld); sc.collection.objects.link(lo_)
        lo_.location = (c[0] + loc[0] * H, c[1] + loc[1] * H, c[2] + loc[2] * H * 0.6)
        d = np.array(c) - np.array(lo_.location); lo_.rotation_euler = _look(d)
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = half * 2 * max(1.0, res[0] / res[1]) * (res[1] / res[0]) * 1.0
    cam.ortho_scale = half * 2
    co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    tiles = []
    for yaw in views:
        a = math.radians(yaw)
        d = np.array([math.sin(a), -math.cos(a), elev]); d /= np.linalg.norm(d)
        co.location = tuple(np.array(c) + d * half * 6)
        co.rotation_euler = _look(-d)
        # the camera ortho_scale spans the larger image side
        cam.ortho_scale = half * 2 * (res[0] / res[1] if res[0] > res[1] else 1.0)
        sc.render.filepath = path + f'.v{yaw}.png'
        bpy.ops.render.render(write_still=True)
        tiles.append(Image.open(sc.render.filepath).convert('RGB'))
        os.remove(sc.render.filepath)
    W = sum(t.width for t in tiles); Hh = max(t.height for t in tiles)
    out = Image.new('RGB', (W, Hh)); x = 0
    for t in tiles: out.paste(t, (x, 0)); x += t.width
    out.save(path)
    return path

def _look(d):
    from mathutils import Vector
    return Vector(tuple(d)).to_track_quat('-Z', 'Y').to_euler()
