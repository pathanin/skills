"""Find a font family's Regular and Bold files on this machine, and its "normal" line height.

    python fonts.py "IBM Plex Sans Thai"      # prints the files it would bundle
"""
import os
import sys
from pathlib import Path

DIRS = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
        Path.home() / "Library" / "Fonts", Path("/Library/Fonts"), Path("/usr/share/fonts"), Path.home() / ".fonts"]


def _names(path):
    from fontTools.ttLib import TTFont
    f = TTFont(str(path), lazy=True, fontNumber=0)
    nm = f["name"]
    fam = nm.getDebugName(16) or nm.getDebugName(1)
    sub = (nm.getDebugName(17) or nm.getDebugName(2) or "").lower()
    weight = f["OS/2"].usWeightClass if "OS/2" in f else 400
    italic = "italic" in sub or "oblique" in sub
    return fam, sub, weight, italic


def find(family):
    """{'regular': path, 'bold': path} for the family (either may be missing)."""
    want = family.strip().lower()
    hits = []
    for d in DIRS:
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.suffix.lower() not in (".ttf", ".otf"):
                continue
            try:
                fam, sub, weight, italic = _names(p)
            except Exception:
                continue
            if fam and fam.strip().lower() == want and not italic:
                hits.append((weight, sub, p))
    out = {}
    reg = [h for h in hits if h[1] in ("regular", "normal", "book", "roman")] or [h for h in hits if h[0] == 400]
    bold = [h for h in hits if h[1] == "bold"] or [h for h in hits if h[0] == 700]
    if reg: out["regular"] = reg[0][2]
    if bold: out["bold"] = bold[0][2]
    return out


def line_normal(path):
    """CSS 'normal' line height of the font as a multiple of the font size (hhea metrics, as Chromium uses)."""
    from fontTools.ttLib import TTFont
    f = TTFont(str(path), lazy=True)
    h, upm = f["hhea"], f["head"].unitsPerEm
    return round((h.ascent - h.descent + h.lineGap) / upm, 3)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    r = find(sys.argv[1])
    print(r)
    if r.get("regular"): print("line-height normal:", line_normal(r["regular"]))
