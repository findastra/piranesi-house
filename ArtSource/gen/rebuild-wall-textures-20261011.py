"""Rebuild the existing pale ashlar textures without truncated edge courses.

Requires numpy and Pillow. Coordinates are metric-periodic: three blocks across,
six courses high, alternate courses offset half a block in a 4.8 metre tile.
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image


def bond_fields(n):
    yy, xx = np.mgrid[0:n, 0:n]
    y = (yy + .5) * 6 / n
    row = np.floor(y).astype(int)
    x = (xx + .5) * 3 / n - .5 * (row % 2)
    column = np.floor(x).astype(int) % 3
    fx, fy = x % 1, y % 1
    distance = np.minimum(np.minimum(fx, 1-fx) * n/3,
                          np.minimum(fy, 1-fy) * n/6)
    return row, column, np.clip(distance / (14*n/2048), 0, 1)


def noise(n, beta, seed, low=1):
    freq = np.fft.fftfreq(n) * n
    k = np.hypot(freq[:, None], freq[None, :])
    amplitude = np.maximum(k, 1) ** (-beta/2-.5)
    amplitude[k < low] = 0
    phase = np.random.default_rng(seed).uniform(0, 2*np.pi, (n, n))
    value = np.fft.ifft2(amplitude * np.exp(1j*phase)).real
    return (value-value.min()) / max(float(np.ptp(value)), 1e-12)


def make_wall(folder, n=2048):
    folder = Path(folder)
    sources = [np.asarray(Image.open(folder / f'Marble{k}_Albedo.png')
               .convert('RGB').resize((n, n)), dtype=float)/255
               for k in ('Cream', 'White')]
    rows, columns, bevel = bond_fields(n)
    colour = np.full((n, n, 3), np.nan)
    r = np.random.default_rng(5)
    for row in range(6):
        for column in range(3):
            src = sources[0 if r.random() < .7 else 1]
            shift = r.integers(0, n, 2)
            tint = 1 + r.normal(0, .03)
            select = (rows == row) & (columns == column)
            colour[select] = np.roll(src, tuple(shift), (0, 1))[select] * tint
    assert np.isfinite(colour).all(), 'Every pixel must belong to exactly one block'
    colour *= (.6 + .4*bevel)[..., None] ** .5
    grime = noise(n, 2.2, 90)
    # Periodic Gaussian smoothing in frequency space; no boundary padding seam.
    freq = np.fft.fftfreq(n)
    blur = np.exp(-2*np.pi**2*2**2*(freq[:, None]**2+freq[None, :]**2))
    grime = np.fft.ifft2(np.fft.fft2(grime)*blur).real
    colour *= (.92+.08*grime)[..., None]
    height = bevel*.6 + .03*noise(n, 1.5, 91, low=max(1, n*100/2048))
    dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))*.5
    dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))*.5
    # PNG rows run down; Unity texture V runs up, so its tangent Y is +dy.
    normal = np.stack([-dx*10, dy*10, np.ones_like(height)], -1)
    normal /= np.linalg.norm(normal, axis=-1)[..., None]
    mask = np.stack([.55+.25*bevel-.1*grime, .6+.4*bevel, height,
                     (noise(n, 0, 92, low=n/6)>.86).astype(float)], -1)
    for suffix, value in [('Albedo', colour), ('Normal', normal*.5+.5), ('Mask', mask)]:
        encoded = (np.clip(value, 0, 1)*255).astype(np.uint8)
        Image.fromarray(encoded).save(folder / f'Wall_{suffix}.png', optimize=True)
    return {'resolution': n, 'blocks': 18, 'unpainted_pixels': int(np.isnan(colour).sum())}


def check_bond():
    for n in (63, 64, 127, 2048):
        row, col, bevel = bond_fields(n)
        assert row.min() == 0 and row.max() == 5
        assert col.min() == 0 and col.max() == 2
        assert np.isfinite(bevel).all()
        # The wrap crosses one mortar joint; neither edge can expose a full block.
        joint_sample = (.5 * 2048 / n) / 14
        assert np.max(bevel[0]) <= min(1, joint_sample) + 1e-10
        assert np.max(bevel[-1]) <= min(1, joint_sample) + 1e-10
        for course in range(6):
            for block in range(3):
                assert np.any((row == course) & (col == block))
    print('PASS: complete periodic courses at four resolutions, including 2048')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--textures', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check_bond()
    if args.textures:
        print(make_wall(args.textures))
    if not args.check and not args.textures:
        parser.error('supply --textures and/or --check')
