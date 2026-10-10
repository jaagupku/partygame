#!/usr/bin/env python3
"""Original deterministic department-store score. Python stdlib only, no source samples.
Run from any directory: python3 scripts/generate-price-audio.py
16 bars, 96 BPM, Cmaj9 / Am9 / Dm9 / G13; wrapped release tails make an exact loop.
24 kHz mono PCM WAV keeps browser decoding universal and the whole set under 3 MB.
"""

import math
import random
import sys
import wave
from array import array
from pathlib import Path

RATE = 24000
OUT = Path(__file__).resolve().parents[1] / "frontend/static/presentation/price/audio"
OUT.mkdir(parents=True, exist_ok=True)
TAU = math.tau


def canvas(seconds):
    return array("d", [0.0]) * round(seconds * RATE)


def note(buf, at, midi, duration, volume, voice="keys", wrap=False):
    f = 440 * 2 ** ((midi - 69) / 12)
    start = round(at * RATE)
    for i in range(round(duration * RATE)):
        t = i / RATE
        attack = min(1, t / 0.012)
        release = min(1, (duration - t) / 0.08)
        env = attack * release * math.exp(-t * (3 if voice == "keys" else 5))
        if voice == "keys":
            val = math.sin(
                TAU * f * t + 0.65 * math.sin(TAU * 2 * f * t) * math.exp(-7 * t)
            ) + 0.13 * math.sin(TAU * 3 * f * t)
        else:
            val = math.sin(TAU * f * t) + 0.18 * math.sin(TAU * 2 * f * t)
        j = start + i
        if wrap:
            j %= len(buf)
        if 0 <= j < len(buf):
            buf[j] += val * env * volume


def noise(buf, at, duration, volume, seed):
    rng = random.Random(seed)
    last = 0
    for i in range(round(duration * RATE)):
        t = i / RATE
        val = rng.uniform(-1, 1)
        high = val - last
        last = val
        env = min(1, t / 0.004) * (1 - t / duration) ** 2
        j = round(at * RATE) + i
        if 0 <= j < len(buf):
            buf[j] += high * env * volume


def save(name, buf):
    peak = max(abs(x) for x in buf)
    assert peak < 0.95, (name, peak)
    pcm = array("h", (round(x * 32767) for x in buf))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(OUT / f"{name}.wav"), "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        wav.writeframes(pcm.tobytes())
    rms = math.sqrt(sum(x * x for x in buf) / len(buf))
    print(
        f"{name}: {len(buf)/RATE:.3f}s peak={peak:.3f} rms={rms:.3f} seam={abs(buf[0]-buf[-1]):.6f}"
    )


beat = 60 / 96
music = canvas(64 * beat)
chords = [
    (60, 64, 67, 71, 74),
    (57, 60, 64, 67, 71),
    (50, 57, 60, 64, 65),
    (55, 59, 62, 64, 69),
]
melody = [76, 74, 71, 74, 72, 71, 69, 67, 69, 72, 76, 74, 71, 69, 67, 74]
for bar in range(16):
    at = bar * 4 * beat
    chord = chords[bar % 4]
    for offset in [0, 1.75, 3]:
        for k, pitch in enumerate(chord[1:]):
            note(music, at + offset * beat + k * 0.009, pitch, 1.25, 0.044, wrap=True)
    for offset, pitch in [
        (0, chord[0] - 12),
        (1.5, chord[0] - 12),
        (2.5, chord[0] - 5),
        (3.5, chord[0] - 10),
    ]:
        note(music, at + offset * beat, pitch, 0.42, 0.12, "bass", wrap=True)
    # Space between phrases; later passes vary the rhythm and octave.
    if bar % 4 != 3:
        for n, offset in enumerate([0.5, 2.25] if bar < 8 else [0.75, 2, 3.25]):
            note(
                music,
                at + offset * beat,
                melody[(bar * 2 + n) % 16],
                0.65,
                0.07,
                wrap=True,
            )
    for tick in range(8):
        noise(
            music,
            at + tick * 0.5 * beat + (0.015 if tick % 2 else 0),
            0.045,
            0.014 if tick % 2 else 0.009,
            bar * 8 + tick,
        )
    for offset in [1, 3]:
        noise(music, at + offset * beat, 0.09, 0.028, bar + 100)
save("store-loop", music)

# Count-up: after the 0.5 s reveal sting, ticks follow the ease-in (value = t^3 over
# 1.2 s), then the price lands.
count = canvas(2.3)
for k in range(17):
    note(count, 0.5 + 1.2 * (k / 16) ** (1 / 3), 72 + k, 0.05, 0.07 + 0.004 * k)
for pitch in [84, 88]:
    note(count, 1.7, pitch, 0.55, 0.15)
save("count", count)

for name, length in [
    ("bag", 0.45),
    ("tick", 0.11),
    ("register", 0.28),
    ("scan", 0.65),
    ("receipt", 0.85),
    ("chime", 0.7),
    ("confirm", 0.22),
    ("victory", 2.8),
]:
    buf = canvas(length)
    if name == "bag":
        for i in range(3):
            noise(buf, i * 0.09, 0.22, 0.065, i + 400)
    elif name == "tick":
        note(buf, 0, 79, 0.09, 0.13)
    elif name == "register":
        noise(buf, 0, 0.07, 0.13, 9)
        note(buf, 0.045, 55, 0.19, 0.17)
    elif name == "scan":
        for t, pitch in [(0, 83), (0.13, 88), (0.25, 76)]:
            note(buf, t, pitch, 0.25, 0.19)
    elif name == "receipt":
        noise(buf, 0, 0.32, 0.055, 123)
        for t, pitch in [(0.1, 64), (0.24, 67), (0.38, 72)]:
            note(buf, t, pitch, 0.45, 0.16)
    elif name == "chime":
        for pitch in [72, 76, 79]:
            note(buf, 0, pitch, 0.65, 0.1)
    elif name == "confirm":
        note(buf, 0, 76, 0.2, 0.14)
    else:
        for t, pitch in [
            (0, 67),
            (0.2, 72),
            (0.4, 76),
            (0.7, 74),
            (0.95, 79),
            (1.25, 84),
        ]:
            note(buf, t, pitch, 0.65, 0.2)
        for pitch in [48, 60, 64, 67, 71]:
            note(buf, 1.25, pitch, 1.5, 0.075)
    save(name, buf)
