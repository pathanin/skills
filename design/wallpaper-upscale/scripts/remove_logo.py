"""Inpaint logos out of an image (run BEFORE upscaling).
Usage: remove_logo.py IN OUT x0,y0,x1,y1 [x0,y0,x1,y1 ...] [--thresh 170]
Masks bright-white and orange/accent pixels inside each box, dilates, Telea-inpaints.
Also writes OUT_mask.png so you can check what was masked."""
import sys, cv2, numpy as np
args = [s for s in sys.argv[1:] if not s.startswith('--')]
thr = 170
if '--thresh' in sys.argv: thr = int(sys.argv[sys.argv.index('--thresh') + 1]); args.remove(str(thr))
inp, outp, boxes = args[0], args[1], [tuple(map(int, b.split(','))) for b in args[2:]]
a = cv2.imread(inp)
b, g, r = [a[..., i].astype(int) for i in range(3)]
hit = (np.minimum(np.minimum(r, g), b) > thr) | ((r > 180) & (g < 150) & (b < 100) & (r - g > 60))
m = np.zeros(a.shape[:2], np.uint8)
for x0, y0, x1, y1 in boxes:
    m[y0:y1, x0:x1][hit[y0:y1, x0:x1]] = 255
m = cv2.dilate(m, np.ones((5, 5), np.uint8))
cv2.imwrite(outp, cv2.inpaint(a, m, 6, cv2.INPAINT_TELEA))
cv2.imwrite(outp.rsplit('.', 1)[0] + '_mask.png', m)
print('saved', outp)
