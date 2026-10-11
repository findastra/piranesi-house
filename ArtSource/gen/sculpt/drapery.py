"""Carved cloth for the statues. A garment layer is a surface of revolution r(theta, z) wrapped round the body:
the body is sampled to find its outline at each height, the cloth spans that outline (it bridges hollows, it does
not dip between the legs or under the breasts), hangs straight down from whatever holds it out (hips, breasts, a
bent knee), and carries folds - ridges that start small where the cloth is gathered (belt, brooches, shoulders)
and grow, wander and break as they fall, then splay where the hem meets the floor."""
import math
import numpy as np
from sdf import frame, rot, catmull
from human import nrm, lerp

TAU = 2 * math.pi

def body_outline(sc, centres, zs, nt, rmax, step):
    """radius of the body's outline from each centre, at each height, at nt angles (theta from +x toward +y)."""
    th = np.linspace(0, TAU, nt, endpoint=False)
    rho = np.arange(rmax, 0, -step)
    nz = len(zs)
    P = np.empty((nz, nt, len(rho), 3))
    for i in range(nz):
        P[i, :, :, 0] = centres[i][0] + np.cos(th)[:, None] * rho[None, :]
        P[i, :, :, 1] = centres[i][1] + np.sin(th)[:, None] * rho[None, :]
        P[i, :, :, 2] = zs[i]
    v = sc.sample(P.reshape(-1, 3)).reshape(nz, nt, len(rho))
    inside = v < 0
    first = np.where(inside.any(2), inside.argmax(2), len(rho) - 1)
    return rho[first] * inside.any(2), th

def hull_radius(r, th):
    """per height, the radius of the convex hull of the outline (cloth stretched round it)."""
    out = np.empty_like(r)
    for i in range(r.shape[0]):
        pts = np.stack([np.cos(th) * r[i], np.sin(th) * r[i]], 1)
        if r[i].max() <= 0: out[i] = 0; continue
        from scipy.spatial import ConvexHull
        try:
            hv = ConvexHull(pts).vertices
        except Exception:
            out[i] = r[i]; continue
        hp = pts[hv]; ha = np.arctan2(hp[:, 1], hp[:, 0]) % TAU; o = np.argsort(ha); hp = hp[o]; ha = ha[o]
        # intersect each ray with the hull polygon
        for j, a in enumerate(th):
            d = np.array([math.cos(a), math.sin(a)]); best = 0.0
            for k in range(len(hp)):
                p0 = hp[k]; p1 = hp[(k + 1) % len(hp)]
                e = p1 - p0; den = d[0] * (-e[1]) - d[1] * (-e[0])
                if abs(den) < 1e-12: continue
                tt = (p0[0] * (-e[1]) - p0[1] * (-e[0])) / den
                ss = (d[0] * p0[1] - d[1] * p0[0]) / den
                if tt > 0 and -1e-9 <= ss <= 1 + 1e-9: best = max(best, tt)
            out[i, j] = best
    return out

def smooth_theta(r, n=2):
    for _ in range(n): r = (np.roll(r, 1, 1) + 2 * r + np.roll(r, -1, 1)) / 4
    return r

def adiff(a, b):
    return (a - b + math.pi) % TAU - math.pi

def add_folds(r, th, zs, folds, rng):
    """folds: list of dicts with theta0, drift (rad per metre fallen), z0 (start), A (amplitude at the bottom, m),
    w (width, m), grow (exponent). Adds tube-like ridges outward."""
    out = r.copy()
    zt = zs[0]
    for f in folds:
        for i, z in enumerate(zs):
            fall = f['z0'] - z
            if fall <= 0: continue
            g = min(1.0, fall / f.get('span', 0.6)) ** f.get('grow', 0.8)
            amp = f['A'] * (f.get('a0', 0.15) + (1 - f.get('a0', 0.15)) * g)
            amp *= f.get('fade', lambda z_, t_: 1.0)(z, th) if callable(f.get('fade')) else 1.0
            tc = f['theta0'] + f['drift'] * fall + f.get('wob', 0.0) * math.sin(fall * f.get('wf', 7.0) + f.get('ph', 0.0))
            base = np.maximum(r[i], 0.02)
            w = (f['w'] * (0.5 + 0.5 * g)) / base
            u = adiff(th, tc) / w
            prof = np.where(np.abs(u) < 1, 0.7 * np.sqrt(np.clip(1 - u * u, 0, 1)) + 0.3 * (1 - u * u) ** 2, 0.0)
            out[i] = np.maximum(out[i], r[i] + amp * prof) if f.get('max', True) else out[i] + amp * prof
    return out

class Layer:
    """one garment layer between z_top and z_bot round a centre line."""
    def __init__(self, sc, centres, zs, nt=144):
        self.sc = sc; self.c = np.asarray(centres, float); self.zs = np.asarray(zs, float); self.nt = nt

    def outline(self, rmax=0.45, step=0.003):
        r, self.th = body_outline(self.sc, self.c, self.zs, self.nt, rmax, step)
        return r

class Peplos:
    """a peplos: the long skirt (hanging from the hips, flaring at the hem, pooling on the floor, tented over a bent
    knee) and the overfold (hanging free from the breasts to the hips, its hem falling lower at the sides),
    with straps over the shoulders and a neckline. Call carve() after the torso and legs are built and before
    the arms, so the arms don't count as body."""
    def __init__(self, sc, sk, fig, seed=3, folds=30, cling='R', thick=0.012, floor_pool=1.0, trail=0.0, overfold=True, straps=True, hem_lift=0.0, top='waist'):
        self.b = sc; self.s = sk; self.f = fig; self.rng = np.random.default_rng(seed)
        self.n = folds; self.cling = cling; self.K = fig.k; self.thick = thick; self.pool = floor_pool
        self.trail = trail; self.overfold = overfold; self.straps = straps; self.hem_lift = hem_lift; self.top = top

    def R(self, x): return x * self.K

    def centre(self, z):
        J = self.s.J
        line = [J['ankle_L'] * 0.5 + J['ankle_R'] * 0.5, J['knee_L'] * 0.5 + J['knee_R'] * 0.5, J['pelvis'], J['waist'], J['chest'], J['neck']]
        zs = [p[2] for p in line]
        if z <= zs[0]: return line[0][:2]
        for a, b in zip(line[:-1], line[1:]):
            if a[2] <= z <= b[2]:
                t = (z - a[2]) / (b[2] - a[2] + 1e-9); return lerp(a, b, t)[:2]
        return line[-1][:2]

    def carve(self):
        J = self.s.J; R = self.R; rng = self.rng; b = self.b
        z_floor = min(J['toe_L'][2], J['toe_R'][2]) - R(0.06) + R(self.hem_lift)
        z_waist = J['waist'][2] if self.top == 'waist' else J['pelvis'][2] + R(0.035); z_hip = J['pelvis'][2] - R(0.04)
        z_arm = lerp(J['chest'], J['neck'], 0.25)[2]
        # ---------------- skirt: waist to floor
        zs = np.linspace(z_waist, z_floor + R(0.002), 70)
        cen = np.array([self.centre(z) for z in zs])
        cen[:, 1] += np.linspace(0, R(0.025), len(zs)) + np.linspace(0, R(self.trail), len(zs)) ** 1.0   # the hem drifts (forward, or back in a wind)
        L = Layer(b, cen, zs); r_body = L.outline(rmax=R(0.42), step=R(0.0025)); th = L.th
        r = hull_radius(r_body, th) + R(self.thick) - R(0.008)
        for i in range(1, len(zs)):                                       # the cloth falls straight from what holds it out
            r[i] = np.maximum(r[i], r[i - 1] * 0.998)
        nz = len(zs)
        fl = np.linspace(0, 1, nz)
        r = r + (R(0.035) * fl ** 2.5)[:, None]                            # gentle flare toward the hem
        pool = np.clip((zs - (z_floor + R(0.1))) / R(-0.1), 0, 1)          # last 10 cm: spreading on the floor
        r = r + (R(0.035) * self.pool * pool ** 2.2)[:, None]
        r = smooth_theta(r, 2)
        # folds: hanging from the waist, wandering; fewer and deeper toward the hem
        folds = []
        n = self.n
        for k in range(n):
            t0 = k / n * TAU + rng.uniform(-0.08, 0.08)
            big = rng.uniform(0.5, 1.4)
            folds.append(dict(theta0=t0, drift=rng.normal(0, 0.06), z0=z_waist - R(rng.uniform(0.0, 0.25)),
                              A=R(0.034 * big), w=R(0.03 * big + 0.008), span=R(0.6), grow=0.7, a0=0.12,
                              wob=rng.uniform(0.0, 0.05), wf=rng.uniform(4, 9), ph=rng.uniform(0, 6)))
        # over the bent knee: folds radiate from the knee and run down to the hem
        if self.cling:
            kn = J['knee_' + self.cling]
            i_k = int(np.argmin(np.abs(zs - kn[2])))
            ak = math.atan2(kn[1] - cen[i_k][1], kn[0] - cen[i_k][0])
            for k in range(7):
                folds.append(dict(theta0=ak + (k - 3) * 0.15, drift=(k - 3) * 0.14, z0=kn[2] - R(0.02), A=R(0.026 + 0.008 * (k % 2)),
                                  w=R(0.03), span=R(0.3), grow=0.6, a0=0.05))
        r2 = add_folds(r, th, zs, folds, rng)
        # chiselled grooves between the folds
        hem = z_floor + R(0.012) * (1 + np.sin(th * 7 + 0.6) * 0.5 + np.sin(th * 13 + 2.0) * 0.3)
        b.radial(cen, r2, hem, z_waist + R(0.03), z_floor, k=R(0.02))
        if not self.overfold: return self.straps_only(J, R, b, z_arm)
        # ---------------- overfold: from the armpits to below the hips, hanging free from the breasts
        zs2 = np.linspace(z_arm, z_hip - R(0.12), 60)
        cen2 = np.array([self.centre(z) for z in zs2])
        L2 = Layer(b, cen2, zs2); rb2 = L2.outline(rmax=R(0.36), step=R(0.002)); th2 = L2.th
        r2b = hull_radius(rb2, th2) + R(0.004)
        for i in range(1, len(zs2)):
            r2b[i] = np.maximum(r2b[i], r2b[i - 1] * 0.996)
        r2b = smooth_theta(r2b, 3)
        folds2 = []
        # from each breast and from the shoulders, folds fall to the hem
        Fc = frame(self.s.chest_up, self.s.shoulder_x)
        for sg in (1, -1):
            bc = J['chest'] + Fc @ [sg * R(0.079), -R(0.1), 0]
            ab = math.atan2(bc[1] - cen2[0][1], bc[0] - cen2[0][0])
            for k in range(5):
                folds2.append(dict(theta0=ab + (k - 2) * 0.17, drift=(k - 2) * 0.09, z0=bc[2] - R(0.02), A=R(0.022 + 0.008 * (k % 2)),
                                   w=R(0.028), span=R(0.22), grow=0.6, a0=0.1))
        for k in range(14):                                        # round the sides and back
            t0 = rng.uniform(0, TAU)
            folds2.append(dict(theta0=t0, drift=rng.normal(0, 0.05), z0=z_arm - R(0.02), A=R(rng.uniform(0.014, 0.026)), w=R(0.03),
                               span=R(0.3), grow=0.7, a0=0.15))
        r2f = add_folds(r2b, th2, zs2, folds2, rng)
        # its hem: lower at the sides where the open edges hang in zigzag points, scalloped between the folds
        side = np.abs(np.cos(th2 - math.atan2(self.s.shoulder_x[1], self.s.shoulder_x[0])))
        hem2 = (z_hip - R(0.02)) - R(0.13) * side ** 4 + R(0.02) * np.sin(th2 * 9 + 0.3)
        b.radial(cen2, r2f, hem2, z_arm, zs2[-1], k=R(0.012))
        # its lower edge turned out a little: a rolled lip
        pts = []
        for j in range(0, len(th2) + 1, 2):
            jj = j % len(th2); a = th2[jj]
            i = int(np.clip(np.searchsorted(-zs2, -hem2[jj]), 0, len(zs2) - 1))
            pts.append(np.array([cen2[i][0] + math.cos(a) * (r2f[i][jj] + R(0.002)), cen2[i][1] + math.sin(a) * (r2f[i][jj] + R(0.002)), hem2[jj] + R(0.004)]))
        b.curve(pts, [R(0.0055)] * len(pts), k=R(0.005))
        self.straps_only(J, R, b, z_arm)

    def straps_only(self, J, R, b, z_arm):
        if not self.straps: return
        Fc = frame(self.s.chest_up, self.s.shoulder_x)
        # ---------------- over each shoulder the cloth is gathered up to a brooch: fans of folds front and back
        for s, sg in (('L', 1), ('R', -1)):
            sh = J['shoulder_' + s]
            top = sh + Fc @ [-sg * R(0.05), R(0.0), R(0.035)]
            for yy in (-1, 1):
                for j in range(7):
                    x = sg * R(0.015 + 0.02 * j)
                    foot = J['chest'] + Fc @ [x, yy * (R(0.11) if yy < 0 else R(0.1)), (z_arm - J['chest'][2]) - R(0.01)]
                    mid = lerp(foot, top, 0.5) + Fc @ [0, yy * R(0.014), R(0.004)]
                    b.curve([foot, mid, top], [R(0.011), R(0.009), R(0.006)], k=R(0.008))
            b.cyl(top + Fc @ [0, -R(0.002), R(0.008)], Fc[:, 2] * 0.6 + Fc @ [-sg * 0.25, -0.35, 0], R(0.019), R(0.006), rnd=R(0.003), k=R(0.004))
            b.ball(top + Fc @ [0, -R(0.004), R(0.014)], R(0.007), k=R(0.002))

class Mantle:
    """a himation over one shoulder, down the back, and hanging in a cascade from the forearm on that side."""
    def __init__(self, sc, sk, fig, side='L', seed=8):
        self.b = sc; self.s = sk; self.f = fig; self.side = side; self.rng = np.random.default_rng(seed); self.K = fig.k
    def R(self, x): return x * self.K
    def carve(self):
        J = self.s.J; R = self.R; b = self.b; s = self.side; sg = 1 if s == 'L' else -1; rng = self.rng
        Fc = frame(self.s.chest_up, self.s.shoulder_x)
        sh = J['shoulder_' + s]; el = J['elbow_' + s]; wr = J['wrist_' + s]
        # over the shoulder and down the back: a sheet of folds fanning out toward the hips
        for j in range(9):
            a = sh + Fc @ [-sg * R(0.012 * j), R(0.03), R(0.03 - 0.002 * j)]
            back = J['pelvis'] + Fc @ [sg * R(0.12 - 0.035 * j), R(0.13), -R(0.04 + 0.01 * (j % 3))]
            mid = lerp(a, back, 0.5) + Fc @ [0, R(0.06), 0]
            b.curve([a + Fc @ [0, -R(0.035), -R(0.01)], a, mid, back], [R(0.01), R(0.016), R(0.019 + 0.004 * (j % 2)), R(0.02)], k=R(0.014))
        # draped over the forearm, hanging in a zigzag cascade
        Fw = frame(nrm(wr - el), [0, 0, 1])
        for j in range(7):
            a = lerp(el, wr, 0.15 + j * 0.11) + np.array([0, 0, R(0.018)])
            b.ball(a, R(0.024), k=R(0.012))
            drop = R(0.42 + 0.12 * math.sin(j * 1.9))
            bot = a + np.array([sg * R(0.018) * math.sin(j * 2.2), R(0.008 * j), -drop])
            mid = lerp(a, bot, 0.45) + np.array([sg * R(0.03) * math.cos(j * 1.3), -R(0.01), 0])
            b.curve([a, mid, bot], [R(0.017), R(0.021), R(0.014)], k=R(0.012))
        # the zigzag lower edge of the cascade
        pts = [lerp(el, wr, 0.15 + j * 0.11) + np.array([sg * R(0.018) * math.sin(j * 2.2), R(0.008 * j), -R(0.42 + 0.12 * math.sin(j * 1.9)) + R(0.02)]) for j in range(7)]
        b.curve(pts, [R(0.008)] * 7, k=R(0.01))
