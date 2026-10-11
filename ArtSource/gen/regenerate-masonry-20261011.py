"""Regenerate only the existing Wall/Stone modules with surface-aware PMS2 UVs.

Run in Blender, for example:
  blender -b --factory-startup --python-exit-code 1 --python ArtSource/gen/regenerate-masonry-20261011.py -- --apply

Without --apply, assets are staged and audited only. Source constructors remain
the authority. The AST loader selects their architecture code without importing
the unrelated downloaded-prop/texture pipeline or needing Pillow/DracoPy/SciPy.
Backups, staged meshes and reports use the owner's dated filename convention;
--apply updates existing Unity assets without renaming their asset identities.
"""
import argparse
import ast
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import kit as K

def owner_date():
    """Use America/Denver even when Blender's Windows Python lacks tzdata."""
    try:
        return datetime.now(ZoneInfo('America/Denver')).strftime('%Y%m%d')
    except ZoneInfoNotFoundError:
        command = "[TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTimeOffset]::UtcNow, 'Mountain Standard Time').ToString('yyyyMMdd')"
        value = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', command],
                                        text=True, timeout=15).strip()
        datetime.strptime(value, '%Y%m%d')
        return value


DATE = owner_date()
ASSETS = ROOT / 'Assets' / 'Piranesi' / 'Meshes'
AUDIT = ROOT / ('local-audit-' + DATE) / ('masonry-regenerated-' + DATE)


def dated(name, extension):
    return name.lower().replace('_', '-').replace(' ', '-') + '-' + DATE + extension


def read_mesh(path):
    data = path.read_bytes()
    magic = data[:4]
    nv, ns, flags = struct.unpack_from('<iii', data, 4)
    assert magic in (b'PMS1', b'PMS2'), path
    p = np.frombuffer(data, '<f4', count=nv * 3, offset=16).reshape(-1, 3)
    normals = np.frombuffer(data, '<f4', count=nv * 3, offset=16 + nv * 12).reshape(-1, 3)
    offset = 16 + nv * 28
    uv = None
    if magic == b'PMS2':
        uv = np.frombuffer(data, '<f4', count=nv * 2, offset=offset).reshape(-1, 2)
        offset += nv * 8
    subs = {}
    for _ in range(ns):
        length = struct.unpack_from('<i', data, offset)[0]; offset += 4
        name = data[offset:offset + length].decode(); offset += length
        count = struct.unpack_from('<i', data, offset)[0]; offset += 4
        subs[name] = np.frombuffer(data, '<i4', count=count, offset=offset).reshape(-1, 3)
        offset += count * 4
    assert offset == len(data), path
    return p, normals, uv, subs


def mesh_stats(path):
    p, n, uv, subs = read_mesh(path)
    result = dict(vertices=len(p), triangles=sum(len(t) for t in subs.values()),
                  bounds_min=p.min(axis=0).tolist(), bounds_max=p.max(axis=0).tolist(),
                  materials=list(subs), finite=bool(np.isfinite(p).all() and np.isfinite(n).all()),
                  format='PMS2' if uv is not None else 'PMS1', masonry={})
    for name in ('Wall', 'Stone'):
        if name not in subs: continue
        t = subs[name]
        tri = p[t]
        area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        stats = dict(triangles=len(t), degenerate_geometry=int(np.count_nonzero(area < 1e-8)))
        if uv is not None:
            q = uv[t]; a = q[:, 1] - q[:, 0]; b = q[:, 2] - q[:, 0]
            ua = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
            stats.update(finite_uv=bool(np.isfinite(q).all()),
                         collapsed_uv_triangles=int(np.count_nonzero((ua < 1e-8) & (area > 1e-8))),
                         uv_min=q.reshape(-1, 2).min(axis=0).tolist(),
                         uv_max=q.reshape(-1, 2).max(axis=0).tolist())
        result['masonry'][name] = stats
    return result


def verify_openings(staged):
    """Bidirectional segment/triangle checks catch filled Boolean openings.

    All coordinates are mesh-local Unity metres. A known solid Aqueduct pier
    is a positive control, so an accidentally empty triangle set cannot pass.
    """
    triangles = {}
    for name in ('Aqueduct', 'Arcade', 'Arcade_Win', 'Nave', 'PumpHouse',
                 'Vest_SideOpen', 'Vest_SideBlind', 'Vest_SideWindow'):
        p, normals, uv, subs = read_mesh(staged[name])
        indices = np.concatenate([t for mat, t in subs.items() if mat in ('Wall', 'Stone')])
        triangles[name] = p[indices].astype(np.float64)
    cases = []
    for b in range(4):
        z = (b + 0.5) * 7.25
        for y in (3.0, 11.0):
            cases.append(('Aqueduct', (-4, y, z), (4, y, z), True, 'through arch'))
    cases.append(('Aqueduct', (-4, 3, 7.25), (4, 3, 7.25), False, 'solid pier control'))
    for k in range(8):
        z = -15.75 + 4.5 * k
        cases.append(('Arcade_Win', (4, 3, z), (8, 3, z), True, 'window masonry aperture'))
        for s in (-1, 1):
            cases.append(('Arcade', (s * 4, 3, z), (s * 5.9, 3, z), True, 'recess before blind-niche back'))
    for k in range(7):
        z = -13.5 + 4.5 * k
        for s in (-1, 1):
            cases.append(('Nave', (s * 7, 3, z), (s * 8.8, 3, z), True, 'recess before blind-niche back'))
    cases.append(('PumpHouse', (-4, 1.5, 0), (-2, 1.5, 0), True, 'door aperture'))
    for name in ('Vest_SideOpen', 'Vest_SideBlind', 'Vest_SideWindow'):
        cases.append((name, (0.5, 18.7, 9), (0.5, 18.7, 13), True, 'circular clerestory aperture away from mullions'))
    for side in (-1, 1):
        cases.append(('Nave', (0.5, 18.7, side * 16), (0.5, 18.7, side * 19),
                      True, 'end-cap clerestory continues vestibule opening'))
    layout = json.loads((ROOT / 'Assets/Piranesi/Data/HouseLayout.json').read_text(encoding='utf-8'))
    center = [o for o in layout['objects'] if o.get('mesh') in staged and abs(o['p'][0]) + abs(o['p'][2]) <= 31]
    required = {'Vestibule_11_E', 'Vestibule_11_W', 'Nave_01_11', 'Nave_11_21'}
    if not required.issubset({o['name'] for o in center}):
        raise RuntimeError('Central junction regression requires the authored vestibule/Nave layout objects')
    assembled = []
    for obj in center:
        name = obj['mesh']
        if name not in triangles:
            p, n, uv, subs = read_mesh(staged[name])
            indices = np.concatenate([t for mat, t in subs.items() if mat in ('Wall', 'Stone')])
            triangles[name] = p[indices].astype(np.float64)
        angle = math.radians(obj['r'])
        rotation = np.array([[math.cos(angle), 0, math.sin(angle)], [0, 1, 0],
                             [-math.sin(angle), 0, math.cos(angle)]])
        assembled.append((triangles[name] * np.array(obj['s'])) @ rotation.T + np.array(obj['p']))
    triangles['AssembledCenter'] = np.concatenate(assembled)
    for side in (-1, 1):
        cases.append(('AssembledCenter', (side * 7, 18.7, 0.5), (side * 14, 18.7, 0.5),
                      True, 'assembled east/west vestibule and Nave clerestory junction'))
        cases.append(('AssembledCenter', (0.5, 18.7, side * 7), (0.5, 18.7, side * 14),
                      True, 'assembled north/south clerestory junction control'))
    results = []
    for name, start, end, want_clear, purpose in cases:
        t = triangles[name]; origin = np.array(start, float); direction = np.array(end, float) - origin
        e1, e2 = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
        h = np.cross(direction, e2); det = np.einsum('ij,ij->i', e1, h)
        valid = abs(det) > 1e-9
        inv = np.zeros_like(det); inv[valid] = 1 / det[valid]
        s = origin - t[:, 0]; u = inv * np.einsum('ij,ij->i', s, h)
        q = np.cross(s, e1); v = inv * np.einsum('j,ij->i', direction, q)
        distance = inv * np.einsum('ij,ij->i', e2, q)
        hits = valid & (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1 + 1e-7) & (distance > 1e-7) & (distance < 1 - 1e-7)
        count = int(np.count_nonzero(hits))
        results.append(dict(mesh=name, purpose=purpose, start=start, end=end,
                            triangle_intersections=count, expected_clear=want_clear,
                            passed=bool((count == 0) == want_clear)))
    return results


def architecture_v2():
    path = HERE / 'kit2.py'
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    names = {'reset', 'vest_side_window', 'arcade_window', 'make_aqueduct', 'make_noria', 'make_tower'}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for fn in functions:
        if fn.name == 'make_aqueduct':
            # Keep the stone export; stop before the water ribbon constructor.
            end = next(i for i, s in enumerate(fn.body) if isinstance(s, ast.Expr)
                       and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name)
                       and s.value.func.id == 'export_stone')
            fn.body = fn.body[:end + 1]
        if fn.name == 'make_noria':
            # Keep dimensions and the frame/house; skip the plank wheel.
            start = next(i for i, s in enumerate(fn.body) if isinstance(s, ast.Expr)
                         and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name)
                         and s.value.func.id == 'reset')
            constants = [s for s in fn.body[:start] if isinstance(s, ast.Assign)
                         and all(isinstance(t, ast.Name) and t.id in ('R', 'wid', 'n') for t in s.targets)]
            fn.body = constants + fn.body[start:]
    module = ast.Module(body=functions, type_ignores=[])
    ns = dict(K=K, bpy=bpy, np=np, pi=math.pi, sin=math.sin, cos=math.cos, sqrt=math.sqrt,
              EXTRA={}, export_stone=K.export_bytes)
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), ns)
    return ns


def preview_arcade(aqueduct=False):
    """Offline geometry/UV proof; the final appearance still needs Unity review."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if aqueduct:
        K.export_bytes = lambda ob, name: None
        architecture_v2()['make_aqueduct']()
    else:
        K.make_arcade()
    image = bpy.data.images.load(str(ROOT / 'Assets/Piranesi/Textures/Wall_Albedo.png'))
    for name in ('Wall', 'Stone'):
        material = K.mat(name)
        nodes = material.node_tree.nodes; links = material.node_tree.links
        bsdf = nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value = 0.8
        uv = nodes.new('ShaderNodeTexCoord')
        scale = nodes.new('ShaderNodeVectorMath'); scale.operation = 'SCALE'
        scale.inputs[3].default_value = 1 / 4.8
        texture = nodes.new('ShaderNodeTexImage'); texture.image = image
        links.new(uv.outputs['UV'], scale.inputs[0]); links.new(scale.outputs[0], texture.inputs['Vector'])
        links.new(texture.outputs['Color'], bsdf.inputs['Base Color'])
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200; scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.world = bpy.data.worlds.new('Masonry review world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.5, 0.55, 0.65, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.4
    lights = ((6, 3, 11), (6, 12, 14), (6, 25, 16)) if aqueduct else ((0, -11, 6), (0, -3, 8), (0, 9, 9))
    for i, location in enumerate(lights):
        light = bpy.data.lights.new('Review light ' + str(i), 'POINT')
        light.energy = 1800; light.shadow_soft_size = 2
        ob = bpy.data.objects.new(light.name, light); scene.collection.objects.link(ob); ob.location = location
    camera = bpy.data.cameras.new('Review camera'); ob = bpy.data.objects.new('Review camera', camera)
    scene.collection.objects.link(ob); scene.camera = ob
    views = (
            ('arcade-vault-masonry-preview', (0, -14, 3.5), (0, 1, 10), 22),
            ('arcade-arch-masonry-preview', (0, -7.6, 3.3), (5, -6.75, 4.1), 35))
    if aqueduct:
        views = (('aqueduct-masonry-preview', (22, -6, 11), (0, 12, 9), 27),
                 ('aqueduct-arch-masonry-preview', (12, 5.7, 8.5), (0, 3.625, 8.5), 42))
    for name, origin, target, lens in views:
        ob.location = origin; ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
        camera.lens = lens
        scene.render.filepath = str(AUDIT / dated(name, '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Update existing mesh bytes after the complete audit passes.')
    parser.add_argument('--preview-only', action='store_true', help='Render architecture/UV review images without regenerating Unity assets.')
    parser.add_argument('--aqueduct', action='store_true', help='Select Aqueduct instead of Arcade for --preview-only.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    AUDIT.mkdir(parents=True, exist_ok=True)
    if args.preview_only:
        preview_arcade(args.aqueduct)
        return
    originals = {}
    for path in ASSETS.glob('*.bytes'):
        stat = mesh_stats(path)
        if stat['masonry']: originals[path.stem] = stat
    expected = set(originals)
    backup_dir = AUDIT / ('backups-' + DATE)
    backup_dir.mkdir(exist_ok=True)
    for name in expected:
        backup = backup_dir / dated(name, '.bytes')
        if not backup.exists(): shutil.copy2(ASSETS / (name + '.bytes'), backup)
        originals[name] = mesh_stats(backup)
    for src in (HERE / 'kit.py', HERE / 'kit2.py'):
        # The existing source is kept in Git; don't confuse its edited working
        # version with the original binary backup captured above.
        assert src.exists()

    K.OUT_MESH = str(AUDIT)
    raw_export = K.export_bytes
    staged = {}

    def export(ob, name):
        if name not in expected: raise RuntimeError('Unexpected non-masonry export: ' + name)
        filename = dated(name, '')
        raw_export(ob, filename)
        staged[name] = AUDIT / (filename + '.bytes')

    K.export_bytes = export
    builders = [
        ('Vest_Core', K.make_vestibule_core),
        ('Vest_SideOpen', lambda: K.make_vestibule_side(True)),
        ('Vest_SideBlind', lambda: K.make_vestibule_side(False)),
        ('Nave', K.make_nave), ('Arcade', K.make_arcade), ('SeaGate', K.make_seagate),
        ('Wing_1', lambda: K.make_distant_wing(1)),
        ('Wing_2', lambda: K.make_distant_wing(2)),
        ('Wing_3', lambda: K.make_distant_wing(3)),
    ]
    for name, builder in builders:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        print('Building', name, flush=True)
        export(builder(), name)
    ns = architecture_v2()
    for name in ('vest_side_window', 'arcade_window', 'make_aqueduct', 'make_noria', 'make_tower'):
        print('Building', name, flush=True)
        ns[name]()
    if set(staged) != expected:
        raise RuntimeError('Masonry inventory mismatch: ' + repr(expected.symmetric_difference(staged)))
    report = dict(used_at_utc=datetime.now(timezone.utc).isoformat(), timezone='America/Denver',
                  tool='ArtSource/gen/regenerate-masonry-20261011.py', applied=False, meshes={}, failures=[])
    report['corrections'] = [
        'All 15 Wall/Stone mesh modules now use authored per-corner metric UVs exported as PMS2.',
        'Flat courses follow height; vaults follow arc length; dome meridians and arch radial joints stay continuous.',
        'Reflected axis-y arch cutters now retain outward winding, restoring real holes and recessed niches instead of filled duplicate caps.',
        'Closed Boolean cutter signed volumes are checked and inward winding corrected, restoring all three circular clerestory window modules.',
        'High Nave end caps continue the adjoining vestibule circular apertures; assembled layout rays guard both east/west junctions.',
        'Arcade archivolts face the corridor; their backs are embedded in the wall.',
        'Previously unframed load-bearing openings have shallow bonded voussoir and jamb surrounds.',
        'Gallery end faces are clipped where the cap already supplies the visible surface; cap side faces covered by longitudinal walls are removed.',
        'Dome flange and roof ring share one 48-segment boundary; Aqueduct sill surfaces are separated by 4 mm.',
    ]
    for name, path in staged.items():
        after = mesh_stats(path)
        report['meshes'][name] = dict(before=originals[name], after=after)
        if after['materials'] != originals[name]['materials']:
            report['failures'].append(name + ': material-slot contract changed')
        for key in ('bounds_min', 'bounds_max'):
            if not np.allclose(after[key], originals[name][key], atol=1e-5, rtol=0):
                report['failures'].append(name + ': module bounding box changed')
        if not after['finite']: report['failures'].append(name + ': non-finite geometry')
        for matname, stats in after['masonry'].items():
            if not stats['finite_uv'] or stats['collapsed_uv_triangles']:
                report['failures'].append(name + '/' + matname + ': missing or collapsed UV triangles')
    report['opening_checks'] = verify_openings(staged)
    report['closed_cutter_winding_fixes'] = K.BOOLEAN_WINDING_FIXES
    for check in report['opening_checks']:
        if not check['passed']: report['failures'].append(check['mesh'] + ': ' + check['purpose'] + ' failed')
    report_path = AUDIT / dated('masonry-regeneration-report', '.json')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if report['failures']: raise RuntimeError('; '.join(report['failures']))
    if args.apply:
        for name, path in staged.items(): shutil.copyfile(path, ASSETS / (name + '.bytes'))
        report['applied'] = True
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(report=str(report_path), count=len(staged), applied=report['applied']), indent=2), flush=True)


if __name__ == '__main__':
    main()
