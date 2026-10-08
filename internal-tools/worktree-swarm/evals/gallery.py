#!/usr/bin/env python3
"""Build a side-by-side gallery of a visual case's runs: reference vs with-skill vs without-skill.

    python3 evals/gallery.py evals/results/physics1 <out_dir>                    # physics-scene
    python3 evals/gallery.py evals/results/rt1 <out_dir> --case raytracer

Writes <out_dir>/index.html plus the images it shows. Needs Pillow for the pixel comparison
(skipped without it). The reference images are rendered from <case>/reference/.
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
TOL = 6              # per-channel tolerance for "same pixel"


def _physics_stats(m):
    ok = bool(m) and m.get("finite") and m.get("energy_max_ratio", 9) <= 1.02 and m.get("max_penetration", 9) <= 0.03
    return [("Physics", "in bounds" if ok else "out of bounds", "good" if ok else "bad"),
            ("Energy peak / start", m.get("energy_max_ratio", "-"), ""),
            ("Energy end (J)", m.get("energy_end", "-"), ""),
            ("Deepest overlap", f"{m.get('max_penetration', '-')} m", "")]


def _rt_stats(m):
    return [("Primitives", m.get("primitives", "-"), ""), ("Render time", f"{m.get('seconds', '-')} s", "")]


CASES = {
    "physics-scene": {
        "package": "ballpit", "command": "make_movie.py", "metrics": "metrics.json", "stats": _physics_stats,
        "images": [("final.png", "Final frame, t = 2.5 s"), ("sheet.png", "8 frames, t = 0 to 2.5 s")],
        "title": "Ballpit Swarm Test", "eyebrow": "worktree-swarm eval · physics-scene",
        "lede": "Twenty balls stacked in a pyramid, hit by a heavy cue ball, simulated for 2.5 seconds and "
                "ray-traced. The repo was missing seven modules: integrator, walls, collisions, camera, renderer, "
                "scene and contact sheet. Each run had an Opus session build them from the same spec, three times "
                "with the worktree-swarm skill and three times without it.",
        "notes": "<p><strong>Match</strong> is the share of pixels within ±{tol} per channel of the reference image. "
                 "The final frame comes after 600 steps of colliding balls, a chaotic system, so builds that differ "
                 "only in floating-point order can end with balls in different places; the energy and overlap "
                 "figures say whether the physics is right.</p>",
    },
    "raytracer": {
        "package": "rt", "command": "render.py", "metrics": "metrics.json", "stats": _rt_stats,
        "images": [("final.png", "Final render, 400 × 300"), ("views.png", "Four orbit views")],
        "title": "Tinyrt Swarm Test", "eyebrow": "worktree-swarm eval · raytracer",
        "lede": "A Whitted-style ray tracer with mirror, glass, marble and noise materials, a triangle-mesh torus, "
                "icosphere and cylinder, a loaded OBJ gem and a BVH. The repo was missing thirteen substantial "
                "modules. Each run had an Opus session build them from the same spec, three times with the "
                "worktree-swarm skill and three times without it. The render is deterministic, so a correct build "
                "matches the reference pixel for pixel.",
        "notes": "<p><strong>Match</strong> is the share of pixels within ±{tol} per channel of the reference "
                 "image. Ray tracing here is deterministic, so anything below about 99% points at a real "
                 "difference in some module: a formula, a normal, a texture, a refraction step.</p>",
    },
}

try:
    from PIL import Image
except ImportError:  # pixel match columns show "-"
    Image = None


def render_reference(case, cfg, dest):
    src = EVALS / case
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["bash", str(src / "fixture.sh")], cwd=d, check=True, capture_output=True)
        shutil.copytree(src / "reference" / cfg["package"], Path(d) / cfg["package"], dirs_exist_ok=True)
        subprocess.run([sys.executable, cfg["command"]], cwd=d, check=True, capture_output=True)
        for f, _ in cfg["images"]:
            shutil.copy(Path(d) / "out" / f, dest / f"reference-{f}")
        shutil.copy(Path(d) / "out" / cfg["metrics"], dest / "reference-metrics.json")
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


def collect(case, cfg, results, dest):
    runs = []
    for run_dir in sorted((results / case).iterdir()):
        r = json.loads((run_dir / "result.json").read_text())
        repo = (run_dir / "repo").resolve()
        name = f"{r['arm']}-{r['run']}"
        out = repo / "out"
        imgs = {}
        for f, _ in cfg["images"]:
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
        runs.append({
            "name": name, "arm": r["arm"], "run": r["run"], "score": r["score"], "cost": r["cost_usd"],
            "seconds": r["seconds"], "graders": r["graders"], "imgs": imgs, "metrics": metrics,
            "tests": next((l for l in check.splitlines() if l.startswith("CHECK RESULT")), "no check-output.txt"),
            "models": [{"role": k[0], "model": k[1], "effort": k[2], "n": n} for k, n in sorted(models.items())],
            "match": {f: match(out / f, dest / f"reference-{f}") for f, _ in cfg["images"]},
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


def card(cfg, run, notes):
    m = run["metrics"] or {}
    note = notes.get(run["name"])
    note_html = f'<p class="note">{html.escape(note)}</p>' if note else ""
    ok_tests = "PASS" in run["tests"]
    imgs = run["imgs"]
    pics = "".join(
        f'<figure><img src="{html.escape(imgs[f])}" alt="{label} for {run["name"]}" loading="lazy">'
        f"<figcaption>{label}</figcaption></figure>"
        for f, label in cfg["images"] if f in imgs)
    stats = "".join(f'<div><dt>{html.escape(str(k))}</dt><dd class="{c}">{html.escape(str(v))}</dd></div>'
                    for k, v, c in cfg["stats"](m))
    stats += "".join(f'<div><dt>Match, {html.escape(label.split(",")[0].lower())}</dt><dd>{pct(run["match"][f])}</dd></div>'
                     for f, label in cfg["images"])
    if not pics:
        pics = '<p class="missing">No images were rendered.</p>'
    return f"""
<article class="run">
  <header><h3>Run {run['run']}</h3><span class="score">score {run['score']:.2f}</span></header>
  {pics}
  <dl class="stats">
    <div><dt>Tests</dt><dd class="{'good' if ok_tests else 'bad'}">{html.escape(run['tests'].replace('CHECK RESULT: ', ''))}</dd></div>
    {stats}
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
        weight = next(g["weight"] for g in runs[0]["graders"] if g["name"] == n)
        label = html.escape(n) + (' <span class="unscored">not scored</span>' if weight == 0 else "")
        rows.append(f"<tr><th scope=\"row\">{label}</th>{''.join(cells)}</tr>")
    return "\n".join(rows)


def page(cfg, ref, runs, notes):
    def arm_stats(arm):
        ar = [r for r in runs if r["arm"] == arm]
        return (sum(r["score"] for r in ar) / len(ar), sum(r["seconds"] for r in ar) / len(ar),
                sum(r["cost"] for r in ar) / len(ar))
    ws, wt, wc = arm_stats("with")
    ns, nt, nc = arm_stats("without")
    with_cards = "".join(card(cfg, r, notes) for r in runs if r["arm"] == "with")
    without_cards = "".join(card(cfg, r, notes) for r in runs if r["arm"] == "without")
    ref_figs = "".join(f'<figure><img src="reference-{f}" alt="Reference: {html.escape(label)}">'
                       f"<figcaption>{html.escape(label)}</figcaption></figure>" for f, label in cfg["images"])
    ref_stats = ", ".join(f"{k.lower()} {v}" for k, v, _ in cfg["stats"](ref))
    return (EVALS / "gallery_template.html").read_text().format(
        title=cfg["title"], eyebrow=cfg["eyebrow"], lede=cfg["lede"], ref_figs=ref_figs, ref_stats=ref_stats,
        case_notes=cfg["notes"].format(tol=TOL),
        with_score=f"{ws:.2f}", with_time=f"{wt:.0f}", with_cost=f"{wc:.2f}",
        without_score=f"{ns:.2f}", without_time=f"{nt:.0f}", without_cost=f"{nc:.2f}",
        with_cards=with_cards, without_cards=without_cards, grader_rows=grader_table(runs))


def main():
    args = sys.argv[1:]
    case = "physics-scene"
    if "--case" in args:
        i = args.index("--case")
        case = args[i + 1]
        del args[i:i + 2]
    cfg = CASES[case]
    results, dest = Path(args[0]), Path(args[1])
    dest.mkdir(parents=True, exist_ok=True)
    ref = render_reference(case, cfg, dest)
    runs = collect(case, cfg, results, dest)
    (dest / "runs.json").write_text(json.dumps(runs, indent=2))
    # optional hand-written findings per run, e.g. {"with-3": "..."}
    notes_file = results / "notes.json"
    notes = json.loads(notes_file.read_text()) if notes_file.exists() else {}
    (dest / "index.html").write_text(page(cfg, ref, runs, notes))
    print(f"{len(runs)} runs -> {dest / 'index.html'}")


if __name__ == "__main__":
    main()
