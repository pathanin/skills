"""Render assets/banner.gif from assets/banner.svg: the network dots drift on a seamless 4s loop.

  python3 assets/render-banner-gif.py assets/banner.svg 48 /tmp/frames
  ffmpeg -framerate 12 -i /tmp/frames/f%03d.png -vf "scale=600:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=32[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" -loop 0 assets/banner.gif

Needs Python Playwright with Chromium. Fewer than 32 colors turns the orange accent brown.
"""
import sys, math
from playwright.sync_api import sync_playwright
svg = open(sys.argv[1]).read()
FRAMES = int(sys.argv[2]); OUT = sys.argv[3]
JS = r"""
(t) => {
  const svg = document.querySelector('svg');
  if (!window._init) {
    const groups = [...svg.querySelectorAll('g')];
    const edgeG = groups[0], dotG = groups[1], accG = groups[2];
    // unique node positions from grey dots
    const nodes = [...dotG.querySelectorAll('circle')].map((c,i)=>({x:+c.getAttribute('cx'),y:+c.getAttribute('cy'),el:[c],
      ph1:(i*2.399)%6.283, ph2:(i*1.618*3.1)%6.283, fx:1+(i%2), fy:1+((i+1)%3===0?1:0)}));
    const find=(x,y)=>nodes.find(n=>Math.abs(n.x-x)<0.01&&Math.abs(n.y-y)<0.01);
    window._acc=[];
    accG.querySelectorAll('circle').forEach(c=>{const n=find(+c.getAttribute('cx'),+c.getAttribute('cy')); n.el.push(c); window._acc.push({c,n,r:+c.getAttribute('r')});});
    const edges=[];
    edgeG.querySelectorAll('path').forEach(p=>{
      const segs=p.getAttribute('d').trim().split('M').filter(Boolean);
      segs.forEach(s=>{const m=s.match(/([\d.]+) ([\d.]+) L([\d.]+) ([\d.]+)/); edges.push([find(+m[1],+m[2]),find(+m[3],+m[4])]);});
      p.remove();
    });
    window._lines=edges.map(([a,b])=>{const l=document.createElementNS('http://www.w3.org/2000/svg','line'); edgeG.appendChild(l); return {l,a,b};});
    window._nodes=nodes; window._init=true;
  }
  const A=7, T=2*Math.PI*t;
  for (const n of window._nodes){
    n.cx=n.x+A*Math.sin(n.fx*T+n.ph1); n.cy=n.y+A*Math.cos(n.fy*T+n.ph2);
    n.el.forEach(e=>{e.setAttribute('cx',n.cx.toFixed(2)); e.setAttribute('cy',n.cy.toFixed(2));});
  }
  for (const {l,a,b} of window._lines){l.setAttribute('x1',a.cx);l.setAttribute('y1',a.cy);l.setAttribute('x2',b.cx);l.setAttribute('y2',b.cy);}
  window._acc.forEach((o,i)=>{o.c.setAttribute('r',(o.r*(1+0.35*Math.max(0,Math.sin(T-i*1.256)))).toFixed(2));});
}
"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width':1200,'height':300})
    pg.set_content('<html><body style="margin:0">'+svg+'</body></html>')
    for f in range(FRAMES):
        pg.evaluate(JS, f/FRAMES)
        pg.screenshot(path=f"{OUT}/f{f:03d}.png")
    b.close()
