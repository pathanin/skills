# code-animation evals

How to run the `code-animation` eval suite, and how to read the result.

## What the suite tests

Three cases, each a real request with real materials. Each one exercises a different path through the skill.

| Case | Materials | Right outcome |
|---|---|---|
| `logo-sting` | An Illustrator-style SVG logo (shared `.cls-*` classes, a gradient id), brand guidelines ("calm, nothing bounces", logo don'ts), the wordmark font file | A ~4 s MP4 plus a transparent `.mov` or `.webm`; the supplied font loaded; calm motion, no bounce; the logo ends undistorted and holds; reviewed with sheets or stills and QA |
| `boxo-walk` | A raster PNG model sheet of a robot (front and side views, expressions, palette chips, notes) and a vague format ("short for Instagram") | Boxo rebuilt from measured pixels with exact hex values, checked with a `--ref` overlay, a walk-on + notice + wave in a 1080-wide Instagram format, the walk reviewed with `study`, an MP4 delivered |
| `radio-loop` | A 7.2 s music loop at 100 BPM, and a show name | The track analysed with `render.js audio`, a loop a whole number of beats long, the seam checked with `qa --loop`, a GIF plus an MP4 with the track muxed in |

The graders check that the skill fired, that the pipeline's own tools did the work (probe, stills or sheet, study, qa, audio), what the scene file contains (exact palette, format, font loading), and, with a judge, what the final reply delivers.

## Run it with the harness

From the skill directory:

```bash
cd design/code-animation
claude plugin eval . --runs 1 --ablation none --scaffold --trust-plugin \
  --allow-tools Write Edit Bash -j 3 --keep-temp
```

- `--ablation none`: the point of the skill is to save the agent from rebuilding the pipeline, not to beat a baseline, so skip the no-plugin arm.
- `--scaffold`: run each case's `fixture.sh` to build its materials.
- Each run is a full animation job: expect 20–45 minutes and a few dollars per case.

The agent needs Bash, Node with Playwright, a Chromium, and a full ffmpeg inside the eval's sandbox (see `SKILL.md`, Setup). Check first:

```bash
claude -p "Run this and print the raw output: echo ok && NODE_PATH=\$(npm root -g) node -e \"require('playwright').chromium.launch().then(b=>{console.log(b.version());return b.close()})\"" \
  --allowedTools Bash --settings '{"sandbox":{"enabled":true,"failIfUnavailable":true}}'
```

## Run it without the harness (containers)

Inside some containers the harness cannot sandbox Bash: every command fails with `apply-seccomp: write /proc/self/uid_map: Operation not permitted`, even with `enableWeakerNestedSandbox`, because the harness runs the agent with its own home directory. The agent then reports that Bash is broken and stops, so the run measures nothing.

There, run each case as a fresh `claude -p` session with the plugin loaded. The container is the isolation:

```bash
evals/run-local.sh boxo-walk            # scaffolds, runs the prompt, saves trace.jsonl
python3 evals/grade-local.py boxo-walk  # applies the tool_used and regex graders; prints the final reply for the llm graders
```

Runs go to `$TMPDIR/code-animation-evals/<case>/`, with the agent's files in `work/`. Judge the `llm` graders by reading the final reply against each grader's text. The three cases can run in parallel.

## Read the result

**First, rule out an environment failure.** If most checks fail, read the final reply. If it says Bash, the browser or ffmpeg was unavailable, the run is invalid.

**When a check fails**, look at what the agent actually ran before changing the skill:

- **The skill is wrong:** the agent skipped a step the skill asks for, or had to invent something the pipeline should provide. Fix `SKILL.md`, a reference, or `assets/`.
- **The grader is wrong:** the agent did the right thing another way (for example, reviewed with `sheet` where the grader expected `stills`). Fix the grader.

The traces are also the best source of engine improvements: every time a fresh agent writes a helper script, the pipeline is missing a tool.

## Results

Fresh `claude -p` sessions via `run-local.sh`, 1 run per case, 2026-09-27:

| Case | Automatic graders | Judge | Turns, cost | Notes |
|---|---|---|---|---|
| `logo-sting` | 6/6 | pass | 41, $1.15 | Loaded the real SVG and font, used `--set=alpha`, tuned the end hold after QA. The ProRes master was 266 MB, too big to send |
| `boxo-walk` | 6/6 | pass | 66, $2.38 | Faithful to the sheet (exact expressions, antenna lag, motion blur on the wave); frame 0 was empty, which is the thumbnail on Instagram |
| `radio-loop` | 6/6 | pass | 54, $1.37 | Exactly 12 beats, seam verified; the equalizer bars crossed a line of copy; the GIF was 13 MB at 640 px |

Round 2, after the first round's fixes, with a fourth case (`storyboard-ad`):

| Case | Automatic graders | Judge | Turns, cost | Notes |
|---|---|---|---|---|
| `logo-sting` | 6/6 | pass | 48, $1.46 | Chose `--codec=png` itself: a 35 MB lossless alpha master instead of 266 MB |
| `boxo-walk` | 4/6 | pass | 69, $2.28 | Exported a poster frame for the empty first frame, but skipped the `--ref` trace check and the `study`; guessed `M.ease.inOut.Sine`; passed `--bbox` twice and lost the first |
| `radio-loop` | 6/6 (after the grader fix) | pass | 43, $1.15 | Used `SCENE.audio` and `audio --json`; the old grader only accepted `--audio=` |
| `storyboard-ad` | 7/7 (after the grader fix) | fail | 85, $3.81 | Copy, palette and drop timing right, but it forced `--workers=1` with `--mblur=8`, the render outlived the Bash tool's 2-minute wait, and the session ended with the MP4 truncated at 8 s |

## Findings so far

Fresh sessions on these cases (2026-09-27) led to these changes:

- `radio-loop`: to make visuals pulse with the track, the agent wrote its own Python envelope extractor. `render.js audio --json` now writes per-frame `level`, `low` and `high` curves plus the beat grid.
- `boxo-walk`: the agent measured the head, torso and legs by slicing the front view with `--bbox`, and got the whole slice back. `--bbox` now takes the image's dominant colour as the background, so slices measure their part.
- All three: the skill fired from the natural prompt, without being named.
- `logo-sting`: ProRes 4444 is about 60 MB per second at 1080p. `video --codec=png` now writes a lossless PNG-in-MOV several times smaller.
- `radio-loop`: `video --colors=N` now caps a GIF's palette (13 MB → 6 MB at 32 colours); the sheet review now checks that nothing crosses text while it must be read.
- `boxo-walk`: delivery now covers the poster frame, because platforms use frame 0 as the thumbnail.
- `logo-sting`: QA reported two sub-pixel "jumps" (0.3) that the agent rightly dismissed; the jump floor is now 0.5.
- `boxo-walk` (round 2): a done-checklist now precedes the final render (trace check, `study` per key action, `sheet`, `qa`); unknown `M` and `M.ease` names throw with the real names listed; repeated list options accumulate.
- `storyboard-ad` (round 2): the final-render step now has you estimate the render time, keep the default workers, raise the Bash timeout, and never reply while a render runs; progress lines show the time remaining.
