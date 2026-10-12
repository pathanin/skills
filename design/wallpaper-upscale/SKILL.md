---
name: wallpaper-upscale
description: Manual-only local wallpaper upscale, invoked with /wallpaper-upscale. Turns an image, YouTube thumbnail or video frame into a high-res desktop wallpaper on this Mac - finds the best source, AI-upscales it on the Apple GPU (IllustrationJaNai for art, RealPLKSR for photos), optionally removes logos, and crops to the screen.
argument-hint: "[image path or YouTube URL, optional screen size WxH, remove logos?]"
disable-model-invocation: true
---

# Wallpaper upscale (local, for Claude Code on macOS)

Everything runs on this Mac. Bundled files:
- `${CLAUDE_SKILL_DIR}/scripts/match.py` - scores every video frame against a thumbnail
- `${CLAUDE_SKILL_DIR}/scripts/upscale.py` - tiled upscale with any spandrel model file (scale read from the model), uses the Apple GPU (MPS) when available, optional `--fit WxH` crop
- `${CLAUDE_SKILL_DIR}/scripts/test_upscale.py` - tests for upscale.py (`PY -m unittest discover -s "${CLAUDE_SKILL_DIR}/scripts"`)
- `${CLAUDE_SKILL_DIR}/scripts/remove_logo.py` - inpaints logos out by bounding box

## 0. One-time setup (check, don't redo)

The skill folder is a plugin cache snapshot that is replaced on every update, so keep the venv and models outside it, in `~/.cache/wallpaper-upscale`. If `~/.cache/wallpaper-upscale/.venv/bin/python` doesn't exist, create it:
```
mkdir -p ~/.cache/wallpaper-upscale/models
python3 -m venv ~/.cache/wallpaper-upscale/.venv
~/.cache/wallpaper-upscale/.venv/bin/pip install torch spandrel opencv-python-headless pillow numpy
```
Below, `PY` means `~/.cache/wallpaper-upscale/.venv/bin/python`.

Also needed: `ffmpeg`/`ffprobe` and `yt-dlp` (`brew install ffmpeg yt-dlp` if `which` finds them missing).

Models live in `~/.cache/wallpaper-upscale/models/`; set `MD=~/.cache/wallpaper-upscale/models` in each shell command that uses `$MD` below. Download each one the first time it's needed, and check its sha256 with `shasum -a 256`; if a hash doesn't match, delete the file and stop.
- **Anime/illustration art (default): `4x_IllustrationJaNai_V3detail_FDAT_XL_27k_bf16.safetensors`.** It ships inside a 318 MB zip with other models; extract only this file, then delete the zip:
  ```
  curl -L -o "$MD/v3detail.zip" https://github.com/the-database/MangaJaNai/releases/download/3.0.0/IllustrationJaNai_V3detail.zip
  unzip -j "$MD/v3detail.zip" 4x_IllustrationJaNai_V3detail_FDAT_XL_27k_bf16.safetensors -d "$MD" && rm "$MD/v3detail.zip"
  ```
  sha256 `fbafec1f5a126c251de8a21e177e5a710ba2e75c7fd88fe989eb8df0508790c9`.
- **Photos (default): `4xNomosWebPhoto_RealPLKSR.safetensors`**, best for web/social JPEGs:
  `curl -L -o "$MD/4xNomosWebPhoto_RealPLKSR.safetensors" https://github.com/Phhofm/models/releases/download/4xNomosWebPhoto_RealPLKSR/4xNomosWebPhoto_RealPLKSR.safetensors`
  sha256 `9be0228f98156a100d6636d99b373ed2785b999723f9adc4cca504329ab157f2`.
- Optional models; download one only when the user asks for it or its case applies:
  - Clean, uncompressed camera photos (RAW exports, PNG, high-quality JPEG with no visible block artifacts): `4xNomos2_hq_dat2.pth`, about 10x slower than RealPLKSR. On web JPEGs it magnifies 8x8 compression blocks, so don't use it there.
    `curl -L -o "$MD/4xNomos2_hq_dat2.pth" https://github.com/Phhofm/models/releases/download/4xNomos2_hq_dat2/4xNomos2_hq_dat2.pth`, sha256 `1f2be2b4786b5031776aed90e1818564f5576ab1e44da9355c7f3788ea25bdea`.
  - Fast art preview, if the user wants speed over quality: `RealESRGAN_x4plus_anime_6B.pth` (about 15x faster than FDAT-XL, but it flattens gradients and shifts colours).
    `curl -L -o "$MD/RealESRGAN_x4plus_anime_6B.pth" https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth`, sha256 `f872d837d3c90ed2e05227bed711af5671a6fd1c9f7d7e91c911a61f155e99da`.

The JaNai and Nomos2 models were picked in a local benchmark (LPIPS/DISTS against ground truth plus visual crops) over Real-ESRGAN, APISR, AnimeSharpV4, SwinIR and DRCT. JaNai is licensed CC-BY-NC-SA: fine for personal wallpapers, not for commercial use.

Work in a temp folder (e.g. `mktemp -d`), not in the user's Downloads, until the final files are ready.

## 1. Get the source

- **Image file**: use it directly.
- **YouTube link**: download both the thumbnail and the video-only stream:
  ```
  yt-dlp --write-thumbnail --convert-thumbnails jpg --skip-download -o "$WORK/thumb" "<URL>"
  yt-dlp -f "bv*" -o "$WORK/video.%(ext)s" "<URL>"
  ```

## 2. If there is a video: look for a better frame first

A frame only beats the thumbnail if the video is higher-res than the thumbnail AND shows the full image cleanly.
1. `PY "${CLAUDE_SKILL_DIR}/scripts/match.py" video.* thumb.jpg` - a score above ~0.85 is a near-exact match; below ~0.6 the thumbnail is likely a separate illustration or an edited composite.
2. Either way, make 1 fps contact sheets and view them (Read the jpg):
   `ffmpeg -ss S -t 55 -i VIDEO -vf "fps=1,scale=320:-1,drawtext=text='%{pts\:hms\:S}':x=4:y=4:fontsize=18:fontcolor=yellow:box=1:boxcolor=black,tile=7x8" -frames:v 1 sheet.jpg`
   Zoom into promising spans at 5 fps.
3. If a clean full frame exists: `ffmpeg -ss T -i VIDEO -frames:v 1 frame.png` and use it. Otherwise use the thumbnail and tell the user why (close-up pans only, title text over the full shot, etc.).

## 3. Optional: remove logos (before upscaling)

View the image, estimate each logo's box in original-resolution pixels, then:
`PY "${CLAUDE_SKILL_DIR}/scripts/remove_logo.py" src.jpg clean.png x0,y0,x1,y1 x0,y0,x1,y1`
Check `clean_mask.png` covers the logo and crop-view the patched areas. Inpainting is fine over smoke/sky/flat areas and smudges over detailed art - say so. Keep a with-logo version too.

## 4. Upscale and fit

Art: `PY "${CLAUDE_SKILL_DIR}/scripts/upscale.py" "$MD/4x_IllustrationJaNai_V3detail_FDAT_XL_27k_bf16.safetensors" clean.png out.jpg [--fit 2560x1664]`
Photos: the same command with `"$MD/4xNomosWebPhoto_RealPLKSR.safetensors"`.
- Expect FDAT-XL to take about 2 minutes per input megapixel on an M-series Mac; RealPLKSR takes about 10 seconds per megapixel. For inputs over 1 MP, run the upscale in the background and tell the user the expected wait.
- Ask for (or detect with `system_profiler SPDisplaysDataType | grep Resolution`) the screen resolution and pass `--fit`; otherwise keep the 4x 16:9 output.
- Verify: side-by-side crop of a face/detailed area, bicubic vs upscaled, and look at it.

## 5. Deliver

Save to `~/Downloads/<Subject>_wallpaper_<W>x<H>.jpg` (and `..._with_logo.jpg` if relevant). Reply briefly: where the files are, which source and model were used and why, and any visible artifacts.
To set it as the wallpaper only if the user asks:
`osascript -e 'tell application "System Events" to tell every desktop to set picture to "/full/path.jpg"'`
