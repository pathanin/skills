"""Tiled AI upscale (any spandrel model: ESRGAN, FDAT, PLKSR, DAT...). Usage: upscale.py MODEL IN OUT [--fit WxH]
Uses Apple GPU (MPS) when available, else CPU. --fit center-crops to that aspect and resizes."""
import argparse, os
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')  # ops MPS lacks fall back to CPU
import numpy as np, torch
from PIL import Image
from spandrel import ModelLoader

ap = argparse.ArgumentParser()
ap.add_argument('model'); ap.add_argument('inp'); ap.add_argument('out')
ap.add_argument('--fit', help='e.g. 2560x1664')
ap.add_argument('--tile', type=int, default=0, help='tile size (0 = auto)')
a = ap.parse_args()

dev = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
desc = ModelLoader().load_from_file(a.model)
m, S = desc.model.eval().to(dev), desc.scale  # the module itself may lack .scale
img = np.asarray(Image.open(a.inp).convert('RGB')).astype(np.float32) / 255
H, W, _ = img.shape
T = a.tile or (512 if dev != 'cpu' else 192); P = 48  # 16 left visible seams
x = torch.from_numpy(img).permute(2, 0, 1)[None].to(dev)
out = np.zeros((H * S, W * S, 3), np.float32)
print(f'device={dev} input={W}x{H} scale={S}', flush=True)
with torch.no_grad():
    for y0 in range(0, H, T):
        for x0 in range(0, W, T):
            y1, x1 = min(y0 + T, H), min(x0 + T, W)
            ya, xa = max(y0 - P, 0), max(x0 - P, 0); yb, xb = min(y1 + P, H), min(x1 + P, W)
            o = m(x[:, :, ya:yb, xa:xb])[0].permute(1, 2, 0).float().cpu().numpy()
            out[y0*S:y1*S, x0*S:x1*S] = o[(y0-ya)*S:(y1-ya)*S, (x0-xa)*S:(x1-xa)*S]
        print(f'row {y0}/{H}', flush=True)
res = Image.fromarray((out.clip(0, 1) * 255 + .5).astype(np.uint8))
if a.fit:
    tw, th = map(int, a.fit.lower().split('x'))
    w, h = res.size; r = tw / th
    cw, ch = (int(h * r), h) if w / h > r else (w, int(w / r))
    l, t = (w - cw) // 2, (h - ch) // 2
    res = res.crop((l, t, l + cw, t + ch)).resize((tw, th), Image.LANCZOS)
kw = {'quality': 95, 'subsampling': 0} if a.out.lower().endswith(('.jpg', '.jpeg')) else {}
res.save(a.out, **kw)
print('saved', a.out, res.size)
