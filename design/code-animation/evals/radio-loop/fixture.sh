#!/bin/bash
# A 7.2 s music loop at 100 BPM (12 beats): kick on every beat, a hat on the off-beats, and a louder, brighter second half.
set -e
python3 - <<'PY'
import math, random, struct, wave
sr, bpm, beats = 44100, 100, 12
beat = 60 / bpm; n = int(sr * beat * beats); random.seed(1); out = []
for i in range(n):
    t = i / sr; b = t % beat; h = (t + beat / 2) % beat; second = t >= beat * 6
    kick = math.sin(2 * math.pi * (50 + 90 * math.exp(-b * 30)) * b) * math.exp(-b * 8)
    hat = (random.random() - .5) * math.exp(-h * 60) * (.5 if second else .15)
    pad = .12 * math.sin(2 * math.pi * 110 * t) * (1.6 if second else 1)
    out.append(max(-1, min(1, .7 * kick + hat + pad)))
with wave.open('track.wav', 'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(b''.join(struct.pack('<h', int(v * 32000)) for v in out))
PY
