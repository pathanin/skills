"""Per-shape diff between a deck's conversion baseline (DECK/.source/baseline.html) and its
current index.html. Used by export.py; run alone to print the change list:

    python html_diff.py DECK
"""
import re
import sys
from pathlib import Path

from lxml import html as LH


def slides(path):
    doc = LH.fromstring(Path(path).read_text(encoding="utf-8"))
    return doc.xpath('//section[contains(concat(" ",@class," ")," slide ")]')


def style(el):
    d = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            d[k.strip().lower()] = v.strip()
    return d


def classes(el):
    return (el.get("class") or "").split()


def runs(el):
    """normalized paragraphs of a text container: [[(text, size, bold, color), ...], ...]"""
    out = []
    for p in el.xpath('.//p'):
        pst = style(p)
        rr = []
        spans = p.xpath('./span')
        items = spans if spans else [p]
        for s in items:
            st = {**pst, **style(s)} if s is not p else pst
            t = s.text_content().replace("​", "")
            col = st.get("color", "")
            m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", col)
            if m: col = "#%02X%02X%02X" % tuple(int(v) for v in m.groups())
            sz = st.get("font-size", "")
            sz = "%.2f" % float(sz[:-2]) if sz.endswith("px") else sz
            rr.append((t, sz, st.get("font-weight") in ("700", "bold"), col.upper()))
        m = []                      # merge adjacent runs with identical formatting (browser edits split/merge spans)
        for r in rr:
            if m and m[-1][1:] == r[1:]: m[-1] = (m[-1][0] + r[0],) + r[1:]
            elif r[0]: m.append(r)
        out.append(m)
    while out and not out[-1]: out.pop()
    return out


def texts(el):
    if el.tag == "table":
        return [runs(c) for c in el.xpath('.//div[contains(@class,"cell")]')]
    tx = el.xpath('./div[contains(@class,"tx")]')
    return runs(tx[0]) if tx else None


GEOM = ("left", "top", "width", "height")


def num(v):
    try: return round(float(v[:-2]), 1)
    except (TypeError, ValueError): return None


def describe(el):
    st = style(el)
    return {"tag": el.tag, "cls": el.get("class"), "geom": tuple(num(st.get(k)) for k in GEOM),
            "rest": {k: v for k, v in st.items() if k not in GEOM and not k.startswith("--")},
            "inner": LH.tostring(el, encoding="unicode") if el.tag != "table" else None,
            "text": texts(el), "el": el, "id": el.get("data-id") or None, "name": el.get("data-name")}


def shapes(sec):
    """ordered list of exportable elements (master/layout artwork excluded)"""
    return [describe(el) for el in sec if el.get("data-name") and el.get("data-layer") != "master"]


def mapping(base, cur):
    """current slide index -> baseline slide index (first use of each data-src), else None (build anew)"""
    by_src = {s.get("data-src"): j for j, s in enumerate(base) if s.get("data-src")}
    out, used = {}, set()
    for i, s in enumerate(cur):
        k = s.get("data-src")
        if k in by_src and k not in used:
            out[i] = by_src[k]; used.add(k)
        else:
            out[i] = None
    return out


def svg_sig(d):
    """the drawn part of a preset/line shape, without the text"""
    el = d["el"]
    svg = el.xpath("./svg")
    return LH.tostring(svg[0], encoding="unicode") if svg else ""


def diff_slide(bsec, csec):
    b = shapes(bsec) if bsec is not None else []
    c = shapes(csec)
    bid = {d["id"]: d for d in b if d["id"]}
    seen = set()
    ch = {"deleted": [], "added": [], "changed": {}}
    pairs = []
    for d in c:
        o = bid.get(d["id"]) if d["id"] and d["id"] not in seen else None
        if o is None:
            ch["added"].append(d)
            continue
        seen.add(d["id"])
        kinds = []
        if o["geom"] != d["geom"]: kinds.append("geom")
        if o["cls"] != d["cls"] or o["rest"] != d["rest"] or svg_sig(o) != svg_sig(d) or o["tag"] != d["tag"]: kinds.append("style")
        if o["text"] != d["text"]: kinds.append("text")
        if d["tag"] != "table" and "pic" in classes(d["el"]):
            if [i.get("src") for i in o["el"].iter("img", "video")] != [i.get("src") for i in d["el"].iter("img", "video")]:
                kinds.append("style")
        if kinds: ch["changed"][d["id"]] = (kinds, o, d)
        pairs.append(d["id"])
    ch["deleted"] = [d for d in b if d["id"] and d["id"] not in seen]
    return ch, c


def diff(deck):
    deck = Path(deck)
    cur = slides(deck / "index.html")
    basef = deck / ".source" / "baseline.html"
    base = slides(basef) if basef.exists() else []
    mp = mapping(base, cur) if base else {i: None for i in range(len(cur))}
    result = []
    for i, s in enumerate(cur):
        j = mp[i]
        ch, c = diff_slide(base[j] if j is not None else None, s)
        result.append({"n": i + 1, "src": int(base[j].get("data-src")) if j is not None else None,
                       "dup_of": int(s.get("data-src")) if j is None and s.get("data-src") else None,
                       "title": s.get("data-title"), "ch": ch, "cur": c, "sec": s,
                       "base_sec": base[j] if j is not None else None})
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for r in diff(sys.argv[1]):
        ch = r["ch"]
        if r["src"] is None:
            print(f"s{r['n']}  NEW slide ({len(r['cur'])} shapes{', layout of source slide %d' % r['dup_of'] if r['dup_of'] else ''})  {r['title']}")
            continue
        if not (ch["deleted"] or ch["added"] or ch["changed"]): continue
        print(f"s{r['n']} <- source slide {r['src']}  {r['title']}")
        for d in ch["deleted"]: print("   - del", d["name"])
        for d in ch["added"]: print("   + add", d["name"])
        for k, (kinds, o, d) in ch["changed"].items(): print("   ~", d["name"], kinds)
