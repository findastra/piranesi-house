"""Flattens Materials.json (mesh -> submesh material entries) into MaterialsU.json, a list Unity's JsonUtility
can read. Every field is filled with an explicit default, texture paths are resolved relative to
Assets/Piranesi/Imported, and identical materials share a 'key' so the builder creates each material only once."""
import os, json, hashlib
from ivy import read_pms

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
IMP = os.path.join(OUT, 'Imported')

def tex(path, entry, mesh):
    if not path: return ''
    rel = path if '/' in path else f"{entry.get('dir') or mesh}/{path}"
    if not os.path.exists(os.path.join(IMP, rel)):
        print('  missing texture', rel); return ''
    return rel

def normalise(mesh, e):
    sh = e.get('shader', 'prop')
    albedo, normal, mask = tex(e.get('albedo'), e, mesh), tex(e.get('normal'), e, mesh), tex(e.get('mask'), e, mesh)
    alpha = e.get('alpha', 'OPAQUE')
    n = dict(sub=e['sub'], shader=sh, albedo=albedo, normal=normal, mask=mask, alpha=alpha,
             doubleSided=bool(e.get('doubleSided', sh == 'foliage')), tint=list(e.get('tint', [1, 1, 1]))[:3])
    if sh == 'prop':
        n['smooth'] = float(e['smooth']) if 'smooth' in e else (1.0 if mask else 0.45)
        n['metal'] = float(e['metal']) if 'metal' in e else (1.0 if mask else 0.0)
        n['cutoff'] = 0.5 if alpha == 'MASK' else (0.3 if alpha == 'BLEND' else 0.0)
    elif sh == 'foliage':
        n['smooth'] = float(e.get('smooth', 0.6)); n['metal'] = 0.0
        n['cutoff'] = float(e.get('cutoff', 0.45))
        n['wind'] = float(e.get('wind', 0.4)); n['windScale'] = float(e.get('windScale', 2.0))
        n['translucency'] = float(e.get('translucency', 0.6)); n['vertexTint'] = float(e.get('vertexTint', 0.0))
    elif sh == 'coral':
        P = read_pms(mesh)[0]
        n['base'] = list(e.get('base', [0.55, 0.35, 0.45])); n['tip'] = list(e.get('tip', [0.95, 0.65, 0.75]))
        n['height'] = float(e.get('height', max(0.05, float(P[:, 1].max()))))
        n['detail'] = float(e.get('detail', 0.6)); n['glow'] = float(e.get('glow', 0.25)); n['smooth'] = float(e.get('smooth', 0.35))
    elif sh == 'flow':
        n['cutoff'] = 0.0
    for k in ('smooth', 'metal', 'cutoff', 'wind', 'windScale', 'translucency', 'vertexTint', 'height', 'detail', 'glow'):
        n.setdefault(k, 0.0)
    n.setdefault('base', [1, 1, 1]); n.setdefault('tip', [1, 1, 1])
    body = {k: v for k, v in n.items() if k != 'sub'}
    n['key'] = hashlib.md5(json.dumps(body, sort_keys=True).encode()).hexdigest()[:10]
    return n

def main():
    man = json.load(open(os.path.join(OUT, 'Data', 'Materials.json')))
    seen = {}
    for mesh in sorted(man):
        if not os.path.exists(os.path.join(OUT, 'Meshes', mesh + '.bytes')): continue
        for e in man[mesh]:
            if e['sub'] in seen: continue
            seen[e['sub']] = normalise(mesh, e)
    entries = list(seen.values())
    json.dump(dict(entries=entries), open(os.path.join(OUT, 'Data', 'MaterialsU.json'), 'w'), indent=0)
    print('MaterialsU:', len(entries), 'submesh materials,', len({e['key'] for e in entries}), 'unique')

if __name__ == '__main__':
    main()
