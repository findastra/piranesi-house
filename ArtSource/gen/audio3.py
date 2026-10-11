"""v3 sounds for the Stormscape and the End Show: rain, thunder, the dead-end chime, the meteor whoosh and the warp."""
import numpy as np
import audio as A
from audio import SR, bp, lp, hp, write, env, t_, make_loop, pink
rng = np.random.default_rng(31)

def rain(dur=24.0):
    n = int(dur * SR)
    hiss = hp(rng.normal(0, 1, n), 2500) * 0.35 + bp(rng.normal(0, 1, n), 700, 5000) * 0.5
    drops = np.zeros(n)
    for k in range(int(dur * 260)):
        i = rng.integers(0, n - 2000); a = rng.uniform(0.2, 1.0)
        f = rng.uniform(2500, 7000); m = int(SR * 0.012)
        drops[i:i + m] += a * np.sin(2 * np.pi * f * np.arange(m) / SR) * np.exp(-np.arange(m) / (SR * 0.003))
    body = lp(pink(n, rng), 900) * 0.6
    x = hiss + drops * 0.25 + body
    return make_loop(x, 3.0)

def thunder(seed):
    r = np.random.default_rng(seed)
    dur = r.uniform(5.5, 8.0); n = int(dur * SR); t = np.arange(n) / SR
    crack = hp(r.normal(0, 1, n), 1200) * np.exp(-t / 0.08) * (t < 0.6)
    rumble = lp(pink(n, r), 160, 4) * 3.0
    envr = np.minimum(t / 0.25, 1) * np.exp(-t / r.uniform(1.6, 2.6))
    for k in range(5):                                     # rolling swells
        c = r.uniform(0.4, dur * 0.6); envr += 0.5 * np.exp(-((t - c) / r.uniform(0.25, 0.7)) ** 2) * np.exp(-t / 3.0)
    return crack * 0.5 + rumble * envr

def chime():
    t = t_(3.2); x = np.zeros_like(t)
    for k, (f, d) in enumerate(((1318.5, 0.0), (1760.0, 0.11), (2093.0, 0.22), (2637.0, 0.36))):
        tt = np.clip(t - d, 0, None)
        x += (t >= d) * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt / 0.9) * 0.4
    return x

def whoosh():
    t = t_(2.2); n = len(t)
    noise = rng.normal(0, 1, n)
    sweep = np.zeros(n); f0 = 400.0
    out = np.zeros(n)
    for k in range(0, n, 2048):                            # band sweeping down as the meteor passes
        seg = noise[k:k + 2048]
        fc = 4000 * np.exp(-k / n * 2.4) + 200
        out[k:k + len(seg)] = bp(seg, fc * 0.6, min(fc * 1.6, 16000))
    return out * np.sin(np.pi * t / t[-1]) ** 2

def warp(dur=12.0):
    t = t_(dur); n = len(t)
    roar = lp(pink(n, rng), 600, 2) * 2.0 + bp(rng.normal(0, 1, n), 1500, 6000) * 0.25
    rise = np.zeros(n)
    for f in (55.0, 82.5, 110.0, 165.0, 220.0):
        ph = 2 * np.pi * np.cumsum(f * (1 + 2.5 * (t / dur) ** 2)) / SR
        rise += np.sin(ph) * 0.18
    e = np.minimum(t / 1.5, 1) * np.minimum((dur - t) / 0.6, 1)
    return (roar + rise) * e

if __name__ == '__main__':
    write('Rain_Loop.wav', rain())
    for k in range(3): write(f'Thunder_{k}.wav', thunder(70 + k))
    write('Chime_Found.wav', chime())
    write('Meteor_Whoosh.wav', whoosh())
    write('Warp_Rush.wav', warp())
    print('audio3 done')
