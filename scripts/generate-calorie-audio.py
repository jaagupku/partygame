#!/usr/bin/env python3
"""Original deterministic retro aerobics score, no recordings or external dependencies.
Run: python3 scripts/generate-calorie-audio.py
16 bars at 120 BPM, D / Bm / G / A. Release tails wrap across the 32-second loop.
24 kHz mono PCM WAV, gentle pulse synths, bass and synthesized percussion.
"""

import math
import random
import sys
import wave
from array import array
from pathlib import Path

RATE = 24000
OUT = Path(__file__).resolve().parents[1] / "frontend/static/presentation/calorie/audio"
OUT.mkdir(parents=True, exist_ok=True)


def canvas(seconds):
    return array("d", [0.0]) * round(seconds * RATE)


def tone(buf, at, midi, duration, volume, voice="synth", wrap=False):
    frequency = 440 * 2 ** ((midi - 69) / 12)
    for i in range(round(duration * RATE)):
        t = i / RATE
        envelope = min(1, t / 0.012) * min(1, (duration - t) / 0.06)
        phase = math.tau * frequency * t
        if voice == "whistle":
            value = math.sin(phase + 0.12 * math.sin(math.tau * 6 * t))
        elif voice == "bass":
            value = math.sin(phase) + 0.15 * math.sin(2 * phase)
            envelope *= math.exp(-t * 4)
        else:
            value = (
                math.sin(phase)
                + 0.22 * math.sin(2 * phase)
                + 0.08 * math.sin(3 * phase)
            )
            envelope *= math.exp(-t * 3)
        j = round(at * RATE) + i
        if wrap:
            j %= len(buf)
        if j < len(buf):
            buf[j] += value * envelope * volume


def drum(buf, at, kind, seed):
    rng = random.Random(seed)
    duration = 0.16 if kind == "kick" else 0.09
    for i in range(round(duration * RATE)):
        t = i / RATE
        envelope = min(1, t / 0.003) * (1 - t / duration) ** 3
        if kind == "kick":
            # Integrated descending frequency gives a rounded, click-free kick.
            value = math.sin(math.tau * (48 * t + 3 * (1 - math.exp(-30 * t)))) * 0.15
        else:
            value = rng.uniform(-1, 1) * (0.045 if kind == "snare" else 0.018)
        j = (round(at * RATE) + i) % len(buf)
        buf[j] += value * envelope


def save(name, buf):
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
        f"{name}: {len(buf)/RATE:.3f}s peak={peak:.3f} rms={rms:.3f} seam={abs(buf[0]-buf[-1]):.6f}"
    )


music = canvas(32)
chords = [(50, 62, 66, 69), (47, 62, 66, 71), (43, 62, 67, 71), (45, 61, 64, 69)]
melody = [78, 76, 74, 81, 78, 74, 76, 73]
for bar in range(16):
    at = bar * 2
    chord = chords[bar % 4]
    for beat in range(4):
        drum(music, at + beat * 0.5, "kick", bar * 4 + beat)
        if beat % 2:
            drum(music, at + beat * 0.5, "snare", bar * 9 + beat)
        tone(music, at + beat * 0.5, chord[0], 0.24, 0.12, "bass", True)
        for pitch in chord[1:]:
            tone(music, at + beat * 0.5 + 0.25, pitch, 0.25, 0.04, wrap=True)
    for tick in range(8):
        drum(music, at + tick * 0.25, "hat", bar * 8 + tick)
    # Alternate phrases and leave a rest at each turnaround; later bars add a response.
    if bar % 4 != 3:
        for k, offset in enumerate([0.25, 1] if bar < 8 else [0.25, 1, 1.75]):
            tone(music, at + offset, melody[(bar + k) % 8], 0.35, 0.055, wrap=True)
save("studio-loop", music)

for name, seconds, notes in [
    ("whistle", 0.36, [(0, 86), (0.15, 88)]),
    ("interval", 0.12, [(0, 74)]),
    ("stop", 0.30, [(0, 69), (0.12, 62)]),
    ("reveal", 0.72, [(0, 74), (0.14, 78), (0.28, 81)]),
    ("milestone", 0.9, [(0, 62), (0.16, 69), (0.32, 74), (0.48, 78)]),
    ("stage", 0.5, [(0, 74), (0.13, 81)]),
    ("confirm", 0.20, [(0, 78)]),
    (
        "complete",
        2.6,
        [(0, 74), (0.20, 78), (0.4, 81), (0.7, 78), (0.9, 83), (1.25, 86)],
    ),
]:
    buf = canvas(seconds)
    for at, midi in notes:
        tone(
            buf,
            at,
            midi,
            min(0.38, seconds - at),
            0.085 if name == "whistle" else 0.16,
            "whistle" if name == "whistle" else "synth",
        )
    if name == "complete":
        for midi in [50, 62, 66, 69]:
            tone(buf, 1.25, midi, 1.35, 0.06)
    save(name, buf)
