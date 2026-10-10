# Sketchbook and judging-stage assets

Original project artwork and synthesized audio, with no third-party samples.
`sketchbook.svg` is the open spiral pad used on the home card, setup and lobby;
`plot-twist.svg` is the comic burst shown when the judging stage takes over.
All artwork is decorative. Topics, criteria, drawings and controls remain HTML
or canvas.

Regenerate every WAV file from the repository root:

```sh
python3 scripts/generate-drawing-audio.py
```

The deterministic Python standard-library generator writes mono, 24 kHz, 16-bit
PCM. `sketch-loop.wav` is 8 bars at 90 BPM (C / Am / F / G) of mellow
Karplus-Strong plucks. `judging-loop.wav` is 8 bars at 112 BPM with a swung
E minor bass walk, finger snaps and staccato answers. Release tails wrap across
each loop boundary. `twist.wav` is the musical interruption at the criterion
reveal. The other effects cover page flips, pencil starts, voting, countdowns,
results milestones, finale stages and the phone's personal confirmation. The
generator reports duration, peak, RMS and endpoint difference, and rejects
clipping.
