---
name: wallpaper-upscale
description: Manual-only local wallpaper upscale, invoked with /wallpaper-upscale. Turns an image, YouTube thumbnail or video frame into a high-res desktop wallpaper on this Mac - finds the best source, AI-upscales it (Real-ESRGAN on the Apple GPU), optionally removes logos, and crops to the screen.
argument-hint: "[image path or YouTube URL, optional screen size WxH, remove logos?]"
disable-model-invocation: true
---

# Wallpaper upscale (local, for Claude Code on macOS)

Everything runs on this Mac. Bundled files:
- `${CLAUDE_SKILL_DIR}/scripts/match.py` - scores every video frame against a thumbnail
- `${CLAUDE_SKILL_DIR}/scripts/upscale.py` - tiled Real-ESRGAN upscale, uses the Apple GPU (MPS) when available, optional `--fit WxH` crop
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

Models live in `~/.cache/wallpaper-upscale/models/`. Download each one the first time it's needed:
- Anime/illustration art (the default):
  `curl -L -o ~/.cache/wallpaper-upscale/models/RealESRGAN_x4plus_anime_6B.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth`
  Its sha256 must be `f872d837d3c90ed2e05227bed711af5671a6fd1c9f7d7e91c911a61f155e99da` (`shasum -a 256`); if it isn't, delete it and stop.
- Photos:
  `curl -L -o ~/.cache/wallpaper-upscale/models/RealESRGAN_x4plus.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth`

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

`PY "${CLAUDE_SKILL_DIR}/scripts/upscale.py" ~/.cache/wallpaper-upscale/models/RealESRGAN_x4plus_anime_6B.pth clean.png out.jpg [--fit 2560x1664]`
- For photos, use `~/.cache/wallpaper-upscale/models/RealESRGAN_x4plus.pth` instead.
- Ask for (or detect with `system_profiler SPDisplaysDataType | grep Resolution`) the screen resolution and pass `--fit`; otherwise keep the 4x 16:9 output.
- Verify: side-by-side crop of a face/detailed area, bicubic vs upscaled, and look at it.

## 5. Deliver

Save to `~/Downloads/<Subject>_wallpaper_<W>x<H>.jpg` (and `..._with_logo.jpg` if relevant). Reply briefly: where the files are, which source was used and why, and any visible artifacts.
To set it as the wallpaper only if the user asks:
`osascript -e 'tell application "System Events" to tell every desktop to set picture to "/full/path.jpg"'`
