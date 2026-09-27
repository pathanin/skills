#!/bin/bash
# A brand kit: an Illustrator-style SVG logo (shared class names, a gradient id), guidelines with tone and don'ts, and the wordmark font.
set -e
mkdir -p brand
cat > brand/lumen-logo.svg <<'SVG'
<?xml version="1.0" encoding="UTF-8"?>
<!-- Generator: Adobe Illustrator 27.0.0, SVG Export Plug-In -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120" width="400" height="120">
  <defs><style>.cls-1{fill:none;stroke:#1b2a4a;stroke-width:8;stroke-linecap:round}.cls-2{fill:#ffb400}.cls-3{fill:#1b2a4a}</style>
  <linearGradient id="grad1" x1="0" x2="1"><stop offset="0" stop-color="#ffb400"/><stop offset="1" stop-color="#ff6a00"/></linearGradient></defs>
  <g transform="translate(60 60)">
    <circle class="cls-1" r="44"/>
    <path class="cls-2" d="M0 -26 L7 -7 L26 0 L7 7 L0 26 L-7 7 L-26 0 L-7 -7 Z"/>
  </g>
  <text class="cls-3" x="130" y="78" font-family="Lumen Serif" font-size="56" font-weight="700">lumen</text>
</svg>
SVG
cat > brand/guidelines.md <<'MD'
# Lumen brand guidelines (excerpt)
Lumen makes smart lighting that wakes you gently. Personality: calm, warm, premium. Tagline: "Light that feels like morning."
Palette: Midnight #1B2A4A (primary), Dawn #FFB400 (accent), Ember #FF6A00 (accent 2), Paper #F7F3EA (background).
Type: Lumen Serif Bold for the wordmark: brand/LumenSerif-Bold.ttf.
Logo: ring + four-point spark + wordmark. Never recolour, stretch, skew or rotate the logo. Keep clear space equal to the ring radius.
Motion note from the brand team: "light arrives slowly, like sunrise; nothing bounces".
MD
for f in /usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf /usr/share/fonts/TTF/DejaVuSerif-Bold.ttf /Library/Fonts/Georgia\ Bold.ttf /System/Library/Fonts/Supplemental/Georgia\ Bold.ttf; do
  [ -f "$f" ] && cp "$f" brand/LumenSerif-Bold.ttf && break; done
