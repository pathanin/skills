"""Find a font family's Regular and Bold files on this machine, and its "normal" line height.

    python fonts.py "IBM Plex Sans Thai"      # prints the files it would bundle
"""
import os
import re
import sys
from collections import namedtuple
from pathlib import Path

if sys.platform == "win32":
    DIRS = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"]
elif sys.platform == "darwin":
    DIRS = [Path.home() / "Library" / "Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"),
            # fonts that come with Microsoft Office for Mac (Aptos, Calibri, ...)
            Path("/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts")]
else:
    DIRS = [Path.home() / ".local" / "share" / "fonts", Path.home() / ".fonts", Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts")]

# A font face on disk. index is the face number inside a .ttc collection (0 for .ttf/.otf).
Face = namedtuple("Face", "path index")


def _faces(path):
    """Face numbers in the file: one for .ttf/.otf, every member of a .ttc/.otc collection."""
    if path.suffix.lower() in (".ttc", ".otc"):
        from fontTools.ttLib import TTCollection
        return range(len(TTCollection(str(path), lazy=True).fonts))
    return range(1)


def _names(path, index=0):
    from fontTools.ttLib import TTFont
    f = TTFont(str(path), lazy=True, fontNumber=index)
    nm = f["name"]
    fam = nm.getDebugName(16) or nm.getDebugName(1)
    sub = (nm.getDebugName(17) or nm.getDebugName(2) or "").lower()
    weight = f["OS/2"].usWeightClass if "OS/2" in f else 400
    italic = "italic" in sub or "oblique" in sub
    return fam, sub, weight, italic


def find(family):
    """{'regular': Face, 'bold': Face} for the family (either may be missing)."""
    want = family.strip().lower()
    hits = []
    for d in DIRS:
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.suffix.lower() not in (".ttf", ".otf", ".ttc", ".otc"):
                continue
            try:
                for i in _faces(p):
                    fam, sub, weight, italic = _names(p, i)
                    if fam and fam.strip().lower() == want and not italic:
                        hits.append((weight, sub, Face(p, i)))
            except Exception:
                continue
    out = {}
    reg = [h for h in hits if h[1] in ("regular", "normal", "book", "roman")] or [h for h in hits if h[0] == 400]
    bold = [h for h in hits if h[1] == "bold"] or [h for h in hits if h[0] == 700]
    if reg: out["regular"] = reg[0][2]
    if bold: out["bold"] = bold[0][2]
    return out


def aat_only(face):
    """True for Apple fonts that shape only through AAT (morx) tables, e.g. Thonburi. Chrome's font
    sanitizer drops morx from @font-face fonts, so marks in complex scripts lose their positioning."""
    from fontTools.ttLib import TTFont
    f = TTFont(str(face.path), lazy=True, fontNumber=face.index)
    return "morx" in f and "GSUB" not in f and "GPOS" not in f


def bundle(face, dest):
    """Copy the face into the folder dest and return the file name. A face inside a .ttc collection is
    extracted to its own .ttf/.otf, because browsers load single fonts from @font-face."""
    import shutil
    dest = Path(dest)
    if face.path.suffix.lower() not in (".ttc", ".otc"):
        shutil.copy(face.path, dest / face.path.name)
        return face.path.name
    from fontTools.ttLib import TTFont
    f = TTFont(str(face.path), fontNumber=face.index)
    name = re.sub(r"[^\w.-]", "", f["name"].getDebugName(6) or "") or f"{face.path.stem}-{face.index}"
    name += ".otf" if "CFF " in f or "CFF2" in f else ".ttf"
    f.save(str(dest / name))
    return name


def line_normal(face):
    """CSS 'normal' line height of the font as a multiple of the font size (hhea metrics, as Chromium uses)."""
    from fontTools.ttLib import TTFont
    f = TTFont(str(face.path), lazy=True, fontNumber=face.index)
    h, upm = f["hhea"], f["head"].unitsPerEm
    return round((h.ascent - h.descent + h.lineGap) / upm, 3)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    r = find(sys.argv[1])
    print(r)
    if r.get("regular"): print("line-height normal:", line_normal(r["regular"]))
