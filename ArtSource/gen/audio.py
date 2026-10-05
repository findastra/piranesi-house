"""Synthesized sound set for the House (placeholder-quality but tuned): footsteps on marble,
sand and shallow water, seamless ocean / wind / house-drone loops."""
import numpy as np, os, wave
from scipy.signal import butter, sosfilt, sosfiltfilt

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), '..', 'out', 'Audio')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)
def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)

def write(name, x, stereo=None):
    x = np.asarray(x, float)
    peak = np.max(np.abs(x)) + 1e-9
    x = x / peak * 0.89
    if stereo is not None:
        s = np.asarray(stereo, float) / peak * 0.89
        data = np.stack([x, s], -1)
        ch = 2
    else:
        data = x[:, None]; ch = 1
    pcm = (np.clip(data, -1, 1) * 32767).astype('<i2')
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / attack, 1) * np.exp(-t / decay)

def t_(dur):
    return np.arange(int(dur * SR)) / SR

# ------------------------------------------------ marble footsteps: heel click + toe tap, stone resonance
def marble_step(seed):
    r = np.random.default_rng(seed)
    dur = 0.35; n = int(dur * SR); t = t_(dur)
    out = np.zeros(n)
    for k, (delay, gain) in enumerate([(0.0, 1.0), (r.uniform(0.045, 0.075), r.uniform(0.35, 0.55))]):
        d = int(delay * SR)
        m = n - d
        click = r.normal(0, 1, m) * env(m, 0.0004, 0.004 + 0.002 * r.random())
        click = hp(click, 1200) + 0.6 * bp(click, 2500 + 800 * r.random(), 6000)
        thud = np.sin(2 * np.pi * (85 + 30 * r.random()) * t[:m]) * env(m, 0.001, 0.018)
        ring = np.zeros(m)
        for f in r.uniform(1800, 4200, 3):
            ring += np.sin(2 * np.pi * f * t[:m] + r.uniform(0, 6)) * env(m, 0.0005, 0.012 + 0.01 * r.random()) * 0.12
        out[d:] += gain * (click * 0.9 + thud * 0.55 + ring)
    # tiny grit scrape
    grit = hp(r.normal(0, 1, n), 3000) * env(n, 0.02, 0.03) * 0.04
    return out + grit

for i in range(6):
    write(f'Step_Marble_{i}.wav', marble_step(100 + i))

# ------------------------------------------------ sand footsteps: granular crunch
def sand_step(seed):
    r = np.random.default_rng(seed)
    dur = 0.45; n = int(dur * SR)
    out = np.zeros(n)
    centre = 0.09
    grains = r.integers(250, 420)
    for _ in range(grains):
        pos = int(abs(r.normal(centre, 0.05)) * SR)
        if pos >= n - 400: continue
        L = r.integers(60, 300)
        g = r.normal(0, 1, L) * np.exp(-np.arange(L) / (L / 4)) * r.uniform(0.2, 1)
        out[pos:pos + L] += g
    out = bp(out, 400, 7000) + 0.3 * lp(out, 900)
    out *= env(n, 0.03, 0.12)
    thump = lp(r.normal(0, 1, n), 180) * env(n, 0.01, 0.05) * 3
    return out + thump

for i in range(5):
    write(f'Step_Sand_{i}.wav', sand_step(200 + i))

# ------------------------------------------------ shallow water steps: splash + bubbles
def water_step(seed):
    r = np.random.default_rng(seed)
    dur = 0.7; n = int(dur * SR); t = t_(dur)
    splash = bp(r.normal(0, 1, n), 500, 6000) * env(n, 0.008, 0.09)
    slosh = lp(r.normal(0, 1, n), 700) * env(n, 0.05, 0.22) * 1.5
    bub = np.zeros(n)
    for _ in range(r.integers(6, 14)):
        st = int(r.uniform(0.02, 0.4) * SR); L = int(r.uniform(0.015, 0.05) * SR)
        if st + L >= n: continue
        f0 = r.uniform(500, 1600)
        tt = np.arange(L) / SR
        bub[st:st + L] += np.sin(2 * np.pi * f0 * tt * (1 + 6 * tt)) * np.exp(-tt / (L / SR / 3)) * r.uniform(0.1, 0.4)
    return splash + slosh + bub

for i in range(5):
    write(f'Step_Water_{i}.wav', water_step(300 + i))

# ------------------------------------------------ helpers for seamless loops: crossfade tail into head
def make_loop(x, fade_s=3.0):
    f = int(fade_s * SR)
    head, body, tail = x[:f], x[f:-f], x[-f:]
    w = np.sin(np.linspace(0, np.pi / 2, f)) ** 2
    blended = tail * (1 - w) + head * w
    return np.concatenate([body, blended])

def pink(n, r):
    w = r.normal(0, 1, n)
    X = np.fft.rfft(w); f = np.fft.rfftfreq(n); f[0] = f[1]
    return np.fft.irfft(X / np.sqrt(f), n)

# ------------------------------------------------ ocean: breaking waves with long swell cycle
def ocean(dur, seed, distant=False):
    r = np.random.default_rng(seed)
    n = int((dur + 3) * SR); t = np.arange(n) / SR
    base = pink(n, r); base /= np.std(base)
    out = lp(base, 600) * 0.25
    tt = 0.0
    while tt < dur + 3:
        period = r.uniform(7, 12)
        crash_t = tt + r.uniform(0.5, 2.0)
        i0 = int(crash_t * SR)
        L = int(r.uniform(4, 7) * SR)
        if i0 + L > n: L = n - i0
        if L <= 0: break
        e = np.arange(L) / SR
        envl = np.minimum(e / 0.6, 1) ** 2 * np.exp(-e / r.uniform(1.2, 2.2))
        burst = r.normal(0, 1, L)
        cut = 2500 if not distant else 900
        b = bp(burst, 150, cut) * envl
        # backwash hiss
        bw = hp(r.normal(0, 1, L), 2000) * np.exp(-((e - 2.5) ** 2) / 1.5) * 0.25 * (0 if distant else 1)
        out[i0:i0 + L] += b * r.uniform(0.6, 1.0) + bw
        # swell rumble
        out[i0:i0 + L] += lp(r.normal(0, 1, L), 120) * envl * 1.2
        tt += period
    return make_loop(out, 3.0)

write('Ocean_Near_Loop.wav', ocean(60, 400))
write('Ocean_Far_Loop.wav', ocean(60, 401, distant=True))

# ------------------------------------------------ wind through colonnades: moving band-pass + whistle
def wind(dur, seed):
    r = np.random.default_rng(seed)
    n = int((dur + 3) * SR); t = np.arange(n) / SR
    src = pink(n, r); src /= np.std(src)
    gust = 0.5 + 0.5 * np.sin(2 * np.pi * t / 11 + 1) * np.sin(2 * np.pi * t / 4.7)
    gust = np.clip(gust, 0.1, 1)
    out = np.zeros(n)
    blk = 2048
    for s in range(0, n, blk):
        seg = slice(s, min(n, s + blk))
    # cheap: sum of bands each amplitude-modulated differently
    for fc, ph in [(250, 0), (450, 1.3), (800, 2.1), (1300, 3.7)]:
        band = bp(src, fc * 0.8, fc * 1.25)
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * t / r.uniform(5, 13) + ph)
        out += band * mod
    whistle = np.sin(2 * np.pi * (620 + 40 * np.sin(2 * np.pi * t / 7)) * t) * 0.03 * gust ** 3
    return make_loop(out * gust + whistle, 3.0)

write('Wind_Loop.wav', wind(45, 500))

# ------------------------------------------------ house drone: distant choir-like harmonic pad (stereo)
def drone(dur, seed):
    r = np.random.default_rng(seed)
    n = int((dur + 4) * SR); t = np.arange(n) / SR
    L = np.zeros(n); R = np.zeros(n)
    root = 55.0
    for ratio, amp in [(1, 1), (1.5, 0.6), (2, 0.5), (3, 0.3), (4, 0.18), (5, 0.12), (6, 0.08), (2.5, 0.2)]:
        for det, side in [(-0.12, 0), (0.15, 1)]:
            f = root * ratio + det
            lfo = 0.6 + 0.4 * np.sin(2 * np.pi * t / r.uniform(9, 23) + r.uniform(0, 6))
            s = np.sin(2 * np.pi * f * t + r.uniform(0, 6)) * amp * lfo
            (L if side == 0 else R)[:] += s
    air = lp(r.normal(0, 1, n), 2000) * 0.02
    return make_loop(L + air, 4.0), make_loop(R + air[::-1], 4.0)

dl, dr = drone(50, 600)
write('House_Drone_Loop.wav', dl, dr)

# ------------------------------------------------ season stingers: soft glass shimmer when seasons turn
def shimmer(seed):
    r = np.random.default_rng(seed)
    dur = 6; n = dur * SR; t = np.arange(n) / SR
    out = np.zeros(n)
    notes = [523.25, 659.25, 783.99, 987.77, 1174.66, 1318.5]
    for k in range(24):
        st = int(r.uniform(0, 3.5) * SR)
        f = r.choice(notes) * r.choice([1, 2])
        m = n - st; tt = np.arange(m) / SR
        out[st:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / r.uniform(0.6, 1.8)) * r.uniform(0.05, 0.2) * np.minimum(tt / 0.005, 1)
    return out

write('Season_Shimmer.wav', shimmer(700))
def cascade(dur, seed):
    r = np.random.default_rng(seed)
    n = int((dur + 3) * SR); t = np.arange(n) / SR
    src = pink(n, r); src /= np.std(src)
    body = bp(src, 200, 5000) * (0.85 + 0.15 * np.sin(2 * np.pi * t * 0.31))
    rumble = lp(r.normal(0, 1, n), 150) * 0.8
    splash = hp(r.normal(0, 1, n), 3000) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * t * 1.7))) * 0.3
    return make_loop(body + rumble + splash, 3.0)

write('Cascade_Loop.wav', cascade(30, 800))
print('audio done', sorted(os.listdir(OUT)))
