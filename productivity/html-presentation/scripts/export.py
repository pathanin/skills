# -*- coding: utf-8 -*-
"""Export an HTML deck to an editable PowerPoint (with entrance animations) and/or PDF.

    python export.py DECK --pptx OUT.pptx [--pdf OUT.pdf] [--no-anim] [--render DIR] [--keep]
    python export.py DECK --pdf OUT.pdf

PPTX, stage 1 (python-pptx + lxml):
  * deck converted from a PPTX (deck.json "source"): each slide that still has its data-src is
    the source slide itself. Unchanged shapes keep their XML exactly (layouts, notes, clips,
    charts). Moved shapes get a new position. Re-texted shapes get their paragraphs rebuilt from the HTML
    with the shape's own paragraph/run properties as templates. Restyled, added or regrouped
    shapes are rebuilt by pptx_writer. Slides without a source (new, or a second copy of a
    source slide) are built from the HTML on the source's layout. Order follows the HTML; slides
    no longer in the HTML are dropped.
  * new deck: every slide is built from the HTML on a blank 16:9 presentation.
PPTX, stage 2 (PowerPoint through COM, export_anim.ps1): entrance animations in reading order,
  clips play on entry and loop, fonts embedded. Windows only; skipped with a notice elsewhere
  or when PowerPoint is missing.
PDF: headless Edge/Chrome prints index.html (one slide per page).
"""
import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.util import Emu

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import html_diff  # noqa: E402
import pptx_writer  # noqa: E402

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
A, P, R = ("{%s}" % NS[k] for k in ("a", "p", "r"))
PT = 4 / 3
WARN = []


def X(el, path): return etree._Element.xpath(el, path, namespaces=NS)   # bypass python-pptx's one-argument xpath()
def warn(msg): WARN.append(msg)


def hexcol(c):
    c = pptx_writer.color(c)
    return c[0] if c else ""


# ------------------------------------------------------------------ text rebuilt in place
def html_paragraphs(container):
    """[(pstyle, [(text, px, bold, colorhex, spacing_px, italic)])]; bullet spans are dropped (the pPr carries the bullet)"""
    out = []
    for p in container.xpath("./p"):
        ps = html_diff.style(p)
        spans = [s for s in p.xpath("./span") if "bu" not in (s.get("class") or "").split()] or ([p] if not p.xpath("./span") else [])
        runs = []
        for s in spans:
            st = {**ps, **(html_diff.style(s) if s is not p else {})}
            parts = []
            if s.text: parts.append(s.text)
            for ch in s:
                parts.append("\n" if ch.tag == "br" else ch.text_content())
                if ch.tail: parts.append(ch.tail)
            t = "".join(parts).replace("​", "")
            runs.append((t, pptx_writer.fpx(st.get("font-size")), st.get("font-weight") in ("700", "bold"), hexcol(st.get("color")),
                         pptx_writer.fpx(st.get("letter-spacing")) or 0.0, st.get("font-style") == "italic"))
        out.append((ps, runs))
    while out and not "".join(r[0] for r in out[-1][1]).strip(): out.pop()
    return out


def xml_par_sig(p):
    lp = X(p, "a:pPr/a:lnSpc/a:spcPts/@val")
    mt = X(p, "a:pPr/a:spcBef/a:spcPts/@val")
    al = (X(p, "a:pPr/@algn") or ["l"])[0]
    return ("%.2f" % (int(lp[0]) / 100 * PT) if lp else None, "%.2f" % (int(mt[0]) / 100 * PT) if mt and int(mt[0]) else None, al)


def html_par_sig(ps):
    lh = ps.get("line-height", "")
    mt = pptx_writer.fpx(ps.get("margin-top"))
    al = {"left": "l", "center": "ctr", "right": "r", "justify": "just"}.get(ps.get("text-align", "left"), "l")
    return ("%.2f" % pptx_writer.fpx(lh) if lh.endswith("px") else None, "%.2f" % mt if mt else None, al)


def run_sig(r):
    rp = (X(r, "a:rPr") or [None])[0]
    sz = int(rp.get("sz", "1800")) / 100 * PT if rp is not None and rp.get("sz") else None
    col = X(r, "a:rPr/a:solidFill/a:srgbClr/@val")
    return (round(sz, 1) if sz else None, rp is not None and rp.get("b") == "1", (col[0] if col else "").upper())


def rebuild_text(txBody, paras):
    old_ps = X(txBody, "a:p")
    old_runs = X(txBody, ".//a:r")
    for p in old_ps: txBody.remove(p)
    if not old_ps: old_ps = [etree.Element(A + "p")]
    for i, (ps, runs) in enumerate(paras):
        sig = html_par_sig(ps)
        tpl = next((p for p in old_ps if xml_par_sig(p) == sig), old_ps[min(i, len(old_ps) - 1)])
        np_ = etree.SubElement(txBody, A + "p")
        if X(tpl, "a:pPr"): np_.append(copy.deepcopy(X(tpl, "a:pPr")[0]))
        last = None
        for (t, px_, bold, col, spc, ital) in runs:
            want = (round(px_, 1) if px_ else None, bold, col)
            src = next((r for r in old_runs if run_sig(r) == want), None)
            if src is None: src = next((r for r in old_runs if run_sig(r)[:2] == want[:2]), None)
            if src is None and old_runs: src = old_runs[0]
            rpr = copy.deepcopy(X(src, "a:rPr")[0]) if src is not None and X(src, "a:rPr") else etree.Element(A + "rPr")
            if px_: rpr.set("sz", str(int(round(px_ / PT * 100))))
            rpr.set("b", "1" if bold else "0")
            if ital: rpr.set("i", "1")
            elif rpr.get("i"): rpr.set("i", "0")
            if spc: rpr.set("spc", str(int(round(spc / PT * 100))))
            elif "spc" in rpr.attrib: rpr.set("spc", "0")
            if col:
                for f in X(rpr, "a:solidFill"): rpr.remove(f)
                sf = etree.Element(A + "solidFill"); etree.SubElement(sf, A + "srgbClr").set("val", col)
                ln = X(rpr, "a:ln")
                (ln[0].addnext(sf) if ln else rpr.insert(0, sf))
            last = rpr
            for k, piece in enumerate(t.split("\n")):
                if k:
                    br = etree.SubElement(np_, A + "br"); br.append(copy.deepcopy(rpr))
                if piece:
                    r = etree.SubElement(np_, A + "r"); r.append(copy.deepcopy(rpr))
                    etree.SubElement(r, A + "t").text = piece
        if last is None:
            sz = int(round((pptx_writer.fpx(ps.get("font-size")) or 24) / PT * 100))
            etree.SubElement(np_, A + "endParaRPr").set("sz", str(sz))


# ------------------------------------------------------------------ shapes in the source XML
def find_by_id(tree, sid):
    hits = X(tree, f'.//p:cNvPr[@id="{sid}"]')
    return hits[0].getparent().getparent() if hits else None


def set_geom(el, g, sx, sy):
    left, top, w, h = g
    xf = X(el, "./p:spPr/a:xfrm | ./p:xfrm")
    if not xf: return False
    off, ext = X(xf[0], "a:off")[0], X(xf[0], "a:ext")[0]
    off.set("x", str(round(left * sx))); off.set("y", str(round(top * sy)))
    if w is not None: ext.set("cx", str(round(w * sx)))
    if h is not None and X(el, "./p:spPr"): ext.set("cy", str(round(h * sy)))
    return True


def in_group(el):
    return etree.QName(el.getparent()).localname == "grpSp"


def replay(slide, ch, writer, sx, sy):
    """apply one slide's HTML changes to its own XML; returns ids built anew"""
    tree = slide._element
    sp_tree = slide.shapes._spTree
    rebuild = []
    for d in ch["deleted"]:
        el = find_by_id(tree, d["id"])
        if el is not None: el.getparent().remove(el)
    for sid, (kinds, o, d) in ch["changed"].items():
        el = find_by_id(tree, sid)
        if el is None:
            warn(f"{d['name']}: not found in the source slide, rebuilt"); rebuild.append(d); continue
        if "style" in kinds or ("geom" in kinds and in_group(el)):
            el.getparent().remove(el); rebuild.append(d); continue
        if "geom" in kinds and not set_geom(el, d["geom"], sx, sy):
            el.getparent().remove(el); rebuild.append(d); continue
        if "text" in kinds:
            if d["tag"] == "table":
                cells = d["el"].xpath('.//div[contains(@class,"cell")]')
                tcs = [tc for tc in X(el, ".//a:tc") if tc.get("hMerge") != "1" and tc.get("vMerge") != "1"]
                if len(cells) != len(tcs):
                    el.getparent().remove(el); rebuild.append(d); continue
                for hc, tc, bc in zip(cells, tcs, o["el"].xpath('.//div[contains(@class,"cell")]')):
                    if html_diff.runs(hc) != html_diff.runs(bc):
                        tb = X(tc, "a:txBody")
                        if tb: rebuild_text(tb[0], html_paragraphs(hc))
            else:
                tb = X(el, "p:txBody")
                tx = d["el"].xpath('./div[contains(@class,"tx")]')
                if not tb or not tx:
                    el.getparent().remove(el); rebuild.append(d); continue
                rebuild_text(tb[0], html_paragraphs(tx[0]))
    return rebuild


def place(sp_tree, new_el, prev_ids):
    """move a newly built shape to sit right after the nearest earlier HTML sibling that exists in the XML"""
    for sid in reversed(prev_ids):
        anchor = find_by_id(sp_tree, sid) if sid else None
        if anchor is not None and anchor.getparent() is sp_tree:
            anchor.addnext(new_el); return
    first = X(sp_tree, "./p:grpSpPr")
    (first[0].addnext(new_el) if first else sp_tree.insert(0, new_el))


def build_into(slide, shapes_to_build, cur, writer):
    """build the given HTML shapes on the slide at their HTML stacking position"""
    sp_tree = slide.shapes._spTree
    want = {id(d["el"]) for d in shapes_to_build}
    prev = []
    nid = max([int(i) for i in X(slide._element, ".//p:cNvPr/@id")] + [1]) + 1
    for d in cur:
        if id(d["el"]) in want:
            try:
                new_el = writer.build(slide, d["el"])
            except Exception as e:                       # noqa: BLE001
                warn(f"s{slide_no(slide)} {d['name']}: could not export ({e})"); continue
            X(new_el, ".//p:cNvPr")[0].set("id", str(nid)); nid += 1
            new_el.getparent().remove(new_el)
            place(sp_tree, new_el, prev)
            prev.append(X(new_el, ".//p:cNvPr/@id")[0])
        elif d["id"]:
            prev.append(d["id"])


def slide_no(slide):
    try: return list(slide.part.package.presentation_part.presentation.slides).index(slide) + 1
    except Exception: return "?"


def set_bg(slide, css):
    c = pptx_writer.color(css)
    if css and css.startswith("linear-gradient"):
        pptx_writer.Writer.set_fill(slide.background.fill, css, warn, "slide background")
    elif c:
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = pptx_writer.RGBColor.from_string(c[0])


def blank_layout(prs):
    lays = [l for m in prs.slide_masters for l in m.slide_layouts]
    by_name = [l for l in lays if l.name.lower() in ("blank", "ว่างเปล่า")]
    return by_name[0] if by_name else min(lays, key=lambda l: len(l.placeholders))


def drop_unused_media_rels(slide):
    xml = etree.tostring(slide._element).decode()
    for rid, rel in list(slide.part.rels.items()):
        if any(k in rel.reltype for k in ("/image", "/video", "/media")) and f'"{rid}"' not in xml:
            slide.part.drop_rel(rid)


def drop_stale_timing(slide, n):
    """The source slide's animations survive stage 1, but an effect whose shape was deleted or rebuilt
    (new id) points at nothing, and PowerPoint then offers to repair the file. Drop the slide's timing
    in that case; stage 2 (Windows) re-adds animation anyway."""
    t = X(slide._element, "./p:timing")
    if not t: return
    ids = set(X(slide._element, "./p:cSld/p:spTree//p:cNvPr/@id"))
    if any(sp not in ids for sp in X(t[0], ".//p:spTgt/@spid")):
        t[0].getparent().remove(t[0])
        warn(f"s{n}: source animations dropped (an animated shape was deleted or rebuilt)")


def stage1(deck, out_pptx):
    meta = json.loads((deck / "deck.json").read_text(encoding="utf-8"))
    font = meta.get("font", {})
    results = html_diff.diff(deck)
    src = meta.get("source")
    prs = Presentation(str(deck / src)) if src else Presentation()
    if not src:
        prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    sx, sy = prs.slide_width / 1280, prs.slide_height / 720
    writer = pptx_writer.Writer(deck, font.get("family", "Arial"), font.get("line_normal", 1.2), sx, sy,
                                lambda m: warn(m))
    orig = list(prs.slides)
    order = []
    for r in results:
        if r["src"] is not None:
            slide = orig[r["src"] - 1]
            rb = replay(slide, r["ch"], writer, sx, sy)
            bg_now, bg_was = (html_diff.style(x).get("background") for x in (r["sec"], r["base_sec"]))
            if bg_now != bg_was:
                if bg_now and "url(" in bg_now: warn(f"s{r['n']}: background picture change not exported (set it on the layout in PowerPoint)")
                else: set_bg(slide, bg_now)
            build_into(slide, rb + r["ch"]["added"], r["cur"], writer)
            drop_unused_media_rels(slide)
            drop_stale_timing(slide, r["n"])
            n = len(r["ch"]["deleted"]) + len(r["ch"]["added"]) + len(r["ch"]["changed"])
            print(f"s{r['n']:<3} source slide {r['src']:<3} {n} shape changes ({len(rb)} rebuilt)" if n else f"s{r['n']:<3} source slide {r['src']}")
        else:
            want = r["sec"].get("data-layout")
            named = [l for m in prs.slide_masters for l in m.slide_layouts if want and l.name == want]
            lay = (named[0] if named else orig[r["dup_of"] - 1].slide_layout if r["dup_of"] and r["dup_of"] <= len(orig)
                   else blank_layout(prs))
            slide = prs.slides.add_slide(lay)
            pptx_writer.strip_placeholders(slide)
            set_bg(slide, html_diff.style(r["sec"]).get("background"))
            build_into(slide, r["cur"], r["cur"], writer)
            print(f"s{r['n']:<3} built from HTML ({len(r['cur'])} shapes)")
        order.append(slide)
    # slide order = HTML order; drop slides no longer used
    lst = prs.slides._sldIdLst
    id_of = {s.part.partname: s for s in prs.slides}
    entries = {prs.part.related_part(e.rId).partname: e for e in list(lst)}
    for e in list(lst): lst.remove(e)
    keep = {s.part.partname for s in order}
    for pn, e in entries.items():
        if pn not in keep: prs.part.drop_rel(e.rId)
    for s in order: lst.append(entries[s.part.partname])
    del id_of
    prs.save(str(out_pptx))
    return len(order)


def powerpoint_available():
    if sys.platform != "win32": return False
    try:
        import winreg
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID"))
        return True
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--pptx")
    ap.add_argument("--pdf")
    ap.add_argument("--no-anim", action="store_true")
    ap.add_argument("--render", help="also export PowerPoint's own rendering of every slide as PNGs here")
    ap.add_argument("--keep", action="store_true", help="keep the stage-1 file next to the output")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    deck = Path(a.deck).resolve()
    if not (a.pptx or a.pdf): sys.exit("nothing to do: pass --pptx and/or --pdf")
    if a.pptx:
        out = Path(a.pptx).resolve()
        lock = out.parent / ("~$" + out.name)
        if lock.exists():
            msg = f"{out.name} looks open in PowerPoint (lock file {lock.name})"
            # PowerPoint for Mac doesn't block the write, and a ~$ file there is often a stale one synced from Windows
            if sys.platform == "win32": sys.exit(msg + "; close it first")
            print(f"!! {msg}; writing anyway. Close it in PowerPoint without saving, or the export gets overwritten")
        tmp = Path(tempfile.mkdtemp(prefix="deckexport-"))
        s1 = tmp / "stage1.pptx"
        n = stage1(deck, s1)
        anim = not a.no_anim and powerpoint_available()
        if anim:
            cmd = ["pwsh" if shutil.which("pwsh") else "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", str(HERE / "export_anim.ps1"), "-in", str(s1), "-out", str(out)]
            if a.render: cmd += ["-render", str(Path(a.render).resolve())]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                print(r.stdout[-2000:], r.stderr[-2000:])
                print("!! PowerPoint stage failed; writing the deck without animation")
                if a.render: print(f"!! --render needs the PowerPoint stage; nothing was rendered to {a.render}")
                shutil.copy(s1, out); anim = False
            else:
                bad = [l for l in r.stdout.splitlines() if re.search(r", [1-9]\d* on click", l)]
                print(f"animation: {len(r.stdout.splitlines())} slides processed" + (f"; on-click effects on: {bad}" if bad else ""))
        else:
            shutil.copy(s1, out)
            why = "--no-anim" if a.no_anim else "PowerPoint not installed" if sys.platform == "win32" else \
                  "the animation stage drives PowerPoint through COM, which only exists on Windows"
            print(f"animation: skipped ({why}); clips will need a click to play")
            if a.render: print(f"!! --render needs the PowerPoint stage; nothing was rendered to {a.render}")
        if a.keep: shutil.copy(s1, out.with_name(out.stem + ".stage1.pptx"))
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"wrote {out} ({n} slides{', animated, fonts embedded' if anim else ''})")
    if a.pdf:
        r = subprocess.run(["node", str(HERE / "shoot.mjs"), str(deck), "--pdf", str(Path(a.pdf).resolve())], text=True)
        if r.returncode: sys.exit("PDF export failed")
    if WARN:
        print(f"\n{len(WARN)} warnings:")
        for w in dict.fromkeys(WARN): print("  -", w)


if __name__ == "__main__":
    main()
