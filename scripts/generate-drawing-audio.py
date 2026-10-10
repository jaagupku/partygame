#!/usr/bin/env python3
"""Original deterministic Drawing Mashup score, no recordings or external dependencies.
Run: python3 scripts/generate-drawing-audio.py
Sketchbook loop: 8 bars at 90 BPM, C / Am / F / G, mellow Karplus-Strong plucks.
Judging loop: 8 bars at 112 BPM, swung E minor bass walk, snaps and staccato plucks.
Release tails wrap across each loop boundary. 24 kHz mono 16-bit PCM WAV.
"""

import math
import random
import sys
import wave
from array import array
from pathlib import Path

RATE = 24000
OUT = Path(__file__).resolve().parents[1] / "frontend/static/presentation/drawing/audio"
OUT.mkdir(parents=True, exist_ok=True)


def canvas(seconds):
    return array("d", [0.0]) * round(seconds * RATE)


def mix(buf, at, samples, volume, wrap=False):
    start = round(at * RATE)
    for i, value in enumerate(samples):
        j = start + i
        if wrap:
            j %= len(buf)
        if 0 <= j < len(buf):
            buf[j] += value * volume


def pluck(midi, duration, seed, brightness=0.5, decay=0.996):
    """Karplus-Strong string; low brightness smooths the excitation for a mellow tone."""
    rng = random.Random(seed)
    period = max(2, round(RATE / (440 * 2 ** ((midi - 69) / 12))))
    line = [rng.uniform(-1, 1) for _ in range(period)]
    for _ in range(round((1 - brightness) * 4)):
        line = [(line[i] + line[i - 1]) / 2 for i in range(period)]
    out = []
    for i in range(round(duration * RATE)):
        k = i % period
        value = line[k]
        line[k] = decay * (value + line[k - 1]) / 2
        fade = min(1, (duration - i / RATE) / 0.05)
        out.append(value * fade)
    return out


def tone(midi, duration, voice="bass"):
    frequency = 440 * 2 ** ((midi - 69) / 12)
    out = []
    for i in range(round(duration * RATE)):
        t = i / RATE
        envelope = min(1, t / 0.006) * min(1, (duration - t) / 0.04)
        phase = math.tau * frequency * t
        if voice == "bass":
            value = (math.sin(phase) + 0.25 * math.sin(2 * phase)) * math.exp(-t * 5)
        elif voice == "brass":
            value = sum(math.sin(k * phase) / k for k in range(1, 6)) * math.exp(
                -t * 2.5
            )
        else:
            value = math.sin(phase) * math.exp(-t * 6)
        out.append(value * envelope)
    return out


def noise(duration, seed, shape):
    """Filtered noise; `shape(t)` gives the envelope, a one-pole filter keeps it soft."""
    rng = random.Random(seed)
    out, last = [], 0.0
    for i in range(round(duration * RATE)):
        t = i / RATE
        last += 0.35 * (rng.uniform(-1, 1) - last)
        out.append(last * shape(t))
    return out


def glide(start, end, duration):
    out, phase = [], 0.0
    for i in range(round(duration * RATE)):
        t = i / RATE
        frequency = start * (end / start) ** (t / duration)
        phase += math.tau * frequency / RATE
        envelope = min(1, t / 0.01) * (1 - t / duration) ** 1.5
        out.append((math.sin(phase) + 0.3 * math.sin(3 * phase)) * envelope)
    return out


def save(name, buf, gain=1.0):
    for i, value in enumerate(buf):
        buf[i] = value * gain
    peak = max(abs(value) for value in buf)
    assert 0.01 < peak < 0.9, (name, peak)
    pcm = array("h", (round(value * 32767) for value in buf))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(OUT / f"{name}.wav"), "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        wav.writeframes(pcm.tobytes())
    rms = math.sqrt(sum(value * value for value in buf) / len(buf))
    print(
        f"{name}: {len(buf)/RATE:.3f}s peak={peak:.3f} rms={rms:.3f}"
        f" seam={abs(buf[0]-buf[-1]):.6f}"
    )


# Sketchbook: unhurried broken chords with a light melody every other bar.
beat = 60 / 90
sketch = canvas(8 * 4 * beat)
chords = [(48, 60, 64, 67), (45, 57, 60, 64), (41, 57, 60, 65), (43, 55, 59, 62)]
tune = [76, 74, 72, 74, 79, 76, 77, 74]
for bar in range(8):
    at = bar * 4 * beat
    root, *upper = chords[bar % 4]
    mix(sketch, at, tone(root, 2.4, "bass"), 0.13, wrap=True)
    for step, pitch in enumerate([upper[0], upper[1], upper[2], upper[1]] * 2):
        mix(
            sketch,
            at + step * beat / 2,
            pluck(pitch, 1.2, bar * 16 + step, 0.3),
            0.075,
            wrap=True,
        )
    if bar % 2 == 0:
        for k, offset in enumerate((0.5, 1.5, 2.5)):
            mix(
                sketch,
                at + offset * beat,
                pluck(tune[(bar + k) % 8], 1.4, 900 + bar * 4 + k, 0.55),
                0.09,
                wrap=True,
            )
# Balanced against the judging groove and the other games' loops.
save("sketch-loop", sketch, 2.5)

# Judging: a sneaky swung bass walk, finger snaps and cheeky staccato answers.
beat = 60 / 112
judging = canvas(8 * 4 * beat)
walk = [40, 43, 45, 46, 47, 45, 43, 42]
riff = [(0.5, 71), (1.66, 74), (2.5, 76), (3.66, 75)]
for bar in range(8):
    at = bar * 4 * beat
    for step in range(8):
        swing = 0.66 if step % 2 else 0
        when = at + (step // 2 + swing) * beat
        mix(judging, when, tone(walk[(bar * 2 + step) % 8], 0.22), 0.16, wrap=True)
    for snap in (1, 3):
        mix(
            judging,
            at + snap * beat,
            noise(0.08, bar * 7 + snap, lambda t: math.exp(-t * 60)),
            0.22,
            wrap=True,
        )
    if bar % 2 == 1:
        for offset, pitch in riff:
            mix(
                judging,
                at + offset * beat,
                pluck(pitch, 0.35, bar * 5 + pitch, 0.8),
                0.1,
                True,
            )
    else:
        mix(judging, at + 2 * beat, tone(64, 0.3, "brass"), 0.05, wrap=True)
save("judging-loop", judging, 0.85)


def effect(name, seconds, parts, gain=1.5):
    buf = canvas(seconds)
    for at, samples, volume in parts:
        mix(buf, at, samples, volume)
    save(name, buf, gain)


effect(
    "page-flip",
    0.42,
    [(0, noise(0.42, 1, lambda t: math.sin(math.pi * min(1, t / 0.42)) ** 2), 0.5)],
)
effect(
    "pencil",
    0.5,
    [
        (k * 0.11, noise(0.09, 10 + k, lambda t: math.sin(math.pi * t / 0.09)), 0.35)
        for k in range(4)
    ],
)
# Musical interruption: a falling slide, then a bright stab chord.
effect(
    "twist",
    1.1,
    [(0, glide(880, 180, 0.32), 0.18)]
    + [(0.34, tone(m, 0.7, "brass"), 0.07) for m in (64, 67, 71, 74)]
    + [(0.34, pluck(88, 0.7, 77, 0.9), 0.12)],
)
effect(
    "vote-open",
    0.5,
    [(0, pluck(72, 0.4, 21, 0.8), 0.25), (0.12, pluck(79, 0.38, 22, 0.8), 0.25)],
)
effect(
    "results",
    0.9,
    [
        (k * 0.1, pluck(m, 0.6, 30 + k, 0.7), 0.22)
        for k, m in enumerate((67, 71, 74, 79))
    ],
)
effect("tally", 0.2, [(0, tone(84, 0.18, "wood"), 0.3)])
effect(
    "points",
    0.9,
    [
        (k * 0.07, pluck(m, 0.55, 40 + k, 0.85), 0.2)
        for k, m in enumerate((72, 76, 79, 84, 88))
    ],
)
effect(
    "bonus",
    0.6,
    [(0, pluck(84, 0.5, 50, 0.9), 0.22), (0.1, pluck(91, 0.45, 51, 0.9), 0.18)],
)
effect(
    "warning",
    0.36,
    [(0, tone(81, 0.14, "wood"), 0.35), (0.17, tone(81, 0.14, "wood"), 0.35)],
)
effect("tick", 0.15, [(0, tone(88, 0.12, "wood"), 0.3)])
effect(
    "stage",
    0.6,
    [(0, pluck(67, 0.5, 60, 0.7), 0.24), (0.14, pluck(74, 0.45, 61, 0.7), 0.24)],
)
effect("confirm", 0.3, [(0, pluck(79, 0.28, 70, 0.6), 0.26)])
effect(
    "fanfare",
    2.4,
    [
        (k * 0.16, pluck(m, 0.9, 80 + k, 0.8), 0.18)
        for k, m in enumerate((60, 64, 67, 72, 76))
    ]
    + [(0.9, tone(m, 1.4, "brass"), 0.05) for m in (60, 64, 67, 72)]
    + [(0.9, pluck(84, 1.4, 90, 0.9), 0.15)],
)
