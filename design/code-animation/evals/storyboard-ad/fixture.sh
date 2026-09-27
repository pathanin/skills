#!/bin/bash
# A storyboard with exact copy and a 12 s track at 120 BPM whose drop (hats and bass enter) lands at 6.0 s.
set -e
cat > storyboard.md <<'MD'
# "Brew" — 12 s vertical ad for Kettle & Co. (Reels / TikTok)
Music: track.wav. Palette: Oat #F3E9DC, Espresso #3B2A20, Copper #C8743A, Steam #FFFFFF.
1. Close-up of a copper kettle on a stove. Copy: "Mornings start slow."
2. Steam curls up from the spout and fills the frame (transition). No copy.
3. ON THE DROP: a mug slides in and fills with coffee. Copy: "Brew it right."
4. End card, hold: logo text "Kettle & Co." and "kettleandco.com".
Copy must appear exactly as written. The end card holds at least 1.5 s.
MD
python3 - <<'PY'
import math, random, struct, wave
sr, bpm, secs = 44100, 120, 12
beat = 60 / bpm; random.seed(2); out = []
for i in range(sr * secs):
    t = i / sr; b = t % beat; h = (t + beat / 2) % beat; drop = t >= 6.0
    kick = math.sin(2 * math.pi * (50 + 90 * math.exp(-b * 30)) * b) * math.exp(-b * 8)
    hat = (random.random() - .5) * math.exp(-h * 50) * (.55 if drop else 0)
    bass = .2 * math.sin(2 * math.pi * 55 * t) * (1 if drop else 0)
    pad = .08 * math.sin(2 * math.pi * 220 * t)
    out.append(max(-1, min(1, .6 * kick + hat + bass + pad)))
with wave.open('track.wav', 'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(b''.join(struct.pack('<h', int(v * 32000)) for v in out))
PY
