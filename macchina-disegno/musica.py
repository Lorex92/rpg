"""Colonna sonora del Reel: musichetta allegra (ukulele, glockenspiel, basso, shaker)
più i rumori della scena (matita, pastello, motori del braccio, "pop" delle scritte).
Uso: python3 musica.py uscita.wav
"""
import sys, wave
import numpy as np

SR = 44100
DUR = 39.6
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)

def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - pan) / 2 * 2 ** 0.5 * 0.7071 * 2
    R[i:i + len(sig)] += sig * gain * (1 + pan) / 2 * 2 ** 0.5 * 0.7071 * 2

def midi(m): return 440.0 * 2 ** ((m - 69) / 12)

def env_t(d): return np.arange(int(d * SR)) / SR

def pluck(f, d=1.6):
    t = env_t(d); s = np.zeros_like(t)
    for k in range(1, 9):
        s += np.sin(2 * np.pi * k * f * t) / k ** 1.3 * np.exp(-t * (2.2 + k * 1.4))
    s *= np.minimum(t / 0.003, 1)
    return s

def glock(f, d=1.4):
    t = env_t(d)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)
    s += 0.12 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 16)
    return s * np.minimum(t / 0.002, 1)

def bass(f, d=0.9):
    t = env_t(d)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return s * np.exp(-t * 3.5) * np.minimum(t / 0.008, 1)

def kick(d=0.18):
    t = env_t(d)
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)

def bandnoise(n, lo, hi, seed):
    x = np.random.default_rng(seed).standard_normal(n)
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-((np.log(fr + 1) - np.log((lo * hi) ** 0.5)) / np.log(hi / lo) * 2.2) ** 2)
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)

def shaker(d=0.06):
    t = env_t(d)
    return bandnoise(len(t), 5000, 11000, int(rng.integers(1_000_000))) * np.exp(-t * 70) * np.minimum(t / 0.004, 1)

# ---------- music ----------
BPM = 116
BEAT = 60 / BPM
BAR = 4 * BEAT
C, G, Am, F = [48, 52, 55, 60, 64], [43, 50, 55, 59, 62], [45, 52, 57, 60, 64], [41, 48, 53, 57, 60]
PROG = [C, G, Am, F]
ROOT = {id(C): 36, id(G): 31, id(Am): 33, id(F): 29}
_ = None
A = [[76, _, 79, _, 81, 79, 76, _], [74, _, 79, _, 71, _, 74, _], [72, _, 76, 81, 79, _, 76, _], [77, 76, 74, _, 72, _, _, _]]
B = [[79, _, 79, 81, 79, _, 76, _], [74, 76, 74, _, 71, _, 67, _], [69, 72, 76, _, 81, _, 79, _], [77, _, 81, _, 79, 77, 76, 74]]
MEL = A + B + A + B            # bars 2..17
LAST = 18

for bar in range(LAST + 1):
    t0 = bar * BAR
    chord = C if bar == LAST else PROG[bar % 4]
    if bar == LAST:
        for j, m in enumerate(chord): add(pluck(midi(m), 2.4), t0 + j * 0.03, 0.22, -0.35)
        add(bass(midi(36), 2.4), t0, 0.5)
        for j, m in enumerate([72, 76, 79, 84]): add(glock(midi(m), 2.4), t0 + j * 0.06, 0.16, 0.3)
        add(kick(), t0, 0.2)
        break
    # ukulele strum: down on 1, up on 2&, down on 3, up on 4&
    for beat_pos, up in [(0, False), (1.5, True), (2, False), (3.5, True)]:
        notes = chord[::-1] if up else chord
        for j, m in enumerate(notes):
            add(pluck(midi(m), 1.2), t0 + beat_pos * BEAT + j * 0.011, 0.16 if not up else 0.11, -0.35)
    add(bass(midi(ROOT[id(chord)])), t0, 0.55)
    add(bass(midi(ROOT[id(chord)] + 7)), t0 + 2 * BEAT, 0.42)
    if bar >= 1:
        add(kick(), t0, 0.18); add(kick(), t0 + 2 * BEAT, 0.13)
        for e in range(8):
            if e % 2: add(shaker(), t0 + e * BEAT / 2, 0.05, 0.25)
    if 2 <= bar < LAST:
        for e, m in enumerate(MEL[bar - 2]):
            if m is not None: add(glock(midi(m)), t0 + e * BEAT / 2, 0.2, 0.3)

# final fade-out of the music tail
fade = np.ones(N); k = int(1.0 * SR); fade[-k:] = np.linspace(1, 0, k) ** 1.5
music_L, music_R = L * fade, R * fade
L[:] = 0; R[:] = 0

# ---------- sound effects (synced with the animation timeline) ----------
def scratch(t0, t1, lo, hi, rate, seed, gain):
    n = int((t1 - t0) * SR); t = np.arange(n) / SR
    x = bandnoise(n, lo, hi, seed)
    am = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * rate * t)) ** 1.5
    edge = np.minimum(np.minimum(t / 0.15, 1), np.minimum((t1 - t0 - t) / 0.15, 1))
    grit = 0.8 + 0.4 * bandnoise(n, 20, 60, seed + 1)
    add(x * am * edge * grit, t0, gain)

scratch(2.6, 15.6, 2500, 7000, 5.5, 11, 0.028)      # pencil
scratch(21.0, 33.0, 400, 1800, 3.6, 12, 0.05)       # crayon

def whirr(t0, d, gain=0.03):
    t = env_t(d); p = t / d
    f = 150 + 70 * np.sin(np.pi * p)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)
    s += 0.3 * bandnoise(len(t), 800, 3000, int(t0 * 100))
    add(s * np.sin(np.pi * p) ** 0.8, t0, gain)

for t0, d in [(1.2, 1.4), (15.6, 1.4), (17.7, 1.1), (19.5, 1.5), (33.0, 1.3), (35.0, 1.4)]:
    whirr(t0, d)

def click(t0, gain=0.12):
    t = env_t(0.05)
    s = bandnoise(len(t), 1500, 5000, int(t0 * 1000)) * np.exp(-t * 120) + 0.6 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 80)
    add(s, t0, gain)

for t in (17.35, 19.15, 34.65): click(t)

def pop(t0, gain=0.14):
    t = env_t(0.14)
    f = 380 + 900 * (t / 0.14) ** 0.6
    add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22) * np.minimum(t / 0.004, 1), t0, gain, 0.1)

for t in (0.4, 5.2, 10.6, 17.0, 31.0): pop(t)

# ---------- mix ----------
L += music_L; R += music_R
peak = max(np.abs(L).max(), np.abs(R).max())
L *= 0.89 / peak; R *= 0.89 / peak
st = np.empty(2 * N, dtype=np.int16)
st[0::2] = (L * 32767).astype(np.int16); st[1::2] = (R * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
print('ok', DUR, 's')
