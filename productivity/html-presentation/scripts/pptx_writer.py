"""Build native PowerPoint shapes from HTML deck elements (python-pptx).

Handles the deck vocabulary (see references/format.md):
  .sh  [.tx]        rectangle / rounded rectangle / ellipse / preset (data-prst) with fill, border, shadow, text
  .sh  data-prst=line  straight connector (arrow heads from the SVG markers)
  .pic / .pic.crop  picture (crop, rounded corners)
  .pic.vid          embedded clip with its poster frame
  table.tbl         table (fills, borders, padding, merged cells)
Anything it cannot express is reported through `warn`.
"""
import copy
import re
from pathlib import Path
from urllib.parse import unquote

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

PT = 4 / 3          # CSS px per point
ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT, "justify": PP_ALIGN.JUSTIFY}
ANCHOR = {"flex-start": MSO_ANCHOR.TOP, "center": MSO_ANCHOR.MIDDLE, "flex-end": MSO_ANCHOR.BOTTOM,
          "top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}


def style(el):
    d = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            d[k.strip().lower()] = v.strip()
    return d


def fpx(v, default=None):
    if v is None: return default
    m = re.match(r"\s*(-?[\d.]+)\s*(px)?\s*$", str(v))
    return float(m.group(1)) if m else default


def color(c):
    """css colour -> (RRGGBB, alpha) or None"""
    if not c: return None
    c = c.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", c)
    if m: return m.group(1).upper(), 1.0
    m = re.fullmatch(r"#([0-9a-fA-F]{3})", c)
    if m: return "".join(ch * 2 for ch in m.group(1)).upper(), 1.0
    m = re.fullmatch(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", c)
    if m:
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        return "%02X%02X%02X" % (r, g, b), float(m.group(4)) if m.group(4) else 1.0
    named = {"white": "FFFFFF", "black": "000000", "transparent": None}
    if c.lower() in named: return (named[c.lower()], 1.0) if named[c.lower()] else None
    return None


def pad(st, key="padding"):
    """css padding -> (top, right, bottom, left) px"""
    v = [fpx(x, 0) for x in st.get(key, "").split()] or [None]
    if v == [None]: return None
    if len(v) == 1: v = v * 4
    elif len(v) == 2: v = [v[0], v[1], v[0], v[1]]
    elif len(v) == 3: v = [v[0], v[1], v[2], v[1]]
    return tuple(v[:4])


class Writer:
    def __init__(self, deck_dir, family, line_normal, sx, sy, warn):
        self.dir = Path(deck_dir)
        self.family, self.ln, self.sx, self.sy, self.warn = family, line_normal, sx, sy, warn

    # ---------- helpers ----------
    def E(self, v, axis="x"): return Emu(int(round(v * (self.sx if axis == "x" else self.sy))))

    def box(self, st, h=None):
        return (self.E(fpx(st.get("left"), 0)), self.E(fpx(st.get("top"), 0), "y"),
                self.E(max(fpx(st.get("width"), 1), 1)), self.E(max(h if h is not None else fpx(st.get("height"), 1), 1), "y"))

    def media(self, src):
        p = self.dir / unquote(src)
        if not p.exists(): raise FileNotFoundError(f"missing media file {p}")
        return str(p)

    @staticmethod
    def set_fill(fill_fmt, css, warn, what):
        if not css or css in ("none", "transparent"):
            fill_fmt.background(); return
        if css.startswith("linear-gradient"):
            m = re.match(r"linear-gradient\(\s*(?:([-\d.]+)deg\s*,)?(.*)\)\s*$", css)
            ang = float(m.group(1)) if m and m.group(1) else 180.0
            stops = re.findall(r"(#[0-9a-fA-F]{3,6}|rgba?\([^)]*\))\s*([\d.]+%)?", m.group(2) if m else "")
            if len(stops) >= 2:
                fill_fmt.gradient()
                fill_fmt.gradient_angle = (ang - 90) % 360
                gs = fill_fmt.gradient_stops
                # python-pptx gives 2 stops; set first/last
                c0, c1 = color(stops[0][0]), color(stops[-1][0])
                gs[0].color.rgb = RGBColor.from_string(c0[0]); gs[0].position = 0
                gs[1].color.rgb = RGBColor.from_string(c1[0]); gs[1].position = 1.0
                if len(stops) > 2: warn(f"{what}: gradient with {len(stops)} stops exported with first and last only")
                return
        c = color(css)
        if c is None:
            warn(f"{what}: background '{css[:40]}' not exported"); fill_fmt.background(); return
        fill_fmt.solid(); fill_fmt.fore_color.rgb = RGBColor.from_string(c[0])
        if c[1] < 1: Writer.alpha(fill_fmt._xPr.find(qn("a:solidFill")), c[1])

    @staticmethod
    def alpha(solid_el, a):
        if solid_el is None: return
        clr = solid_el[0]
        for x in clr.findall(qn("a:alpha")): clr.remove(x)
        etree.SubElement(clr, qn("a:alpha")).set("val", str(int(a * 100000)))

    def set_line(self, line, css_border, what):
        if not css_border or css_border.startswith("none") or css_border.startswith("0"):
            line.fill.background(); return
        m = re.match(r"([\d.]+)px\s+(solid|dashed|dotted)\s+(.+)$", css_border)
        if not m:
            self.warn(f"{what}: border '{css_border}' not exported"); line.fill.background(); return
        c = color(m.group(3))
        line.width = Pt(float(m.group(1)) / PT)
        if c:
            line.color.rgb = RGBColor.from_string(c[0])
        if m.group(2) != "solid":
            ln = line._get_or_add_ln()
            d = etree.SubElement(ln, qn("a:prstDash")); d.set("val", "dash" if m.group(2) == "dashed" else "sysDot")

    def shadow(self, sp_el, css):
        m = re.match(r"(?:inset\s+)?(-?[\d.]+)px\s+(-?[\d.]+)px\s+([\d.]+)px\s*(?:([\d.]+)px\s*)?(.+)$", css or "")
        if not m or css.startswith("inset"): return False
        import math
        x, y, blur = float(m.group(1)), float(m.group(2)), float(m.group(3))
        c = color(m.group(5))
        if not c: return False
        spPr = sp_el.find(qn("p:spPr"))
        eff = etree.SubElement(spPr, qn("a:effectLst"))
        sh = etree.SubElement(eff, qn("a:outerShdw"), blurRad=str(int(blur * 9525)), dist=str(int(math.hypot(x, y) * 9525)),
                              dir=str(int((math.degrees(math.atan2(y, x)) % 360) * 60000)), algn="ctr", rotWithShape="0")
        clr = etree.SubElement(sh, qn("a:srgbClr"), val=c[0])
        etree.SubElement(clr, qn("a:alpha"), val=str(int(c[1] * 100000)))
        return True

    # ---------- text ----------
    def fill_text(self, tf, container, st_box=None, cell=False):
        """container = .tx div or .cell div"""
        cst = style(container)
        if not cell:
            tf.word_wrap = cst.get("white-space") != "pre"
            tf.auto_size = MSO_AUTO_SIZE.NONE
            p4 = pad(cst) or (0, 0, 0, 0)
            tf.margin_top, tf.margin_right = Emu(int(p4[0] * 9525)), Emu(int(p4[1] * 9525))
            tf.margin_bottom, tf.margin_left = Emu(int(p4[2] * 9525)), Emu(int(p4[3] * 9525))
            tf.vertical_anchor = ANCHOR.get(cst.get("justify-content", "flex-start"), MSO_ANCHOR.TOP)
        paras = container.xpath("./p")
        first = True
        for p in paras:
            para = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            ps = style(p)
            para.alignment = ALIGN.get(ps.get("text-align", "left"), PP_ALIGN.LEFT)
            lh = ps.get("line-height")
            if lh:
                if lh.endswith("px"): para.line_spacing = Pt(fpx(lh) / PT)
                else:
                    try: para.line_spacing = float(lh) / self.ln
                    except ValueError: pass
            if fpx(ps.get("margin-top")): para.space_before = Pt(fpx(ps.get("margin-top")) / PT)
            if fpx(ps.get("margin-bottom")): para.space_after = Pt(fpx(ps.get("margin-bottom")) / PT)
            pPr = para._p.get_or_add_pPr()
            if fpx(ps.get("padding-left")): pPr.set("marL", str(int(fpx(ps.get("padding-left")) * 9525)))
            if fpx(ps.get("text-indent")): pPr.set("indent", str(int(fpx(ps.get("text-indent")) * 9525)))
            base_px = fpx(ps.get("font-size"), 24)
            spans = p.xpath("./span") or [p]
            wrote = False
            for s in spans:
                sst = {**ps, **(style(s) if s is not p else {})}
                if "bu" in (s.get("class") or "").split():
                    ch = (s.text_content() or "•").strip() or "•"
                    for t in ("a:buClr", "a:buSzPct", "a:buFont", "a:buChar", "a:buNone"):
                        for x in pPr.findall(qn(t)): pPr.remove(x)
                    c = color(sst.get("color"))
                    if c: etree.SubElement(etree.SubElement(pPr, qn("a:buClr")), qn("a:srgbClr"), val=c[0])
                    etree.SubElement(pPr, qn("a:buFont"), typeface=self.family)
                    etree.SubElement(pPr, qn("a:buChar"), char=ch[0])
                    if not fpx(ps.get("padding-left")):
                        pPr.set("marL", str(int(base_px * 1.2 * 9525))); pPr.set("indent", str(int(-base_px * 1.2 * 9525)))
                    continue
                pieces = []
                if s.text: pieces.append(s.text)
                for chn in s:
                    pieces.append("\n" if chn.tag == "br" else chn.text_content())
                    if chn.tail: pieces.append(chn.tail)
                text = "".join(pieces).replace("​", "")
                for k, piece in enumerate(text.split("\n")):
                    if k: para.add_line_break()
                    if not piece: continue
                    r = para.add_run(); r.text = piece; wrote = True
                    self.run_fmt(r, sst)
            if not wrote:
                endp = para._p.get_or_add_endParaRPr()
                endp.set("sz", str(int(round(base_px / PT * 100))))
        return tf

    def run_fmt(self, r, st):
        f = r.font
        f.size = Pt(fpx(st.get("font-size"), 24) / PT)
        f.bold = st.get("font-weight") in ("700", "bold", "600", "800")
        if st.get("font-style") == "italic": f.italic = True
        if "underline" in st.get("text-decoration", ""): f.underline = True
        c = color(st.get("color"))
        if c:
            f.color.rgb = RGBColor.from_string(c[0])
            if c[1] < 1: self.alpha(r._r.get_or_add_rPr().find(qn("a:solidFill")), c[1])
        rPr = r._r.get_or_add_rPr()
        if fpx(st.get("letter-spacing")): rPr.set("spc", str(int(round(fpx(st.get("letter-spacing")) / PT * 100))))
        if st.get("vertical-align") == "super": rPr.set("baseline", "30000")
        for tag in ("a:latin", "a:ea", "a:cs"):
            e = rPr.find(qn(tag))
            if e is None: e = etree.SubElement(rPr, qn(tag))
            e.set("typeface", self.family)

    # ---------- shapes ----------
    def build(self, slide, el):
        """add the element to the slide; returns the new shape's XML element"""
        tag, cls, st = el.tag, (el.get("class") or "").split(), style(el)
        name = el.get("data-name") or "Shape"
        if tag == "table": shp = self.table(slide, el, st)
        elif "pic" in cls: shp = self.picture(slide, el, st, cls)
        elif el.get("data-prst") == "line": shp = self.connector(slide, el, st)
        else: shp = self.shape(slide, el, st)
        shp.name = name
        rot = re.search(r"rotate\(([-\d.]+)deg\)", st.get("transform", ""))
        if rot: shp.rotation = float(rot.group(1))
        return shp._element

    def shape(self, slide, el, st):
        what = el.get("data-name")
        svg = el.xpath("./svg")
        prst = el.get("data-prst")
        rad = st.get("border-radius", "")
        bg, border = st.get("background") or st.get("background-color"), st.get("border")
        svg_fill = svg_stroke = None
        if svg:
            body = svg[0].xpath(".//*[local-name()='path' or local-name()='rect' or local-name()='line']")
            if body:
                svg_fill = body[0].get("fill"); sw = body[0].get("stroke-width")
                if body[0].get("stroke") not in (None, "none"): svg_stroke = f"{sw or 1}px solid {body[0].get('stroke')}"
            bg, border = svg_fill if svg_fill != "none" else None, svg_stroke
        tx = el.xpath('./div[contains(@class,"tx")]')
        plain_text = tx and not bg and not border and not st.get("box-shadow") and not prst
        x, y, w, h = self.box(st)
        if plain_text:
            shp = slide.shapes.add_textbox(x, y, w, h)
        else:
            kind = MSO_SHAPE.RECTANGLE
            if rad.strip() == "50%": kind = MSO_SHAPE.OVAL
            elif fpx(rad): kind = MSO_SHAPE.ROUNDED_RECTANGLE
            shp = slide.shapes.add_shape(kind, x, y, w, h)
            if prst and prst not in ("custom",):
                shp._element.spPr.find(qn("a:prstGeom")).set("prst", prst)
            elif prst == "custom":
                self.warn(f"{what}: freeform shape exported as its bounding rectangle")
            if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
                shp.adjustments[0] = min(0.5, fpx(rad) / max(1, min(fpx(st.get("width"), 1), fpx(st.get("height"), 1))))
            self.set_fill(shp.fill, bg, self.warn, what)
            self.set_line(shp.line, border, what)
            st_el = shp._element.find(qn("p:style"))
            if st_el is not None: shp._element.remove(st_el)          # no theme style: text colour comes from the runs
            if st.get("box-shadow"):
                if not self.shadow(shp._element, st["box-shadow"]): self.warn(f"{what}: box-shadow not exported")
        if tx:
            self.fill_text(shp.text_frame, tx[0])
        elif not plain_text:
            shp.text_frame.text = ""
        return shp

    def connector(self, slide, el, st):
        line = el.xpath(".//*[local-name()='line']")[0]
        g = el.xpath(".//*[local-name()='g']")
        tr = g[0].get("transform", "") if g else ""
        x, y = fpx(st.get("left"), 0), fpx(st.get("top"), 0)
        w, h = fpx(st.get("width"), 0), fpx(st.get("height"), 0)
        x1, y1, x2, y2 = 0, 0, w, h
        m = re.search(r"scale\((-?1)\s+(-?1)\)", tr)
        if m:
            if m.group(1) == "-1": x1, x2 = w, 0
            if m.group(2) == "-1": y1, y2 = h, 0
        c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, self.E(x + x1), self.E(y + y1, "y"), self.E(x + x2), self.E(y + y2, "y"))
        col = color(line.get("stroke"))
        if col: c.line.color.rgb = RGBColor.from_string(col[0])
        c.line.width = Pt(fpx(line.get("stroke-width"), 1) / PT)
        ln = c.line._get_or_add_ln()
        if line.get("stroke-dasharray"): etree.SubElement(ln, qn("a:prstDash"), val="dash")
        for attr, tagn in (("marker-start", "a:headEnd"), ("marker-end", "a:tailEnd")):
            if line.get(attr): etree.SubElement(ln, qn(tagn), type="triangle")
        return c

    def picture(self, slide, el, st, cls):
        x, y, w, h = self.box(st)
        if "vid" in cls:
            v = el.xpath(".//video")[0]
            poster = v.get("poster") or (el.xpath(".//img/@src") or [None])[0]
            shp = slide.shapes.add_movie(self.media(v.get("src")), x, y, w, h,
                                         poster_frame_image=self.media(poster) if poster else None, mime_type="video/mp4")
            return shp
        img = el.xpath(".//img")[0]
        shp = slide.shapes.add_picture(self.media(img.get("src")), x, y, w, h)
        if "crop" in cls:
            ist = style(img)
            iw, ih = fpx(ist.get("width", "100%").rstrip("%"), 100) / 100, fpx(ist.get("height", "100%").rstrip("%"), 100) / 100
            l, t = -fpx(ist.get("left", "0%").rstrip("%"), 0) / 100 / iw, -fpx(ist.get("top", "0%").rstrip("%"), 0) / 100 / ih
            shp.crop_left, shp.crop_top = l, t
            shp.crop_right, shp.crop_bottom = 1 - l - 1 / iw, 1 - t - 1 / ih
        rad = st.get("border-radius", "")
        geom = shp._element.spPr.find(qn("a:prstGeom"))
        if rad.strip() == "50%": geom.set("prst", "ellipse")
        elif fpx(rad):
            geom.set("prst", "roundRect")
            for ch in list(geom): geom.remove(ch)
            av = etree.SubElement(geom, qn("a:avLst"))
            etree.SubElement(av, qn("a:gd"), name="adj", fmla="val %d" % round(
                fpx(rad) / max(1, min(fpx(st.get("width"), 1), fpx(st.get("height"), 1))) * 100000))
        if st.get("filter", "").startswith("drop-shadow"):
            self.shadow(shp._element, st["filter"][len("drop-shadow("):-1])
        return shp

    def table(self, slide, el, st):
        cols = [fpx(style(c).get("width"), 100) for c in el.xpath(".//col")]
        rows = el.xpath(".//tr")
        ncols = len(cols) or max(len(r.xpath("./td|./th")) for r in rows)
        heights = [fpx(style(r).get("height"), 40) for r in rows]
        x, y, w, h = self.box(st, h=sum(heights))
        gf = slide.shapes.add_table(len(rows), ncols, x, y, w, h)
        tbl = gf.table
        tblPr = tbl._tbl.tblPr
        for a in ("firstRow", "bandRow"): tblPr.set(a, "0")
        sid = tblPr.find(qn("a:tableStyleId"))
        if sid is None: sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
        sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"          # "No Style, No Grid"
        for k, cw in enumerate(cols[:ncols]): tbl.columns[k].width = self.E(cw)
        for k, rh in enumerate(heights): tbl.rows[k].height = self.E(rh, "y")
        taken = set()
        for ri, tr in enumerate(rows):
            ci = 0
            for td in tr.xpath("./td|./th"):
                while (ri, ci) in taken: ci += 1
                if ci >= ncols: break
                cs, rs = int(td.get("colspan", "1")), int(td.get("rowspan", "1"))
                cell = tbl.cell(ri, ci)
                if cs > 1 or rs > 1:
                    cell.merge(tbl.cell(min(ri + rs, len(rows)) - 1, min(ci + cs, ncols) - 1))
                for a in range(rs):
                    for b in range(cs): taken.add((ri + a, ci + b))
                tst = style(td)
                p4 = pad(tst) or (3.6, 7.2, 3.6, 7.2)
                cell.margin_top, cell.margin_right = Emu(int(p4[0] * 9525)), Emu(int(p4[1] * 9525))
                cell.margin_bottom, cell.margin_left = Emu(int(p4[2] * 9525)), Emu(int(p4[3] * 9525))
                cell.vertical_anchor = ANCHOR.get(tst.get("vertical-align", "top"), MSO_ANCHOR.TOP)
                bgc = color(tst.get("background") or tst.get("background-color"))
                if bgc:
                    cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor.from_string(bgc[0])
                else:
                    cell.fill.background()
                tcPr = cell._tc.get_or_add_tcPr()
                for side, tagn in (("left", "a:lnL"), ("right", "a:lnR"), ("top", "a:lnT"), ("bottom", "a:lnB")):
                    v = tst.get(f"border-{side}") or tst.get("border")
                    lnel = etree.Element(qn(tagn))
                    m = re.match(r"([\d.]+)px\s+\w+\s+(.+)$", v or "")
                    c = color(m.group(2)) if m else None
                    if m and c and float(m.group(1)) > 0:
                        lnel.set("w", str(int(float(m.group(1)) * 9525)))
                        etree.SubElement(etree.SubElement(lnel, qn("a:solidFill")), qn("a:srgbClr"), val=c[0])
                    else:
                        lnel.set("w", "0"); etree.SubElement(lnel, qn("a:noFill"))
                    tcPr.insert(["a:lnL", "a:lnR", "a:lnT", "a:lnB"].index(tagn), lnel)
                box = td.xpath('./div[contains(@class,"cell")]')
                tf = cell.text_frame
                if box: self.fill_text(tf, box[0], cell=True)
                ci += cs
        return gf


def strip_placeholders(slide):
    for ph in list(slide.placeholders):
        ph._element.getparent().remove(ph._element)


def deep(el): return copy.deepcopy(el)
