"""Original human figures for the House's statues, built from my own skeleton, proportions and anatomy (no scans,
no base meshes). Blender coordinates: z up, metres, the figure faces -y, its right side is -x.

A pose is a set of bone directions (world space) laid down the chains from the pelvis; the body is then pressed
onto the posed bones as clay: the masses a sculptor blocks in (ribcage, pelvis, the big muscle groups), the joints,
hands with jointed fingers, feet with toes, and a head carved feature by feature."""
import math
import numpy as np
from sdf import frame, rot

def nrm(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-12)

def lerp(a, b, t): return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t

# ------------------------------------------------------------------------------------------------ proportions
def proportions(height=1.70, sex=0.0, child=0.0):
    """landmark heights and lengths (m). sex 0 = woman .. 1 = man. child 1 = a boy of about seven (scaled to height)."""
    P = dict(ankle=0.075, knee=0.46, hip=0.86, pelvis_w=0.085 + 0.004 * sex, waist=1.04, chest=1.235, neck=1.405,
             shoulder=1.385, shoulder_w=0.162 + 0.022 * sex, chin=1.48, crown=1.70,
             upperarm=0.285 + 0.01 * sex, forearm=0.245 + 0.01 * sex, hand=0.18 + 0.01 * sex, foot=0.235 + 0.02 * sex, head=1.0)
    if child:
        # about six heads tall: big head, short legs, narrow shoulders
        c = child
        P.update(ankle=0.075, knee=0.43 - 0.05 * c, hip=0.86 - 0.12 * c, waist=1.04 - 0.1 * c, chest=1.235 - 0.12 * c,
                 neck=1.405 - 0.125 * c, shoulder=1.385 - 0.125 * c, shoulder_w=0.162 - 0.03 * c, chin=1.48 - 0.1 * c,
                 upperarm=0.285 - 0.05 * c, forearm=0.245 - 0.045 * c, hand=0.18 - 0.035 * c, foot=0.235 - 0.04 * c,
                 pelvis_w=0.085 - 0.01 * c, head=1.0 + 0.0 * c)
    k = height / 1.70
    out = {a: (b * k if a != 'head' else b) for a, b in P.items()}
    out['k'] = k
    out['headk'] = (out['crown'] - out['chin']) / 0.22        # head size relative to the 0.22 m canon head
    return out

# ------------------------------------------------------------------------------------------------ skeleton
class Skeleton:
    """joint positions from world-space bone directions. pose keys (all optional): spine_lo, spine_hi, neck, head
    (the head's up), head_fwd (where the face looks), hip_tilt / shoulder_tilt (deg, + raises the figure's left),
    twist / pelvis_twist (deg about z), upperarm_L/R, forearm_L/R, hand_L/R (finger direction), palm_L/R (palm
    normal), thigh_L/R, shin_L/R, foot_L/R, curl_L/R (thumb + 4 fingers, 0 straight .. 1 closed), root (x, y)."""
    def __init__(self, P, pose):
        self.P = P; self.pose = pose
        d = lambda key, dflt: nrm(pose.get(key, dflt))
        rx, ry = pose.get('root', (0.0, 0.0))
        drop = pose.get('drop', 0.0)                  # pelvis lowered by bent knees
        pel = np.array([rx, ry, P['hip'] + 0.055 * P['k'] - drop], float)
        J = {'pelvis': pel}
        tilt = math.radians(pose.get('hip_tilt', 0.0)); stilt = math.radians(pose.get('shoulder_tilt', 0.0))
        tw = math.radians(pose.get('twist', 0.0)); ptw = math.radians(pose.get('pelvis_twist', 0.0))
        px = np.array([math.cos(tilt) * math.cos(ptw), -math.sin(ptw) * math.cos(tilt), math.sin(tilt)])
        self.pelvis_x = nrm(px)
        J['hip_L'] = pel + px * P['pelvis_w'] - np.array([0, 0, 0.055 * P['k']])
        J['hip_R'] = pel - px * P['pelvis_w'] - np.array([0, 0, 0.055 * P['k']])
        sp_lo = d('spine_lo', (0, 0, 1)); sp_hi = d('spine_hi', (0, 0.03, 1))
        J['waist'] = pel + sp_lo * (P['waist'] - P['hip'] - 0.055 * P['k'])
        J['chest'] = J['waist'] + sp_hi * (P['chest'] - P['waist'])
        J['neck'] = J['chest'] + nrm(sp_hi + np.array([0, 0.06, 0])) * (P['neck'] - P['chest'])
        sx = np.array([math.cos(stilt) * math.cos(tw), -math.sin(tw) * math.cos(stilt), math.sin(stilt)])
        self.shoulder_x = nrm(sx)
        self.chest_up = sp_hi
        drop_sh = (P['neck'] - P['shoulder'])
        J['shoulder_L'] = J['neck'] + sx * P['shoulder_w'] - sp_hi * drop_sh + np.array([0, 0.005, 0])
        J['shoulder_R'] = J['neck'] - sx * P['shoulder_w'] - sp_hi * drop_sh + np.array([0, 0.005, 0])
        nk = d('neck', (0, -0.18, 1))
        J['head_base'] = J['neck'] + nk * (P['chin'] - P['neck']) * 1.04
        self.head_up = d('head', (0, -0.02, 1)); hf = nrm(pose.get('head_fwd', (0, -1, 0)))
        self.head_fwd = nrm(hf - self.head_up * np.dot(hf, self.head_up))
        for s, sg in (('L', 1), ('R', -1)):
            J['elbow_' + s] = J['shoulder_' + s] + d('upperarm_' + s, (sg * 0.14, 0.02, -1)) * P['upperarm']
            J['wrist_' + s] = J['elbow_' + s] + d('forearm_' + s, (sg * 0.05, -0.12, -1)) * P['forearm']
            J['knee_' + s] = J['hip_' + s] + d('thigh_' + s, (sg * 0.02, 0, -1)) * (P['hip'] - P['knee'])
            J['ankle_' + s] = J['knee_' + s] + d('shin_' + s, (0, 0.01, -1)) * (P['knee'] - P['ankle'])
            J['toe_' + s] = J['ankle_' + s] + d('foot_' + s, (sg * 0.15, -1, -0.32)) * P['foot']
        self.J = J
        self.hand = {}
        for s, sg in (('L', 1), ('R', -1)):
            fd = d('hand_' + s, J['wrist_' + s] - J['elbow_' + s])
            pn = d('palm_' + s, (-sg, 0.2, 0))
            pn = nrm(pn - fd * np.dot(pn, fd))
            self.hand[s] = (fd, pn)

# ------------------------------------------------------------------------------------------------ body
class Figure:
    def __init__(self, sc, sk: Skeleton, sex=0.0, child=0.0, muscle=0.4, build=1.0, belly=0.0):
        self.b = sc; self.s = sk; self.sex = sex; self.child = child; self.muscle = muscle; self.build = build; self.belly = belly
        self.P = sk.P; self.k = sk.P['k']

    def r(self, x): return x * self.k * self.build
    def rl(self, x): return x * self.k                 # lengths that don't thicken with build

    def torso(self):
        b, J = self.b, self.s.J; R = self.r; sex = self.sex; ch = self.child
        up_lo = nrm(J['waist'] - J['pelvis']); up_hi = nrm(J['chest'] - J['waist'])
        Fp = frame(up_lo, self.s.pelvis_x); Fc = frame(up_hi, self.s.shoulder_x)
        Fw = frame(nrm(up_lo + up_hi), nrm(self.s.pelvis_x + self.s.shoulder_x))
        wide = 1 - sex
        # pelvis bowl and sacrum
        b.ell(J['pelvis'] + Fp @ [0, R(0.005), -R(0.02)], [R(0.138 + 0.018 * wide - 0.02 * ch), R(0.095), R(0.095)], Fp, k=R(0.05))
        for sg in (1, -1):        # gluteal masses
            b.ell(J['pelvis'] + Fp @ [sg * R(0.062), R(0.045), -R(0.055)], [R(0.078 + 0.008 * wide), R(0.068), R(0.09)], Fp, k=R(0.045))
        # belly: soft below the navel, a hollow at the navel
        bl = self.belly
        b.ell(lerp(J['pelvis'], J['waist'], 0.4) + Fp @ [0, -R(0.035 + 0.025 * bl), 0], [R(0.105 + 0.01 * bl), R(0.07 + 0.03 * bl), R(0.09)], Fp, k=R(0.05))
        b.ell(J['waist'] + Fw @ [0, -R(0.004), 0], [R(0.112 + 0.012 * sex), R(0.082 + 0.01 * bl), R(0.085)], Fw, k=R(0.06))
        b.ell(lerp(J['pelvis'], J['waist'], 0.75) + Fw @ [0, -R(0.088 + 0.02 * bl), 0], [R(0.006), R(0.006), R(0.009)], Fw, k=R(0.008), op='cut')   # navel
        # ribcage and upper chest
        b.ell(J['chest'] + Fc @ [0, R(0.004), -R(0.03)], [R(0.128 + 0.026 * sex - 0.02 * ch), R(0.098 + 0.01 * sex), R(0.145)], Fc, k=R(0.05))
        b.ell(lerp(J['chest'], J['neck'], 0.5) + Fc @ [0, R(0.012), 0], [R(0.11 + 0.035 * sex), R(0.075), R(0.065)], Fc, k=R(0.05))
        # back: shoulder blades and the spine furrow
        for sg in (1, -1):
            b.ell(lerp(J['chest'], J['neck'], 0.3) + Fc @ [sg * R(0.065), R(0.085), 0], [R(0.055), R(0.02), R(0.07)], Fc, k=R(0.04))
        b.cone(J['waist'] + Fw @ [0, R(0.097), 0], J['chest'] + Fc @ [0, R(0.1), R(0.04)], R(0.006), R(0.006), k=R(0.025), op='cut')
        for s, sg in (('L', 1), ('R', -1)):
            sh = J['shoulder_' + s]
            # trapezius: from the back of the neck to the point of the shoulder, low and flat
            b.cone(J['neck'] + Fc @ [sg * R(0.01), R(0.035), R(0.045)], sh + Fc @ [-sg * R(0.012), R(0.02), R(0.012)], R(0.032), R(0.022), k=R(0.035))
            # clavicle: from the pit of the throat out to the shoulder, nearly level
            b.cone(J['neck'] + Fc @ [sg * R(0.016), -R(0.05), -R(0.006)], sh + Fc @ [-sg * R(0.012), -R(0.025), R(0.014)], R(0.008), R(0.0095), k=R(0.012))
            # deltoid cap
            ua = nrm(J['elbow_' + s] - sh)
            b.ell(sh + ua * R(0.035) + Fc @ [sg * R(0.006), 0, 0], [R(0.042 + 0.012 * self.muscle), R(0.047), R(0.068)], frame(ua, Fc[:, 0] * sg), k=R(0.03))
            # pectoral
            b.ell(J['chest'] + Fc @ [sg * R(0.065), -R(0.07), R(0.045)], [R(0.068), R(0.028 + 0.012 * sex * self.muscle), R(0.055)], Fc, k=R(0.04))
            if sex < 0.5 and not ch:
                bc = J['chest'] + Fc @ [sg * R(0.079), -R(0.095), -R(0.008)]
                Fb = Fc @ rot([0, 0, 1], sg * 14) @ rot([1, 0, 0], 10)
                b.ell(bc, [R(0.05), R(0.047), R(0.05)], Fb, k=R(0.035))
                b.ell(bc + Fc @ [sg * R(0.004), -R(0.03), -R(0.01)], [R(0.034), R(0.026), R(0.034)], Fb, k=R(0.025))
            # obliques / flank
            b.ell(lerp(J['waist'], J['chest'], 0.35) + Fc @ [sg * R(0.098 + 0.01 * sex), -R(0.005), 0], [R(0.035), R(0.06), R(0.1)], Fc, k=R(0.05))
            b.ell(lerp(J['pelvis'], J['waist'], 0.55) + Fp @ [sg * R(0.11 + 0.012 * wide), -R(0.005), 0], [R(0.04), R(0.06), R(0.07)], Fp, k=R(0.05))
            # latissimus
            b.ell(lerp(J['waist'], J['chest'], 0.7) + Fc @ [sg * R(0.105), R(0.035), 0], [R(0.035 + 0.01 * sex), R(0.05), R(0.1)], Fc, k=R(0.045))
        if sex > 0.5 and not ch:                       # the rectus wall
            for row in range(3):
                for sg in (1, -1):
                    c = lerp(J['waist'], J['chest'], -0.35 + row * 0.33) + Fw @ [sg * R(0.03), -R(0.084), 0]
                    b.ell(c, [R(0.028), R(0.012 * self.muscle + 0.004), R(0.032)], Fw, k=R(0.02))
        self.neck()

    def neck(self):
        b, J = self.b, self.s.J; R = self.r
        Fc = frame(self.s.chest_up, self.s.shoulder_x)
        hb = J['head_base']; hk = self.P['headk']
        hu = self.s.head_up; hf = self.s.head_fwd; hx = nrm(np.cross(hf, hu))
        top = hb + hu * self.rl(0.03) * hk + hf * self.rl(-0.012) * hk
        b.cone(J['neck'] - self.s.chest_up * R(0.035), top, R(0.052 + 0.01 * self.sex), R(0.047 + 0.006 * self.sex), k=R(0.03))
        for sg in (1, -1):         # the two strap muscles from behind the ears to the pit of the throat
            ear = hb + hx * sg * self.rl(0.046) * hk + hu * self.rl(0.045) * hk - hf * self.rl(0.0) * hk
            pit = J['neck'] + Fc @ [sg * R(0.012), -R(0.052), -R(0.006)]
            b.cone(ear, pit, R(0.011), R(0.009), k=R(0.016))
        if self.sex > 0.5:
            b.ell(lerp(J['neck'], hb, 0.55) + hf * R(0.04), [R(0.012), R(0.012), R(0.016)], frame(hu), k=R(0.01))   # Adam's apple

    def arm(self, s, hand=True):
        b, J = self.b, self.s.J; R = self.r; sg = 1 if s == 'L' else -1
        sh, el, wr = J['shoulder_' + s], J['elbow_' + s], J['wrist_' + s]
        ua = nrm(el - sh); fa = nrm(wr - el)
        Fu = frame(ua, self.s.shoulder_x * sg)
        fd, pn = self.s.hand[s]
        b.cone(sh, el, R(0.04), R(0.029), k=R(0.02))
        b.ell(lerp(sh, el, 0.55) + Fu @ [0, -R(0.012), 0], [R(0.03 + 0.008 * self.muscle), R(0.031 + 0.01 * self.muscle), R(0.075)], Fu, k=R(0.022))
        b.ell(lerp(sh, el, 0.42) + Fu @ [0, R(0.016), 0], [R(0.032), R(0.03), R(0.085)], Fu, k=R(0.022))
        b.ball(el, R(0.028), k=R(0.018))
        b.ball(el + Fu @ [0, R(0.022), 0], R(0.012), k=R(0.012))                   # point of the elbow
        Ff = frame(fa, np.cross(pn, fa) * sg)
        b.cone(el, wr, R(0.031), R(0.02), k=R(0.018))
        b.ell(lerp(el, wr, 0.27), [R(0.033), R(0.028), R(0.07)], Ff, k=R(0.022))
        b.ell(lerp(el, wr, 0.75), [R(0.024), R(0.016), R(0.04)], Ff, k=R(0.015))     # wrist flattens
        if hand: self.hand(s)

    def hand(self, s, curl=None, spread=0.5, scale=1.0, thumb_open=None, nails=True):
        """the carved hand (hand.py) at this figure's wrist. curl = [thumb, index, middle, ring, little]."""
        from hand import carve_hand
        fd, pn = self.s.hand[s]
        if curl is None: curl = self.s.pose.get('curl_' + s, [0.2, 0.15, 0.2, 0.25, 0.3])
        if thumb_open is None: thumb_open = self.s.pose.get('thumb_' + s, 0.3)
        hs = self.k * scale * (1 + 0.08 * self.sex) * (self.P['hand'] / (0.18 * self.k) if self.child else 1.0)
        carve_hand(self.b, self.s.J['wrist_' + s], fd, pn, side=s, s=hs, curl=curl, spread=spread, thumb_open=thumb_open, nails=nails)

    def leg(self, s):
        b, J = self.b, self.s.J; R = self.r; sg = 1 if s == 'L' else -1; wide = 1 - self.sex
        hp, kn, an, to = J['hip_' + s], J['knee_' + s], J['ankle_' + s], J['toe_' + s]
        th = nrm(kn - hp); sh = nrm(an - kn)
        Ft = frame(th, self.s.pelvis_x * sg)
        b.cone(hp + self.s.pelvis_x * sg * R(0.012), kn, R(0.078 + 0.006 * wide), R(0.045), k=R(0.04))
        b.ell(lerp(hp, kn, 0.45) + Ft @ [R(0.004), -R(0.02), 0], [R(0.053), R(0.052), R(0.16)], Ft, k=R(0.04))         # quadriceps
        b.ell(lerp(hp, kn, 0.3) + Ft @ [-R(0.026), R(0.004), 0], [R(0.045), R(0.05), R(0.13)], Ft, k=R(0.04))          # adductors
        b.ell(lerp(hp, kn, 0.1) + Ft @ [R(0.035), R(0.01), 0], [R(0.045 + 0.008 * wide), R(0.055), R(0.085)], Ft, k=R(0.05))  # hip
        b.ell(lerp(hp, kn, 0.78) + Ft @ [-R(0.018), -R(0.012), 0], [R(0.03), R(0.03), R(0.05)], Ft, k=R(0.03))       # vastus medialis
        b.ball(kn + Ft @ [0, -R(0.006), 0], R(0.042), k=R(0.02))
        b.ell(kn + Ft @ [0, -R(0.036), -R(0.008)], [R(0.022), R(0.012), R(0.026)], Ft, k=R(0.012))                   # kneecap
        Fs = frame(sh, self.s.pelvis_x * sg)
        b.cone(kn, an, R(0.042), R(0.025), k=R(0.02))
        b.ell(lerp(kn, an, 0.28) + Fs @ [-R(0.008), R(0.024), 0], [R(0.042), R(0.038), R(0.1)], Fs, k=R(0.03))        # calf
        b.ell(lerp(kn, an, 0.6) + Fs @ [0, R(0.012), 0], [R(0.03), R(0.026), R(0.09)], Fs, k=R(0.03))
        for sx in (1, -1): b.ball(an + Fs @ [sx * R(0.024), 0, R(0.004 * sx)], R(0.015), k=R(0.012))          # ankle bones
        self.foot(s)

    def foot(self, s):
        b, J = self.b, self.s.J; R = self.r; sg = 1 if s == 'L' else -1
        an, to = J['ankle_' + s], J['toe_' + s]
        fdir = nrm(to - an)
        fl = nrm(np.array([fdir[0], fdir[1], 0])) if np.linalg.norm(fdir[:2]) > 0.2 else np.array([0, -1.0, 0])
        fx = nrm(np.cross(fl, [0, 0, 1])) * -1            # foot's own left
        ground = min(an[2] - R(0.075), to[2] - R(0.022))
        heel = an - fl * R(0.04); heel[2] = ground + R(0.034)
        b.ell(heel, [R(0.028), R(0.034), R(0.034)], frame(fl), k=R(0.02))
        ball = an + fl * self.rl(0.15); ball[2] = ground + R(0.022)
        b.cone(an, lerp(an, ball, 0.5) + np.array([0, 0, R(0.01)]), R(0.03), R(0.028), k=R(0.02))
        b.cone(heel, ball, R(0.026), R(0.022), k=R(0.025))
        arch = lerp(heel, ball, 0.5) + fx * sg * -R(0.012)
        b.ell(arch + np.array([0, 0, R(0.012)]), [R(0.035), R(0.06), R(0.022)], frame([0, 0, 1], fl), k=R(0.02))
        b.ell(ball + fx * sg * -R(0.004), [R(0.036), R(0.02), R(0.018)], frame([0, 0, 1], fx), k=R(0.015))
        # toes, big toe on the inside
        for t in range(5):
            off = (0.022 - t * 0.0112) * -sg
            base = ball + fx * self.rl(off) * -1 + fl * self.rl(0.006 - 0.004 * t)
            base[2] = ground + R(0.016 - 0.0015 * t)
            ln = [0.042, 0.032, 0.029, 0.025, 0.021][t]; rr = [0.0125, 0.0085, 0.0082, 0.0078, 0.0072][t]
            tip = base + nrm(fl - fx * (0.06 * (t - 1.5)) * -sg) * self.rl(ln); tip[2] = ground + R(rr * 0.9)
            mid = lerp(base, tip, 0.55); mid[2] += R(0.004)
            b.chain([base, mid, tip], [R(rr), R(rr * 0.95), R(rr * 0.8)], k=R(0.005))

    def head(self, **kw):
        Head(self.b, self.s.J['head_base'], self.s.head_up, self.s.head_fwd, self.P['headk'] * self.k * (1.0 if not self.child else 1.0),
             sex=self.sex, child=self.child, **kw).carve()

    def body(self, arms=('L', 'R'), legs=('L', 'R'), hands=True):
        self.torso()
        for s in arms: self.arm(s, hand=hands)
        for s in legs: self.leg(s)

# ------------------------------------------------------------------------------------------------ head
class Head:
    """a classical head carved feature by feature in its own frame: x to the figure's left, y back, z up, origin on
    the neck axis at the height of the chin. Canon: 0.22 from chin to crown, eyes half way, thirds of the face from
    hairline to brow to nose to chin."""
    def __init__(self, b, base, up, fwd, k, sex=0.0, child=0.0, hair='waves', beard=False, face=None, fillet=True):
        self.b = b; self.k = k; self.sex = sex; self.child = child; self.hair = hair; self.beard = beard
        self.face = face or {}; self.fillet = fillet
        up = nrm(up); fwd = nrm(fwd - up * np.dot(fwd, up))
        x = nrm(np.cross(fwd, up))
        self.F = np.stack([x, -fwd, up], 1); self.o = np.asarray(base, float)
    def p(self, x, y, z):
        if self.child and not getattr(self, '_skull', False):         # a child's face sits low and small on a big skull
            c = self.child; z = 0.012 + (z - 0.012) * (1 - 0.12 * c); x = x * (1 - 0.06 * c); y = y * (1 - 0.06 * c)
        return self.o + self.F @ (np.array([x, y, z], float) * self.k)
    def R(self, v): return v * self.k
    def M(self, extra=np.eye(3)): return self.F @ extra

    # the skull's own surface for laying hair: azimuth u (0 = face, +-pi/2 = ears, pi = back), elevation v
    CR = np.array([0.0, 0.014, 0.134]); CRR = np.array([0.074, 0.092, 0.088])
    def cap(self, u, v, lift=0.0):
        ch = self.child
        c = self.CR + [0, 0.004 * ch, 0.006 * ch] + np.array([math.sin(u) * math.cos(v) * self.CRR[0], -math.cos(u) * math.cos(v) * self.CRR[1], math.sin(v) * self.CRR[2]]) * (1 + lift) * (1 + 0.07 * ch)
        self._skull = True; q = self.p(*c); self._skull = False
        return q

    def carve(self):
        b, p, R, M = self.b, self.p, self.R, self.M
        sx = 1.0 + 0.05 * self.sex; ch = self.child; fm = self.face
        jaw = 0.93 + 0.27 * self.sex - 0.1 * ch
        fem = 1 - self.sex
        # cranium (a child's larger)
        self._skull = True
        b.ell(p(*(self.CR + [0, 0.004 * ch, 0.006 * ch])), list(self.CRR * [sx, 1, 1] * self.k * (1 + 0.07 * ch)), M(), k=R(0.02))
        self._skull = False
        if ch:
            for sg in (1, -1): b.ell(p(sg * 0.034, -0.06, 0.062), [R(0.022), R(0.022), R(0.022)], M(), k=R(0.02))   # round cheeks
        # maxilla and the mouth's mound, cheeks and cheekbones, the jaw and chin, filled under the jaw to the neck
        b.ell(p(0, -0.07, 0.046), [R(0.028), R(0.026), R(0.024)], M(), k=R(0.022))
        b.ell(p(0, -0.072, 0.086), [R(0.021), R(0.016), R(0.032)], M(), k=R(0.025))                        # mid-face under the nose
        b.ell(p(0, -0.05, 0.143), [R(0.058), R(0.034), R(0.03)], M(), k=R(0.03))                           # forehead
        for sg in (1, -1):
            b.ell(p(sg * 0.024, -0.072, 0.09), [R(0.016), R(0.012), R(0.015)], M(), k=R(0.02))             # under the eyes
        for sg in (1, -1):
            b.ell(p(sg * 0.035, -0.048 - 0.003 * fem, 0.074), [R(0.022 + 0.002 * fem), R(0.028 + 0.002 * fem), R(0.027)], M(), k=R(0.035))   # cheek
            b.ell(p(sg * 0.046 * jaw, -0.018, 0.064), [R(0.015), R(0.042), R(0.04)], M(), k=R(0.04))             # masseter, cheek to ear
            b.ell(p(sg * 0.047, -0.056, 0.097), [R(0.017), R(0.019), R(0.011)], M(), k=R(0.022))                 # cheekbone
            b.ell(p(sg * 0.051, -0.05, 0.115), [R(0.013), R(0.03), R(0.024)], M(), k=R(0.025))                   # temple / outer orbit
            b.cone(p(sg * 0.045, -0.079, 0.122), p(sg * 0.049, -0.067, 0.099), R(0.0055), R(0.006), k=R(0.007))  # orbital rim
            b.cone(p(sg * 0.05 * jaw, -0.008, 0.033), p(sg * 0.012, -0.08, 0.009), R(0.010 * jaw), R(0.011), k=R(0.022))
        b.ell(p(0, -0.082 + 0.002 * fem, 0.013 + 0.004 * ch), [R(0.017 * jaw), R(0.012), R(0.013 + 0.002 * self.sex)], M(), k=R(0.014))
        b.ell(p(0, -0.04, 0.016), [R(0.04), R(0.042), R(0.022)], M(), k=R(0.02))
        # brow ridge and glabella
        b.cone(p(-0.044, -0.082 + 0.003 * fem, 0.124), p(0.044, -0.082 + 0.003 * fem, 0.124), R(0.0085 - 0.0015 * fem), R(0.0085 - 0.0015 * fem), k=R(0.014))
        b.ball(p(0, -0.088, 0.12), R(0.0085), k=R(0.01))
        # eyes: socket, blank eyeball, lids, and the soft arch under the brow
        for sg in (1, -1):
            b.ell(p(sg * 0.03, -0.093, 0.11), [R(0.0175), R(0.0085), R(0.0115)], M(), k=R(0.008), op='cut')
            b.ball(p(sg * 0.03, -0.0745 - 0.0008 * fem, 0.11), R(0.0125 + 0.0005 * fem), k=R(0.0015))
            b.curve([p(sg * 0.0155, -0.0845, 0.1085), p(sg * 0.03, -0.0885, 0.1157), p(sg * 0.0455, -0.0805, 0.1112)],
                    [R(0.0016), R(0.0026), R(0.0016)], k=R(0.002))
            b.curve([p(sg * 0.0165, -0.085, 0.106), p(sg * 0.03, -0.0868, 0.1036), p(sg * 0.0445, -0.0805, 0.1068)],
                    [R(0.0012), R(0.0018), R(0.0012)], k=R(0.002))
            b.ell(p(sg * 0.031, -0.081, 0.121), [R(0.016), R(0.006), R(0.004)], M(), k=R(0.006))
        # nose: bridge from the root, tip, wings, nostrils, the base
        nl = fm.get('nose', 1.0) * (0.72 + 0.36 * self.sex - 0.25 * ch)
        b.cone(p(0, -0.088, 0.114), p(0, -0.1 - 0.004 * nl, 0.072), R(0.0062), R(0.0074), k=R(0.007))
        b.ball(p(0, -0.1015 - 0.004 * nl, 0.064), R(0.0088), k=R(0.006))
        b.cone(p(0, -0.1 - 0.003 * nl, 0.058), p(0, -0.094, 0.053), R(0.0042), R(0.0036), k=R(0.003))
        for sg in (1, -1):
            b.cone(p(sg * 0.006, -0.089, 0.108), p(sg * 0.009, -0.096, 0.07), R(0.004), R(0.0055), k=R(0.006))
            b.ell(p(sg * 0.0118, -0.0925, 0.0595), [R(0.0072), R(0.0078), R(0.0064)], M(), k=R(0.0045))
            b.ell(p(sg * 0.0066, -0.0985, 0.0545), [R(0.0033), R(0.0042), R(0.002)], M(), k=R(0.0015), op='cut')
        # mouth: philtrum ridges, lips, the parting, the corners, the hollow under the lower lip
        sm = fm.get('smile', 0.0)
        if sm:
            for sg in (1, -1): b.ell(p(sg * 0.03, -0.075, 0.06), [R(0.014), R(0.012), R(0.011)], M(), k=R(0.012))   # cheeks lifted by the smile
        for sg in (1, -1): b.cone(p(sg * 0.0038, -0.0955, 0.0515), p(sg * 0.0048, -0.0975, 0.0448), R(0.0016), R(0.0017), k=R(0.002))
        b.curve([p(-0.0235, -0.087, 0.0388), p(-0.0125, -0.0958, 0.0412), p(-0.0045, -0.0985, 0.0428), p(0, -0.0978, 0.0418),
                 p(0.0045, -0.0985, 0.0428), p(0.0125, -0.0958, 0.0412), p(0.0235, -0.087, 0.0388)],
                [R(0.0012), R(0.0034 * (1 + 0.2 * fem)), R(0.0043 * (1 + 0.2 * fem)), R(0.004 * (1 + 0.2 * fem)), R(0.0043 * (1 + 0.2 * fem)), R(0.0034 * (1 + 0.2 * fem)), R(0.0012)], k=R(0.0025))
        b.curve([p(-0.02, -0.088, 0.0362), p(-0.0095, -0.0952, 0.0322), p(0, -0.0962, 0.0315), p(0.0095, -0.0952, 0.0322), p(0.02, -0.088, 0.0362)],
                [R(0.0012), R(0.0046 * (1 + 0.25 * fem)), R(0.0052 * (1 + 0.25 * fem)), R(0.0046 * (1 + 0.25 * fem)), R(0.0012)], k=R(0.0025))
        b.curve([p(-0.0245, -0.0885, 0.0381 + 0.005 * sm), p(-0.012, -0.0975, 0.0377 + 0.0012 * sm), p(0, -0.1005, 0.0375), p(0.012, -0.0975, 0.0377 + 0.0012 * sm), p(0.0245, -0.0885, 0.0381 + 0.005 * sm)],
                [R(0.0006), R(0.0009), R(0.001), R(0.0009), R(0.0006)], k=R(0.0008), op='cut')
        for sg in (1, -1): b.ball(p(sg * 0.0238, -0.0868, 0.0381 + 0.005 * sm), R(0.0018), k=R(0.0015), op='cut')
        b.ell(p(0, -0.0935, 0.0235), [R(0.011), R(0.004), R(0.0038)], M(), k=R(0.004), op='cut')
        # ears
        for sg in (1, -1):
            ec = p(sg * 0.069, 0.004, 0.105)
            Fe = M(rot([0, 0, 1], -sg * 20))
            b.ell(ec, [R(0.0065), R(0.016), R(0.029)], Fe, k=R(0.005))
            b.ell(ec + Fe @ [R(0.0045) * sg, -R(0.002), R(0.003)], [R(0.004), R(0.0095), R(0.017)], Fe, k=R(0.0025), op='cut')
            b.ell(p(sg * 0.067, 0.0, 0.081), [R(0.005), R(0.0065), R(0.0075)], Fe, k=R(0.004))
        if self.hair: getattr(self, 'hair_' + self.hair)()
        if self.beard: self.carve_beard()

    # ---- hair
    def lock(self, pts_uvl, r0, r1, k=None):
        pts = [self.cap(u, v, l) for (u, v, l) in pts_uvl]
        n = len(pts)
        rr = [self.R(r0 + (r1 - r0) * (i / (n - 1))) * (0.6 + 0.4 * math.sin(math.pi * min(1, (i + 0.5) / (n * 0.35)))) for i in range(n)]
        self.b.curve(pts, rr, k=k if k is not None else self.R(0.003))

    def hair_waves(self):
        """centre-parted waves drawn back over the tops of the ears into a coiled knot low at the back, with a fillet.
        Broad locks with chiselled grooves between them, the waves' crests running across the locks."""
        b = self.b; R = self.R
        b.ell(self.p(0, 0.026, 0.141), [R(0.0785), R(0.0975), R(0.092)], self.M(), k=R(0.012))              # the hair mass, behind the hairline
        b.ell(self.p(0, 0.075, 0.075), [R(0.058), R(0.04), R(0.05)], self.M(), k=R(0.02))                  # the nape gathered up
        kv = -0.36                                                                                          # the knot's height on the skull
        N = 10
        def path(side, f, lift_add=0.0, n=15):
            v0 = 0.44 + f * 1.0
            pts = []
            for t in np.linspace(0, 1, n):
                u = side * (0.04 + (math.pi - 0.32) * t)
                au = abs(u)
                dip = (1 - f) * 0.6 * math.sin(min(math.pi, max(0.0, (au - 0.3) / 2.3 * math.pi))) ** 1.2
                v = (1 - t) * v0 + t * (kv + 0.16 * (f - 0.5)) - dip
                wave = math.sin(au * 2.4 + 0.4)
                pts.append((u, v + 0.035 * wave, 0.062 + 0.018 * wave + 0.02 * t + lift_add))
            return pts
        for side in (1, -1):
            for i in range(N):
                f = i / (N - 1)
                self.lock(path(side, f), 0.0125 - 0.002 * f, 0.008)
            for i in range(N - 1):                                       # grooves between the locks
                f = (i + 0.5) / (N - 1)
                pts = [self.cap(u, v, l + 0.085) for (u, v, l) in path(side, f, 0.0)]
                b.curve(pts[1:-2], [R(0.0026)] * (len(pts) - 3), k=R(0.002), op='cut')
        b.curve([self.cap(0, v, 0.11) for v in np.linspace(0.45, 1.45, 8)], [R(0.0025)] * 8, k=R(0.002), op='cut')   # the parting
        for j in range(-3, 4):                                           # the crown combed straight back down into the knot
            u0 = math.pi + j * 0.13
            pts = [(u0 + 0.04 * math.sin(t * 6 + j), (1 - t) * 1.42 + t * (kv + 0.12), 0.06 + 0.018 * math.sin(t * 7 + j) + 0.03 * t) for t in np.linspace(0, 1, 10)]
            self.lock(pts, 0.011, 0.008)
        # the knot: a coiled lock wound three times round itself
        kc = self.cap(math.pi, kv, 0.2)
        bx = self.F[:, 0]; by = self.F[:, 1]; bz = self.F[:, 2]
        pts = []
        for t in np.linspace(0, 1, 40):
            a = t * 2 * math.pi * 2.6; rr = R(0.03 * (1 - 0.7 * t))
            pts.append(kc + (bx * math.cos(a) + bz * math.sin(a)) * rr + by * R(0.004 + 0.022 * t))
        b.curve(pts, [R(0.011), R(0.0095), R(0.008)], k=R(0.004))
        if self.fillet:                                                  # a ribbon round the head
            pts = [self.cap(u, 0.7 - 0.62 * abs(u) / math.pi, 0.1) for u in np.linspace(-2.95, 2.95, 19)]
            b.curve(pts, [R(0.004)] * len(pts), k=R(0.002))

    def hair_curls(self):
        """a boy's short curls: snail-shell knots over the whole head, leaving the face and the nape."""
        b = self.b; R = self.R
        rng = np.random.default_rng(5)
        b.ell(self.p(*self.CR), list(self.CRR * self.k * 1.03), self.M(), k=R(0.01))
        n = 0
        while n < 170:
            u = rng.uniform(-math.pi, math.pi); v = rng.uniform(-0.25, 1.5)
            if math.cos(u) > 0.25 and v < 0.62: continue           # forehead and face
            if abs(abs(u) - math.pi / 2) < 0.35 and v < 0.05: continue   # ears
            c = self.cap(u, v, 0.045)
            nrm_ = nrm(c - self.p(*self.CR))
            rr = R(rng.uniform(0.0085, 0.012))
            b.ball(c, rr, k=R(0.0035))
            b.torus(c + nrm_ * rr * 0.55, nrm_, rr * 0.55, rr * 0.22, k=R(0.0015), op='cut')
            n += 1

    def hair_short(self):
        """a man's short, combed-forward locks."""
        b = self.b; R = self.R
        rng = np.random.default_rng(9)
        b.ell(self.p(*self.CR), list(self.CRR * self.k * 1.025), self.M(), k=R(0.01))
        for i in range(120):
            u = rng.uniform(-math.pi, math.pi); v = rng.uniform(-0.1, 1.45)
            if math.cos(u) > 0.3 and v < 0.6: continue
            c0 = (u, v, 0.03); c1 = (u * 0.9, v - 0.12, 0.05); c2 = (u * 0.82, v - 0.22, 0.03)
            self.lock([c0, c1, c2], 0.007, 0.003)

    def carve_beard(self):
        b, p, R = self.b, self.p, self.R
        rng = np.random.default_rng(11)
        for i in range(90):
            x = rng.uniform(-0.055, 0.055); z = rng.uniform(-0.03, 0.07)
            if z > 0.03 and abs(x) < 0.028: continue
            y = -0.06 - 0.025 * (1 - (abs(x) / 0.06) ** 2) ** 0.5
            c = p(x, y, z)
            b.curve([c, c + self.M() @ R(np.array([rng.normal(0, 0.006), -0.01, -0.02])), c + self.M() @ R(np.array([rng.normal(0, 0.01), -0.006, -0.035]))],
                    [R(0.007), R(0.006), R(0.002)], k=R(0.003))
