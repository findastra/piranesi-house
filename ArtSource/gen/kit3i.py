"""v3 Ariadne's golden thread: a thin gold ribbon on the floors of the whole labyrinth, through every gallery and hall,
whose UV.x is the distance (m) back to the Colossus, so the thread shader can send pulses of light home along it.
Hidden until the Thread-Bearer quest (Hall of the Minotaurs) is done. Run: python3 gen/kit3i.py"""
import os, sys, json, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import NA, MAN, EXTRA, AS
from kit3b import uv_export
import plan7 as PL

G = PL.G; C = PL.N // 2
def cpos(c): return np.array([(c[0] - C) * G, (c[1] - C) * G], float)
E = {tuple(sorted((tuple(a), tuple(b)))) for a, b in PL.MAZE['edges']}
root = (C, C)
parent = {root: None}; order = [root]
for n in order:
    for a, b in E:
        if n in (a, b):
            m = b if a == n else a
            if m not in parent: parent[m] = n; order.append(m)
children = {n: [m for m in parent if parent[m] == n] for n in parent}
def unit(a, b): d = cpos(b) - cpos(a); return d / np.linalg.norm(d)

def hall_path(c, d_in, d_out):
    """floor path inside hall c from the opening toward d_in to the opening toward d_out (unit vectors), round the fountain."""
    o = cpos(c)
    A = o + d_in * 10.4; B = o + d_out * 10.4
    if np.dot(d_in, d_out) < -0.5:                          # straight through: bend round the fountain
        p = np.array([-d_in[1], d_in[0]]) * 5.2
        return [A, o + d_in * 5.5 + p, o + d_out * 5.5 + p, B]
    return [A, o + d_in * 5.0 + d_out * 5.0, B]

paths = []                                                  # (points, distance at the start), each pointing home
dist = {root: 0.0}
for n in order:
    if n == root: continue
    pr = parent[n]
    # gallery: from n's opening to pr's opening
    d = unit(n, pr)
    a = cpos(n) + d * 10.4; b = cpos(pr) - d * 10.4
    dist_pr_open = dist[pr] + (0.0 if pr == root else 10.4 + 6.0)       # rough distance from pr's opening to home
    L_g = float(np.linalg.norm(b - a))
    dist[n] = dist_pr_open + L_g + 12.0
    paths.append(([a, b], dist_pr_open + L_g))
for n in order:                                             # through each hall: every child opening to the parent opening
    pr = parent[n]
    d_home = unit(n, pr) if pr is not None else None
    for ch in children[n]:
        d_c = unit(n, ch)
        if d_home is None:                                  # the Colossus: from each nave to the foot of the statue
            o = cpos(n); pts = [o + d_c * 10.4, o + d_c * 6.0]
        else:
            pts = hall_path(n, d_c, d_home)
        paths.append((pts, dist[n]))
    if not children[n] and d_home is not None:             # a dead end: from the far side of the hall to the way out
        o = cpos(n); pts = [o - d_home * 6.0 + np.array([-d_home[1], d_home[0]]) * 5.0, o + d_home * 5.0 + np.array([-d_home[1], d_home[0]]) * 5.0, o + d_home * 10.4]
        paths.append((pts, dist[n]))

B = NA.Builder(); w = 0.035
for pts, d0 in paths:
    P = [np.array(p, float) for p in pts]
    seg = [np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1)]
    total = sum(seg); acc = 0.0
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; L = seg[i]
        if L < 1e-3: continue
        t = (b - a) / L; nrm = np.array([-t[1], t[0]]) * w
        n_sub = max(1, int(L / 1.0))
        for k in range(n_sub):
            p0 = a + t * L * k / n_sub; p1 = a + t * L * (k + 1) / n_sub
            u0 = d0 + total - (acc + L * k / n_sub); u1 = d0 + total - (acc + L * (k + 1) / n_sub)   # distance home falls along the path
            q = [(p0 - nrm), (p0 + nrm), (p1 + nrm), (p1 - nrm)]
            # Blender coords: (x, y=z_unity, z=height)
            B.quad_strip([[(q[0][0], q[0][1], 0.03), (q[1][0], q[1][1], 0.03)], [(q[3][0], q[3][1], 0.03), (q[2][0], q[2][1], 0.03)]],
                         [[(u0, 0), (u0, 1)], [(u1, 0), (u1, 1)]], 'Thread')
        acc += L
uv_export(B, 'ThreadLines', {'Thread': dict(shader='thread', alpha='BLEND')})
json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1)
print('thread paths', len(paths), 'max distance', round(max(dist.values()), 1))
