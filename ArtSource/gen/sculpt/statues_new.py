"""The House's statues, sculpted from scratch (my own designs, no scans): the six road families and the figures in the
halls. Each builder returns (Sculpt, origin) at human scale; export scales to the size the layout expects.

  python3 statues_new.py preview <name> [h]   render a quick look to the scratchpad
  python3 statues_new.py export <name|all>    write out/Meshes/<mesh>.bytes (+ _LOD1)
"""
import sys, os, math, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdf import Sculpt, frame, rot
from human import proportions, Skeleton, Figure, Head, nrm, lerp
from drapery import Peplos, Mantle
from wings import carve_wing

SCR = './'

# ================================================================================================ the Angel
def angel():
    """a winged woman alighting: the left foot set down, the right trailing on its toes, her chiton blown back
    against her legs, both hands opening forward in welcome, her wings half raised behind her."""
    P = proportions(1.70, sex=0)
    pose = dict(hip_tilt=3, shoulder_tilt=-2, twist=-4, spine_lo=(0, -0.04, 1), spine_hi=(0, 0.02, 1),
                neck=(0, -0.18, 1), head=(0.04, -0.2, 1), head_fwd=(0.08, -1, -0.3),
                upperarm_L=(0.35, -0.3, -0.88), forearm_L=(0.3, -0.85, -0.25), hand_L=(0.25, -0.9, 0.05), palm_L=(0.15, -0.35, 1.0),
                upperarm_R=(-0.35, -0.3, -0.88), forearm_R=(-0.3, -0.85, -0.25), hand_R=(-0.25, -0.9, 0.05), palm_R=(-0.15, -0.35, 1.0),
                curl_L=[0.25, 0.15, 0.2, 0.25, 0.3], curl_R=[0.25, 0.15, 0.2, 0.25, 0.3],
                thigh_L=(0.03, -0.12, -1), shin_L=(0.0, 0.1, -1), foot_L=(0.12, -1, -0.25),
                thigh_R=(-0.03, 0.25, -1), shin_R=(-0.02, 0.55, -1), foot_R=(-0.05, 0.25, -1.0))
    sk = Skeleton(P, pose)
    sc = Sculpt(); fig = Figure(sc, sk, sex=0, muscle=0.25)
    fig.torso(); fig.leg('L'); fig.leg('R')
    Peplos(sc, sk, fig, seed=11, folds=26, cling='L', trail=0.09, floor_pool=0.3, hem_lift=0.04).carve()
    fig.arm('L', hand=False); fig.arm('R', hand=False)
    fig.hand('L', spread=0.4, thumb_open=0.3); fig.hand('R', spread=0.4, thumb_open=0.3)
    fig.head(hair='waves')
    Fc = frame(sk.chest_up, sk.shoulder_x)
    for sgn in (1, -1):
        root = sk.J['chest'] + Fc @ [sgn * 0.075, 0.09, 0.05]
        carve_wing(sc, root, Fc[:, 0] * sgn, Fc[:, 1], np.array([0, 0, 1.0]), span=1.0, raise_=0.55, spread=0.8, side=sgn)
    floor = min(sk.J['toe_L'][2], sk.J['toe_R'][2]) - 0.06
    return sc, np.array([sk.J['pelvis'][0], sk.J['pelvis'][1], floor]), 'Statue_WingedFigure', 2.3

# ================================================================================================ the Boy with Cymbals
def cymbal(sc, c, n, r=0.11):
    """a bronze cymbal carved in stone: a shallow dish with a raised boss, facing n."""
    sc.cyl(c, n, r, 0.004, rnd=0.003, k=0.004)
    sc.ell(c - nrm(n) * 0.006, [0.03, 0.03, 0.016], frame(n), k=0.006)
    sc.torus(c + nrm(n) * 0.002, n, r * 0.62, 0.002, k=0.002, op='cut')

def boy():
    """a boy of six or seven in a short belted tunic, feet planted wide, arms flung out with a cymbal in each hand,
    a heartbeat before he clashes them; his head of curls tipped back, grinning."""
    P = proportions(1.70, sex=1, child=1)
    pose = dict(hip_tilt=-2, shoulder_tilt=3, twist=4, spine_lo=(0, 0.04, 1), spine_hi=(0, 0.08, 1),
                neck=(0.0, -0.05, 1), head=(0.08, 0.3, 1), head_fwd=(0.15, -1, 0.35),
                upperarm_L=(0.75, -0.55, 0.05), forearm_L=(-0.15, -0.9, 0.35), hand_L=(-0.3, -0.5, 0.8), palm_L=(-1, 0.1, 0.1),
                upperarm_R=(-0.75, -0.5, 0.0), forearm_R=(0.12, -0.9, 0.4), hand_R=(0.3, -0.5, 0.8), palm_R=(1, 0.1, 0.1),
                curl_L=[0.6, 0.8, 0.85, 0.9, 0.9], curl_R=[0.6, 0.8, 0.85, 0.9, 0.9],
                thigh_L=(0.18, -0.02, -1), shin_L=(0.06, 0.04, -1), foot_L=(0.35, -1, -0.3),
                thigh_R=(-0.18, -0.05, -1), shin_R=(-0.05, 0.06, -1), foot_R=(-0.3, -1, -0.3))
    sk = Skeleton(P, pose)
    sc = Sculpt(); fig = Figure(sc, sk, sex=1, child=1, muscle=0.0, build=1.18, belly=0.6)
    fig.torso(); fig.leg('L'); fig.leg('R')
    z_mid = lerp(sk.J['hip_L'], sk.J['knee_L'], 0.45)[2]
    floor = min(sk.J['toe_L'][2], sk.J['toe_R'][2]) - 0.06
    Peplos(sc, sk, fig, seed=5, folds=18, cling=None, floor_pool=0.0, hem_lift=z_mid - floor + 0.03, thick=0.008).carve()
    fig.arm('L', hand=False); fig.arm('R', hand=False)
    fig.hand('L', spread=0.2, thumb_open=0.0); fig.hand('R', spread=0.2, thumb_open=0.0)
    for s, sg in (('L', 1), ('R', -1)):
        wr = sk.J['wrist_' + s]; fd, pn = sk.hand[s]
        c = wr + fd * 0.06 + pn * 0.035
        cymbal(sc, c, nrm(pn), r=0.12)
    fig.head(hair='curls', face=dict(smile=1.0))
    return sc, np.array([sk.J['pelvis'][0], sk.J['pelvis'][1], floor]), 'Statue_Child', 0.7

# ================================================================================================ the Minotaur
def bull_head(sc, base, up, fwd, k=1.0):
    """a bull's head: poll and brow, the long face to a broad wet muzzle, jowls, side-set eyes, leaf ears, and horns
    sweeping out, up and forward, ringed at the base, with a curly forelock between them."""
    up = nrm(up); fwd = nrm(fwd - up * np.dot(fwd, up)); x = nrm(np.cross(fwd, up))
    F = np.stack([x, -fwd, up], 1)
    p = lambda a, b_, c: base + F @ (np.array([a, b_, c]) * k)
    R = lambda v: v * k
    sc.ell(p(0, 0.02, 0.16), [R(0.078), R(0.085), R(0.075)], F, k=R(0.03))                    # poll and skull
    sc.cone(p(0, -0.06, 0.16), p(0, -0.2, 0.05), R(0.072), R(0.05), k=R(0.03))                 # the long face
    sc.ell(p(0, -0.225, 0.04), [R(0.062), R(0.05), R(0.048)], F, k=R(0.025))                    # muzzle
    sc.ell(p(0, -0.27, 0.045), [R(0.05), R(0.012), R(0.035)], F, k=R(0.012))                    # the nose pad
    for sg in (1, -1):
        sc.ell(p(sg * 0.026, -0.274, 0.048), [R(0.011), R(0.012), R(0.016)], F @ rot([0, 1, 0], sg * 25), k=R(0.004), op='cut')   # nostril
        sc.ell(p(sg * 0.062, -0.07, 0.08), [R(0.035), R(0.06), R(0.05)], F, k=R(0.03))       # jowl / cheek
        e = p(sg * 0.074, -0.08, 0.15)
        sc.ell(e, [R(0.012), R(0.02), R(0.017)], F, k=R(0.008), op='cut')
        sc.ball(e + F @ [sg * R(-0.004), 0, 0], R(0.016), k=R(0.003))                           # eye
        sc.curve([p(sg * 0.06, -0.06, 0.175), p(sg * 0.08, -0.085, 0.172), p(sg * 0.085, -0.105, 0.16)], [R(0.008), R(0.01), R(0.006)], k=R(0.008))  # brow
        # ears, out sideways under the horns
        ec = p(sg * 0.12, 0.03, 0.17)
        sc.ell(ec, [R(0.055), R(0.014), R(0.026)], F @ rot([0, 1, 0], -sg * 12), k=R(0.012))
        sc.ell(ec + F @ [sg * R(0.005), -R(0.008), 0], [R(0.042), R(0.008), R(0.016)], F @ rot([0, 1, 0], -sg * 12), k=R(0.004), op='cut')
        # horns
        hp = [p(sg * 0.065, 0.0, 0.215), p(sg * 0.15, -0.01, 0.24), p(sg * 0.23, -0.06, 0.31), p(sg * 0.24, -0.13, 0.4), p(sg * 0.2, -0.17, 0.46)]
        sc.curve(hp, [R(0.034), R(0.028), R(0.02), R(0.013), R(0.005)], k=R(0.012))
        for j in range(4):
            c = p(sg * (0.085 + 0.02 * j), -0.003 * j, 0.222 + 0.006 * j)
            sc.torus(c, F @ [sg * 1.0, 0, 0.25], R(0.031 - 0.002 * j), R(0.0025), k=R(0.002), op='cut')
    sc.ell(p(0, -0.17, 0.0), [R(0.045), R(0.06), R(0.026)], F, k=R(0.02))                      # lower jaw
    sc.curve([p(-0.045, -0.255, 0.018), p(0, -0.275, 0.016), p(0.045, -0.255, 0.018)], [R(0.002)] * 3, k=R(0.002), op='cut')   # mouth
    rng = np.random.default_rng(3)
    for i in range(26):                                                                          # forelock curls on the poll
        a = rng.uniform(-0.05, 0.05); c = p(a, -0.035 - rng.uniform(0, 0.045), 0.215 - abs(a) * 0.3 + rng.uniform(-0.02, 0.01))
        sc.ball(c, R(rng.uniform(0.012, 0.017)), k=R(0.004)); sc.ball(c - F[:, 1] * R(0.006), R(0.005), k=R(0.002), op='cut')

def minotaur():
    """a man of great strength with a bull's head, standing his ground: weight on the right leg, fists closed, the
    head lowered a little as a bull lowers it, a short cloth wrapped at the hips."""
    P = proportions(1.85, sex=1); P['shoulder_w'] *= 1.18; P['pelvis_w'] *= 1.05
    pose = dict(hip_tilt=-4, shoulder_tilt=3, twist=-6, spine_lo=(0, 0.0, 1), spine_hi=(0, 0.06, 1),
                neck=(0, -0.22, 1), head=(0, -0.15, 1), head_fwd=(0, -1, -0.1),
                upperarm_L=(0.32, 0.02, -1), forearm_L=(0.18, -0.25, -1), hand_L=(0.05, -0.15, -1), palm_L=(-1, 0.1, 0),
                upperarm_R=(-0.3, 0.05, -1), forearm_R=(-0.12, -0.32, -1), hand_R=(-0.02, -0.2, -1), palm_R=(1, 0.1, 0),
                curl_L=[0.8, 1.0, 1.05, 1.05, 1.05], curl_R=[0.8, 1.0, 1.05, 1.05, 1.05],
                thigh_R=(-0.05, 0.0, -1), shin_R=(0.0, 0.01, -1), foot_R=(-0.2, -1, -0.3),
                thigh_L=(0.1, -0.15, -1), shin_L=(0.02, 0.12, -1), foot_L=(0.3, -1, -0.2))
    sk = Skeleton(P, pose)
    sc = Sculpt(); fig = Figure(sc, sk, sex=1, muscle=1.0, build=1.32)
    fig.torso(); fig.leg('L'); fig.leg('R')
    z_mid = lerp(sk.J['hip_L'], sk.J['knee_L'], 0.4)[2]
    floor = min(sk.J['toe_L'][2], sk.J['toe_R'][2]) - 0.06
    Peplos(sc, sk, fig, seed=9, folds=16, cling=None, floor_pool=0.0, hem_lift=z_mid - floor, thick=0.01, overfold=False, straps=False, top='hips').carve()
    fig.arm('L', hand=False); fig.arm('R', hand=False)
    fig.hand('L', spread=0.1, thumb_open=0.0); fig.hand('R', spread=0.1, thumb_open=0.0)
    hb = sk.J['head_base']
    # the bull's neck: a great mass rising from the shoulders
    Fc = frame(sk.chest_up, sk.shoulder_x)
    sc.cone(sk.J['neck'] - sk.chest_up * 0.04, hb + sk.head_up * 0.08, 0.11, 0.095, k=0.06)
    sc.ell(sk.J['neck'] + Fc @ [0, 0.06, 0.07], [0.16, 0.09, 0.12], Fc, k=0.06)                 # the hump of the bull's neck
    sc.ell(sk.J['neck'] + Fc @ [0, -0.05, -0.02], [0.08, 0.05, 0.08], Fc, k=0.05)               # dewlap into the chest
    bull_head(sc, hb + sk.head_up * 0.02, sk.head_up, sk.head_fwd, k=1.25)
    return sc, np.array([sk.J['pelvis'][0], sk.J['pelvis'][1], floor]), 'Statue_Minotaur', 2.45

# ================================================================================================ the Gorilla
def gorilla():
    """a silverback knuckle-walking, the great shoulders up, the head low and forward, looking out under its brow;
    the fur carved as a ripple over the whole body."""
    sc = Sculpt()
    E = lambda c, r, R=np.eye(3), k=0.06: sc.ell(np.array(c, float), r, R, k=k)
    C = lambda a, b, r1, r2, k=0.05: sc.cone(np.array(a, float), np.array(b, float), r1, r2, k=k)
    tilt = rot([1, 0, 0], -28)                                   # the back slopes down from the shoulders to the rump
    E((0, 0.42, 0.74), [0.27, 0.24, 0.25])                       # hips and rump
    E((0, 0.08, 0.92), [0.37, 0.42, 0.33], tilt)                 # barrel of the chest and belly
    E((0, -0.12, 1.16), [0.43, 0.24, 0.21], tilt, k=0.08)        # shoulders and the hump over them
    E((0, 0.18, 1.02), [0.27, 0.3, 0.2], tilt, k=0.08)           # the saddle of the back
    E((0, -0.18, 0.88), [0.3, 0.22, 0.22], tilt)                 # chest
    for sg in (1, -1):
        E((sg * 0.18, -0.26, 0.95), [0.15, 0.1, 0.14], k=0.05)    # pectorals
    # head, low and forward on a short thick neck
    C((0, -0.2, 1.12), (0, -0.4, 1.12), 0.2, 0.17, k=0.07)
    hc = np.array([0, -0.46, 1.12])
    E(hc + [0, 0.02, 0.02], [0.155, 0.165, 0.16], k=0.04)        # skull
    C(hc + [0, -0.06, 0.15], hc + [0, 0.12, 0.13], 0.035, 0.03, k=0.05)    # sagittal crest
    E(hc + [0, 0.1, 0.12], [0.07, 0.06, 0.06], k=0.05)
    C(hc + [-0.11, -0.13, 0.06], hc + [0.11, -0.13, 0.06], 0.04, 0.04, k=0.03)   # the heavy brow
    E(hc + [0, -0.12, -0.07], [0.13, 0.1, 0.1], k=0.04)          # the broad, jutting muzzle
    E(hc + [0, -0.155, -0.005], [0.075, 0.045, 0.06], k=0.03)     # the flat nose, wide across the nostrils
    for sg in (1, -1):
        sc.ell(hc + [sg * 0.032, -0.195, -0.03], [0.022, 0.016, 0.014], rot([0, 1, 0], sg * 20), k=0.008, op='cut')   # flared nostrils
        E(hc + [sg * 0.042, -0.18, -0.028], [0.026, 0.018, 0.02], k=0.012)                                              # nostril wings
        sc.ell(hc + [sg * 0.065, -0.155, 0.025], [0.028, 0.02, 0.018], np.eye(3), k=0.01, op='cut')      # eye under the brow
        sc.ball(hc + [sg * 0.065, -0.145, 0.025], 0.016, k=0.004)                                         # eye
        E(hc + [sg * 0.15, 0.03, 0.03], [0.03, 0.035, 0.045], k=0.015)                                     # small ear
    sc.curve([hc + [-0.08, -0.19, -0.1], hc + [0, -0.215, -0.11], hc + [0.08, -0.19, -0.1]], [0.005] * 3, k=0.004, op='cut')   # mouth
    E(hc + [0, -0.1, -0.15], [0.11, 0.09, 0.06], k=0.04)         # jaw
    # arms: huge, the knuckles down on the ground
    for sg in (1, -1):
        sh = np.array([sg * 0.36, -0.18, 1.08]); el = np.array([sg * 0.43, -0.3, 0.6]); wr = np.array([sg * 0.4, -0.42, 0.2])
        E(sh + [sg * 0.03, 0, 0.02], [0.17, 0.17, 0.17], k=0.06)                                           # shoulder ball
        C(sh, el, 0.145, 0.105, k=0.05); E((sh + el) / 2 + [0, -0.03, 0], [0.12, 0.12, 0.2], frame(el - sh), k=0.05)
        C(el, wr, 0.11, 0.075, k=0.04); E(el * 0.65 + wr * 0.35, [0.1, 0.1, 0.16], frame(wr - el), k=0.04)
        kn = np.array([sg * 0.4, -0.47, 0.065])
        sc.box(kn, [0.08, 0.06, 0.06], rot([0, 0, 1], sg * 10), rnd=0.035, k=0.03)                         # the fist on its knuckles
        C(wr, kn + [0, 0.02, 0.03], 0.075, 0.07, k=0.03)
        for f in range(4):
            sc.ball(kn + [sg * (0.055 - f * 0.037), -0.05, -0.02], 0.03, k=0.012)                           # knuckles of the folded fingers
        sc.ball(kn + [-sg * 0.075, -0.02, 0.02], 0.032, k=0.015)                                            # thumb tucked
        # legs, short and bent, feet flat with the big toe out to the side
        hp = np.array([sg * 0.2, 0.45, 0.68]); knee = np.array([sg * 0.34, 0.24, 0.36]); an = np.array([sg * 0.3, 0.52, 0.1])
        C(hp, knee, 0.16, 0.1, k=0.06); C(knee, an, 0.1, 0.07, k=0.04)
        E(knee * 0.6 + an * 0.4 + [0, 0.05, 0], [0.09, 0.09, 0.14], frame(an - knee), k=0.04)            # calf
        E(an + [0, -0.1, -0.055], [0.085, 0.16, 0.05], k=0.03)                                              # foot
        for f in range(4): sc.ball(an + [sg * (-0.05 + f * 0.03), -0.25, -0.07], 0.024, k=0.01)
        sc.ball(an + [-sg * 0.085, -0.13, -0.07], 0.03, k=0.015)                                           # the big toe, set apart
    # fur: a fine ripple, combed down the limbs and back over the body, chiselled into the surface
    from sdf import noise
    def fur(P):
        n1 = noise(P * [1.0, 1.0, 0.35], 9.0, seed=4, octaves=2)
        n2 = noise(P, 3.0, seed=7, octaves=1)
        return 0.006 * n1 + 0.004 * n2
    sc.displace(fur, 0.02)
    return sc, np.array([0.0, 0.0, 0.0]), 'Statue_Beast', None

# ================================================================================================ the Elephant
def elephant():
    """an elephant standing square, its trunk hanging and curling forward at the tip, tusks out, ears spread a
    little; on its back, over a fringed saddle cloth, a small castle of dressed stone with a crenellated top."""
    sc = Sculpt()
    E = lambda c, r, R=np.eye(3), k=0.08: sc.ell(np.array(c, float), r, R, k=k)
    C = lambda a, b, r1, r2, k=0.05: sc.cone(np.array(a, float), np.array(b, float), r1, r2, k=k)
    E((0, 0.08, 0.98), [0.4, 0.64, 0.42])                       # body
    E((0, 0.55, 0.95), [0.37, 0.32, 0.42])                      # rump
    E((0, -0.32, 1.02), [0.41, 0.32, 0.44])                     # shoulders and chest
    E((0, 0.1, 0.72), [0.33, 0.5, 0.2], k=0.1)                  # belly
    for sg in (1, -1):
        for yy, back in ((-0.34, 0), (0.56, 1)):
            top = np.array([sg * 0.23, yy, 0.8]); knee = np.array([sg * 0.23, yy - 0.02 + 0.04 * back, 0.42]); foot = np.array([sg * 0.23, yy, 0.0])
            C(top, knee, 0.17, 0.135, k=0.07); C(knee, foot + [0, 0, 0.1], 0.135, 0.125, k=0.05)
            sc.cyl(foot + [0, 0, 0.06], [0, 0, 1], 0.14, 0.06, rnd=0.04, k=0.04)                              # foot pad
            for t in range(3):
                a_ = math.radians(-35 + 35 * t - 90)
                sc.ell(foot + [0.13 * math.cos(a_) * sg if False else 0.13 * math.cos(a_), 0.13 * math.sin(a_), 0.03], [0.035, 0.022, 0.025],
                       frame([math.cos(a_), math.sin(a_), 0]), k=0.01)                                           # toenails
            for j in range(5):                                                                                   # skin folds
                sc.torus(np.array([sg * 0.23, yy, 0.15 + j * 0.06]), [0, 0, 1], 0.128, 0.006, k=0.01, op='cut')
    # head with its twin domes, small eyes, the trunk and tusks
    hc = np.array([0, -0.74, 1.18])
    E(hc, [0.24, 0.26, 0.28], k=0.08)
    for sg in (1, -1): E(hc + [sg * 0.09, 0.02, 0.2], [0.11, 0.12, 0.1], k=0.06)
    E(hc + [0, -0.14, -0.12], [0.17, 0.12, 0.2], k=0.06)                                                    # the face down to the trunk
    for sg in (1, -1):
        sc.ell(hc + [sg * 0.17, -0.12, 0.02], [0.02, 0.025, 0.015], np.eye(3), k=0.01, op='cut')
        sc.ball(hc + [sg * 0.165, -0.115, 0.02], 0.014, k=0.004)
        # ears: broad flaps spread a little from the head, the edge rolled
        ec = hc + [sg * 0.3, 0.06, -0.02]
        Re = frame([sg * 1.0, 0.45, 0.0], [0, 0, 1])
        Fe = frame([sg * 1.0, 0.45, 0], [0, 1, 0])
        sc.ell(ec, [0.04, 0.28, 0.32], Fe, k=0.03)
        sc.ell(ec + Fe @ [0, 0, 0] + np.array([sg * 0.03, 0.0, 0.0]), [0.014, 0.22, 0.25], Fe, k=0.02, op='cut')   # a shallow hollow on the outer face
        # tusks
        sc.curve([hc + [sg * 0.11, -0.2, -0.2], hc + [sg * 0.13, -0.33, -0.3], hc + [sg * 0.13, -0.48, -0.32], hc + [sg * 0.1, -0.58, -0.25]],
                 [0.042, 0.036, 0.025, 0.01], k=0.012)
    trunk = [hc + [0, -0.22, -0.14], hc + [0, -0.3, -0.35], hc + [0, -0.31, -0.6], hc + [0, -0.27, -0.85], hc + [0, -0.17, -0.98], hc + [0, -0.1, -0.93]]
    sc.curve(trunk, [0.115, 0.095, 0.075, 0.06, 0.045, 0.035], k=0.03)
    P = __import__('sdf').catmull(np.array(trunk), 22)
    for i in range(2, 20):                                                                                   # rings of the trunk
        d = nrm(P[i + 1] - P[i - 1]); r = np.interp(i, [0, 21], [0.11, 0.035])
        sc.torus(P[i], d, r * 0.98, 0.0045, k=0.004, op='cut')
    sc.ell(hc + [0, -0.12, -0.24], [0.1, 0.07, 0.05], np.eye(3), k=0.03)                                    # lower lip
    # tail with a tuft
    sc.curve([(0, 0.85, 1.05), (0, 0.92, 0.9), (0, 0.93, 0.65), (0, 0.91, 0.5)], [0.035, 0.025, 0.018, 0.015], k=0.02)
    for j in range(5): sc.curve([(0, 0.91, 0.5), (0.02 * (j - 2), 0.92, 0.42)], [0.012, 0.006], k=0.006)
    # saddle cloth with a fringe, then the castle
    back = 1.38
    sc.box((0, 0.1, back - 0.02), [0.42, 0.36, 0.025], np.eye(3), rnd=0.02, k=0.05)
    for sg in (1, -1):
        sc.box((sg * 0.4, 0.1, back - 0.22), [0.02, 0.36, 0.2], rot([0, 1, 0], sg * 10), rnd=0.015, k=0.04)
        for j in range(14):
            sc.cone((sg * 0.43, -0.22 + j * 0.05, back - 0.42), (sg * 0.43, -0.22 + j * 0.05, back - 0.5), 0.012, 0.006, k=0.006)
    c0 = np.array([0, 0.1, back])
    sc.box(c0 + [0, 0, 0.3], [0.3, 0.3, 0.3], np.eye(3), rnd=0.01, k=0.02)                                   # the keep
    sc.box(c0 + [0, 0, 0.62], [0.35, 0.35, 0.03], np.eye(3), rnd=0.01, k=0.01)                               # corbelled course
    for i in range(4):
        for j in range(4):
            if 0 < i < 3 and 0 < j < 3: continue
            sc.box(c0 + [-0.27 + i * 0.18, -0.27 + j * 0.18, 0.72], [0.055, 0.055, 0.08], np.eye(3), rnd=0.008, k=0.008)   # merlons
    for z in (0.12, 0.27, 0.42):                                                                             # coursing
        for nrm_ in ((1, 0), (0, 1)):
            sc.box(c0 + [0, 0, z], [0.31 if nrm_[0] else 0.311, 0.311 if nrm_[0] else 0.31, 0.004], np.eye(3), k=0.003, op='cut')
    for sg in (1, -1):                                                                                       # arched windows
        for ax in (0, 1):
            w = np.zeros(3); w[ax] = sg * 0.3
            sc.box(c0 + w + [0, 0, 0.4], [0.05 if ax else 0.02, 0.02 if ax else 0.05, 0.08], np.eye(3), rnd=0.01, k=0.006, op='cut')
            sc.cyl(c0 + w + [0, 0, 0.48], [1, 0, 0] if ax == 0 else [0, 1, 0], 0.05, 0.03, k=0.005, op='cut')
    from sdf import noise
    sc.displace(lambda P: 0.004 * noise(P * [1, 1, 3.0], 6.0, seed=2, octaves=2), 0.015)                    # wrinkled hide
    return sc, np.array([0.0, 0.0, 0.0]), 'Statue_Elephant', None

# ================================================================================================ the Albatross
def albatross():
    """an albatross on a sea-worn rock in its sky-pointing display: the long narrow wings opened wide and half
    raised, the neck stretched up, the hooked beak to the sky."""
    sc = Sculpt()
    from sdf import noise
    # the rock
    sc.ell((0, 0.05, 0.12), [0.42, 0.34, 0.2], np.eye(3), k=0.06)
    sc.ell((0.12, -0.08, 0.2), [0.22, 0.2, 0.15], np.eye(3), k=0.06)
    sc.ell((-0.15, 0.18, 0.16), [0.2, 0.18, 0.13], np.eye(3), k=0.06)
    # body: a deep, smooth torpedo, tilted up toward the head
    body = np.array([0, 0.05, 0.52]); ax = nrm([0, -0.55, 0.45])
    sc.ell(body, [0.15, 0.2, 0.34], frame([0, -1, 0.25], [1, 0, 0]), k=0.05)                                 # a long, deep body
    sc.ell(body + [0, 0.22, -0.02], [0.1, 0.1, 0.16], frame([0, 1, -0.1], [1, 0, 0]), k=0.05)               # rump
    sc.tri(body + [-0.07, 0.3, 0.0], body + [0.07, 0.3, 0.0], body + [0, 0.46, 0.02], 0.012, k=0.012)        # short wedge tail
    # neck stretched up, head pointing at the sky
    neck0 = body + [0, -0.24, 0.08]; head = body + [0, -0.3, 0.46]
    sc.curve([neck0, body + [0, -0.3, 0.26], head], [0.085, 0.062, 0.06], k=0.035)
    sc.ell(head, [0.07, 0.085, 0.075], frame([0, -0.6, 1], [1, 0, 0]), k=0.03)
    bd = nrm([0, -0.35, 1])                                                                                  # the beak's direction
    b0 = head + bd * 0.06 + np.array([0, -0.02, 0])
    tip = b0 + bd * 0.26
    sc.cone(b0, tip - bd * 0.03, 0.034, 0.016, k=0.012)
    sc.curve([tip - bd * 0.04, tip, tip + np.array([0, -0.035, -0.01])], [0.017, 0.016, 0.008], k=0.006)    # the hook
    sc.curve([b0 + [0, -0.01, -0.005], (b0 + tip) / 2 + [0, -0.018, -0.008], tip - bd * 0.02], [0.024, 0.016, 0.01], k=0.006)   # lower mandible
    sc.curve([b0 - [0, 0, 0.0] + bd * 0.01, tip - bd * 0.03], [0.003, 0.002], k=0.002, op='cut')            # the bill's seam
    for sg in (1, -1):
        sc.cone(b0 + [sg * 0.018, -0.012, 0.012], b0 + bd * 0.07 + [sg * 0.012, -0.02, 0.012], 0.008, 0.005, k=0.004)   # tube nostrils
        e = head + [sg * 0.052, -0.01, 0.02]
        sc.ball(e, 0.012, k=0.003)
        sc.curve([e + [0, 0.018, 0.012], e + [sg * 0.006, -0.004, 0.016], e + [0, -0.02, 0.006]], [0.004, 0.006, 0.003], k=0.004)   # the dark brow
        # legs and webbed feet gripping the rock
        hp = body + [sg * 0.08, 0.04, -0.14]; ft = np.array([sg * 0.1, -0.02, 0.31])
        sc.cone(hp, ft + [0, 0, 0.04], 0.03, 0.018, k=0.02)
        for t in range(3):
            a_ = math.radians(-30 + 30 * t)
            toe = ft + [math.sin(a_) * 0.11, -math.cos(a_) * 0.11, -0.02]
            sc.cone(ft + [0, 0, 0.02], toe, 0.012, 0.007, k=0.006)
        sc.tri(ft + [0, 0, 0.015], ft + [math.sin(math.radians(-30)) * 0.1, -math.cos(math.radians(-30)) * 0.1, -0.01],
               ft + [math.sin(math.radians(30)) * 0.1, -math.cos(math.radians(30)) * 0.1, -0.01], 0.004, k=0.006)   # the web
        # the wings: long and narrow, opened wide and half raised
        root = body + [sg * 0.13, -0.05, 0.1]
        carve_wing(sc, root, np.array([sg * 1.0, 0.0, 0.0]), np.array([0, 1.0, 0.0]), np.array([0, 0, 1.0]),
                   span=1.15, raise_=0.3, spread=1.0, side=sg, chord=0.42, sweep=0.35)
    sc.displace(lambda P: 0.003 * noise(P, 7.0, seed=5, octaves=2) * (P[:, 2] < 0.34), 0.02)                 # the rock pitted
    return sc, np.array([0.0, 0.0, 0.0]), 'Statue_Albatross', None

# ================================================================================================ the Seated Sage
def sage():
    """an old man seated on a block of stone, wrapped to the waist in his mantle, which climbs over his left
    shoulder; he leans forward with his chin on his right hand, a scroll held loosely on his left knee."""
    P = proportions(1.75, sex=1)
    drop = P['hip'] + 0.055 * P['k'] - 0.5
    pose = dict(drop=drop, spine_lo=(0, -0.2, 1), spine_hi=(0, -0.38, 1), neck=(0, -0.45, 1), head=(0, -0.35, 1), head_fwd=(0, -1, -0.35),
                thigh_L=(0.12, -1, -0.02), shin_L=(0.04, -0.05, -1), foot_L=(0.1, -1, -0.15),
                thigh_R=(-0.1, -1, 0.0), shin_R=(-0.04, 0.08, -1), foot_R=(-0.15, -1, -0.2),
                upperarm_R=(-0.02, -0.62, -0.78), forearm_R=(0.12, -0.05, 1.0), hand_R=(0.2, -0.35, 0.92), palm_R=(0.5, -0.8, 0.1),
                curl_R=[0.7, 1.0, 1.05, 1.05, 1.05],
                upperarm_L=(0.2, -0.4, -0.9), forearm_L=(0.05, -0.95, -0.3), hand_L=(-0.1, -0.9, -0.4), palm_L=(-0.4, 0.2, -1),
                curl_L=[0.6, 0.6, 0.7, 0.75, 0.8])
    sk = Skeleton(P, pose)
    sc = Sculpt(); fig = Figure(sc, sk, sex=1, muscle=0.45, build=1.12, belly=0.4)
    fig.torso(); fig.leg('L'); fig.leg('R')
    floor = min(sk.J['toe_L'][2], sk.J['toe_R'][2]) - 0.06
    Peplos(sc, sk, fig, seed=13, folds=24, cling='L', floor_pool=0.6, thick=0.014, overfold=False, straps=False, top='hips').carve()
    fig.arm('L', hand=False); fig.arm('R', hand=False)
    fig.hand('L', spread=0.2, thumb_open=0.2); fig.hand('R', spread=0.2, thumb_open=0.2)
    Mantle(sc, sk, fig, side='L').carve()
    # the block he sits on
    pel = sk.J['pelvis']
    sc.box([pel[0], pel[1] + 0.1, floor + 0.23], [0.3, 0.26, 0.23], np.eye(3), rnd=0.02, k=0.02)
    # the scroll on his knee
    fd, pn = sk.hand['L']; wr = sk.J['wrist_L']
    sc.cyl(wr + fd * 0.06 - pn * 0.03, np.cross(fd, pn), 0.025, 0.11, rnd=0.006, k=0.006)
    fig.head(hair='short', beard=True)
    return sc, np.array([pel[0], pel[1], floor]), 'Statue_SeatedSage', 1.7 * 0.82

# ================================================================================================ busts
def bust_base(sex, hair, beard, crown=False, seed=1):
    P = proportions(1.70, sex=sex)
    pose = dict(neck=(0.05, -0.12, 1), head=(0.08, -0.05, 1), head_fwd=(0.25, -1, -0.05), twist=-4,
                upperarm_L=(0.3, 0.05, -1), upperarm_R=(-0.3, 0.05, -1))
    sk = Skeleton(P, pose)
    sc = Sculpt(); fig = Figure(sc, sk, sex=sex, muscle=0.3)
    fig.torso()
    J = sk.J; Fc = frame(sk.chest_up, sk.shoulder_x)
    for s, sg in (('L', 1), ('R', -1)):                    # the tops of the arms, to be cut
        sh = J['shoulder_' + s]; sc.cone(sh, sh + np.array([sg * 0.04, 0.0, -0.2]), 0.042, 0.038, k=0.03)
    # a garment over the shoulders: folds from a brooch on the left shoulder across the chest
    br = J['shoulder_L'] + Fc @ [-0.04, -0.03, 0.03]
    for j in range(7):
        a_ = J['chest'] + Fc @ [-0.14 + 0.035 * j, -0.15, -0.08 + 0.01 * j]
        sc.curve([br, (br + a_) / 2 + Fc @ [0, -0.035, 0], a_], [0.005, 0.008, 0.009], k=0.01)
    sc.ell(J['chest'] + Fc @ [0.0, -0.025, -0.03], [0.165, 0.138, 0.13], Fc, k=0.04)                  # the garment over the breast
    sc.cyl(br + Fc @ [0, -0.01, 0.0], Fc[:, 2] * 0.4 - Fc[:, 1], 0.02, 0.006, rnd=0.003, k=0.004)
    hb = J['head_base']
    # trim to the bust: a rounded cut under the chest and through the upper arms
    cut_c = J['chest'] + Fc @ [0, 0.0, 0.14]
    sc.ell(cut_c, [0.2, 0.2, 0.26], Fc, k=0.006, op='keep')
    fig.neck()
    Head(sc, hb, sk.head_up, sk.head_fwd, P['headk'] * P['k'], sex=sex, hair=hair, beard=beard).carve()
    if crown:                                             # a mural crown: a ring of towers and wall
        up = sk.head_up; c = hb + up * 0.2 + sk.head_fwd * -0.005
        sc.cyl(c, up, 0.083, 0.03, rnd=0.004, k=0.01)
        for j in range(10):
            a_ = j / 10 * 2 * math.pi; d = np.array([math.cos(a_), math.sin(a_), 0]); d = nrm(d - up * np.dot(d, up))
            sc.box(c + d * 0.083 + up * 0.04, [0.014, 0.014, 0.02], frame(up, d), rnd=0.003, k=0.004)
        sc.torus(c - up * 0.02, up, 0.084, 0.006, k=0.004)
        # a veil from the crown down the back of the neck
        for j in range(9):
            a_ = math.pi * (0.15 + 0.7 * j / 8); d = nrm(np.array([math.cos(a_), math.sin(a_), 0]))
            top = c + d * 0.08 - up * 0.02
            sc.curve([top, top + d * 0.03 - up * 0.12, top + d * 0.05 - up * 0.25], [0.008, 0.011, 0.012], k=0.012)
    # the socle: a short round stem and a moulded foot
    z0 = (cut_c - Fc[:, 2] * 0.26)[2]
    sc.cyl([J['chest'][0], J['chest'][1], z0 - 0.04], [0, 0, 1], 0.06, 0.05, rnd=0.01, k=0.03)
    sc.cyl([J['chest'][0], J['chest'][1], z0 - 0.12], [0, 0, 1], 0.12, 0.035, rnd=0.012, k=0.02)
    sc.torus([J['chest'][0], J['chest'][1], z0 - 0.08], [0, 0, 1], 0.075, 0.015, k=0.01)
    floor = z0 - 0.155
    return sc, np.array([J['chest'][0], J['chest'][1], floor])

def bust():
    sc, o = bust_base(0.0, 'waves', False)
    return sc, o, 'Statue_Head', 0.75

def queen():
    sc, o = bust_base(0.0, 'waves', False, crown=True)
    return sc, o, 'Statue_Queen', 0.85

BUILDERS = {'angel': angel, 'boy': boy, 'minotaur': minotaur, 'gorilla': gorilla, 'elephant': elephant, 'albatross': albatross, 'sage': sage,
            'bust': bust, 'queen': queen}

def preview(name, h=0.004):
    import look
    sc, origin, mesh, height = BUILDERS[name]()
    V, F = sc.mesh(h, smooth=3, target=200000)
    ext = np.ptp(V, axis=0); wide = max(ext[0], ext[1]) > ext[2] * 1.1
    look.render(V, F, SCR + f'st_{name}.png', views=(0, 40, 100, 200), res=(480, 360) if wide else (330, 520), samples=12)
    np.savez(SCR + f'st_{name}.npz', V=V, F=F)

def export(name):
    from export import export_statue
    sc, origin, mesh, height = BUILDERS[name]()
    lo, hi = sc.bounds(); hgt = float(hi[2] - lo[2])
    V, F = sc.mesh(max(0.0016, hgt * 0.0011), smooth=3, target=600000)
    h = V[:, 2].max() - origin[2]
    export_statue(mesh, V, F, origin, (height / h) if height else 1.0, lods=(('', 60000), ('_LOD1', 9000)))

if __name__ == '__main__':
    cmd, name = sys.argv[1], sys.argv[2]
    t = time.time()
    if cmd == 'preview': preview(name, float(sys.argv[3]) if len(sys.argv) > 3 else 0.004)
    else:
        for n in (BUILDERS if name == 'all' else [name]): export(n)
    print('done', round(time.time() - t, 1))
