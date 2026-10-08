#!/usr/bin/env python3
"""Build a side-by-side gallery of physics-scene runs: reference vs with-skill vs without-skill.

    python3 evals/gallery.py evals/results/physics1 <out_dir>

Writes <out_dir>/index.html plus the images it shows. Needs Pillow for the pixel comparison
(skipped without it). The reference images are rendered from physics-scene/reference/.
"""
import html
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

EVALS = Path(__file__).resolve().parent
CASE = EVALS / "physics-scene"
FRAME = (200, 150)   # make_movie.py frame size
GUTTER = 2
TOL = 6              # per-channel tolerance for "same pixel"

try:
    from PIL import Image
except ImportError:  # pixel match columns show "-"
    Image = None


def render_reference(dest):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["bash", str(CASE / "fixture.sh")], cwd=d, check=True, capture_output=True)
        for f in (CASE / "reference" / "ballpit").glob("*.py"):
            shutil.copy(f, Path(d) / "ballpit")
        subprocess.run([sys.executable, "make_movie.py"], cwd=d, check=True, capture_output=True)
        for f in ("sheet.png", "final.png", "metrics.json"):
            shutil.copy(Path(d) / "out" / f, dest / f"reference-{f}")
    return json.loads((dest / "reference-metrics.json").read_text())


def match(a_path, b_path, box=None):
    """Share of pixels whose channels are all within TOL of the reference."""
    if Image is None or not a_path.exists():
        return None
    a, b = Image.open(a_path).convert("RGB"), Image.open(b_path).convert("RGB")
    if a.size != b.size:
        return 0.0
    if box:
        a, b = a.crop(box), b.crop(box)
    pa, pb = list(a.getdata()), list(b.getdata())
    same = sum(1 for x, y in zip(pa, pb) if max(abs(x[i] - y[i]) for i in range(3)) <= TOL)
    return same / len(pa)


def collect(results, dest):
    runs = []
    for run_dir in sorted((results / "physics-scene").iterdir()):
        r = json.loads((run_dir / "result.json").read_text())
        repo = (run_dir / "repo").resolve()
        name = f"{r['arm']}-{r['run']}"
        out = repo / "out"
        imgs = {}
        for f in ("sheet.png", "final.png"):
            if (out / f).exists():
                shutil.copy(out / f, dest / f"{name}-{f}")
                imgs[f] = f"{name}-{f}"
        metrics = json.loads((out / "metrics.json").read_text()) if (out / "metrics.json").exists() else None
        check = (repo / "check-output.txt").read_text() if (repo / "check-output.txt").exists() else ""
        models = Counter()
        for a in r["agents"]:
            if a["error"]:
                continue
            role = "builder" if a.get("isolation") == "worktree" else ("verifier" if a.get("effort") == "low" else "other")
            models[(role, a.get("model") or "the session's Opus (no model set)", a.get("effort"))] += 1
        frame0 = (GUTTER, GUTTER, GUTTER + FRAME[0], GUTTER + FRAME[1])
        runs.append({
            "name": name, "arm": r["arm"], "run": r["run"], "score": r["score"], "cost": r["cost_usd"],
            "seconds": r["seconds"], "graders": r["graders"], "imgs": imgs, "metrics": metrics,
            "tests": next((l for l in check.splitlines() if l.startswith("CHECK RESULT")), "no check-output.txt"),
            "models": [{"role": k[0], "model": k[1], "effort": k[2], "n": n} for k, n in sorted(models.items())],
            "match_frame0": match(out / "sheet.png", dest / "reference-sheet.png", frame0),
            "match_sheet": match(out / "sheet.png", dest / "reference-sheet.png"),
            "match_final": match(out / "final.png", dest / "reference-final.png"),
        })
    return runs


def pct(x):
    return "-" if x is None else f"{x * 100:.1f}%"


def agent_line(models):
    if not models:
        return "no subagents"
    parts = []
    for m in models:
        eff = f" ({m['effort']} effort)" if m["effort"] else ""
        parts.append(f"{m['n']} {m['role']}{'s' if m['n'] > 1 else ''} on {m['model']}{eff}")
    return ", ".join(parts)


def card(run, notes):
    m = run["metrics"] or {}
    note = notes.get(run["name"])
    note_html = f'<p class="note">{html.escape(note)}</p>' if note else ""
    ok_tests = "PASS" in run["tests"]
    phys_ok = bool(m) and m.get("finite") and m.get("energy_max_ratio", 9) <= 1.02 and m.get("max_penetration", 9) <= 0.03
    imgs = run["imgs"]
    pics = "".join(
        f'<figure><img src="{html.escape(imgs[f])}" alt="{label} for {run["name"]}" loading="lazy">'
        f"<figcaption>{label}</figcaption></figure>"
        for f, label in (("final.png", "Final frame, t = 2.5 s"), ("sheet.png", "8 frames, t = 0 to 2.5 s")) if f in imgs)
    if not pics:
        pics = '<p class="missing">No images were rendered.</p>'
    return f"""
<article class="run">
  <header><h3>Run {run['run']}</h3><span class="score">score {run['score']:.2f}</span></header>
  {pics}
  <dl class="stats">
    <div><dt>Tests</dt><dd class="{'good' if ok_tests else 'bad'}">{html.escape(run['tests'].replace('CHECK RESULT: ', ''))}</dd></div>
    <div><dt>Physics</dt><dd class="{'good' if phys_ok else 'bad'}">{'in bounds' if phys_ok else 'out of bounds'}</dd></div>
    <div><dt>Energy peak / start</dt><dd>{m.get('energy_max_ratio', '-')}</dd></div>
    <div><dt>Energy end (J)</dt><dd>{m.get('energy_end', '-')}</dd></div>
    <div><dt>Deepest overlap</dt><dd>{m.get('max_penetration', '-')} m</dd></div>
    <div><dt>Match, first frame</dt><dd>{pct(run['match_frame0'])}</dd></div>
    <div><dt>Match, final frame</dt><dd>{pct(run['match_final'])}</dd></div>
    <div><dt>Time, cost</dt><dd>{run['seconds']} s, ${run['cost']:.2f}</dd></div>
  </dl>
  {note_html}
  <p class="agents">{html.escape(agent_line(run['models']))}</p>
</article>"""


def grader_table(runs):
    names = [g["name"] for g in runs[0]["graders"]]
    rows = []
    for n in names:
        cells = []
        for arm in ("with", "without"):
            ar = [r for r in runs if r["arm"] == arm]
            p = sum(1 for r in ar for g in r["graders"] if g["name"] == n and g["passed"])
            cls = "good" if p == len(ar) else ("bad" if p == 0 else "mixed")
            cells.append(f'<td class="{cls}">{p}/{len(ar)}</td>')
        rows.append(f"<tr><th scope=\"row\">{html.escape(n)}</th>{''.join(cells)}</tr>")
    return "\n".join(rows)


def page(ref, runs, notes):
    def arm_stats(arm):
        ar = [r for r in runs if r["arm"] == arm]
        return (sum(r["score"] for r in ar) / len(ar), sum(r["seconds"] for r in ar) / len(ar),
                sum(r["cost"] for r in ar) / len(ar))
    ws, wt, wc = arm_stats("with")
    ns, nt, nc = arm_stats("without")
    with_cards = "".join(card(r, notes) for r in runs if r["arm"] == "with")
    without_cards = "".join(card(r, notes) for r in runs if r["arm"] == "without")
    return (EVALS / "gallery_template.html").read_text().format(
        ref_energy_end=ref["energy_end"], ref_pen=ref["max_penetration"], ref_ratio=ref["energy_max_ratio"],
        with_score=f"{ws:.2f}", with_time=f"{wt:.0f}", with_cost=f"{wc:.2f}",
        without_score=f"{ns:.2f}", without_time=f"{nt:.0f}", without_cost=f"{nc:.2f}",
        with_cards=with_cards, without_cards=without_cards, grader_rows=grader_table(runs), tol=TOL)


def main():
    results, dest = Path(sys.argv[1]), Path(sys.argv[2])
    dest.mkdir(parents=True, exist_ok=True)
    ref = render_reference(dest)
    runs = collect(results, dest)
    (dest / "runs.json").write_text(json.dumps(runs, indent=2))
    # optional hand-written findings per run, e.g. {"with-3": "..."}
    notes_file = results / "notes.json"
    notes = json.loads(notes_file.read_text()) if notes_file.exists() else {}
    (dest / "index.html").write_text(page(ref, runs, notes))
    print(f"{len(runs)} runs -> {dest / 'index.html'}")


if __name__ == "__main__":
    main()
