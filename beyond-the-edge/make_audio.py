"""Procedural soundtrack for Beyond the Edge (15 s, 48 kHz stereo).

Engine (flat-six firing order harmonics), gear shifts, exhaust crackle, tyre
screech, impact, guardrail scrape, wind, and a D-minor orchestral cue that
builds, cuts out for the slow-motion crash, and returns as an epic swell.
All events are synced to the same frame->time speed ramps as build_scene.py.

Usage: python3 make_audio.py out.wav
"""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 15.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(11)
FPS = 24


def speed_factor(f):
    if f <= 214: return 1.0
    if f <= 222: return 1.0 - 0.72 * (f - 214) / 8
    if f <= 288: return 0.28
    return 0.28 + (1.25 - 0.28) * min(1, (f - 288) / 50.0)


frames = 1 + t * FPS
SPEED = np.interp(frames, np.arange(1, 362), [speed_factor(f) for f in range(1, 362)])
T_IMPACT = (239 - 1) / FPS
T_EDGE = (258 - 1) / FPS
T_SLOW = (214 - 1) / FPS


def env_pts(pts):
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys)


def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR / 2 - 100) / (SR / 2), 'low')
    return signal.lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high')
    return signal.lfilter(b, a, x)


def bp(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), f2 / (SR / 2)], 'band')
    return signal.lfilter(b, a, x)


def tv_lp(x, fc_curve):
    """time-varying one-pole lowpass (cutoff per sample), processed in blocks"""
    out = np.zeros_like(x); y = 0.0; B = 256
    for i in range(0, len(x), B):
        fc = float(fc_curve[i]); a = np.exp(-2 * np.pi * fc / SR)
        zi = [y * a]
        seg, _ = signal.lfilter([1 - a], [1, -a], x[i:i + B], zi=zi)
        out[i:i + B] = seg; y = seg[-1]
    return out


# ------------------------------------------------------------------ engine
rpm = env_pts([
    (0.0, 6200), (1.70, 7600), (1.76, 5700), (3.0, 6800),
    (3.0, 6900), (4.30, 8200), (4.36, 6100), (4.48, 8700), (4.62, 7300), (6.0, 8000),
    (6.0, 7000), (7.40, 9000), (7.46, 7100), (8.85, 8900),
    (9.6, 9100), (T_IMPACT, 9300), (T_IMPACT + 0.4, 9500), (11.0, 9600), (12.0, 7000), (15.0, 5000)])
pitch = SPEED.copy()
f0 = rpm / 60.0 * 3.0 * pitch
ph = 2 * np.pi * np.cumsum(f0) / SR
orders = [(0.5, 0.55), (1, 1.0), (1.5, 0.45), (2, 0.6), (3, 0.38), (4, 0.25), (5, 0.16), (6, 0.12), (8, 0.06), (10, 0.04)]
eng = sum(a * np.sin(k * ph + 0.7 * k) for k, a in orders)
rough = lp(rng.normal(0, 1, N), 90)
eng *= 1 + 0.9 * rough / np.std(rough) * 0.25
eng = np.tanh(1.8 * eng / np.std(eng))
intake = bp(rng.normal(0, 1, N), 900, 3800) * 0.08
eng = eng + intake * (rpm / 9000) ** 2
# shift dips
for ts in (1.70, 4.30, 7.40):
    eng *= 1 - 0.75 * np.exp(-((t - ts - 0.03) / 0.035) ** 2)
eng_amp = env_pts([(0, 0.32), (2.98, 0.36), (3.0, 1.0), (5.98, 1.0), (6.0, 0.85), (8.9, 0.95),
                   (9.3, 0.55), (T_IMPACT, 0.6), (T_IMPACT + 0.3, 0.35), (11.95, 0.2), (12.0, 0.08), (15, 0.02)])
eng_fc = env_pts([(0, 2600), (2.98, 2600), (3.0, 9000), (5.98, 9000), (6.0, 7000), (8.9, 7000), (9.3, 1300),
                  (11.95, 1100), (12.0, 900), (15, 600)])
engine = tv_lp(eng, eng_fc) * eng_amp

# exhaust crackle on the downshift + lift
crk = np.zeros(N)
for tc in list(rng.uniform(4.36, 4.95, 14)) + list(rng.uniform(1.72, 1.95, 5)) + list(rng.uniform(7.42, 7.6, 5)):
    i = int(tc * SR); L = int(rng.uniform(0.002, 0.006) * SR)
    crk[i:i + L] += rng.normal(0, 1, L) * np.hanning(L) * rng.uniform(0.5, 1.4)
crk = bp(crk, 300, 5000) * env_pts([(0, 0.25), (3, 0.25), (3.01, 1.0), (6, 1.0), (6.01, 0.7), (15, 0.7)]) * 1.6

# ------------------------------------------------------------------ crash sound design
noise = rng.normal(0, 1, N)
screech_on = np.clip((t - 8.93) / 0.15, 0, 1) * np.clip((T_EDGE + 0.2 - t) / 0.3, 0, 1)
sc_f = 1900 * SPEED * (1 + 0.06 * np.sin(2 * np.pi * 7 * t))
scr_ph = 2 * np.pi * np.cumsum(sc_f) / SR
screech = (np.sin(scr_ph) * 0.5 + bp(noise, 700, 2600) * 0.6) * screech_on * 0.35
screech = lp(screech, 3000)

def at(t0):
    return np.clip(t - t0, 0, None)

ti = at(T_IMPACT)
boom = np.sin(2 * np.pi * (34 + 30 * np.exp(-ti * 3)) * ti) * np.exp(-ti / 1.1) * (t >= T_IMPACT)
crunch = lp(noise, 700) * np.exp(-ti / 0.55) * (t >= T_IMPACT) * 1.4
clang = sum(np.sin(2 * np.pi * fq * 0.42 * ti + k) * np.exp(-ti / (0.9 - 0.12 * k))
            for k, fq in enumerate([233, 351, 517, 788, 1131, 1490])) * (t >= T_IMPACT) * 0.16
scrape = bp(noise, 500, 1800) * np.clip((t - T_IMPACT) / 0.05, 0, 1) * np.clip((T_EDGE - t) / 0.2, 0, 1) * 0.25
rattle = np.zeros(N)
for tc in rng.uniform(T_IMPACT, T_IMPACT + 1.6, 60):
    i = int(tc * SR); L = int(0.012 * SR)
    rattle[i:i + L] += rng.normal(0, 1, L) * np.exp(-np.arange(L) / (0.003 * SR)) * rng.uniform(0.2, 1)
rattle = bp(rattle, 400, 2500) * 0.5
whoosh_f = 220 * np.exp(-at(T_SLOW) * 1.6) + 38
sub_drop = np.sin(2 * np.pi * np.cumsum(whoosh_f) / SR) * np.exp(-at(T_SLOW) / 1.6) * (t >= T_SLOW) * 0.55
crash = boom * 0.9 + crunch + clang + scrape + rattle + screech + sub_drop

# ------------------------------------------------------------------ wind (stereo)
def wind_ch(seed):
    n = np.random.default_rng(seed).normal(0, 1, N)
    gust = 1 + 0.4 * lp(np.random.default_rng(seed + 1).normal(0, 1, N), 0.8) / 0.05
    return n, np.clip(gust, 0.3, 2.0)
wind_amp = env_pts([(0, 0.13), (3, 0.13), (3.01, 0.05), (6, 0.05), (6.01, 0.09), (8.9, 0.12), (9.3, 0.06),
                    (11.95, 0.08), (12.0, 0.25), (13.5, 0.42), (14.4, 0.3), (15, 0.15)])
wind_fc = env_pts([(0, 700), (8.9, 900), (9.3, 350), (12, 500), (13.5, 1600), (15, 900)])
wL, gL = wind_ch(101); wR, gR = wind_ch(202)
windL = tv_lp(tv_lp(wL, wind_fc), wind_fc) * gL * wind_amp * 1.2
windR = tv_lp(tv_lp(wR, wind_fc), wind_fc) * gR * wind_amp * 1.2

# ------------------------------------------------------------------ orchestra
music = np.zeros((2, N))

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)

NOTES = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
def nm(s):
    name, octv = s[:-1], int(s[-1])
    return mtof(12 * (octv + 1) + NOTES[name.replace("Bb", "A#")])

def adsr(L, a, r, sustain=1.0):
    e = np.ones(L) * sustain
    na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na) ** 1.5 * (np.linspace(1, sustain, na) if sustain != 1 else 1)
    if nr < L: e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e

def saw(freq, L, nh=24, roll=1.0, vib=0.0, phase=0.0):
    tt = np.arange(L) / SR
    fm = freq * (1 + vib * np.sin(2 * np.pi * 5.2 * tt + phase))
    ph = 2 * np.pi * np.cumsum(fm) / SR + phase
    out = np.zeros(L)
    for k in range(1, nh + 1):
        if k * freq > SR / 2 - 2000: break
        out += np.sin(k * ph) / k ** roll
    return out

def add(t0, dur, sig, pan=0.0, amp=1.0):
    i0 = int(t0 * SR); L = min(len(sig), N - i0)
    if L <= 0: return
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    music[0, i0:i0 + L] += sig[:L] * amp * gl
    music[1, i0:i0 + L] += sig[:L] * amp * gr

def strings(t0, dur, note, amp=0.1, att=0.5, rel=0.8, pan=0.0):
    L = int((dur + rel) * SR); f = nm(note); s = np.zeros(L)
    for v, det in enumerate([-0.006, -0.002, 0.003, 0.007]):
        s += saw(f * (1 + det), L, nh=18, roll=1.35, vib=0.004, phase=v * 1.3)
    s = lp(s, 3500) * adsr(L, att, rel)
    add(t0, dur, s, pan, amp)

def stacc(t0, note, amp=0.08, pan=0.0):
    L = int(0.22 * SR); f = nm(note)
    s = (saw(f, L, 14, 1.2) + saw(f * 1.004, L, 14, 1.2, phase=1)) * np.exp(-np.arange(L) / (0.07 * SR))
    s *= adsr(L, 0.004, 0.03)
    add(t0, 0.2, lp(s, 4200), pan, amp)

def brass(t0, dur, note, amp=0.12, att=0.25, rel=0.6, pan=0.0, drive=1.5):
    L = int((dur + rel) * SR); f = nm(note)
    e = adsr(L, att, rel)
    s = saw(f, L, 30, 0.9) + 0.6 * saw(f * 1.003, L, 30, 0.9, phase=2)
    s = np.tanh(drive * s * (0.3 + 0.7 * e))
    s = tv_lp(s, 300 + 3500 * e)
    add(t0, dur, s * e, pan, amp)

def taiko(t0, amp=0.5, base=62):
    L = int(1.4 * SR); tt = np.arange(L) / SR
    s = np.sin(2 * np.pi * (base + 50 * np.exp(-tt * 18)) * tt) * np.exp(-tt / 0.32)
    s += lp(rng.normal(0, 1, L), 1200) * np.exp(-tt / 0.03) * 0.5
    add(t0, 1.4, s, 0.0, amp)

def cymbal_swell(t0, t1, amp=0.25):
    L = int((t1 - t0) * SR)
    s = hp(rng.normal(0, 1, L), 4500) * np.linspace(0, 1, L) ** 3
    add(t0, t1 - t0, s, 0.0, amp)

def crash_cym(t0, amp=0.25):
    L = int(3.0 * SR); tt = np.arange(L) / SR
    s = hp(rng.normal(0, 1, L), 3500) * np.exp(-tt / 0.9)
    add(t0, 3.0, s, 0.0, amp)

# 0-3s: D minor, soft pad + 8th-note ostinato
for n_, p in [("D3", -0.4), ("F3", 0.3), ("A3", -0.1)]:
    strings(0.0, 3.0, n_, amp=0.055, att=1.2, pan=p)
strings(0.0, 3.0, "D2", amp=0.07, att=1.0)
for k in range(12):
    stacc(k * 0.25, "D3" if k % 4 else "D4", amp=0.035 + 0.02 * k / 12, pan=0.25)
# 3-6s: Bb major, low brass swell
for n_, p in [("Bb2", -0.3), ("D3", 0.3), ("F3", 0.0)]:
    strings(3.0, 3.0, n_, amp=0.07, att=0.6, pan=p)
for k in range(12):
    stacc(3 + k * 0.25, ["D3", "F3", "D3", "A3"][k % 4], amp=0.06, pan=0.25)
brass(4.3, 1.7, "Bb1", amp=0.10, att=0.9)
brass(4.3, 1.7, "F2", amp=0.06, att=0.9)
# 6-8.9s: Gm -> A, 16th ostinato, taiko crescendo
for n_, p in [("G2", -0.3), ("Bb2", 0.3), ("D3", 0.0), ("G3", 0.2)]:
    strings(6.0, 1.5, n_, amp=0.08, att=0.15, rel=0.3, pan=p)
for n_, p in [("A2", -0.3), ("C#3", 0.3), ("E3", 0.0), ("A3", 0.2)]:
    strings(7.5, 1.4, n_, amp=0.1, att=0.1, rel=0.25, pan=p)
for k in range(23):
    stacc(6 + k * 0.125, ["G3", "D4", "Bb3", "D4"][k % 4] if k < 12 else ["A3", "E4", "C#4", "E4"][k % 4], amp=0.06 + 0.04 * k / 23, pan=0.3)
for k, tb in enumerate(np.arange(6.0, 8.9, 0.5)):
    taiko(tb, amp=0.25 + 0.06 * k)
taiko(8.75, 0.45); taiko(8.875, 0.5)
brass(6.0, 1.5, "G1", amp=0.13, att=0.4, rel=0.3); brass(7.5, 1.35, "A1", amp=0.16, att=0.3, rel=0.3)
cymbal_swell(7.6, 8.95, 0.12)
# slow motion: music drops away to a tense high harmonic + low drone
strings(9.0, 2.9, "A5", amp=0.03, att=0.6, rel=0.5, pan=0.2)
strings(9.0, 2.9, "D1", amp=0.05, att=0.8, rel=0.5)
cymbal_swell(10.9, 12.0, 0.18)
# 12-15s: epic swell, final hit at 13.0
for n_, p in [("D3", -0.4), ("F3", 0.3), ("A3", -0.2), ("D4", 0.25), ("F4", -0.1), ("A4", 0.15), ("D5", 0.0)]:
    strings(12.0, 2.6, n_, amp=0.06, att=0.35, rel=1.2, pan=p)
brass(12.0, 1.0, "D2", amp=0.14, att=0.25, rel=0.4); brass(12.0, 1.0, "A2", amp=0.1, att=0.25, rel=0.4)
taiko(12.0, 0.5); taiko(12.5, 0.45); taiko(12.75, 0.5); taiko(12.875, 0.55)
for n_ in ("D1", "D2", "A1"):
    brass(13.0, 1.4, n_, amp=0.2, att=0.03, rel=1.4, drive=3.0)
taiko(13.0, 0.9, base=48); crash_cym(13.0, 0.22)
strings(13.0, 1.6, "D6", amp=0.015, att=0.2, rel=1.0)

# reverb on the orchestra bus
def reverb(x, decay=1.1, length=3.0, seed=5):
    L = int(length * SR); tt = np.arange(L) / SR
    ir = np.random.default_rng(seed).normal(0, 1, L) * np.exp(-tt / decay * 3)
    ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
    return signal.fftconvolve(x, ir)[:N]
music_wet = np.stack([reverb(music[0], seed=5), reverb(music[1], seed=6)])
music_mix = 0.7 * music + 0.55 * music_wet
duck = env_pts([(0, 1), (8.9, 1), (9.05, 0.35), (12, 0.35), (12.01, 1), (15, 1)])
music_mix *= duck

# ------------------------------------------------------------------ mix
fx = engine * 0.42 + crk * 0.5 + crash * 0.7
fx_wet = reverb(fx, decay=0.6, length=1.6, seed=9) * 0.25
L_ = fx + fx_wet + windL + music_mix[0]
R_ = fx + fx_wet + windR + music_mix[1]
mix = np.stack([L_, R_])
mix = hp(mix, 25)
fade = np.clip((15.0 - t) / 0.7, 0, 1) * np.clip(t / 0.05, 0, 1)
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(1.5 * mix) / np.tanh(1.5)
mix *= 0.93
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else "beyond_the_edge.wav", SR, (mix.T * 32767).astype(np.int16))
print("wrote audio", mix.shape)
