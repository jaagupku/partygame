# Retro fitness studio assets

Original project artwork and synthesized audio, with no third-party samples.
The thinking, reveal and celebrate coach SVGs share the same sweatband, outfit
and rounded silhouette; `studio.svg` combines the welcoming pose with a mirror,
clock, mats and weights.
All artwork is decorative. Nutrition information and player controls remain HTML.

Regenerate all nine WAV files from the repository root:

```sh
python3 scripts/generate-calorie-audio.py
```

The deterministic Python standard-library generator writes mono, 24 kHz, 16-bit
PCM. `studio-loop.wav` is a 32-second, 16-bar instrumental at 120 BPM, with a
D / Bm / G / A progression, alternating synth phrases, bass and soft percussion.
Release tails wrap across the loop boundary. The generator reports duration,
peak amplitude, RMS and the endpoint discontinuity; it rejects clipping.

`whistle` opens a round; `interval` warns near the deadline; `stop` closes it.
`reveal`, `milestone` and `stage` accompany shared reveals. `complete` celebrates
the winner. Only `confirm` plays on phones, after their own accepted submission.
The shared presentation engine owns mute/volume preferences, autoplay activation,
cue deduplication, ducking, pause/disconnection/visibility fades and cleanup.

The complete bundle is about 1.8 MB. Browser decoding/playback can be checked with
`e2e/calorie-style.spec.ts`. Automated peak/seam and playback checks do not replace
listening on actual speakers to judge mix, transitions and conversational volume.
