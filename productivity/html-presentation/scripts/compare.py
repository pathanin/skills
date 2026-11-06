"""Mean per-pixel difference (0-255) between two folders of sNN.png renders: python compare.py A B [SIDE_BY_SIDE_DIR]"""
import sys, glob, os
from PIL import Image, ImageChops, ImageStat
a, b = sys.argv[1], sys.argv[2]
rows = []
if len(sys.argv) > 3: os.makedirs(sys.argv[3], exist_ok=True)
for f in sorted(glob.glob(os.path.join(a, "s*.png"))):
    g = os.path.join(b, os.path.basename(f))
    if not os.path.exists(g): rows.append((os.path.basename(f), None)); continue
    x = Image.open(f).convert("RGB").resize((640, 360)); y = Image.open(g).convert("RGB").resize((640, 360))
    d = ImageChops.difference(x, y)
    rows.append((os.path.basename(f), sum(ImageStat.Stat(d).mean) / 3))
    if len(sys.argv) > 3:
        Image.fromarray(__import__("numpy").hstack([__import__("numpy").array(x), __import__("numpy").array(y)])).save(os.path.join(sys.argv[3], os.path.basename(f)))
for n, v in rows: print(n, "missing" if v is None else f"{v:.2f}")
