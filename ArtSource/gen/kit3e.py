"""v3 labyrinth extras: the Stormscape stair (floating steps spiralling round Astra's Infinite Pole), its walk and rail
colliders, the secret rosette, the spawn stand, Venetian mooring poles (briccole) that lead from each exit island to its far
wing, and the card textures for the dead-end tally. Run: python3 gen/kit3e.py [name ...]

Stair frame (Unity): origin on the pole axis at the landing (the top ledge of the Colossus); treads climb counter-clockwise
seen from above starting at angle THETA0 (radians, from +x toward +z)."""
import os, sys, json, math, numpy as np
from math import pi, sin, cos, atan2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import K, AS, NA, bpy, reset, apply, mesh, cyl, finish, MAN, EXTRA
from kit3b import worn_block, uv_export, sweep
from PIL import Image, ImageDraw, ImageFont, ImageFilter

rng = np.random.default_rng(5151)
STAIR = dict(r_in=0.32, r_out=2.5, per_turn=16, rise=0.22, turns=40, rail_r=2.42, rail_h=0.95, wall_r=2.58)

def stair_theta0():
    """angle of the Colossus' top ledge about the oculus axis (world), so the first tread starts beside it."""
    ex2 = json.load(open(os.path.join(K3.DATA, 'Kit2Extra.json')))['colossus']
    top = EXTRA['colossus_ledge_top']
    palm = ex2['palm']
    # statue at ry 180 with the palm under the oculus: ledge offset from the palm, rotated by 180 degrees
    dx, dz = -(top[0] - palm[0]), -(top[2] - palm[2])
    return atan2(dz, dx), math.hypot(dx, dz), top[1] + ex2['pedestal']

def tread_mesh(theta0, n, name):
    S = STAIR; d = 2 * pi / S['per_turn']
    V = []; F = []
    for k in range(n):
        a = theta0 + (k + 0.5) * d
        a0, a1 = a - d * 0.54, a + d * 0.54
        top = (k + 1) * S['rise']; bot = top - 0.09
        ring = [(S['r_in'] * cos(a0), S['r_in'] * sin(a0)), (S['r_out'] * cos(a0), S['r_out'] * sin(a0)),
                (S['r_out'] * 1.01 * cos(a), S['r_out'] * 1.01 * sin(a)), (S['r_out'] * cos(a1), S['r_out'] * sin(a1)),
                (S['r_in'] * cos(a1), S['r_in'] * sin(a1))]
        b = len(V)
        V += [(x, y, top) for x, y in ring] + [(x, y, bot) for x, y in ring]
        F.append(tuple(b + i for i in range(5)))
        F.append(tuple(b + 5 + i for i in reversed(range(5))))
        for i in range(5):
            j = (i + 1) % 5
            F.append((b + j, b + i, b + 5 + i, b + 5 + j))
    ob = mesh(V, F, 'AstraStep', name)
    return K3.recalc(ob)

def stair():
    """visual stair: 40 turns of floating treads + a gold thread rail on slender posts (Blender coords, z up)."""
    th0, r0, y0 = stair_theta0()
    S = STAIR; n = S['per_turn'] * S['turns']; d = 2 * pi / S['per_turn']
    reset()
    parts = [tread_mesh(th0, n, 'treads')]
    # rail: helix at rail_r, rail_h above the walking line
    pts = []
    for k in range(n * 2 + 1):
        a = th0 + k * d / 2
        h = (k / 2) * S['rise'] + S['rise'] * 0.5 + S['rail_h']
        pts.append(np.array([S['rail_r'] * cos(a), S['rail_r'] * sin(a), h]))
    prof = [(0.022 * cos(t), 0.022 * sin(t)) for t in np.linspace(0, 2 * pi, 7)[:-1]]
    parts.append(sweep(pts, prof, 'Gold', 'rail', closed=True))
    for k in range(0, n, 2):
        a = th0 + (k + 0.5) * d; top = (k + 1) * S['rise']
        parts.append(cyl(S['rail_r'] * cos(a), S['rail_r'] * sin(a), top, top + S['rail_h'] + 0.05, 0.014, 'Gold', 6, 'post'))
    finish(parts, 'Stair_Spiral')
    # colliders: a helicoid walk (axis to the rail) and a helical wall at the rail
    reset()
    seg = 32; m = S['turns'] * seg
    V = []; F = []
    for i in range(m + 1):
        a = th0 + 2 * pi * i / seg
        h = (S['rise'] * S['per_turn']) * i / seg + S['rise'] * 0.5
        V += [(0.0, 0.0, h), (S['wall_r'] * cos(a), S['wall_r'] * sin(a), h)]
    for i in range(m):
        a, b = 2 * i, 2 * (i + 1)
        F.append((a, a + 1, b + 1, b))
    walk = mesh(V, F, 'Marble', 'walk')
    V = []; F = []
    for i in range(m + 1):
        a = th0 + 2 * pi * i / seg
        h = (S['rise'] * S['per_turn']) * i / seg + S['rise'] * 0.5
        V += [(S['wall_r'] * cos(a), S['wall_r'] * sin(a), h - 0.2), (S['wall_r'] * cos(a), S['wall_r'] * sin(a), h + 1.35)]
    for i in range(m):
        a, b = 2 * i, 2 * (i + 1)
        F.append((a, b, b + 1, a + 1))
    wall = mesh(V, F, 'Marble', 'wall')
    finish([walk, wall], 'Stair_Spiral_Col')
    EXTRA['stair'] = dict(theta0=th0, r_landing=r0, y_landing=y0, period=S['rise'] * S['per_turn'], turns=S['turns'],
                          height=S['rise'] * n, r_out=S['r_out'], walk_r=1.45)
    print('stair theta0 %.3f landing r %.2f y %.2f' % (th0, r0, y0))

def astra_pole():
    """Astra's Infinite Pole: 45 mm silver dance pole, 460 m long (fades with distance in its shader)."""
    reset()
    ob = K.lathe([(0.0225, 0.0), (0.0225, 460.0)], 16, 'AstraPole', name='pole', cap_top=True, cap_bottom=True)
    finish([ob], 'AstraPole')

def rosette():
    """the secret button: a small gilt rosette carved on the Colossus' pedestal (face toward -y Blender = -z Unity)."""
    reset()
    parts = [K.lathe([(0.0, -0.06), (0.11, -0.06), (0.12, -0.03), (0.12, 0.0)], 24, 'Gold', name='disc', cap_top=False)]
    for k in range(8):
        a = 2 * pi * k / 8
        pet = K.lathe([(0.0, 0.0), (0.035, 0.012), (0.03, 0.03), (0.0, 0.034)], 8, 'Gold', name='petal')
        parts.append(apply(pet, (0.07 * cos(a), 0.07 * sin(a), -0.06), (0, 0, 0)))
    parts.append(K.lathe([(0.0, -0.06), (0.03, -0.075), (0.0, -0.09)], 10, 'Gold', name='boss'))
    ob = finish(parts, 'tmp', export=False)
    apply(ob, (0, 0, 0), (pi / 2, 0, 0))          # lathe axis z -> -y (the face looks out of the pedestal)
    ob.name = 'SecretRosette'; K.export_bytes(ob, 'SecretRosette')

def spawn_stand():
    """a marble stele by the spawn point: SPAWN plaque on top, the dead-end tally below (plaques mount on its -y face)."""
    reset()
    parts = [K.box(-0.42, 0.42, -0.2, 0.2, 0.0, 0.12, 'Marble', 'base'), K.box(-0.34, 0.34, -0.14, 0.14, 0.12, 1.32, 'Verde', 'die'),
             K.box(-0.4, 0.4, -0.18, 0.18, 1.32, 1.42, 'Marble', 'cap'), K.box(-0.36, 0.36, -0.16, 0.16, 1.42, 1.5, 'Gold', 'crown')]
    finish(parts, 'SpawnStand')
    EXTRA['spawn_stand'] = dict(face=-0.14, spawn_y=1.12, count_y=0.68, title_y=0.9)

def briccola():
    """Venetian mooring pole cluster: three timber posts lashed together, leaning in (base on the seabed at z=0)."""
    import kit2 as K2
    B = NA.Builder()
    for k in range(3):
        a = 2 * pi * k / 3 + 0.3
        bx, by = 0.32 * cos(a), 0.32 * sin(a)
        top = (0.05 * cos(a), 0.05 * sin(a), 6.2 + 0.25 * k)
        ring0 = [(bx + 0.13 * cos(t), by + 0.13 * sin(t), 0.0) for t in np.linspace(0, 2 * pi, 8)]
        ring1 = [(top[0] + 0.11 * cos(t), top[1] + 0.11 * sin(t), top[2]) for t in np.linspace(0, 2 * pi, 8)]
        B.quad_strip([ring0, ring1], [[(t / 6.28, 0) for t in np.linspace(0, 2 * pi, 8)], [(t / 6.28, 6) for t in np.linspace(0, 2 * pi, 8)]], 'Planks')
    for z in (3.2, 5.6):         # rope lashings
        rr = [[(0.25 * cos(t), 0.25 * sin(t), z + dz) for t in np.linspace(0, 2 * pi, 10)] for dz in (-0.08, 0.08)]
        B.quad_strip(rr, [[(t / 6.28, 0) for t in np.linspace(0, 2 * pi, 10)], [(t / 6.28, 0.2) for t in np.linspace(0, 2 * pi, 10)]], 'Rope')
    uv_export(B, 'Briccola', {'Planks': K2.M('Planks'), 'Rope': K2.M('Rope')})

# ------------------------------------------------------------------------------------------- tally cards (unlit)
FONT = os.path.join(HERE, '..', 'assets', 'fonts', 'CormorantGaramond[wght].ttf')
FONT_I = os.path.join(HERE, '..', 'assets', 'fonts', 'CormorantGaramond-Italic[wght].ttf')
def _font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight:
        try: f.set_variation_by_axes([weight])
        except Exception: pass
    return f

def _card(W, H, dark=False):
    y, x = np.mgrid[0:H, 0:W] / 1024.0
    r = np.random.default_rng(11); n = np.zeros((H, W))
    for k in range(4):
        f = 2 ** k * 1.3; ph = r.uniform(0, 6, 2)
        n += np.sin(x * f * 6.1 + np.sin(y * f * 4.3 + ph[0]) * 1.7 + ph[1]) / 2 ** k
    vein = np.exp(-np.abs(n) * 9) * 0.08
    base = np.stack([0.955 - vein, 0.935 - vein, 0.885 - vein], -1) if not dark else np.stack([0.06 + vein, 0.06 + vein, 0.11 + vein * 1.4], -1)
    return Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8))

def tally_cards():
    out = os.path.join(HERE, '..', 'out', 'Textures'); os.makedirs(out, exist_ok=True)
    gold = (176, 132, 58); ink = (40, 34, 30); soft = (92, 80, 70)
    W, H = 1024, 384
    for n in range(6):
        im = _card(W, H); d = ImageDraw.Draw(im)
        for (m, w) in ((14, 5), (28, 2)): d.rounded_rectangle([m, m, W - m, H - m], radius=20, outline=gold, width=w)
        d.text((W / 2, 78), 'DEAD ENDS FOUND', font=_font(FONT, 54, 700), fill=soft, anchor='mm')
        d.text((W / 2, 190), f'{n} / 5', font=_font(FONT, 150, 600), fill=ink, anchor='mm')
        for k in range(5):                           # five lozenges, filled for every court figure found
            cx = W / 2 + (k - 2) * 92; cy = 312
            pts = [(cx, cy - 26), (cx + 20, cy), (cx, cy + 26), (cx - 20, cy)]
            d.polygon(pts, fill=gold if k < n else None, outline=gold, width=4)
        if n == 5:
            d.text((W / 2 + 330, 312), 'the storm comes', font=_font(FONT_I, 34, 500), fill=soft, anchor='mm')
        im.save(os.path.join(out, f'Tally_{n}.png'))
    im = _card(W, H, dark=True); d = ImageDraw.Draw(im)
    for (m, w) in ((14, 5), (28, 2)): d.rounded_rectangle([m, m, W - m, H - m], radius=20, outline=(150, 160, 210), width=w)
    d.text((W / 2, 150), 'STORMSCAPE', font=_font(FONT, 130, 700), fill=(225, 230, 255), anchor='mm')
    d.text((W / 2, 280), 'climb the stair out of the Colossus to escape the storm', font=_font(FONT_I, 44, 500), fill=(170, 180, 225), anchor='mm')
    im.save(os.path.join(out, 'Tally_Storm.png'))
    print('tally cards written')


# ------------------------------------------------------------------------------------------- far halls (rudimentary)
def neon_ring():
    """a thin glowing band that rings a pedestal's top edge (unit footprint: scale x/z to the pedestal width)."""
    reset()
    o = 0.5; i_ = 0.47; h0, h1 = 0.0, 0.07
    parts = [K.box(-o, o, -o, -i_, h0, h1, 'Neon', 'a'), K.box(-o, o, i_, o, h0, h1, 'Neon', 'b'),
             K.box(-o, -i_, -i_, i_, h0, h1, 'Neon', 'c'), K.box(i_, o, -i_, i_, h0, h1, 'Neon', 'd')]
    finish(parts, 'NeonRing')

def water_lily():
    import kit2 as K2
    B = NA.Builder()
    n = 18; r = 0.32
    # pad: fan of quads (a notch at +x)
    for k in range(1, n - 1):
        a0, a1 = 2 * pi * k / n, 2 * pi * (k + 1) / n
        B.quad_strip([[(0, 0, 0.005), (0, 0, 0.005)], [(r * cos(a0), r * sin(a0), 0), (r * cos(a1), r * sin(a1), 0)]],
                     [[(0.5, 0.5), (0.5, 0.5)], [(0.5 + 0.5 * cos(a0), 0.5 + 0.5 * sin(a0)), (0.5 + 0.5 * cos(a1), 0.5 + 0.5 * sin(a1))]], 'Pad')
    # flower: two rings of upturned petals
    for (cnt, rr, lift, ph) in ((8, 0.11, 0.07, 0.0), (6, 0.07, 0.1, 0.4)):
        for k in range(cnt):
            a = 2 * pi * k / cnt + ph
            c, s_ = cos(a), sin(a)
            base = (0.02 * c, 0.02 * s_, 0.02); tip = (rr * c, rr * s_, lift)
            side = (-s_ * 0.025, c * 0.025, 0)
            p0 = tuple(np.add(base, side)); p1 = tuple(np.subtract(base, side)); p2 = tuple(np.subtract(tip, side)); p3 = tuple(np.add(tip, side))
            B.quad_strip([[p0, p1], [p3, p2]], [[(0, 0), (1, 0)], [(0, 1), (1, 1)]], 'Petal')
    uv_export(B, 'WaterLily', {'Pad': dict(shader='prop', alpha='OPAQUE', tint=[0.2, 0.42, 0.18], smooth=0.6, doubleSided=True),
                               'Petal': dict(shader='prop', alpha='OPAQUE', tint=[1.0, 0.98, 0.94], smooth=0.4, doubleSided=True)})

def grand_stair():
    """a broad marble flight: 6 m wide, 24 steps of 0.25 x 0.42 m (6 m rise), with plain cheeks (base at origin, climbing +y Blender)."""
    reset()
    parts = []
    for i in range(24):
        parts.append(K.box(-3.0, 3.0, i * 0.42, (i + 1) * 0.42, -0.2, (i + 1) * 0.25, 'Marble', 'step'))
    for sx in (-1, 1):
        parts.append(prism_cheek(sx))
    finish(parts, 'GrandStair')

def prism_cheek(sx):
    from kit3 import prism_xz
    pts = [(0.0, -0.2), (10.08, -0.2), (10.08, 6.0 + 0.9), (0.0, 0.9)]
    ob = prism_xz([(p[0], p[1]) for p in pts], 0, 0.3, 'Marble', 'cheek')        # in XZ, extruded along Y
    # prism_xz is (x, y=extrude, z): we want the run along Blender y, so swap x <-> y and place at the side
    for v in ob.data.vertices:
        x, y, z = v.co; v.co = (sx * 3.0 + (y if sx > 0 else -y), x, z)
    return K3.recalc(ob)

def slab():
    reset()
    finish([K.box(-0.5, 0.5, -0.5, 0.5, -1.0, 0.0, 'Marble', 'slab')], 'MarbleSlab')          # top at 0, 1 m thick

def beehive():
    """a straw skep for the Woman Carrying a Beehive (base at origin)."""
    reset()
    prof = [(0.0, 0.0)] + [(0.55 * (1 - (t / 1.1) ** 2.2) ** 0.5 + 0.02 * math.sin(t * 28), t) for t in np.linspace(0, 1.08, 30)] + [(0.0, 1.12)]
    ob = K.lathe(prof, 32, 'Sand', name='skep')
    finish([ob, K.box(-0.12, 0.12, -0.6, -0.5, 0.06, 0.22, 'Stone', 'door')], 'Beehive')

def bull_horns():
    """a pair of curving horns to crown the Minotaurs (statue-local, centred on the head of Statue_Beast)."""
    reset()
    parts = []
    for sx in (-1, 1):
        pts = [np.array([sx * (0.12 + 0.42 * t), -0.05 + 0.1 * t, 0.06 + 0.32 * t * t + 0.2 * t]) for t in np.linspace(0, 1, 14)]
        prof = [(0.07 * cos(a), 0.07 * sin(a)) for a in np.linspace(0, 2 * pi, 9)[:-1]]
        parts.append(sweep(pts, prof, 'Marble', 'horn'))
    finish(parts, 'BullHorns')

def bundle():
    """a bundle wrapped in linen and tied with seaweed twine (the Dead, done gently)."""
    import kit2 as K2
    B = NA.Builder()
    L = 0.9; r = 0.16
    rings = [[(r * (0.75 + 0.25 * math.sin(math.pi * t)) * cos(a), r * (0.75 + 0.25 * math.sin(math.pi * t)) * sin(a), t * L) for a in np.linspace(0, 2 * pi, 13)] for t in np.linspace(0, 1, 9)]
    B.quad_strip(rings, [[(a / 6.28, t) for a in np.linspace(0, 2 * pi, 13)] for t in np.linspace(0, 1, 9)], 'Linen')
    for t in (0.2, 0.5, 0.8):
        rr = r * (0.75 + 0.25 * math.sin(math.pi * t)) + 0.01
        B.quad_strip([[(rr * cos(a), rr * sin(a), t * L + dz) for a in np.linspace(0, 2 * pi, 13)] for dz in (-0.02, 0.02)],
                     [[(a / 6.28, 0) for a in np.linspace(0, 2 * pi, 13)], [(a / 6.28, 0.1) for a in np.linspace(0, 2 * pi, 13)]], 'Rope')
    uv_export(B, 'Bundle', {'Linen': dict(shader='prop', alpha='OPAQUE', tint=[0.86, 0.82, 0.72], smooth=0.2), 'Rope': dict(shader='prop', alpha='OPAQUE', tint=[0.18, 0.3, 0.16], smooth=0.3)})

def biscuit_box():
    reset()
    finish([K.box(-0.14, 0.14, -0.1, 0.1, 0.0, 0.09, 'BoxRed', 'box'), K.box(-0.145, 0.145, -0.105, 0.105, 0.09, 0.11, 'BoxRed', 'lid')], 'BiscuitBox')

def derelict_ledge():
    """a broken upper floor: a cracked slab on two broken piers, 7.5 m up (base at origin)."""
    reset()
    parts = []
    for sx in (-1, 1):
        parts.append(K.box(sx * 3.2 - 0.6, sx * 3.2 + 0.6, 2.2, 3.4, 0.0, 7.2, 'Wall', 'pier'))
    parts.append(worn_block((0, 2.8, 7.45), (8.6, 5.6, 0.5), 77, 'Floor', chips=5, wear=0.2))
    parts.append(worn_block((-3.4, 5.2, 7.2), (2.0, 1.4, 0.45), 78, 'Floor', chips=4, wear=0.3, tilt=(12, -8, 20)))
    finish(parts, 'DerelictLedge')
    EXTRA['derelict_ledge_top'] = 7.7

def flood_water():
    """a still sheet of water for the Ninth Vestibule's flood (20 x 32 m, origin at the near edge centre)."""
    B = NA.Builder()
    B.quad_strip([[(-10.0, 0.0, 0.0), (10.0, 0.0, 0.0)], [(-10.0, 32.0, 0.0), (10.0, 32.0, 0.0)]], [[(0, 0), (4, 0)], [(0, 6.4), (4, 6.4)]], 'Flood')
    uv_export(B, 'FloodWater', {'Flood': dict(shader='pool', alpha='BLEND')})

BUILDERS = {'NeonRing': neon_ring, 'Lily': water_lily, 'GrandStair': grand_stair, 'Slab': slab, 'Beehive': beehive, 'Horns': bull_horns,
            'Bundle': bundle, 'BiscuitBox': biscuit_box, 'Ledge': derelict_ledge, 'Flood': flood_water,
            'Stair': stair, 'Pole': astra_pole, 'Rosette': rosette, 'SpawnStand': spawn_stand, 'Briccola': briccola, 'Tally': tally_cards}
if __name__ == '__main__':
    names = sys.argv[1:] or list(BUILDERS)
    for nm in names:
        print('== kit3e', nm, flush=True)
        BUILDERS[nm]()
        json.dump(MAN, open(AS.MANIFEST, 'w'), indent=1); json.dump(EXTRA, open(K3.EXP, 'w'), indent=1)
    print('kit3e done')
