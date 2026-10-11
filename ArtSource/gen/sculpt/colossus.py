"""The Colossus, recarved: a woman thirteen metres tall in a high-girdled peplos, standing in contrapposto on her
pedestal, her right arm raised forward with the palm turned up to the light of the oculus, her face lifted toward it.
Her left hand gathers a fold of her mantle. Built at human scale (1.70 m) and enlarged.

Run inside the sculpt folder:  python3 colossus.py [preview]"""
import sys, os, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdf import Sculpt, frame, rot
from human import proportions, Skeleton, Figure, nrm, lerp
from drapery import Peplos, Mantle

HEIGHT = 13.0
HAND = 1.3                                  # the offering hand a little larger than life, but in proportion

POSE = dict(
    hip_tilt=4.5, shoulder_tilt=-4.0, pelvis_twist=-4, twist=5,
    spine_lo=(0.0, 0.0, 1), spine_hi=(-0.05, 0.02, 1),
    neck=(-0.06, -0.1, 1), head=(-0.1, 0.22, 1), head_fwd=(-0.35, -0.85, 0.45),
    upperarm_R=(-0.45, -0.78, 0.28), forearm_R=(-0.06, -0.22, 1.0),
    hand_R=(-0.3, -0.95, 0.1), palm_R=(0.06, 0.2, 1.0), curl_R=[0.35, 0.15, 0.2, 0.25, 0.3],
    upperarm_L=(0.18, 0.08, -1), forearm_L=(0.06, -0.38, -0.92), hand_L=(-0.05, -0.35, -0.94), palm_L=(-0.85, 0.35, 0.0),
    curl_L=[0.5, 0.75, 0.85, 0.9, 0.95], thumb_L=0.4,
    thigh_L=(0.03, 0.0, -1), shin_L=(0.0, 0.015, -1), foot_L=(0.18, -1, -0.3),
    thigh_R=(-0.07, -0.16, -1), shin_R=(-0.03, 0.14, -1), foot_R=(-0.3, -1, -0.15),
)

def build():
    P = proportions(1.70, sex=0)
    sk = Skeleton(P, POSE)
    sc = Sculpt()
    fig = Figure(sc, sk, sex=0, muscle=0.25, build=1.06)
    # the body (only arms, shoulders, neck, feet and head show; the rest gives the cloth its form)
    fig.torso()
    fig.leg('L'); fig.leg('R')
    Peplos(sc, sk, fig, folds=30, cling='R').carve()       # before the arms: the cloth is shaped on the body alone
    fig.arm('L', hand=False); fig.arm('R', hand=False)
    fig.hand('L', curl=POSE['curl_L'])
    fig.hand('R', curl=POSE['curl_R'], scale=HAND, spread=0.45, thumb_open=0.15)
    Mantle(sc, sk, fig, side='L').carve()
    fig.head(hair='waves')
    return sc, sk, fig

def palm_point(sk):
    wr = sk.J['wrist_R']; fd, pn = sk.hand['R']
    return wr + fd * 0.05 * HAND * sk.P['k'] + pn * 0.012 * HAND * sk.P['k'], pn

def platforms(Vu, palm, normal):
    """invisible footholds spiralling round her from the floor beside the pedestal up to her palm (statue-local Unity
    coordinates, origin on the pedestal top). Each: centre, size (tangential, thickness, radial), yaw."""
    PED = 1.8; R_PED = 4.7
    th_end = math.atan2(palm[2], palm[0])
    out = []
    rise = 0.21
    # 1) up the outside of the pedestal from the floor to its top: a quarter turn behind her
    h = -PED + rise; th = th_end + math.pi + 2.2
    while h < 0.0:
        r = R_PED + 0.55
        out.append((th, r, h)); th += 0.21 / r * 3.1; h += rise
    # 2) round her on the pedestal and up her side to the palm
    h_end = palm[1] - 0.25
    n = int((h_end - h) / rise) + 1
    dth = ((th_end - th) % (2 * math.pi) + 2 * 2 * math.pi) / n       # two full turns plus the remainder
    for i in range(n):
        hh = h + i * rise
        t = th + i * dth
        m = np.abs(Vu[:, 1] - (hh + 0.9)) < 1.0                         # body within reach of a standing person
        Q = Vu[m]
        if len(Q):
            ang = np.arctan2(Q[:, 2], Q[:, 0]); dang = np.abs((ang - t + math.pi) % (2 * math.pi) - math.pi)
            sel = dang < 0.3
            rb = float(np.linalg.norm(Q[sel][:, [0, 2]], axis=1).max()) if sel.any() else 1.0
        else:
            rb = 1.0
        out.append((t, rb + 0.5, hh))
    plats = []
    for k, (t, r, hh) in enumerate(out):
        if k + 1 < len(out):
            t2, r2, _ = out[k + 1]; arc = abs(t2 - t) * (r + r2) / 2
        else:
            arc = 0.8
        x, z = r * math.cos(t), r * math.sin(t)
        yaw = math.degrees(math.atan2(-math.sin(t), math.cos(t)))      # tangential length along the spiral
        plats.append(dict(p=[round(x, 3), round(hh - 0.1, 3), round(z, 3)], size=[round(max(0.8, arc * 1.25), 3), 0.2, 0.9], r=round(-math.degrees(t) + 90, 2)))
    # the last step into the palm, and the palm itself to stand in
    lt = out[-1]
    plats.append(dict(p=[round(palm[0], 3), round(palm[1] - 0.12, 3), round(palm[2], 3)], size=[1.1, 0.2, 1.1], r=0.0))
    return plats, [round(lt[1] * math.cos(lt[0]), 3), round(lt[2], 3), round(lt[1] * math.sin(lt[0]), 3)]

def export_main():
    from export import export_statue
    t = time.time()
    sc, sk, fig = build()
    V, F = sc.mesh(0.0015, smooth=3, target=900000)
    print('mesh', len(F), round(time.time() - t, 1))
    k = HEIGHT / 1.70
    floor = V[:, 2].min()
    origin = np.array([sk.J['pelvis'][0], sk.J['pelvis'][1], floor])
    xf = export_statue('Colossus', V, F, origin, k, lods=(('', 220000), ('_LOD1', 45000)))
    pp, pn = palm_point(sk)
    palm = xf(pp[None])[0]; nu = np.array([-pn[0], pn[2], -pn[1]])
    Vu = xf(V[::7])
    plats, top = platforms(Vu, palm, nu)
    DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'out', 'Data')
    ex2 = json.load(open(os.path.join(DATA, 'Kit2Extra.json')))
    ex2['colossus'] = dict(palm=palm.round(3).tolist(), palm_normal=(nu / np.linalg.norm(nu)).round(3).tolist(), height=HEIGHT, pedestal=1.8)
    json.dump(ex2, open(os.path.join(DATA, 'Kit2Extra.json'), 'w'), indent=1)
    ex3 = json.load(open(os.path.join(DATA, 'Kit3Extra.json')))
    ex3['colossus_platforms'] = plats
    ex3['colossus_ledges'] = [pl['p'] for pl in plats]
    ex3['colossus_ledge_top'] = top
    json.dump(ex3, open(os.path.join(DATA, 'Kit3Extra.json'), 'w'), indent=1)
    print('palm', palm.round(2), 'normal', nu.round(2), 'platforms', len(plats), 'top', top, round(time.time() - t, 1), 's')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'export':
        export_main(); sys.exit()
    S = './'
    t = time.time()
    sc, sk, fig = build()
    V, F = sc.mesh(0.0035, smooth=3, target=220000)
    np.savez(S + 'colossus.npz', V=V, F=F)
    import look
    look.render(V, F, S + 'colossus.png', views=(0, 35, 90, 200), res=(320, 600), samples=12)
    print('done', round(time.time() - t, 1))
