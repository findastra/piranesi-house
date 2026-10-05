"""Tileable caustics: refract a grid of light rays through a wavy water surface, splat landing density."""
import numpy as np, os
from PIL import Image
from scipy.ndimage import gaussian_filter
OUT = os.path.join(os.path.dirname(__file__), '..', 'out', 'Textures')
def fbm(n, beta, seed, lo=2, hi=None):
    r = np.random.default_rng(seed)
    kx = np.fft.fftfreq(n)[:, None] * n; ky = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt(kx**2 + ky**2); k[0, 0] = 1
    a = k ** (-beta / 2 - .5); a[k < lo] = 0
    if hi: a[k > hi] = 0
    f = np.real(np.fft.ifft2(a * np.exp(1j * r.uniform(0, 2*np.pi, (n, n)))))
    return (f - f.min()) / (f.max() - f.min())
N = 512; S = 4  # supersample rays
h = fbm(N, 3.0, 11, lo=3, hi=40)
gy, gx = np.gradient(h)
up = lambda a: np.kron(a, np.ones((S, S)))
GX, GY = up(gx), up(gy)
yy, xx = np.mgrid[0:N*S, 0:N*S] / S
k = 900.0
px = (xx + GX * k) % N; py = (yy + GY * k) % N
img = np.zeros((N, N))
np.add.at(img, (py.astype(int) % N, px.astype(int) % N), 1.0)
img = gaussian_filter(img, 0.8, mode='wrap')
img = img / np.percentile(img, 99.7); img = np.clip(img, 0, 1) ** 1.4
Image.fromarray((img * 255).astype(np.uint8)).save(os.path.join(OUT, 'Caustics.png'))
print('caustics', img.mean())
