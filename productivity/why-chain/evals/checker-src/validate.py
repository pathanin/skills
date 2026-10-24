import json, subprocess, sys, time
from pathlib import Path
E = Path(sys.argv[1])
reps = {"s2": 2, "s6": 3}
rows = []
for s in sorted(p.name for p in (E / "scenarios").iterdir() if p.is_dir()):
    sd = E / "scenarios" / s
    variants = [(v, sd / v) for v in ("fixture", "reference", "naive") if (sd / v).is_dir()]
    vd = E / "validation" / s
    if vd.is_dir():
        variants += [(f"val:{p.name}", p) for p in sorted(vd.iterdir()) if p.is_dir()]
    for name, path in variants:
        outs = []
        for _ in range(reps.get(s, 1)):
            t = time.time()
            p = subprocess.run([sys.executable, str(sd / "check.py"), str(path)], capture_output=True, text=True, timeout=300)
            try:
                d = json.loads(p.stdout.strip().splitlines()[-1])
            except Exception:
                d = {"pass": None, "score": None, "details": {"raw": p.stdout[-300:] + p.stderr[-300:]}}
            outs.append((d["pass"], d["score"], round(time.time() - t, 1), d["details"]))
        rows.append((s, name, outs))
        print(s, name, [(o[0], o[1], f"{o[2]}s") for o in outs], flush=True)
        if any(o[3].get("checker_error") or o[3].get("error") for o in outs):
            print("   ", json.dumps(outs[0][3])[:600])
