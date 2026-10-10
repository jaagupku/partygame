# Price Guessing assets

All SVG artwork and musical material in this directory were authored for Mänguõhtu.
No stock artwork, recordings, samples, external audio services or runtime synthesis.

Rebuild the bundled WAV files from the repository root:

```sh
python3 scripts/generate-price-audio.py
```

The generator uses only Python's standard library and seeded noise. Output is deterministic
24 kHz, 16-bit mono PCM. The 40-second loop is 16 bars at 96 BPM, with electric-keyboard
chords, a soft bass line, varied melodic phrases and light percussion. Note tails wrap
around the exact bar boundary instead of adding silence or truncating the last release.
The complete audio set is approximately 2.2 MB. Gain staging leaves headroom; the engine
applies the user's separate music/effects levels and ducks music under prominent cues.

- `bag`: round opening, soft paper rustle.
- `tick`: final countdown seconds.
- `register`: round closure, quiet mechanical click.
- `scan`: actual-price reveal, short ascending scanner phrase.
- `count`: price-guess reveal count-up; 0.5 s lead-in under `scan`, then ticks that
  accelerate with the number's ease-in over 1.2 s and land on the price.
- `receipt`: standings and final-results transitions.
- `chime`: podium transitions.
- `victory`: first-place reveal, checkout melody resolving to C major.
- `confirm`: optional phone-only acknowledgement of the first accepted answer per round.

There is deliberately no shared sound for aggregate submissions and no sound for typing.
The runtime exposes submitted-player membership, not individual revision acknowledgements;
answer corrections remain allowed and silent after the first accepted answer. Repeated
snapshots and reconnects do not replay acknowledgements. Selector/setup screens load no audio.

The storefront and shopping-bag SVGs have no embedded text; visible labels are localized
in `frontend/src/lib/i18n.ts`. Colors are authored, fixed, and independent of the app theme.
