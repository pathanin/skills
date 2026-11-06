# -*- coding: utf-8 -*-
"""Convert a .pptx into the HTML deck format (index.html + media/), one <section> per slide.

Used by init_deck.py (--from). Not meant to be re-run over a deck that has been edited:
after conversion, index.html is the source of truth.

Every element keeps its PowerPoint shape name (data-name, made unique per slide) and shape id
(data-id); every slide keeps its source slide number (data-src). export.py uses these to replay
the HTML edits onto the source deck's own XML. Master and layout artwork (logos, bands) is drawn
as a non-editable background layer (data-layer="master") and is not exported (PowerPoint
inherits it from the layout anyway).
"""
import colorsys
import copy
import html
import math
import os
import re
import zipfile

from lxml import etree

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
A = "{%s}" % NS["a"]
R_ = "{%s}" % NS["r"]
PX = 9525.0                       # EMU per CSS px (96 dpi)
PT = 96 / 72.0                    # px per point
LINE_NORMAL = 1.2                 # set by convert() from the bundled font
DEFAULT_RPR = {"sz": "1800", "b": "0", "i": "0"}


def px(v): return round(int(v) / PX, 2)
def q(el, path): return el.find(path, NS) if el is not None else None
def qa(el, path): return el.findall(path, NS) if el is not None else []
def esc(t): return html.escape(t, quote=True)
def ln_(el): return etree.QName(el).localname


class Deck:
    def __init__(self, path, out):
        self.z = zipfile.ZipFile(path)
        self.out = out
        theme_part = [n for n in self.z.namelist() if re.match(r"ppt/theme/theme\d+\.xml$", n)]
        theme = etree.fromstring(self.z.read(sorted(theme_part)[0]))
        self.theme = theme
        self.scheme = {}
        for c in q(theme, ".//a:clrScheme"):
            v = c[0].get("val") if ln_(c[0]) == "srgbClr" else c[0].get("lastClr", "000000")
            self.scheme[ln_(c)] = v
        for k, v in {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}.items(): self.scheme[k] = self.scheme[v]
        self.media = {}            # zip path -> output name
        fs = q(theme, ".//a:fmtScheme")
        self.fill_styles = list(q(fs, "a:fillStyleLst")) if fs is not None and q(fs, "a:fillStyleLst") is not None else []
        self.bg_styles = list(q(fs, "a:bgFillStyleLst")) if fs is not None and q(fs, "a:bgFillStyleLst") is not None else []
        self.pres = self.xml("ppt/presentation.xml")
        self.size = (int(q(self.pres, "p:sldSz").get("cx")), int(q(self.pres, "p:sldSz").get("cy")))
        self.tstyles = {}
        if "ppt/tableStyles.xml" in self.z.namelist():
            for st in self.xml("ppt/tableStyles.xml"): self.tstyles[st.get("styleId")] = st

    def fonts(self):
        """(heading, body) typefaces of the theme (latin; else complex-script)."""
        out = []
        for k in ("a:majorFont", "a:minorFont"):
            f = q(self.theme, f".//a:fontScheme/{k}")
            out.append(next((q(f, t).get("typeface") for t in ("a:latin", "a:cs", "a:ea")
                             if q(f, t) is not None and q(f, t).get("typeface")), None))
        return out

    def dominant_font(self):
        """the typeface most runs on the slides actually use (theme fonts resolved), or None"""
        from collections import Counter
        major, minor = self.fonts()
        cnt = Counter()
        for n in self.z.namelist():
            if not re.match(r"ppt/slides/slide\d+\.xml$", n): continue
            for r in self.xml(n).iter(A + "r"):
                t = r.find("a:t", NS)
                if t is None or not (t.text or "").strip(): continue
                lat = r.find("a:rPr/a:latin", NS)
                face = lat.get("typeface") if lat is not None else "+mn-lt"
                face = {"+mn-lt": minor, "+mj-lt": major}.get(face, face)
                if face: cnt[face] += len(t.text)
        return cnt.most_common(1)[0][0] if cnt else None

    def xml(self, name): return etree.fromstring(self.z.read(name))

    def rels(self, part):
        d, b = os.path.split(part)
        rp = f"{d}/_rels/{b}.rels"
        out = {}
        if rp not in self.z.namelist(): return out
        for r in etree.fromstring(self.z.read(rp)):
            tgt = r.get("Target")
            if r.get("TargetMode") != "External":
                tgt = os.path.normpath(os.path.join(d, tgt)).replace("\\", "/")
            out[r.get("Id")] = tgt
        return out

    def take(self, zpath, prefer=None):
        """copy one media part to media/ once; returns the relative URL"""
        if zpath not in self.media:
            name = os.path.basename(zpath)
            # names are compared case-folded: macOS and Windows disks treat Logo.png and logo.png as one file
            taken = {v.casefold() for v in self.media.values()}
            if prefer:
                cand = re.sub(r"[^\w\u0e00-\u0e7f.\-]+", "_", prefer)      # keep Thai marks (\w drops them)
                if not os.path.splitext(cand)[1]: cand += os.path.splitext(name)[1]
                if cand.casefold() not in taken: name = cand
            stem, ext = os.path.splitext(name)
            k = 2
            while name.casefold() in taken:
                name = f"{stem}-{k}{ext}"; k += 1
            self.media[zpath] = name
            with open(os.path.join(self.out, "media", name), "wb") as f:
                f.write(self.z.read(zpath))
        return "media/" + self.media[zpath]

    # ---------- colours ----------
    def color(self, el, ph=None):
        """el = a solidFill / gs / similar container -> css colour or None (ph = hex that phClr stands for)"""
        if el is None: return None
        c = next((ch for ch in el if ln_(ch) in ("srgbClr", "schemeClr", "sysClr", "prstClr")), None)
        if c is None: return None
        n = ln_(c)
        hexv = (c.get("val") if n == "srgbClr" else (ph or "000000") if n == "schemeClr" and c.get("val") == "phClr"
                else self.scheme.get(c.get("val"), "000000") if n == "schemeClr"
                else c.get("lastClr", "000000") if n == "sysClr" else {"black": "000000", "white": "FFFFFF"}.get(c.get("val"), "000000"))
        r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4))
        alpha = 1.0
        for m in c:
            mn, v = ln_(m), int(m.get("val", "0")) / 100000
            if mn == "alpha": alpha = v
            elif mn in ("lumMod", "lumOff"):
                h, l, s = colorsys.rgb_to_hls(r, g, b)
                l = l * v if mn == "lumMod" else min(1, l + v)
                r, g, b = colorsys.hls_to_rgb(h, l, s)
            elif mn == "tint": r, g, b = (x + (1 - x) * (1 - v) for x in (r, g, b))
            elif mn == "shade": r, g, b = (x * v for x in (r, g, b))
        R, G, B = (round(x * 255) for x in (r, g, b))
        return f"rgba({R},{G},{B},{round(alpha, 3)})" if alpha < 1 else f"#{R:02X}{G:02X}{B:02X}"

    def fill(self, spPr, style):
        """css background for a shape (None = transparent)"""
        if spPr is not None:
            for ch in spPr:
                n = ln_(ch)
                if n == "noFill": return None
                if n == "solidFill": return self.color(ch)
                if n == "gradFill":
                    stops = [f"{self.color(gs)} {int(gs.get('pos')) / 1000:.1f}%" for gs in qa(ch, "a:gsLst/a:gs")]
                    lin = q(ch, "a:lin")
                    ang = int(lin.get("ang", "0")) / 60000 if lin is not None else 90
                    return f"linear-gradient({(ang + 90) % 360:.1f}deg, {', '.join(stops)})"
        if style is not None:
            fr = q(style, "a:fillRef")
            if fr is not None and fr.get("idx") != "0":
                base = self.color(fr)
                idx = int(fr.get("idx"))
                lst, k = (self.bg_styles, idx - 1001) if idx > 1000 else (self.fill_styles, idx - 1)
                if base and not base.startswith("rgba") and 0 <= k < len(lst):
                    st = lst[k]; ph = base[1:]
                    if ln_(st) == "solidFill": return self.color(st, ph)
                    if ln_(st) == "gradFill":
                        stops = [f"{self.color(gs, ph)} {int(gs.get('pos')) / 1000:.1f}%" for gs in qa(st, "a:gsLst/a:gs")]
                        lin = q(st, "a:lin")
                        ang = int(lin.get("ang", "0")) / 60000 if lin is not None else 90
                        return f"linear-gradient({(ang + 90) % 360:.1f}deg, {', '.join(stops)})"
                return base
        return None

    def line(self, spPr, style):
        """(width_px, css colour, dash) or None"""
        ln = q(spPr, "a:ln")
        w, col, dash = 9525, None, None
        if ln is not None:
            if q(ln, "a:noFill") is not None: return None
            w = int(ln.get("w", "9525"))
            sf = q(ln, "a:solidFill")
            col = self.color(sf) if sf is not None else None
            pd = q(ln, "a:prstDash")
            if pd is not None and pd.get("val") != "solid": dash = pd.get("val")
        if col is None and style is not None:
            lr = q(style, "a:lnRef")
            if lr is not None and lr.get("idx") != "0": col = self.color(lr)
        if col is None: return None
        return (max(round(w / PX, 2), 0.5), col, dash)

    def shadow(self, spPr):
        sh = q(spPr, "a:effectLst/a:outerShdw")
        if sh is None: return None
        dist = int(sh.get("dist", "0")) / PX
        d = math.radians(int(sh.get("dir", "0")) / 60000)
        blur = int(sh.get("blurRad", "0")) / PX
        return f"{dist * math.cos(d):.1f}px {dist * math.sin(d):.1f}px {blur:.1f}px {self.color(sh)}"


# ---------------------------------------------------------------- inherited text style
class Ctx:
    """Per-slide context: rels, layout/master placeholders, the list-style chain for text boxes."""

    def __init__(self, deck, part):
        self.deck, self.part = deck, part
        self.rels = deck.rels(part)
        self.names = {}
        lay_part = next((v for v in self.rels.values() if "slideLayout" in v), None)
        self.layout = deck.xml(lay_part) if lay_part else None
        lrels = deck.rels(lay_part) if lay_part else {}
        mst_part = next((v for v in lrels.values() if "slideMaster" in v), None)
        self.master = deck.xml(mst_part) if mst_part else None
        self.lay_part, self.mst_part, self.lrels, self.mrels = lay_part, mst_part, lrels, deck.rels(mst_part) if mst_part else {}

    @staticmethod
    def ph_of(sp):
        return q(sp, "./*/p:nvPr/p:ph")

    def find_ph(self, tree, ph):
        """the placeholder in a layout/master matching this slide placeholder (idx first, then type)"""
        if tree is None or ph is None: return None
        typ, idx = ph.get("type", "body"), ph.get("idx")
        cands = [(sp, self.ph_of(sp)) for sp in tree.iter("{%s}sp" % NS["p"]) if self.ph_of(sp) is not None]
        if idx is not None:
            for sp, p in cands:
                if p.get("idx") == idx: return sp
        alias = {"ctrTitle": "title", "subTitle": "body"}
        for t in (typ, alias.get(typ)):
            for sp, p in cands:
                if p.get("type", "body") == t: return sp
        return None

    def chain(self, sp):
        """list-style elements (lowest priority first) that apply to this shape's text, and inherited bodyPr"""
        ph = self.ph_of(sp)
        lst, bps = [], []
        if ph is None:
            dts = q(self.deck.pres, "p:defaultTextStyle")
            if dts is not None: lst.append(dts)
        else:
            typ = ph.get("type", "body")
            key = "p:titleStyle" if typ in ("title", "ctrTitle") else "p:bodyStyle" if typ in ("body", "subTitle", "obj", None) else "p:otherStyle"
            if typ not in ("title", "ctrTitle", "body", "subTitle", "obj"): key = "p:otherStyle" if typ in ("dt", "ftr", "sldNum") else "p:bodyStyle"
            ts = q(self.master, f"p:txStyles/{key}")
            if ts is not None: lst.append(ts)
            for tree in (self.master, self.layout):
                m = self.find_ph(tree, ph)
                if m is not None:
                    if q(m, "p:txBody/a:lstStyle") is not None: lst.append(q(m, "p:txBody/a:lstStyle"))
                    if q(m, "p:txBody/a:bodyPr") is not None: bps.append(q(m, "p:txBody/a:bodyPr"))
        own = q(sp, "p:txBody/a:lstStyle")
        if own is not None: lst.append(own)
        return lst, bps

    def geom_of(self, sp):
        """inherited xfrm for a placeholder without its own position"""
        ph = self.ph_of(sp)
        for tree in (self.layout, self.master):
            m = self.find_ph(tree, ph)
            if m is not None and xfrm_of(q(m, "p:spPr")) is not None: return xfrm_of(q(m, "p:spPr"))
        return None

    def attrs(self, nv):
        """data-name (unique on the slide) + data-id"""
        name = nv.get("name") or "Shape"
        k = self.names.get(name, 0) + 1
        self.names[name] = k
        uname = name if k == 1 else f"{name} ({k})"
        return f'data-name="{esc(uname)}" data-id="{esc(nv.get("id", ""))}"'


def pick(chain, lvl, attr=None, child=None):
    """last value of attr / child element along the lvlNpPr chain (+ the paragraph's own pPr last)"""
    val = None
    for el in chain:
        if el is None: continue
        node = el if ln_(el) == "pPr" else q(el, f"a:lvl{lvl}pPr")
        if node is None: continue
        if attr and node.get(attr) is not None: val = node.get(attr)
        if child and q(node, child) is not None: val = q(node, child)
    return val


def eff_rpr(chain, lvl, rPr):
    """effective run properties: dict of sz/b/i/u/spc + fill element + typeface"""
    d = dict(DEFAULT_RPR); fill = None
    nodes = []
    for el in chain:
        if el is None: continue
        node = el if ln_(el) == "pPr" else q(el, f"a:lvl{lvl}pPr")
        if node is not None and q(node, "a:defRPr") is not None: nodes.append(q(node, "a:defRPr"))
    if rPr is not None: nodes.append(rPr)
    for n in nodes:
        for k in ("sz", "b", "i", "u", "spc", "baseline"):
            if n.get(k) is not None: d[k] = n.get(k)
        if q(n, "a:solidFill") is not None: fill = q(n, "a:solidFill")
        if q(n, "a:noFill") is not None: fill = None
    return d, fill


# ---------------------------------------------------------------- text
def run_css(deck, d, fill):
    css = [f"font-size:{int(d['sz']) / 100 * PT:.2f}px"]
    if d.get("b") == "1": css.append("font-weight:700")
    if d.get("i") == "1": css.append("font-style:italic")
    if d.get("u") not in (None, "none"): css.append("text-decoration:underline")
    if d.get("spc") and int(d["spc"]): css.append(f"letter-spacing:{int(d['spc']) / 100 * PT:.2f}px")
    if d.get("baseline") and int(d["baseline"]) > 0: css.append("vertical-align:super;font-size:smaller")
    c = deck.color(fill) if fill is not None else None
    css.append(f"color:{c or '#' + deck.scheme.get('tx1', '000000')}")
    return ";".join(css)


SYMBOL_BULLETS = {"": "▪", "": "•", "": "➢", "": "✓", "": "❖", "": "◆", "": "■", "": "➢"}


def bu_char(bu):
    """bullet character; Wingdings/Symbol private-use code points mapped to Unicode look-alikes"""
    ch = bu.get("char", "•") or "•"
    return SYMBOL_BULLETS.get(ch, "•" if "" <= ch <= "" else ch)


def autonum(kind, n):
    def roman(k):
        out = ""
        for v, r in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
            while k >= v: out += r; k -= v
        return out
    alpha = lambda k: chr(ord("a") + (k - 1) % 26)
    body = (roman(n) if "roman" in kind else alpha(n) if "alpha" in kind else str(n))
    if "Uc" in kind: body = body.upper()
    if kind.endswith("ParenBoth"): return f"({body})"
    if kind.endswith("ParenR"): return f"{body})"
    if kind.endswith("Plain"): return body
    return f"{body}."


def paragraphs(deck, txBody, chain):
    out = []
    counters = {}
    for p in qa(txBody, "a:p"):
        pPr = q(p, "a:pPr")
        lvl = int(pPr.get("lvl", "0")) + 1 if pPr is not None else 1
        ch = chain + ([pPr] if pPr is not None else [])
        css = []
        algn = pick(ch, lvl, attr="algn") or "l"
        css.append("text-align:" + {"l": "left", "ctr": "center", "r": "right", "just": "justify", "dist": "justify"}.get(algn, "left"))
        runs = qa(p, "a:r") + qa(p, "a:fld")
        first = q(runs[0], "a:rPr") if runs else q(p, "a:endParaRPr")
        d0, _ = eff_rpr(ch, lvl, first)
        size = int(d0["sz"]) / 100
        ls, lp = pick(ch, lvl, child="a:lnSpc/a:spcPts"), pick(ch, lvl, child="a:lnSpc/a:spcPct")
        if ls is not None: css.append(f"line-height:{int(ls.get('val')) / 100 * PT:.2f}px")
        elif lp is not None: css.append(f"line-height:{LINE_NORMAL * int(lp.get('val')) / 100000:.3f}")
        for tag, prop in (("a:spcBef/a:spcPts", "margin-top"), ("a:spcAft/a:spcPts", "margin-bottom")):
            v = pick(ch, lvl, child=tag)
            if v is not None and int(v.get("val")): css.append(f"{prop}:{int(v.get('val')) / 100 * PT:.2f}px")
        marL, indent = pick(ch, lvl, attr="marL"), pick(ch, lvl, attr="indent")
        if marL and int(marL): css.append(f"padding-left:{px(marL)}px")
        if indent and int(indent): css.append(f"text-indent:{px(indent)}px")
        css.append(f"font-size:{size * PT:.2f}px")
        parts = []
        bu_none = pick(ch, lvl, child="a:buNone")
        bu = pick(ch, lvl, child="a:buChar")
        # buNone set later in the chain than buChar wins
        last_bu = None
        for el in ch:
            node = None if el is None else (el if ln_(el) == "pPr" else q(el, f"a:lvl{lvl}pPr"))
            if node is None: continue
            for t in ("a:buNone", "a:buChar", "a:buAutoNum"):
                if q(node, t) is not None: last_bu = t
        hang = f";display:inline-block;min-width:{-px(indent):.2f}px;text-indent:0" if indent and int(indent) < 0 else ""
        for k in [k for k in counters if k > lvl]: counters.pop(k)
        if runs and last_bu == "a:buAutoNum":
            an = pick(ch, lvl, child="a:buAutoNum")
            counters[lvl] = counters.get(lvl, int(an.get("startAt", "1")) - 1) + 1
            bc = pick(ch, lvl, child="a:buClr")
            col = deck.color(bc) if bc is not None else None
            parts.append(f'<span class="bu" style="{run_css(deck, d0, None)}{";color:" + col if col else ""}{hang}">'
                         f'{esc(autonum(an.get("type", "arabicPeriod"), counters[lvl]))} </span>')
        elif runs: counters.pop(lvl, None)
        if runs and last_bu == "a:buChar" and bu is not None:
            bc = pick(ch, lvl, child="a:buClr")
            col = deck.color(bc) if bc is not None else None
            parts.append(f'<span class="bu" style="{run_css(deck, d0, None)}{";color:" + col if col else ""}{hang}">'
                         f'{esc(bu_char(bu))} </span>')
        for c in p:
            n = ln_(c)
            if n in ("r", "fld"):
                d, fill = eff_rpr(ch, lvl, q(c, "a:rPr"))
                parts.append(f'<span style="{run_css(deck, d, fill)}">{esc(q(c, "a:t").text or "")}</span>')
            elif n == "br":
                parts.append("<br>")
        body = "".join(parts) or "&#8203;"
        out.append(f'<p style="{";".join(css)}">{body}</p>')
    return "".join(out)


def text_block(deck, txBody, chain, bps):
    bp = q(txBody, "a:bodyPr")
    allbp = bps + ([bp] if bp is not None else [])

    def g(k, d):
        v = d
        for b in allbp:
            if b.get(k) is not None: v = b.get(k)
        return v
    ins = [int(g(k, d)) / PX for k, d in (("tIns", 45720), ("rIns", 91440), ("bIns", 45720), ("lIns", 91440))]
    jc = {"t": "flex-start", "ctr": "center", "b": "flex-end"}.get(g("anchor", "t"), "flex-start")
    css = f"padding:{ins[0]:.2f}px {ins[1]:.2f}px {ins[2]:.2f}px {ins[3]:.2f}px;justify-content:{jc}"
    if g("wrap", "square") == "none": css += ";white-space:pre"
    return f'<div class="tx" style="{css}">{paragraphs(deck, txBody, chain)}</div>'


def has_text(txBody):
    return txBody is not None and any((t.text or "").strip() for t in txBody.iter(A + "t"))


# ---------------------------------------------------------------- shapes
def xfrm_of(el):
    x = el.find(".//a:xfrm", NS) if el is not None else None
    if x is None or q(x, "a:off") is None: return None
    off, ext = q(x, "a:off"), q(x, "a:ext")
    return [int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy")), x.get("flipH") == "1", x.get("flipV") == "1",
            int(x.get("rot", "0")) / 60000]


def box_css(g, tf):
    x, y, w, h = tf(g[:4])
    css = f"left:{x / PX:.2f}px;top:{y / PX:.2f}px;width:{w / PX:.2f}px;height:{h / PX:.2f}px"
    if len(g) > 6 and g[6]: css += f";transform:rotate({g[6]:.2f}deg)"
    return css


def shape_html(ctx, sp, tf, master):
    deck = ctx.deck
    nv = q(sp, "p:nvSpPr/p:cNvPr")
    spPr, style = q(sp, "p:spPr"), q(sp, "p:style")
    g = xfrm_of(spPr)
    if g is None and Ctx.ph_of(sp) is not None: g = ctx.geom_of(sp)
    if g is None: return ""
    geom = q(spPr, "a:prstGeom")
    prst = geom.get("prst") if geom is not None else ("custom" if q(spPr, "a:custGeom") is not None else "rect")
    fill, ln, shd = deck.fill(spPr, style), deck.line(spPr, style), deck.shadow(spPr)
    txBody = q(sp, "p:txBody")
    css = [box_css(g, tf)]
    inner, extra = "", ""
    x, y, w, h = tf(g[:4])
    if prst not in ("rect", "roundRect", "ellipse"):
        inner = svg_shape(deck, spPr, prst, w / PX, h / PX, fill, ln, shd, g[4], g[5])
        extra = f' data-prst="{esc(prst)}"'
        fill = ln = shd = None
    else:
        if fill: css.append(f"background:{fill}")
        if ln: css.append(f"border:{ln[0]}px {'dashed' if ln[2] else 'solid'} {ln[1]}")
        if prst == "roundRect":
            adj = q(geom, "a:avLst/a:gd")
            a = int(re.search(r"\d+", adj.get("fmla")).group()) if adj is not None else 16667
            css.append(f"border-radius:{min(w, h) / PX * a / 100000:.2f}px")
        if prst == "ellipse": css.append("border-radius:50%")
        if shd: css.append(f"box-shadow:{shd}")
    if has_text(txBody) and not (master and Ctx.ph_of(sp) is not None):
        lst, bps = ctx.chain(sp)
        inner += text_block(deck, txBody, lst, bps)
    if not inner and not fill and not ln and not shd: return ""
    who = 'data-layer="master"' if master else ctx.attrs(nv)
    return f'<div class="sh" {who}{extra} style="{";".join(css)}">{inner}</div>'


def svg_shape(deck, spPr, prst, w, h, fill, ln, shd, flipH, flipV):
    sw = ln[0] if ln else 0
    stroke = (f'stroke="{ln[1]}" stroke-width="{sw}"' + (' stroke-dasharray="6 4"' if ln[2] else "")) if ln else 'stroke="none"'
    fl = f'fill="{fill}"' if fill and not fill.startswith("linear") else 'fill="none"'
    tr = ""
    if flipH or flipV:
        tr = f' transform="translate({w if flipH else 0} {h if flipV else 0}) scale({-1 if flipH else 1} {-1 if flipV else 1})"'
    body, defs = "", ""
    if prst == "line" or prst.startswith(("straightConnector", "bentConnector", "curvedConnector")):
        lnel = q(spPr, "a:ln")
        mk = ""
        for end, attr in (("a:headEnd", "marker-start"), ("a:tailEnd", "marker-end")):
            e = q(lnel, end)
            if e is not None and e.get("type") not in (None, "none") and ln:
                mid = f"m{abs(hash((w, h, end, ln[1]))) % 10**8}"
                defs += (f'<marker id="{mid}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" '
                         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{ln[1]}"/></marker>')
                mk += f' {attr}="url(#{mid})"'
        body = f'<line x1="0" y1="0" x2="{w}" y2="{h}" {stroke}{mk}/>'
    elif prst == "custom":
        for path in qa(q(spPr, "a:custGeom"), "a:pathLst/a:path"):
            pw, ph = int(path.get("w", "1")) or 1, int(path.get("h", "1")) or 1
            sx, sy = w / pw, h / ph
            d = []
            for c in path:
                t = ln_(c)
                pts = [(int(pt.get("x")) * sx, int(pt.get("y")) * sy) for pt in qa(c, "a:pt")]
                if t == "moveTo": d.append("M%.2f,%.2f" % pts[0])
                elif t == "lnTo": d.append("L%.2f,%.2f" % pts[0])
                elif t == "cubicBezTo": d.append("C" + " ".join("%.2f,%.2f" % p_ for p_ in pts))
                elif t == "quadBezTo": d.append("Q" + " ".join("%.2f,%.2f" % p_ for p_ in pts))
                elif t == "close": d.append("Z")
            body += f'<path d="{" ".join(d)}" {fl} {stroke}/>'
    elif prst == "triangle":
        body = f'<path d="M{w / 2},0 L{w},{h} L0,{h} Z" {fl} {stroke}/>'
    elif prst in ("rightArrow", "leftArrow"):
        hw, hh = min(w, h / 2), h / 4
        d = f"M0,{hh} L{w - hw},{hh} L{w - hw},0 L{w},{h / 2} L{w - hw},{h} L{w - hw},{h - hh} L0,{h - hh} Z"
        if prst == "leftArrow": tr = f' transform="translate({w} 0) scale(-1 1)"'
        body = f'<path d="{d}" {fl} {stroke}/>'
    elif prst in ("star5", "star4", "star6", "star8"):
        k = int(prst[4:]); pts = []
        for i in range(2 * k):
            r = 0.5 if i % 2 == 0 else 0.5 * (0.38 if k == 5 else 0.42)
            a_ = math.pi * i / k - math.pi / 2
            pts.append(f"{w / 2 + r * w * math.cos(a_):.2f},{h / 2 + r * h * math.sin(a_):.2f}")
        body = f'<path d="M{" L".join(pts)} Z" {fl} {stroke}/>'
    elif prst == "diamond":
        body = f'<path d="M{w / 2},0 L{w},{h / 2} L{w / 2},{h} L0,{h / 2} Z" {fl} {stroke}/>'
    elif prst == "parallelogram":
        a = min(w, h) * 0.25
        body = f'<path d="M{a},0 L{w},0 L{w - a},{h} L0,{h} Z" {fl} {stroke}/>'
    elif prst == "chevron" or prst == "homePlate":
        a = min(w, h) / 2
        d = (f"M0,0 L{w - a},0 L{w},{h / 2} L{w - a},{h} L0,{h} L{a},{h / 2} Z" if prst == "chevron"
             else f"M0,0 L{w - a},0 L{w},{h / 2} L{w - a},{h} L0,{h} Z")
        body = f'<path d="{d}" {fl} {stroke}/>'
    else:   # other presets: draw the bounding box so nothing is lost (QA lists these)
        body = f'<rect x="0" y="0" width="{w}" height="{h}" {fl} {stroke}/>'
    filt = f' style="filter:drop-shadow({shd})"' if shd else ""
    return (f'<svg class="svg" width="{max(w, 1):.2f}" height="{max(h, 1):.2f}" overflow="visible"{filt}>'
            f'<defs>{defs}</defs><g{tr}>{body}</g></svg>')


def pic_html(ctx, pic, tf, rels, master):
    deck = ctx.deck
    nv = q(pic, "p:nvPicPr/p:cNvPr")
    name, descr = nv.get("name"), nv.get("descr", "")
    spPr = q(pic, "p:spPr")
    g = xfrm_of(spPr)
    blip = q(pic, "p:blipFill/a:blip")
    if g is None or blip is None or blip.get(R_ + "embed") not in rels: return ""
    img = deck.take(rels[blip.get(R_ + "embed")])
    vf = pic.find(".//a:videoFile", NS)
    css = [box_css(g, tf)]
    shd = deck.shadow(spPr)
    if shd: css.append(f"filter:drop-shadow({shd})")
    geom = q(spPr, "a:prstGeom")
    if geom is not None and geom.get("prst") == "roundRect":
        x, y, w, h = tf(g[:4]); css.append(f"border-radius:{min(w, h) / PX * 0.16667:.2f}px;overflow:hidden")
    if geom is not None and geom.get("prst") == "ellipse": css.append("border-radius:50%;overflow:hidden")
    who = 'data-layer="master"' if master else ctx.attrs(nv)
    if vf is not None and vf.get(R_ + "link") in rels and not master:
        vid = deck.take(rels[vf.get(R_ + "link")], prefer=name)
        return (f'<div class="pic vid" {who} style="{";".join(css)}">'
                f'<video src="{vid}" poster="{img}" preload="none" playsinline></video>'
                f'<img class="poster" src="{img}" alt=""></div>')
    sr = q(pic, "p:blipFill/a:srcRect")
    alt = esc(descr if descr and not re.search(r"\.(png|jpe?g)$", descr, re.I) else "")
    if sr is not None and any(sr.get(k) for k in "ltrb"):
        l, t, r, b = (int(sr.get(k, "0")) / 100000 for k in "ltrb")
        iw, ih = 1 / (1 - l - r), 1 / (1 - t - b)
        return (f'<div class="pic crop" {who} style="{";".join(css)};overflow:hidden">'
                f'<img src="{img}" alt="{alt}" style="position:absolute;width:{iw * 100:.3f}%;height:{ih * 100:.3f}%;'
                f'left:{-l * iw * 100:.3f}%;top:{-t * ih * 100:.3f}%"></div>')
    return f'<div class="pic" {who} style="{";".join(css)}"><img src="{img}" alt="{alt}"></div>'


def table_style_cell(deck, tstyle, flags, r, c, nr, nc):
    """(css fill, synthetic lstStyle for the text, {side: a:ln}) for one cell, from the table's style"""
    if tstyle is None: return None, None, {}
    parts = ["wholeTbl"]
    body_r = r - (1 if flags["firstRow"] else 0)
    if flags["bandRow"] and body_r >= 0 and not (flags["lastRow"] and r == nr - 1):
        parts.append("band1H" if body_r % 2 == 0 else "band2H")
    body_c = c - (1 if flags["firstCol"] else 0)
    if flags["bandCol"] and body_c >= 0: parts.append("band1V" if body_c % 2 == 0 else "band2V")
    if flags["lastCol"] and c == nc - 1: parts.append("lastCol")
    if flags["firstCol"] and c == 0: parts.append("firstCol")
    if flags["lastRow"] and r == nr - 1: parts.append("lastRow")
    if flags["firstRow"] and r == 0: parts.append("firstRow")
    fill, bold, clr, bdr = None, None, None, {}
    for name in parts:
        p = q(tstyle, f"a:{name}")
        if p is None: continue
        f = q(p, "a:tcStyle/a:fill")
        if f is not None:
            fill = deck.fill(f, None)
        fr = q(p, "a:tcStyle/a:fillRef")
        if fr is not None and fr.get("idx") != "0":
            fill = deck.color(fr)
        tx = q(p, "a:tcTxStyle")
        if tx is not None:
            if tx.get("b"): bold = tx.get("b") == "on"
            cc = next((ch for ch in tx if ln_(ch) in ("srgbClr", "schemeClr", "prstClr", "sysClr")), None)
            if cc is not None: clr = cc
        b = q(p, "a:tcStyle/a:tcBdr")
        if b is not None:
            edge = {"left": c == 0, "right": c == nc - 1, "top": r == 0, "bottom": r == nr - 1}
            for side in ("left", "right", "top", "bottom"):
                key = side if edge[side] or name != "wholeTbl" else ("insideV" if side in ("left", "right") else "insideH")
                l = q(b, f"a:{key}/a:ln")
                lr = q(b, f"a:{key}/a:lnRef")
                if l is None and lr is not None and lr.get("idx") != "0":     # theme line: draw it 1 pt in its colour
                    l = etree.Element(A + "ln", w="12700")
                    sf = etree.SubElement(l, A + "solidFill")
                    cc = next((ch for ch in lr if ln_(ch) in ("srgbClr", "schemeClr", "prstClr", "sysClr")), None)
                    if cc is not None: sf.append(copy.deepcopy(cc))
                if l is not None: bdr[side] = l
    txt = None
    if bold is not None or clr is not None:
        txt = etree.Element(A + "lstStyle")
        for lv in range(1, 10):
            d = etree.SubElement(etree.SubElement(txt, A + f"lvl{lv}pPr"), A + "defRPr")
            if bold is not None: d.set("b", "1" if bold else "0")
            if clr is not None:
                sf = etree.SubElement(d, A + "solidFill"); sf.append(copy.deepcopy(clr))
    return fill, txt, bdr


def table_html(ctx, gf, tf):
    deck = ctx.deck
    nv = q(gf, "p:nvGraphicFramePr/p:cNvPr")
    x = q(gf, "p:xfrm")
    off, ext = q(x, "a:off"), q(x, "a:ext")
    g = [int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))]
    tbl = gf.find(".//a:tbl", NS)
    cols = [int(c.get("w")) / PX for c in qa(tbl, "a:tblGrid/a:gridCol")]
    base_chain = [q(deck.pres, "p:defaultTextStyle")]
    tblPr = q(tbl, "a:tblPr")
    sid = q(tblPr, "a:tableStyleId")
    tstyle = deck.tstyles.get(sid.text.strip()) if sid is not None and sid.text else None
    flags = {k: tblPr is not None and tblPr.get(k) == "1" for k in ("firstRow", "lastRow", "firstCol", "lastCol", "bandRow", "bandCol")}
    trs = qa(tbl, "a:tr")
    nr, nc = len(trs), len(cols)
    rows = []
    for ri, tr in enumerate(trs):
        cells = []
        for ci, tc in enumerate(qa(tr, "a:tc")):
            if tc.get("hMerge") == "1" or tc.get("vMerge") == "1": continue
            tcPr = q(tc, "a:tcPr")
            css = []
            st_fill, st_txt, st_bdr = table_style_cell(deck, tstyle, flags, ri, ci, nr, nc)
            chain = base_chain + ([st_txt] if st_txt is not None else [])
            m = [int(tcPr.get(k, d)) / PX if tcPr is not None else d / PX for k, d in
                 (("marT", 45720), ("marR", 91440), ("marB", 45720), ("marL", 91440))]
            css.append(f"padding:{m[0]:.2f}px {m[1]:.2f}px {m[2]:.2f}px {m[3]:.2f}px")
            anchor = tcPr.get("anchor", "t") if tcPr is not None else "t"
            css.append("vertical-align:" + {"t": "top", "ctr": "middle", "b": "bottom"}.get(anchor, "top"))
            own = tcPr is not None and any(ln_(c) in ("solidFill", "gradFill", "noFill") for c in tcPr)
            f = deck.fill(tcPr, None) if own else st_fill
            if f: css.append(f"background:{f}")
            for side, tag in (("left", "a:lnL"), ("right", "a:lnR"), ("top", "a:lnT"), ("bottom", "a:lnB")):
                l = q(tcPr, tag)
                if l is None: l = st_bdr.get(side)
                if l is None: continue
                if q(l, "a:noFill") is not None or int(l.get("w", "12700")) == 0:
                    css.append(f"border-{side}:none")
                else:
                    css.append(f"border-{side}:{int(l.get('w', '12700')) / PX:.2f}px solid {deck.color(q(l, 'a:solidFill')) or '#000'}")
            span = "".join(f' {a}="{tc.get(k)}"' for k, a in (("gridSpan", "colspan"), ("rowSpan", "rowspan")) if tc.get(k))
            txt = paragraphs(deck, q(tc, "a:txBody"), chain) if q(tc, "a:txBody") is not None else ""
            cells.append(f'<td{span} style="{";".join(css)}"><div class="cell">{txt}</div></td>')
        rows.append(f'<tr style="height:{int(tr.get("h")) / PX:.2f}px">{"".join(cells)}</tr>')
    colg = "".join(f'<col style="width:{c:.2f}px">' for c in cols)
    return (f'<table class="tbl" {ctx.attrs(nv)} style="{box_css(g, tf)};height:auto">'
            f'<colgroup>{colg}</colgroup>{"".join(rows)}</table>')


def tree_html(ctx, tree, tf, rels, master=False, skip_ph=False):
    out = []
    for el in tree:
        n = ln_(el)
        if n == "sp":
            if skip_ph and Ctx.ph_of(el) is not None: continue
            out.append(shape_html(ctx, el, tf, master))
        elif n == "cxnSp":
            spPr = q(el, "p:spPr")
            g = xfrm_of(spPr)
            if g is None: continue
            x, y, w, h = tf(g[:4])
            ln = ctx.deck.line(spPr, q(el, "p:style"))
            svg = svg_shape(ctx.deck, spPr, "line", w / PX, h / PX, None, ln, None, g[4], g[5])
            who = 'data-layer="master"' if master else ctx.attrs(q(el, "p:nvCxnSpPr/p:cNvPr"))
            out.append(f'<div class="sh" {who} data-prst="line" style="{box_css(g, tf)}">{svg}</div>')
        elif n == "pic":
            out.append(pic_html(ctx, el, tf, rels, master))
        elif n == "graphicFrame":
            if el.find(".//a:tbl", NS) is not None and not master: out.append(table_html(ctx, el, tf))
            elif not master:
                nv = q(el, "p:nvGraphicFramePr/p:cNvPr")
                g = [int(v) for v in (q(el, "p:xfrm/a:off").get("x"), q(el, "p:xfrm/a:off").get("y"),
                                       q(el, "p:xfrm/a:ext").get("cx"), q(el, "p:xfrm/a:ext").get("cy"))]
                out.append(f'<div class="sh ole" {ctx.attrs(nv)} style="{box_css(g, tf)};background:repeating-linear-gradient(45deg,#eee 0 8px,#ddd 8px 16px)">'
                           f'<div class="tx" style="justify-content:center"><p style="text-align:center;font-size:14px">'
                           f'<span style="font-size:14px;color:#666">[chart / object kept from the source deck]</span></p></div></div>')
        elif n == "grpSp":
            x = q(el, "p:grpSpPr/a:xfrm")
            off, ext, coff, cext = (q(x, t) for t in ("a:off", "a:ext", "a:chOff", "a:chExt"))
            ox, oy, ew, eh = (int(v) for v in (off.get("x"), off.get("y"), ext.get("cx"), ext.get("cy")))
            cx, cy, cw, ch = (int(v) for v in (coff.get("x"), coff.get("y"), cext.get("cx"), cext.get("cy")))
            sx, sy = (ew / cw if cw else 1), (eh / ch if ch else 1)

            def tf2(b, tf=tf, ox=ox, oy=oy, cx=cx, cy=cy, sx=sx, sy=sy):
                return tf([ox + (b[0] - cx) * sx, oy + (b[1] - cy) * sy, b[2] * sx, b[3] * sy])
            out.append(tree_html(ctx, el, tf2, rels, master, skip_ph))
    return "".join(o for o in out if o)


def bg_css(deck, *trees):
    """css background of a slide: its own <p:bg>, else the layout's, else the master's ((tree, rels) pairs)"""
    for t, rels in trees:
        if t is None: continue
        bp = t.find("p:cSld/p:bg/p:bgPr", NS)
        if bp is not None:
            blip = q(bp, "a:blipFill/a:blip")
            if blip is not None and blip.get(R_ + "embed") in rels:
                return f"#FFFFFF url({deck.take(rels[blip.get(R_ + 'embed')])}) center/100% 100% no-repeat"
            return deck.fill(bp, None) or "#FFFFFF"
        br = t.find("p:cSld/p:bg/p:bgRef", NS)
        if br is not None: return deck.color(br) or "#FFFFFF"
    return "#FFFFFF"


def convert(src, out, lang="en", line_normal=1.2):
    """Write out/index.html body sections + out/media. Returns (sections_html, info)."""
    global LINE_NORMAL
    LINE_NORMAL = line_normal
    os.makedirs(os.path.join(out, "media"), exist_ok=True)
    deck = Deck(src, out)
    sx, sy = 1280 * PX / deck.size[0], 720 * PX / deck.size[1]
    tf = (lambda b: [b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy])
    prels = deck.rels("ppt/presentation.xml")
    order = [prels[s.get(R_ + "id")] for s in qa(deck.pres, "p:sldIdLst/p:sldId")]
    sections = []
    for n, part in enumerate(order, 1):
        sl = deck.xml(part)
        ctx = Ctx(deck, part)
        bgc = bg_css(deck, (sl, ctx.rels), (ctx.layout, ctx.lrels), (ctx.master, ctx.mrels))
        lay_name = q(ctx.layout, "p:cSld").get("name", "") if ctx.layout is not None else ""
        layers = ""
        show_mst = (ctx.layout is None or ctx.layout.get("showMasterSp") != "0") and sl.get("showMasterSp") != "0"
        if ctx.master is not None and show_mst:
            layers += tree_html(ctx, q(ctx.master, "p:cSld/p:spTree"), tf, ctx.mrels, master=True, skip_ph=True)
        if ctx.layout is not None and sl.get("showMasterSp") != "0":
            layers += tree_html(ctx, q(ctx.layout, "p:cSld/p:spTree"), tf, ctx.lrels, master=True, skip_ph=True)
        body = tree_html(ctx, q(sl, "p:cSld/p:spTree"), tf, ctx.rels)
        titles = sl.xpath(".//p:sp[p:nvSpPr/p:nvPr/p:ph[@type='title' or @type='ctrTitle']]", namespaces=NS)
        tt = "".join(t.text or "" for t in titles[0].iter(A + "t")) if titles else ""
        sections.append(f'<section class="slide" id="s{n}" data-src="{n}" data-layout="{esc(lay_name)}" data-title="{esc(tt)}" style="background:{bgc}">\n'
                        f'{layers}{body}\n</section>')
    heading, body_font = deck.fonts()
    return sections, {"slides": len(order), "media": len(deck.media), "fonts": (heading, body_font),
                      "size": deck.size}
