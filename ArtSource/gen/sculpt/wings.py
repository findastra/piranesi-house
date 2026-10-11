"""Carved wings: a bone (shoulder, elbow, wrist, tip) feathered in rows - the small rounded coverts close to the
bone, then the secondaries along the forearm, then the long primaries fanning from the wrist to the tip. Each
feather is a thin tapering blade with a raised shaft, laid overlapping like roof tiles."""
import math
import numpy as np
from sdf import frame
from human import nrm, lerp

def feather(b, root, d, up, L, w, th, k):
    """a blade from root along d, broad side facing `up`, length L, width w, thickness th, with a shaft ridge."""
    d = nrm(d); up = nrm(up - d * np.dot(up, d)); side = np.cross(d, up)
    R = np.stack([side, up, d], 1)
    c = root + d * L * 0.5
    b.ell(c, [w, th, L * 0.5], R, k=k)
    b.cone(root, root + d * L * 0.92, th * 0.9, th * 0.5, k=th)               # the shaft

def carve_wing(b, shoulder, out, back, up, span=1.0, raise_=0.6, spread=0.8, side=1, k=0.002, s=1.0, chord=1.0, sweep=0.0):
    """shoulder: root point on the back. out: direction away from the body (lateral), back: behind the figure,
    up: world up. span scales the whole wing (1 = about 1.1 m from root to tip). raise_ lifts the wing toward
    the vertical, spread opens it out from folded (0) to fully spread (1)."""
    S = lambda x: x * span * s
    out = nrm(out); back = nrm(back); up = nrm(up)
    # the wing's bones: the arm sweeps up and out, the hand back and up toward the tip
    a1 = nrm(out * (0.5 + 0.4 * spread) + up * raise_ + back * 0.35)
    elbow = shoulder + a1 * S(0.3)
    a2 = nrm(out * (0.2 + 0.6 * spread) + up * (raise_ * 1.2) + back * (0.55 - 0.3 * spread))
    wrist = elbow + a2 * S(0.32)
    a3 = nrm(out * (0.15 + 0.5 * spread) + up * (raise_ * 1.5 + 0.4) + back * 0.4)
    tip = wrist + a3 * S(0.42)
    bone = [shoulder, elbow, wrist, tip]
    b.chain(bone, [S(0.045), S(0.034), S(0.026), S(0.012)], k=S(0.02))
    # the leading edge thickens into a soft roll
    b.ell(lerp(shoulder, elbow, 0.5) + up * S(0.01), [S(0.05), S(0.035), S(0.17)], frame(a1, up), k=S(0.02))
    # the trailing direction: feathers hang down-and-back from the bone
    trail = nrm(-up * 0.85 + back * 0.6 - out * 0.1)
    face = nrm(np.cross(a2, trail)) * side            # the wing's outer face
    edge = []                                          # the trailing edge, for the vane surface beneath the feathers
    # primaries: from the wrist to the tip, long, fanning, their tips just parted
    n = 12
    for i in range(n):
        t = i / (n - 1)
        root = lerp(wrist, tip, t * 0.92)
        d = nrm(lerp(trail, a3, min(1.0, 0.2 + 0.7 * t + sweep)))
        L = S(0.56 - 0.2 * t * t + 0.03 * math.sin(i * 1.7)) * chord
        feather(b, root + face * S(0.003 * i), d, face, L, S(0.05 - 0.012 * t), S(0.006), k)
        edge.append((root, root + d * L * 0.9))
    # secondaries: along the forearm, hanging back and down
    n = 13
    for i in range(n):
        t = i / (n - 1)
        root = lerp(elbow, wrist, t)
        d = nrm(trail + a2 * 0.15 * (t - 0.5))
        L = S(0.4 - 0.05 * t) * chord
        feather(b, root + face * S(0.006), d, face, L, S(0.048), S(0.006), k)
        edge.append((root, root + d * L * 0.9))
    # the vane beneath: thin slabs from the bone to the feather tips, so the wing reads whole
    edge.sort(key=lambda e: float(np.dot(e[0] - shoulder, a2)))
    for (r0, t0), (r1, t1) in zip(edge[:-1], edge[1:]):
        if np.linalg.norm(t1 - t0) > S(0.18) or np.linalg.norm(r1 - r0) > S(0.12): continue    # no slabs across a fan's gaps
        b.tri(r0 - face * S(0.008), t0 - face * S(0.008), t1 - face * S(0.008), S(0.005), k=S(0.006))
        b.tri(r0 - face * S(0.008), t1 - face * S(0.008), r1 - face * S(0.008), S(0.005), k=S(0.006))
    # tertials by the body
    for i in range(5):
        root = lerp(shoulder, elbow, 0.3 + 0.15 * i)
        feather(b, root + face * S(0.008), nrm(trail - a1 * 0.2), face, S(0.3 - 0.02 * i) * chord, S(0.035), S(0.006), k)
    # coverts: three overlapping rows of shorter, rounder feathers over the roots
    for row, (Lr, wr, off) in enumerate([(0.22, 0.032, 0.03), (0.15, 0.03, 0.05), (0.09, 0.026, 0.065)]):
        n = 18 - row * 3
        for i in range(n):
            t = i / (n - 1)
            root = lerp(shoulder, wrist, 0.08 + 0.9 * t) if t < 0.66 else lerp(wrist, tip, (t - 0.66) * 0.6)
            d = nrm(trail + a2 * 0.1)
            feather(b, root + face * S(off * 0.25) - trail * S(0.01 * row), d, face, S(Lr) * chord, S(wr), S(0.007), k)
    return tip
