"""Score every video frame against a thumbnail. Usage: match.py VIDEO THUMB [top_n]"""
import subprocess, sys
import numpy as np
from PIL import Image

W, H = 64, 36
video, thumb = sys.argv[1], sys.argv[2]
top = int(sys.argv[3]) if len(sys.argv) > 3 else 15
from fractions import Fraction
rate = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', video]).decode().split()[0]
fps = float(Fraction(rate))
t = np.asarray(Image.open(thumb).convert('L').resize((W, H)), np.float32).ravel(); t -= t.mean()
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', video, '-vf', f'scale={W}:{H}',
                      '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
res, i = [], 0
while (b := p.stdout.read(W * H)) and len(b) == W * H:
    f = np.frombuffer(b, np.uint8).astype(np.float32); f -= f.mean()
    res.append((float(f @ t / (np.linalg.norm(f) * np.linalg.norm(t) + 1e-6)), i)); i += 1
for c, i in sorted(res, reverse=True)[:top]:
    print(f'{c:.3f}  frame {i}  t={i / fps:.2f}s')
