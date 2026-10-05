"""Procedural, tileable PBR textures for the House.
Outputs PNGs into out/Textures. All noise is spectral (FFT) so it tiles perfectly."""
import numpy as np, os
from PIL import Image
from scipy.ndimage import map_coordinates, gaussian_filter, sobel

OUT = os.path.join(os.path.dirname(__file__), '..', 'out', 'Textures')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1729)

def fbm(n, beta=2.0, seed=None, lo=1.0, hi=None):
    """Tileable fractal noise via spectral synthesis. beta = spectral falloff."""
    r = np.random.default_rng(seed) if seed is not None else rng
    kx = np.fft.fftfreq(n)[:, None] * n
    ky = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt(kx * kx + ky * ky)
    k[0, 0] = 1
    amp = k ** (-beta / 2.0 - 0.5)
    amp[k < lo] = 0
    if hi: amp[k > hi] = 0
    ph = r.uniform(0, 2 * np.pi, (n, n))
    f = np.real(np.fft.ifft2(amp * np.exp(1j * ph)))
    f -= f.min(); f /= f.max()
    return f

def warp(img, wx, wy, s):
    n = img.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    return map_coordinates(img, [yy + wy * s, xx + wx * s], order=1, mode='wrap')

def normal_from_height(h, strength):
    # wrap-aware gradient
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny, nz = -dx * strength, dy * strength, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / l, ny / l, nz / l], -1)
    return ((n * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)

def save_rgb(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, name), optimize=True)

def save_u8(a, name):
    Image.fromarray(a).save(os.path.join(OUT, name), optimize=True)

def save_mask(smooth, ao, height, sparkle, name):
    m = np.stack([smooth, ao, height, sparkle], -1)
    Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, name), optimize=True)

def lerp(a, b, t):
    return a + (b - a) * t[..., None]

# ---------------------------------------------------------------- marble
def marble_field(n, seed, vein_dirs=((3, 1), (1, -2)), warp_s=0.18, width=0.04):
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n] / n
    w1 = fbm(n, 3.6, r.integers(1e9)); w2 = fbm(n, 3.6, r.integers(1e9))
    turb = fbm(n, 3.1, r.integers(1e9)) + 0.08 * fbm(n, 1.8, r.integers(1e9))
    turb = warp(turb, w1 - .5, w2 - .5, n * warp_s)
    veins = np.zeros((n, n))
    fine = np.zeros((n, n))
    for i, (m, k) in enumerate(vein_dirs):
        ph = 2 * np.pi * (m * xx + k * yy) + 7.0 * turb + i * 1.7
        v = np.abs(np.sin(ph))
        veins = np.maximum(veins, np.exp(-v / width) * 0.85 + np.exp(-v / (width * 5)) * 0.3)
        fine = np.maximum(fine, np.exp(-v / (width * 0.35)) * (fbm(n, 1.6, r.integers(1e9)) > 0.45))
    clouds = fbm(n, 3.0, r.integers(1e9))
    grain = fbm(n, 1.0, r.integers(1e9), lo=n / 8)
    return veins, fine, clouds, grain, turb

def make_marble(name, n, base, base2, vein_col, seed, dirs, width, smooth=0.9, vein_amt=0.85):
    veins, fine, clouds, grain, turb = marble_field(n, seed, dirs, width=width)
    col = lerp(np.broadcast_to(np.array(base, float), (n, n, 3)), np.array(base2, float), clouds)
    col = lerp(col, np.array(vein_col, float), np.clip(veins * vein_amt, 0, 1))
    col = lerp(col, np.array(vein_col, float) * 0.8, np.clip(fine * 0.9, 0, 1))
    col *= (0.97 + 0.06 * grain)[..., None]
    save_rgb(col, f'{name}_Albedo.png')
    h = 0.5 + 0.02 * grain - 0.04 * veins
    save_u8(normal_from_height(h, 6.0), f'{name}_Normal.png')
    sm = smooth - 0.12 * veins - 0.06 * fbm(n, 2.5, seed + 5)
    sparkle = (fbm(n, 0.0, seed + 9, lo=n / 6) > 0.82).astype(float)
    save_mask(sm, np.ones((n, n)), veins, sparkle, f'{name}_Mask.png')
    return col, veins

print('marble...')
N = 2048
white, wveins = make_marble('MarbleWhite', N, (0.93, 0.925, 0.905), (0.86, 0.86, 0.85), (0.42, 0.43, 0.46), 11, ((2, 1), (1, -3)), 0.035)
cream, _ = make_marble('MarbleCream', N, (0.90, 0.84, 0.74), (0.83, 0.75, 0.63), (0.62, 0.52, 0.40), 23, ((1, 2), (3, -1)), 0.05, vein_amt=0.6)
verde, _ = make_marble('MarbleVerde', 1024, (0.10, 0.20, 0.16), (0.05, 0.12, 0.09), (0.80, 0.86, 0.82), 37, ((2, 3), (3, -2), (1, 4)), 0.02, smooth=0.93)
black, _ = make_marble('MarbleBlack', 1024, (0.055, 0.055, 0.06), (0.03, 0.03, 0.035), (0.85, 0.85, 0.86), 41, ((3, 2), (2, -3)), 0.018, smooth=0.95)

# ---------------------------------------------------------------- floor (4m x 4m tile: 2x2 slabs + black keystones)
print('floor...')
n = 2048; half = n // 2
big_w = np.array(Image.open(os.path.join(OUT, 'MarbleWhite_Albedo.png'))).astype(float) / 255
blk = np.array(Image.open(os.path.join(OUT, 'MarbleBlack_Albedo.png')).resize((n, n))).astype(float) / 255
verde_a = np.array(Image.open(os.path.join(OUT, 'MarbleVerde_Albedo.png')).resize((n, n))).astype(float) / 255
col = np.zeros((n, n, 3))
# each slab is a different rotated crop so repetition hides
for i, (sy, sx) in enumerate([(0, 0), (0, half), (half, 0), (half, half)]):
    crop = np.rot90(np.roll(big_w, (i * 517, i * 911), (0, 1)), i)[:half, :half]
    col[sy:sy + half, sx:sx + half] = crop
yy, xx = np.mgrid[0:n, 0:n]
# distance to nearest slab corner (corners every `half` px, wrapping)
cx = np.minimum(xx % half, half - xx % half); cy = np.minimum(yy % half, half - yy % half)
diamond = (cx + cy) < 200
diamond_border = ((cx + cy) < 214) & ~diamond
# thin verde band inset around each slab
ex = np.minimum(xx % half, half - xx % half); ey = np.minimum(yy % half, half - yy % half)
edge = np.minimum(ex, ey)
band = (edge > 40) & (edge < 52) & ~diamond & ~diamond_border
col[band] = verde_a[band]
col[diamond] = blk[diamond]
col[diamond_border] = np.array([0.75, 0.72, 0.66])
grout = edge < 3
col[grout] = col[grout] * 0.55
save_rgb(col, 'Floor_Albedo.png')
h = np.full((n, n), 0.5)
h -= 0.25 * gaussian_filter(grout.astype(float), 1.5)
h -= 0.05 * gaussian_filter((band | diamond_border).astype(float), 1.0)
h += 0.01 * fbm(n, 1.0, 77, lo=200)
save_u8(normal_from_height(h, 18.0), 'Floor_Normal.png')
smooth = np.full((n, n), 0.9) - 0.08 * fbm(n, 2.4, 78) - 0.6 * grout
smooth -= 0.1 * np.clip(gaussian_filter((fbm(n, 2.0, 79) > 0.7).astype(float), 8), 0, 1)  # scuffs
ao = 1 - 0.45 * gaussian_filter(grout.astype(float), 3)
sparkle = (fbm(n, 0.0, 80, lo=n / 6) > 0.84).astype(float)
save_mask(smooth, ao, h, sparkle, 'Floor_Mask.png')

# ---------------------------------------------------------------- ashlar wall (4.8m tile, blocks 1.6 x 0.8)
print('wall...')
n = 2048; bw, bh = n // 3, n // 6
cr = np.array(Image.open(os.path.join(OUT, 'MarbleCream_Albedo.png'))).astype(float) / 255
wh = big_w
col = np.zeros((n, n, 3)); h = np.zeros((n, n))
r = np.random.default_rng(5)
for row in range(6):
    off = (bw // 2) * (row % 2)
    for c in range(-1, 4):
        x0 = c * bw + off; y0 = row * bh
        src = cr if r.random() < 0.7 else wh
        sh = r.integers(0, n, 2)
        tint = 1 + r.normal(0, 0.03)
        for dx in range(0, bw, 256):
            pass
        xs = (np.arange(x0, x0 + bw)) % n
        block = np.roll(src, (int(sh[0]), int(sh[1])), (0, 1))[y0:y0 + bh][:, xs] * tint
        col[y0:y0 + bh][:, xs] = block
        # bevel height: distance to block edge
        yy_, xx_ = np.mgrid[0:bh, 0:bw]
        d = np.minimum(np.minimum(xx_, bw - 1 - xx_), np.minimum(yy_, bh - 1 - yy_)).astype(float)
        hb = np.clip(d / 14.0, 0, 1)
        h[y0:y0 + bh][:, xs] = hb
col *= (0.6 + 0.4 * h)[..., None] ** 0.5
grime = gaussian_filter(fbm(n, 2.2, 90), 2)
col *= (0.92 + 0.08 * grime)[..., None]
save_rgb(col, 'Wall_Albedo.png')
hh = h * 0.6 + 0.03 * fbm(n, 1.5, 91, lo=100)
save_u8(normal_from_height(hh, 10.0), 'Wall_Normal.png')
save_mask(0.55 + 0.25 * h - 0.1 * grime, 0.6 + 0.4 * h, hh, (fbm(n, 0.0, 92, lo=n / 6) > 0.86).astype(float), 'Wall_Mask.png')

# ---------------------------------------------------------------- sand (4m tile)
print('sand...')
n = 1024
yy, xx = np.mgrid[0:n, 0:n] / n
wv = fbm(n, 2.8, 100)
ph = 2 * np.pi * (7 * xx + 2 * yy) + 7 * wv
rip = np.sin(ph); rip = np.sign(rip) * np.abs(rip) ** 0.6
rip2 = np.sin(2 * np.pi * (19 * xx - 5 * yy) + 10 * fbm(n, 2.5, 101)) * 0.25
grain = fbm(n, 0.2, 102, lo=n / 5)
height = 0.5 + 0.18 * rip + 0.05 * rip2 + 0.04 * grain
base = np.array([0.80, 0.70, 0.55])
col = np.broadcast_to(base, (n, n, 3)) * (0.9 + 0.15 * fbm(n, 2.5, 103))[..., None]
col *= (0.92 + 0.12 * height)[..., None]
speck = fbm(n, 0.0, 104, lo=n / 4)
col = lerp(col, np.array([0.35, 0.30, 0.26]), (speck > 0.80).astype(float) * 0.6)
col = lerp(col, np.array([0.97, 0.95, 0.92]), (speck < 0.12).astype(float) * 0.6)
save_rgb(col, 'Sand_Albedo.png')
save_u8(normal_from_height(height, 10.0), 'Sand_Normal.png')
save_mask(0.15 + 0.1 * grain, 0.85 + 0.15 * height, height, (fbm(n, 0.0, 105, lo=n / 3) > 0.86).astype(float), 'Sand_Mask.png')

# ---------------------------------------------------------------- water normals
print('water...')
for i, beta in enumerate([3.2, 2.6]):
    h = fbm(1024, beta, 200 + i, lo=2)
    save_u8(normal_from_height(h, 120.0 if i == 0 else 60.0), f'Water_Normal{i}.png')

# ---------------------------------------------------------------- noise (RGBA)
print('noise...')
n = 512
a = fbm(n, 2.8, 300); b = fbm(n, 2.0, 301); c = rng.random((n, n)); d = fbm(n, 3.4, 302)
Image.fromarray((np.stack([a, b, c, d], -1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'Noise.png'))

# ---------------------------------------------------------------- particle atlas 2x2 (sparkle, petal, leaf, snowflake)
print('particles...')
S = 256
atlas = np.zeros((S * 2, S * 2, 4))
yy, xx = (np.mgrid[0:S, 0:S] + 0.5) / S * 2 - 1
rr = np.sqrt(xx ** 2 + yy ** 2); th = np.arctan2(yy, xx)
# sparkle: glow + 4 rays
glow = np.exp(-rr ** 2 * 18) + 0.35 * np.exp(-rr * 6)
rays = (np.exp(-np.abs(xx) * 60) + np.exp(-np.abs(yy) * 60)) * np.exp(-rr * 2.5)
sp = np.clip(glow + rays * 0.8, 0, 1)
atlas[S:, :S] = np.stack([sp, sp, sp, sp], -1)  # top-left in UV terms (row S.. is bottom in image -> we flip later)
# petal
px, py = xx * 1.0, yy * 1.6
pet = (px ** 2 + (py + 0.25 * px ** 2) ** 2) < 0.55
pet_a = gaussian_filter(pet.astype(float), 2)
pc = np.stack([np.ones_like(rr), 0.82 + 0.1 * yy, 0.88 + 0.08 * yy], -1)
atlas[S:, S:, :3] = pc; atlas[S:, S:, 3] = pet_a
# leaf
lx, ly = xx, yy * 0.75
leaf = (np.abs(lx) < 0.75 * np.cos(ly * 1.7) * (1 - 0.15 * np.abs(np.sin(ly * 14)))) & (np.abs(ly) < 0.92)
vein = np.exp(-np.abs(lx) * 40) + 0.5 * np.exp(-np.abs(np.abs(lx) - (np.abs(ly) * 0.0 + (ly % 0.25))) * 30)
la = gaussian_filter(leaf.astype(float), 1.5)
lc = np.stack([np.full_like(rr, 0.95), 0.55 + 0.25 * yy, np.full_like(rr, 0.2)], -1) * (1 - 0.3 * np.clip(vein, 0, 1))[..., None]
atlas[:S, :S, :3] = lc; atlas[:S, :S, 3] = la
# snowflake: 6-fold dendrite
ang = np.mod(th, np.pi / 3) - np.pi / 6
ax = rr * np.cos(ang); ay = np.abs(rr * np.sin(ang))
arm = (ay < 0.035) & (rr < 0.85)
for t in [0.3, 0.5, 0.68]:
    bx = ax - t; arm |= (np.abs(ay - bx * 0.6) < 0.03) & (bx > 0) & (bx < 0.22 * (1 - t))
sf = gaussian_filter(arm.astype(float), 1.2) + 0.5 * np.exp(-rr ** 2 * 30)
sf = np.clip(sf * 1.4, 0, 1)
atlas[:S, S:] = np.stack([sf, sf, sf, sf], -1)
# image row 0 is top; Unity UV v=0 is bottom. Layout chosen in shader: index0=sparkle(top-left) etc.
img = np.flipud(atlas)
Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'ParticleAtlas.png'))
print('done')
