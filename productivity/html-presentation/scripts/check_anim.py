"""Summarize the entrance animation of an exported deck: python check_anim.py DECK.pptx [slide ...]"""
import sys, zipfile, re
from collections import Counter
from lxml import etree
ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
z = zipfile.ZipFile(sys.argv[1])
show = {int(a) for a in sys.argv[2:]}
nums = sorted(int(m.group(1)) for n in z.namelist() if (m := re.match(r"ppt/slides/slide(\d+)\.xml$", n)))
tot = Counter(); worst = 0
for n in nums:
    t = etree.fromstring(z.read(f"ppt/slides/slide{n}.xml"))
    main = t.xpath('//p:cTn[@nodeType="mainSeq"]', namespaces=ns)
    if not main: print("slide", n, "no animation (nothing on the slide to animate, or stage 2 did not run)"); continue
    eff = main[0].xpath('.//p:cTn[@presetClass]', namespaces=ns)
    groups = main[0].xpath('./p:childTnLst/p:par/p:cTn', namespaces=ns)       # click groups
    end = 0
    for c in eff:
        kind = (c.get("presetClass"), c.get("presetID"), c.get("nodeType")); tot[kind] += 1
        d = int((c.xpath('./p:stCondLst/p:cond/@delay', namespaces=ns) or ["0"])[0])
        dur = max([int(v) for v in c.xpath('.//p:cBhvr/p:cTn/@dur', namespaces=ns) if v.isdigit()] or [0])
        gd = int((c.getparent().getparent().getparent().xpath('./p:stCondLst/p:cond/@delay', namespaces=ns) or ["0"])[0])
        end = max(end, gd + d + dur)
        if n in show: print(n, c.xpath('.//p:spTgt/@spid', namespaces=ns)[0], kind, "start", gd + d, "dur", dur)
    first = groups[0].xpath('./p:stCondLst/p:cond', namespaces=ns) if groups else []
    auto = any(x.get("evt") == "onBegin" for x in first)
    worst = max(worst, end)
    if len(groups) != 1 or not auto: print("slide", n, f"{len(groups)} click groups, auto-start={auto}")
print(dict(tot)); print("longest slide reveal: %.1f s" % (worst / 1000))
