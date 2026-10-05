"""Pure-numpy copies of the island and seabed height fields used by kit2.py, so the layout can put things on the
ground (and under the water) without Blender."""
import numpy as np

ISLANDS = [  # name, centre (x, z), radii, crest height, interior height, seed
    ('Isle_SouthBeach', (0.0, -128.0), (58.0, 22.0), 1.4, 2.6, 1),
    ('Isle_Ruin', (142.0, 12.0), (36.0, 30.0), 1.2, 2.2, 2),
    ('Isle_Albatross', (-152.0, 150.0), (16.0, 13.0), 1.0, 4.5, 3),
    ('Isle_Pump', (60.0, 118.0), (18.0, 12.0), 0.8, 1.6, 4),
]
INDEX = {n[0]: i for i, n in enumerate(ISLANDS)}

def island_height(x, z, ix):
    name, (cx, cz), (rx, rz), crest, inner, seed = ISLANDS[ix]
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6, 4)
    ang = np.arctan2(z - cz, x - cx)
    wob = 1 + 0.12 * np.sin(ang * 3 + ph[0]) + 0.07 * np.sin(ang * 5 + ph[1])
    d = np.sqrt(((x - cx) / (rx * wob)) ** 2 + ((z - cz) / (rz * wob)) ** 2)
    h = np.where(d < 1, crest + (inner - crest) * np.clip(1 - d, 0, 1) ** 0.7 * np.clip((1 - d) * 3, 0, 1), crest - (d - 1) * 9)
    h = h + 0.08 * np.sin(x * 0.7 + ph[2]) * np.sin(z * 0.6 + ph[3]) * (d < 1)
    return np.maximum(h, -4.0), d

def seabed_height(x, z):
    dh = np.maximum(np.abs(x), np.abs(z)) - 72
    d = np.maximum(dh, 0)
    for ix, isl in enumerate(ISLANDS):
        _, (cx, cz), (rx, rz), *_ = isl
        di = np.sqrt(((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2) - 1
        d = np.minimum(d, np.maximum(di, 0) * min(rx, rz))
    shelf = -1.6 - 2.2 * np.clip(d / 30, 0, 1) - 10 * np.clip((d - 35) / 120, 0, 1) ** 1.4
    ripple = 0.25 * np.sin(x * 0.21 + np.sin(z * 0.05) * 3) * np.sin(z * 0.17)
    return shelf + ripple

def ground(x, z):
    """Highest solid surface at (x, z): island sand or seabed (the House footprint is not handled here)."""
    h = seabed_height(np.asarray(x, float), np.asarray(z, float))
    for ix in range(len(ISLANDS)):
        hi, d = island_height(np.asarray(x, float), np.asarray(z, float), ix)
        h = np.maximum(h, np.where(d < 1.45, hi, -99))
    return float(h) if np.ndim(h) == 0 else h

def island_d(x, z, name):
    return float(island_height(np.asarray(x, float), np.asarray(z, float), INDEX[name])[1])
