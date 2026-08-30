---
name: jpeg-concat
description: >
  Concatenate (join/stitch/combine) JPEG images side-by-side or top-to-bottom while
  matching the original encoding parameters (quality level and chroma subsampling) so
  the output file size stays close to the sum of the inputs. Use this skill whenever
  the user wants to join, merge, stitch, combine, or concatenate image files — even if
  they say "put these next to each other", "stack these photos", or just "combine these
  jpgs". Also trigger when the user wants to batch-process a folder of images for
  concatenation. The key value is avoiding the large file-size blowup that happens when
  naive re-encoding uses wrong quality settings.
---

# JPEG Concatenation

## What this skill does

Joins 2+ JPEG images into one by:
1. Trying a **lossless DCT-level path** via `jpegtran -drop` (when conditions are met — see below)
2. Falling back to a **Pillow re-encode path** using the source's exact quantization tables (not a quality estimate) + detected chroma subsampling

This avoids the common mistake of re-encoding at quality 100 (which inflates the file to 2–3× the combined size) or using the wrong subsampling setting.

## How to use the bundled script

The script `concat_jpeg.py` handles everything. Call it via bash:

```bash
python3 <skill-dir>/concat_jpeg.py \
  img1.jpg img2.jpg [img3.jpg ...] \
  [--output out.jpg] \
  [--direction horizontal|vertical|auto] \
  [--order auto|as-given]
```

The script prints the encoding mode used and a size summary.

## Encoding paths (automatic, no flags needed)

### Lossless (jpegtran -drop)
Activated automatically when all of the following hold:
- `jpegtran` (libjpeg-turbo) is in PATH
- All inputs are JPEG with **identical chroma subsampling**
- The perpendicular image dimension and every join offset are **MCU-aligned** (multiple of 8 px for 4:4:4, 16 px for 4:2:0)

When active: DCT blocks are copied directly — no pixel decode, no re-encode. Output is reported as `lossless (jpegtran DCT)`. Size ratio is ~1.00×.

### Exact-table re-encode (Pillow fallback)
Used when lossless conditions are not met. Passes `img.quantization` (the source's actual quantization tables as parsed by libjpeg) directly to `canvas.save(qtables=...)` instead of a rounded quality integer. Output is reported as `quality≈N (exact source tables)`. Size ratio is typically 1.01–1.06×.

## Auto-detection (both on by default — never ask the user)

- **Order (2 images, numpy available)**: edge-color seam matching — tries all order × direction combinations, picks the lowest mean-absolute-difference across the touching edges. Prints scores so the choice is auditable.
- **Order (3+ images or no numpy)**: natural sort on all numeric runs in the filename (left to right as a tuple), then EXIF DateTimeOriginal, then file mtime.
- **Direction (2 images, numpy available)**: chosen by the same seam-score comparison.
- **Direction (3+ images or no numpy)**: majority orientation — portrait (height ≥ width) majority → horizontal; landscape majority → vertical.

Pass `--order as-given` or `--direction horizontal/vertical` only if the user explicitly overrides.

## Workflow

1. **Identify the files** — from the user's message, the mounted folder, or glob patterns they describe (e.g., "all jpgs in this folder").

2. **Run the script** — pass all images for a given pair/group. Order and direction are determined automatically; do not ask the user about either.

3. **Report the result** — show the size summary the script prints and present the output file.

## Edge cases

- **Different dimensions**: Images are pasted onto a canvas sized to fit all of them. Gaps are filled with black. If the user seems to care about this, mention it.
- **Mixed quality levels**: The script uses the encoding params from the first image. If files come from very different sources, ask the user which quality to target, or use the lower of the two.
- **Non-JPEG inputs**: The script works on any PIL-readable format but only detects JPEG params from JPEG files. PNG inputs use default quality 85 and output will be JPEG.
- **Many files / batch mode**: If the user wants to process pairs from a whole folder (e.g., "concat every odd+even file"), write a small loop around the script call.
- **Lossless path not taken**: The script falls back silently and reports which path ran. No action needed unless the user specifically needs lossless (in which case they may need to crop inputs to MCU boundaries first).

## Size expectation

- **Lossless path**: ~1.00× (DCT blocks copied verbatim; only the canvas fill areas differ)
- **Exact-table re-encode**: ~1.01–1.06× (unavoidable overhead from encoding a single larger image)

If the user sees >10% increase, the quality or subsampling likely didn't match — double-check the `Encoding:` line in the script output.
