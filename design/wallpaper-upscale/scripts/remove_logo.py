"""Inpaint logos out of an image with LaMa (run on the ORIGINAL, before upscaling).
Usage: remove_logo.py IN OUT BOX [BOX ...] [--thresh 150] [--grow 7] [--model PATH] [--telea]
BOX is x0,y0,x1,y1, optionally with :T (e.g. 120,530,140,650:65) to mask fainter grey parts
(thin separator lines) inside that box. Inside each box, pixels brighter than the threshold and
orange accent pixels are masked, grown by --grow px to cover JPEG/antialias halos, then filled.
--telea uses OpenCV's Telea instead: no model needed, but it smears over detailed art.
Also writes OUT_mask.png so you can check what was masked."""
import argparse, os, sys
import cv2, numpy as np

LAMA = os.path.expanduser('~/.cache/wallpaper-upscale/models/lama/big-lama.pt')


def parse_box(s):
    box, _, t = s.partition(':')
    return (*map(int, box.split(',')), int(t) if t else None)


def build_mask(a, boxes, thresh, grow):
    b, g, r = [a[..., i].astype(int) for i in range(3)]
    mn = np.minimum(np.minimum(r, g), b)
    orange = (r > 170) & (r - g > 60) & (b < 120)
    m = np.zeros(a.shape[:2], np.uint8)
    for x0, y0, x1, y1, t in boxes:
        hit = (mn > (thresh if t is None else t)) | orange
        m[y0:y1, x0:x1][hit[y0:y1, x0:x1]] = 255
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow, grow))) if grow > 1 else m


def inpaint_lama(a, m, net):
    import torch
    H, W = a.shape[:2]
    ph, pw = -H % 8, -W % 8
    img = np.pad(cv2.cvtColor(a, cv2.COLOR_BGR2RGB), ((0, ph), (0, pw), (0, 0)), mode='reflect')
    mk = np.pad(m, ((0, ph), (0, pw)), mode='reflect')
    with torch.no_grad():
        t = torch.from_numpy(img).permute(2, 0, 1)[None].float() / 255
        k = torch.from_numpy((mk > 127).astype(np.float32))[None, None]
        res = net(t, k)[0].permute(1, 2, 0).cpu().numpy()[:H, :W]
    res = cv2.cvtColor((res * 255).round().clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    return np.where(m[..., None] > 0, res, a)


def main():
    p = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    p.add_argument('inp'); p.add_argument('out'); p.add_argument('boxes', nargs='+', type=parse_box)
    p.add_argument('--thresh', type=int, default=150)
    p.add_argument('--grow', type=int, default=7)
    p.add_argument('--model', default=LAMA)
    p.add_argument('--telea', action='store_true')
    o = p.parse_args()
    if not o.telea and not os.path.exists(o.model):
        sys.exit(f'LaMa model not found at {o.model}; download big-lama.pt (see SKILL.md setup) or pass --telea')
    a = cv2.imread(o.inp)
    if a is None:
        sys.exit(f'cannot read image {o.inp}')
    m = build_mask(a, o.boxes, o.thresh, o.grow)
    if o.telea:
        res = cv2.inpaint(a, m, 6, cv2.INPAINT_TELEA)
    else:
        import torch, warnings
        warnings.filterwarnings('ignore', message='.*torch.jit.load.*')
        res = inpaint_lama(a, m, torch.jit.load(o.model, map_location='cpu').eval())
    cv2.imwrite(o.out, res)
    cv2.imwrite(o.out.rsplit('.', 1)[0] + '_mask.png', m)
    print('saved', o.out)


if __name__ == '__main__':
    main()
