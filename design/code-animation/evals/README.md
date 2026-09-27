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

## Findings so far

Fresh sessions on these cases (2026-09-27) led to these changes:

- `radio-loop`: to make visuals pulse with the track, the agent wrote its own Python envelope extractor. `render.js audio --json` now writes per-frame `level`, `low` and `high` curves plus the beat grid.
- `boxo-walk`: the agent measured the head, torso and legs by slicing the front view with `--bbox`, and got the whole slice back. `--bbox` now takes the image's dominant colour as the background, so slices measure their part.
- All three: the skill fired from the natural prompt, without being named.
