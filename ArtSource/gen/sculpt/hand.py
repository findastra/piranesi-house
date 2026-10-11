"""A carved hand: wrist, palm with its thenar and hypothenar pads, knuckles, four fingers of three phalanges
with joint knuckles, finger pads, palm-side creases and nails, and the thumb. Pose by per-finger curl and spread.

Frame: wrist point w, fingers direction fd, palm normal pn (out of the palm), side = 'L' or 'R'. Human scale
(a woman's hand 0.18 m long) times `s`."""
import math
import numpy as np
from sdf import frame

def nrm(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-12)

def bend(d, pn, deg):
    """turn direction d toward the palm side pn by deg."""
    p = nrm(pn - d * np.dot(pn, d)); a = math.radians(deg)
    return nrm(d * math.cos(a) + p * math.sin(a))

# lengths (m) of the three phalanges, finger widths, and where each finger leaves the palm (x across, toward thumb)
FINGERS = [  # index, middle, ring, little
    dict(L=(0.041, 0.025, 0.019), w=0.0088, x=0.0255, z=0.000),
    dict(L=(0.046, 0.029, 0.021), w=0.0092, x=0.0085, z=0.004),
    dict(L=(0.043, 0.027, 0.020), w=0.0086, x=-0.0085, z=0.001),
    dict(L=(0.033, 0.020, 0.018), w=0.0076, x=-0.0245, z=-0.007),
]

def carve_hand(b, w, fd, pn, side='R', s=1.0, curl=(0.2, 0.15, 0.2, 0.25, 0.3), spread=0.5, thumb_open=0.5, nails=True):
    sg = 1 if side == 'L' else -1
    fd = nrm(fd); pn = nrm(pn - fd * np.dot(pn, fd))
    back = -pn
    tw = nrm(np.cross(pn, fd)) * sg            # across the palm toward the thumb (pn x fd for the left hand)
    S = lambda v: v * s
    F = np.stack([tw, back, fd], 1)            # local: x toward the thumb, y to the back of the hand, z toward the fingers
    P = lambda x, y, z: np.asarray(w, float) + F @ (np.array([x, y, z]) * s)
    # wrist: an oval flattened front to back, into the heel of the palm
    b.ell(P(0, 0.002, -0.012), [S(0.026), S(0.018), S(0.022)], F, k=S(0.01))
    # palm: a cupped slab, thicker at the heel
    b.box(P(0.0, 0.0, 0.045), [S(0.035), S(0.0085), S(0.04)], F, rnd=S(0.008), k=S(0.009))
    b.ell(P(0.0, -0.003, 0.03), [S(0.033), S(0.012), S(0.035)], F, k=S(0.01))
    b.ell(P(0.019, -0.007, 0.022), [S(0.019), S(0.012), S(0.026)], F, k=S(0.01))          # thenar (ball of the thumb)
    b.ell(P(-0.022, -0.006, 0.027), [S(0.013), S(0.01), S(0.03)], F, k=S(0.01))           # hypothenar
    b.ell(P(0.0, -0.006, 0.071), [S(0.033), S(0.0065), S(0.011)], F, k=S(0.012))           # pads under the fingers
    b.ell(P(-0.002, -0.0135, 0.045), [S(0.022), S(0.004), S(0.028)], F, k=S(0.012), op='cut')  # the hollow of the palm
    for f, fi in enumerate(FINGERS):
        base = P(fi['x'], 0.001, 0.081 + fi['z'])
        b.ball(base + F @ np.array([0, S(0.005), 0]), S(fi['w'] * 1.12), k=S(0.006))                 # knuckle
        b.cone(P(fi['x'] * 0.55, 0.004, 0.03), base + F @ np.array([0, S(0.004), 0]), S(0.0045), S(0.006), k=S(0.006))   # metacarpal under the skin
        d = nrm(fd + tw * (fi['x'] / 0.026) * 0.09 * spread)
        c = curl[f + 1]
        p = base
        for ph in range(3):
            d = bend(d, pn, c * (30 + 18 * ph) if ph else c * 35)
            q = p + d * S(fi['L'][ph])
            wd = fi['w'] * (1.0 - 0.09 * ph)
            Fp = frame(d, tw)                                   # x toward the thumb, y = d x x
            yb = nrm(np.cross(d, tw)) if np.dot(np.cross(d, tw), back) > 0 else -nrm(np.cross(d, tw))
            Fq = np.stack([nrm(tw - d * np.dot(tw, d)), yb, d], 1)
            mid = (p + q) / 2
            b.cone(p, q, S(wd * 0.98), S(wd * 0.93), k=S(0.0022))                                          # phalanx
            b.ell(mid - yb * S(wd * 0.22), [S(wd * 0.82), S(wd * 0.7), S(fi['L'][ph] * 0.4)], Fq, k=S(0.003))    # its pad
            if ph < 2:
                b.ell(q + yb * S(wd * 0.28), [S(wd * 0.78), S(wd * 0.5), S(wd * 0.6)], Fq, k=S(0.0035))         # joint knuckle
                b.ell(q - yb * S(wd * 0.85), [S(wd * 0.9), S(wd * 0.22), S(0.0012)], Fq, k=S(0.0012), op='cut')   # crease
            else:
                b.ball(q - d * S(wd * 0.25), S(wd * 0.82), k=S(0.003))                                       # rounded tip
                if nails:
                    nc = q - d * S(fi['L'][ph] * 0.3) + yb * S(wd * 0.78)
                    b.box(nc, [S(wd * 0.62), S(0.0009), S(fi['L'][ph] * 0.34)], Fq, rnd=S(0.0008), k=S(0.0012), op='cut')   # nail bed
                    b.box(nc - yb * S(0.0006), [S(wd * 0.56), S(0.0006), S(fi['L'][ph] * 0.3)], Fq, rnd=S(0.0005), k=S(0.0008))  # nail
            p = q
    # thumb: metacarpal from the side of the wrist, then two phalanges; opens away from the index
    t0 = P(0.022, -0.004, 0.012)
    d = nrm(fd * 0.75 + tw * (0.38 + 0.4 * thumb_open) + pn * 0.3)
    lens = (0.038, 0.03, 0.025); wds = (0.0125, 0.011, 0.0102)
    p = t0
    for ph in range(3):
        if ph: d = bend(d, nrm(pn * 0.6 - tw * 0.8), curl[0] * (20 + 15 * ph))
        q = p + d * S(lens[ph])
        Fq = frame(d, pn)
        b.cone(p, q, S(wds[ph]), S(wds[ph] * 0.94), k=S(0.004 if ph else 0.009))
        if ph == 2:
            b.ball(q - d * S(0.003), S(0.0088), k=S(0.003))
            if nails:
                ybk = nrm(np.cross(d, pn)) if np.dot(np.cross(d, pn), back) > 0 else nrm(-np.cross(d, pn))
                nc = q - d * S(0.008) + nrm(back - d * np.dot(back, d)) * S(0.008)
                b.box(nc, [S(0.0065), S(0.0009), S(0.008)], frame(d, back), rnd=S(0.0008), k=S(0.0012), op='cut')
        p = q
