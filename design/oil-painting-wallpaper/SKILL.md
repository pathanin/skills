---
name: oil-painting-wallpaper
description: Manual-only code-drawn wallpaper render, invoked with /oil-painting-wallpaper. Paints a landscape entirely in code, as oil on linen (multi-bristle stroke engine) or as layered paper cut (shadowed, hand-cut paper pieces), from one polygon scene in headless Chromium, and exports a PNG at any resolution — 4K, ultrawide, or phone.
argument-hint: "[scene, style (oil | paper cut), resolution, number of variations]"
disable-model-invocation: true
---

# Oil-painting wallpaper

Draw a landscape entirely in code and export it as a PNG at the size the user asks for, in one of two styles:

- **Oil** (default): a stroke engine paints over the scene with thousands of directional, multi-bristle brush strokes on a woven linen ground.
- **Paper cut**: every region becomes a sheet of cut paper with a rough edge and a soft drop shadow, stacked back to front.

Both styles use the same scene, a list of flat-coloured polygons, rendered in headless Chromium through Playwright.

## Inputs to settle first

- **Style**: `oil` unless the user asks for paper cut (or cut paper, papercraft, layered paper). Do not ask about style.
- **Scene**: the subject, time of day, mood and any must-have elements. If the user gives only a theme ("a beach"), pick the palette and composition yourself.
- **Resolution**: default 3840 x 2160 (4K UHD). Common alternatives: 2560 x 1440, 5120 x 2160 (ultrawide), 1170 x 2532 or 1080 x 1920 (phone), 6016 x 3384 (6K). Stay at or below about 8000 px per side, because Chromium's canvas limit is roughly 16384 px per side and 268M px in total.
- **How many variations**: each one is a new scene or a new seed.

Take these from the text after `/oil-painting-wallpaper`. If the scene, resolution or number of variations is missing, ask for all of the missing ones in a single message. If the user says to go ahead without answering, use the defaults and state them.

## Coordinate system

- The logical canvas height is always H = 400. The logical width is W = round(400 x width / height), so W is 711 for 16:9, 948 for 21:9 and 225 for 9:16.
- **Compose the scene for the actual W.** A scene built for 711 does not reflow into portrait. For a new aspect ratio, place every element again (horizon, focal point, trees) relative to W.
- Stroke sizes are in logical units, so the texture looks the same at every resolution. Stroke counts scale with the area W x H.
- Every stroke depends only on the scene, the seed and W, not on the pixel size. Any resolution with the same W paints the same image, so a small render is an exact preview of the final one.

## Files (create in a working folder)

### engine.html (use verbatim, except the stroke counts the polishing loop tells you to raise)

```html
<!doctype html><html><body style="margin:0;background:#000">
<canvas id="cv"></canvas>
<script src="scene.js"></script>
<script>
'use strict';
{ // block scope, so scene.js can use any top-level names without clashing with the engine's
const Q=new URLSearchParams(location.search);
const PX=+Q.get('w')||3840, PY=+Q.get('h')||2160, H=400, W=Math.round(H*PX/PY), k=PX/W;
const clamp=(v,a=0,b=1)=>v<a?a:v>b?b:v, lerp=(a,b,t)=>a+(b-a)*t;
const SC=SCENES[+Q.get('s')||0];
if(Q.get('seed')) SC.seed=+Q.get('seed');
let seed=SC.seed; const R=()=>{ seed=(seed*1664525+1013904223)>>>0; return seed/4294967296; };
const rnd=(a=1,b)=>b===undefined?R()*a:a+R()*(b-a);
const hex=h=>{ if(h.length===4) h='#'+h[1]+h[1]+h[2]+h[2]+h[3]+h[3]; return [1,3,5].map(i=>parseInt(h.slice(i,i+2),16)); };
const rgba=(c,a=1)=>`rgba(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])},${a})`;
const shade=(c,f)=>c.map(v=>clamp(v*(1+f),0,255));
const mixc=(a,b,t)=>a.map((v,i)=>lerp(v,b[i],t));
const gradAt=(stops,y)=>{ if(y<=stops[0][0]) return hex(stops[0][1]); for(let i=1;i<stops.length;i++) if(y<=stops[i][0]) return mixc(hex(stops[i-1][1]),hex(stops[i][1]),(y-stops[i-1][0])/(stops[i][0]-stops[i-1][0])); return hex(stops[stops.length-1][1]); };

const REG=SC.build({W,H,rnd,hex,mixc,gradAt,lerp,clamp});
REG.forEach(r=>{ const xs=r.pts.map(p=>p[0]), ys=r.pts.map(p=>p[1]); r.box=[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
  r.area=(r.box[2]-r.box[0])*(r.box[3]-r.box[1]); if(r.col) r.rgb=hex(r.col); });
function pip(pts,x,y){ let c=false; for(let i=0,j=pts.length-1;i<pts.length;j=i++){ const [xi,yi]=pts[i],[xj,yj]=pts[j]; if((yi>y)!==(yj>y)&&x<(xj-xi)*(y-yi)/(yj-yi)+xi) c=!c; } return c; }
const inR=(r,x,y)=>{ const b=REG[r].box; return x>=b[0]&&x<=b[2]&&y>=b[1]&&y<=b[3]&&pip(REG[r].pts,x,y); };
const GS=.5, GX=W/GS|0, GY=H/GS|0, ID=new Uint16Array(GX*GY);
for(let gy=0;gy<GY;gy++) for(let gx=0;gx<GX;gx++){ const x=(gx+.5)*GS, y=(gy+.5)*GS; let r=REG.length-1; while(r>0&&!inR(r,x,y)) r--; ID[gy*GX+gx]=r; }
const idAt=(x,y)=>ID[clamp(Math.floor(y/GS),0,GY-1)*GX+clamp(Math.floor(x/GS),0,GX-1)];
const colorAt=(x,y)=>{ const r=REG[idAt(x,y)]; return r.cf?r.cf(x,y):r.grad?gradAt(r.grad,y):r.rgb; };

function angleAt(x,y,r){ const g=REG[r], d=g.dir||'horiz';
  if(d==='sky') return .28*Math.sin(y*.045+x*.012)+.18*Math.sin(x*.03);
  if(d==='radial') return Math.atan2(y-g.cy,x-g.cx)+Math.PI/2;
  if(d==='ray') return Math.atan2(y-g.cy,x-g.cx);
  if(d==='horiz') return rnd(-.08,.08);
  if(d==='hill') return .15*Math.cos(x*.02);
  if(d==='mtn') return .55*Math.sin(x*.035);
  if(d==='vert') return Math.PI/2;
  if(d==='angle') return g.a;
  if(d==='roof') return x<g.rx?-.72:.72;
  if(d==='pine') return x<g.tx?2.2:.95;
  if(d==='swirl') return Math.atan2(y-g.cy,x-g.cx)+Math.PI/2+.5*Math.sin(x*.3+y*.2);
  return 0;
}
function oilStroke(x,y,L,w){ const r=idAt(x,y), a=angleAt(x,y,r)+rnd(-.3,.3), dx=Math.cos(a), dy=Math.sin(a), st=.5; let l0=0, l1=0;
  while(l0<L/2&&idAt(x-dx*(l0+st),y-dy*(l0+st))===r) l0+=st; while(l1<L/2&&idAt(x+dx*(l1+st),y+dy*(l1+st))===r) l1+=st;
  const col=colorAt(x,y).map(v=>clamp(v*rnd(.9,1.1)+rnd(-8,8),0,255));
  return {p0:[x-dx*l0,y-dy*l0],p1:[x+dx*l1,y+dy*l1],w:Math.min(w,1.2+(l0+l1)*.8),col,dx,dy,bend:rnd(-.3,.3)}; }
function paintStroke(b,s){ const {p0,p1,w,col,dx,dy}=s; let nx=-dy, ny=dx; if(nx*-.7+ny*-.7<0){ nx=-nx; ny=-ny; }
  const q=(o,lw,stl)=>{ b.lineWidth=lw; b.strokeStyle=stl; b.beginPath(); b.moveTo(p0[0]+nx*o,p0[1]+ny*o); b.quadraticCurveTo((p0[0]+p1[0])/2+nx*(o+s.bend*w),(p0[1]+p1[1])/2+ny*(o+s.bend*w),p1[0]+nx*o,p1[1]+ny*o); b.stroke(); };
  b.lineCap='round'; q(0,w,rgba(col));
  for(const o of [-.32,-.1,.12,.33]) q(o*w,w*.16,rgba(shade(col,rnd(-.16,.16)),.55));
  q(-.36*w,w*.14,'rgba(255,248,230,.24)'); q(.4*w,w*.14,'rgba(40,24,10,.22)'); }

const cv=document.getElementById('cv'); cv.width=PX; cv.height=PY; const b=cv.getContext('2d');
b.setTransform(k,0,0,k,0,0);
let n=0;
if(SC.style==='papercut'){
  const t=document.createElement('canvas'); t.width=t.height=256; const tc=t.getContext('2d'), td=tc.createImageData(256,256);
  for(let i=0;i<td.data.length;i+=4){ const v=R()*255; td.data[i]=td.data[i+1]=td.data[i+2]=v; td.data[i+3]=255; } tc.putImageData(td,0,0);
  const grain=b.createPattern(t,'repeat');
  const trace=p=>{ b.beginPath(); b.moveTo(p[0][0],p[0][1]); for(let i=1;i<p.length;i++) b.lineTo(p[i][0],p[i][1]); b.closePath(); };
  // hand-cut edge: a jittered point every 3 units; points on the frame are pushed past it instead, so no cut edge shows there
  const cut=p=>{ const o=[], jit=(v,M)=>v<=0?-3:v>=M?M+3:v+rnd(-.5,.5);
    for(let i=0;i<p.length;i++){ const [x0,y0]=p[i], [x1,y1]=p[(i+1)%p.length], m=Math.max(1,Math.ceil(Math.hypot(x1-x0,y1-y0)/3));
      for(let j=0;j<m;j++) o.push([jit(lerp(x0,x1,j/m),W),jit(lerp(y0,y1,j/m),H)]); } return o; };
  const fillOf=r=>{ if(r.grad){ const s=r.grad, y0=s[0][0], y1=s[s.length-1][0], gr=b.createLinearGradient(0,y0,0,Math.max(y1,y0+1)); s.forEach(([y,c])=>gr.addColorStop(clamp((y-y0)/(y1-y0||1)),c)); return gr; }
    if(!r.cf) return rgba(mixc(r.rgb,[255,255,255],.07));
    // cf: bake the colour function into a texture (1 texel per unit, padded past the jittered edge), smoothed when scaled up
    const x0=Math.floor(clamp(r.box[0],-5,W+5))-4, y0=Math.floor(clamp(r.box[1],-5,H+5))-4, cw=Math.ceil(clamp(r.box[2],-5,W+5))-x0+5, ch=Math.ceil(clamp(r.box[3],-5,H+5))-y0+5;
    const c=document.createElement('canvas'); c.width=cw; c.height=ch; const cc=c.getContext('2d'), id=cc.createImageData(cw,ch);
    for(let y=0;y<ch;y++) for(let x=0;x<cw;x++){ const v=r.cf(x0+x+.5,y0+y+.5), q=(y*cw+x)*4; id.data[q]=v[0]; id.data[q+1]=v[1]; id.data[q+2]=v[2]; id.data[q+3]=255; }
    cc.putImageData(id,0,0); const pt=b.createPattern(c,'no-repeat'); pt.setTransform(new DOMMatrix().translate(x0,y0)); return pt; };
  b.fillStyle=SC.ground||'#2a2530'; b.fillRect(0,0,W,H);
  REG.forEach((r,i)=>{ const p=i?cut(r.pts):[[0,0],[W,0],[W,H],[0,H]];
    b.save(); if(i){ b.shadowColor='rgba(20,10,30,.38)'; b.shadowBlur=3*k; b.shadowOffsetX=1.2*k; b.shadowOffsetY=2.4*k; }
    b.fillStyle=fillOf(r); trace(p); b.fill(); b.restore();
    b.save(); b.globalCompositeOperation='multiply'; b.globalAlpha=.13; b.fillStyle=grain; trace(p); b.fill(); b.restore();
    if(i){ b.strokeStyle='rgba(255,255,255,.3)'; b.lineWidth=.6; trace(p); b.stroke(); }
    n++; });
} else {
b.fillStyle=SC.ground||'#b98d63'; b.fillRect(0,0,W,H);
b.save(); b.globalAlpha=.08; b.strokeStyle='#3b2a1a'; b.lineWidth=.3;
for(let i=0;i<Math.max(W,H);i+=1){ b.beginPath(); b.moveTo(0,i); b.lineTo(W,i); b.stroke(); b.beginPath(); b.moveTo(i,0); b.lineTo(i,H); b.stroke(); } b.restore();
const A=W*H/(400*400);
const add=s=>{ paintStroke(b,s); n++; };
for(let i=0,N=Math.round(2400*A);i<N;i++) add(oilStroke(rnd(W),rnd(H),rnd(14,24),rnd(8,11)));
for(let i=0,N=Math.round(5200*A);i<N;i++) add(oilStroke(rnd(W),rnd(H),rnd(7,12),rnd(3.5,5.5)));
for(let i=0,N=Math.round(3500*A);i<N;i++) add(oilStroke(rnd(W),rnd(H),rnd(4,8),rnd(1.8,3)));
let e=0, tries=0; const N3=Math.round(1050*A*1.4); while(e<N3&&tries++<N3*100){ const x=rnd(W), y=rnd(H), r=idAt(x,y); if(r!==idAt(x+3,y)||r!==idAt(x,y+3)||r!==idAt(x-3,y)||r!==idAt(x,y-3)){ add(oilStroke(x,y,rnd(4,8),rnd(1.8,3))); e++; } }
REG.forEach((r,ri)=>{ if(r.area<900){ const m=r.area<30?12:40; for(let q=0;q<m;q++){ const x=rnd(r.box[0],r.box[2]), y=rnd(r.box[1],r.box[3]); if(idAt(x,y)===ri) add(oilStroke(x,y,rnd(2,6),r.area<30?rnd(.8,1.4):rnd(1.2,2))); } } });
b.setTransform(1,0,0,1,0,0);
const g=document.createElement('canvas'); g.width=g.height=256; const gc=g.getContext('2d'), d=gc.createImageData(256,256);
for(let i=0;i<d.data.length;i+=4){ const v=R()*255; d.data[i]=d.data[i+1]=d.data[i+2]=v; d.data[i+3]=255; } gc.putImageData(d,0,0);
b.save(); b.globalCompositeOperation='multiply'; b.globalAlpha=.07; b.fillStyle=b.createPattern(g,'repeat'); b.fillRect(0,0,PX,PY); b.restore();
}
window.DONE=n;
}
</script></body></html>
```

**Oil** (the default) paints in these passes:

1. A linen ground with a woven grid.
2. A broad underpainting pass.
3. A mid pass.
4. A fine detail pass.
5. Edge strokes placed on region borders.
6. Extra strokes inside small regions such as windows and stars.
7. A multiply grain layer at full resolution.

The per-bristle lines, the highlight bristle and the shadow bristle are what make the strokes read as oil paint.

**Paper cut** (`style:'papercut'`) lays each region down as one sheet of cut paper, back to front. The first region fills the whole canvas. Every later piece gets:

1. A hand-cut edge: a slightly jittered point every 3 units. Edges lying on the canvas frame run off the page instead, so no cut edge shows there.
2. A soft drop shadow down and to the right, cast onto everything beneath it.
3. A fill: `col` lightened 7% like pale construction paper, `grad` as a smooth vertical gradient, or `cf` baked into a smooth texture.
4. A paper-grain texture and a faint white rim along the cut.

Depth comes entirely from the stacking: each piece shadows the ones beneath it.

### render.js (use verbatim)

```js
// usage: node render.js <scene_index> <width> <height> <out.png|out.jpg> [seed] [crop]
// a .jpg name writes JPEG at quality .92; crop "x,y,w,h" (logical units) also writes <out>-crop.png at full resolution
const {chromium}=require('playwright'), fs=require('fs'), path=require('path'), {pathToFileURL}=require('url');
const [i='0',w='3840',h='2160',out='wallpaper.png',seed='',crop='']=process.argv.slice(2);
const save=(f,u)=>fs.writeFileSync(f,Buffer.from(u.split(',')[1],'base64'));
(async()=>{ const br=await chromium.launch(); const p=await br.newPage();
  let err=null; p.on('pageerror',e=>{ err=e.message; console.error('PAGE ERROR:',e.message); });
  // the engine paints synchronously during page load, so the navigation timeout must cover the whole render
  await p.goto(`${pathToFileURL(path.join(__dirname,'engine.html'))}?s=${i}&w=${w}&h=${h}${seed?'&seed='+seed:''}`,{timeout:600000});
  const n=await p.evaluate('window.DONE'); if(err||!n){ await br.close(); process.exit(1); }
  save(out,await p.evaluate(j=>document.getElementById('cv').toDataURL(j?'image/jpeg':'image/png',.92),/\.jpe?g$/i.test(out)));
  if(crop) save(out.replace(/\.\w+$/,'')+'-crop.png',await p.evaluate(c=>{ const cv=document.getElementById('cv'), k=cv.height/400, [cx,cy,cw,ch]=c.split(',').map(v=>Math.round(+v*k));
    const o=document.createElement('canvas'); o.width=cw; o.height=ch; o.getContext('2d').drawImage(cv,cx,cy,cw,ch,0,0,cw,ch); return o.toDataURL('image/png'); },crop));
  console.log('wrote',out,w+'x'+h,'strokes',n); await br.close(); })();
```

Run it with `NODE_PATH=$(npm root -g) node render.js 0 3840 2160 out.png`. A 4K render takes under 10 seconds, and an 8K render about 16.

If it fails with `Cannot find module 'playwright'`, run `npm i playwright` in the working folder and retry. If it then reports a missing browser, run `npx playwright install chromium`, but not when `PLAYWRIGHT_BROWSERS_PATH` is set: that means browsers are preinstalled (as in Claude Code on the web) and the error is something else.

### scene.js (write per request)

`scene.js` defines `const SCENES=[...]`. Each entry is `{name, seed, style?, ground?, build(C)}`, and `build` returns the regions **back to front** (later regions are painted on top). `style` is `'oil'` (the default) or `'papercut'`. To render one scene in both styles, add a second entry `{...SCENES[0], name:'…-papercut', style:'papercut'}`. `ground` is the colour under everything: linen brown for oil, and dark board (`#2a2530`) for paper cut. `C` provides `{W,H,rnd,hex,mixc,gradAt,lerp,clamp}`. Always use `C.rnd`, never `Math.random`, so a seed reproduces the same image exactly.

Each region is `{pts:[[x,y],...], dir, ...colour}`:

- **Colour** is one of three options:
  - `col:'#hex'` for a flat colour.
  - `grad:[[y,'#hex'],...]` for a vertical gradient, used for skies, sea and ground.
  - `cf:(x,y)=>[r,g,b]` for any colour function, used for glows, light beams and shaded cliffs.
- **Stroke direction (`dir`)**, used by oil only (paper cut ignores it):
  - `sky`: wavy sky flow.
  - `horiz`: water, clouds and walls.
  - `hill`: gentle rolling curves.
  - `mtn`: diagonal mountain strokes.
  - `vert`: trunks, towers and cacti.
  - `angle` + `a`: a fixed angle in radians.
  - `radial` + `cx,cy`: strokes circle a point, used for sun, moon and halos.
  - `ray` + `cx,cy`: strokes point outward, used for beams and perspective roads.
  - `roof` + `rx`: the two slopes of a roof.
  - `pine` + `tx`: drooping pine branches.
  - `swirl` + `cx,cy`: foliage.
- **The first region must cover the entire canvas**, usually the sky. It is the fallback for every pixel.

Start the file with these helpers, and reuse or extend them as needed:

```js
const TAU=Math.PI*2;
const circ=(cx,cy,r,n=60,sx=1)=>Array.from({length:n},(_,i)=>{const a=i/n*TAU; return [cx+Math.cos(a)*r*sx,cy+Math.sin(a)*r];});
const rect=(x0,y0,x1,y1)=>[[x0,y0],[x1,y0],[x1,y1],[x0,y1]];
const bandF=(W,fn,y1,step=4)=>{ const p=[]; for(let x=-2;x<=W+2;x+=step) p.push([x,fn(x)]); p.push([W+2,y1],[-2,y1]); return p; };
const blob=(cx,cy,Rr,ph=.5,sx=1.3,sy=.55)=>Array.from({length:60},(_,i)=>{const a=i/60*TAU, r=Rr*(1+.22*Math.sin(3*a+ph)+.12*Math.sin(5*a+1.3)); return [cx+Math.cos(a)*r*sx, Math.min(cy+12,cy+Math.sin(a)*r*sy)];});
// soft halo that blends the sky gradient toward a colour near (cx,cy)
const glowCF=(C,sky,cx,cy,r,col,s)=>(x,y)=>{ const d=Math.hypot(x-cx,y-cy)/r; return C.mixc(C.gradAt(sky,y),C.hex(col),s*Math.pow(C.clamp(1-d),1.6)); };
function pine(out,x,base,h,w,cols,snow){ out.push({pts:rect(x-3.5,base-h*.14,x+3.5,base),col:'#4b3326',dir:'vert'});
  for(let j=0;j<3;j++){ const top=base-h+j*h*.24, bot=top+h*.42, half=w/2*(.55+.25*j);
    out.push({pts:[[x,top],[x+half,bot],[x-half,bot]],col:cols[j%cols.length],dir:'pine',tx:x});
    if(snow) out.push({pts:[[x,top],[x+half*.45,top+h*.19],[x+half*.15,top+h*.16],[x-half*.1,top+h*.2],[x-half*.45,top+h*.18]],col:snow,dir:'pine',tx:x}); } }
function roundTree(out,C,x,base,r,cols){ out.push({pts:rect(x-2.5,base-r*1.2,x+2.5,base),col:'#4a3526',dir:'vert'});
  const cy=base-r*1.6; out.push({pts:blob(x,cy,r,C.rnd(6),.95,.9).map(([a,b])=>[a,Math.min(b,cy+r*.75)]),col:cols[0],dir:'swirl',cx:x,cy});
  out.push({pts:blob(x-r*.25,cy-r*.3,r*.5,C.rnd(6),.95,.8),col:cols[1],dir:'swirl',cx:x-r*.25,cy:cy-r*.3}); }
```

Here is an example scene entry, a lighthouse cove at sunset for W = 711:

```js
const SCENES=[{ name:'lighthouse-sunset', seed:1101, build(C){ const {W,H}=C, o=[];
  const sky=[[0,'#3b3f7e'],[90,'#7b5c9a'],[170,'#d9728a'],[230,'#f8b56a']];
  o.push({pts:rect(0,0,W,H),grad:sky,dir:'sky'});
  o.push({pts:circ(190,228,120),cf:glowCF(C,sky,190,228,120,'#ffd9a0',.6),dir:'radial',cx:190,cy:228});
  o.push({pts:circ(190,222,30),col:'#ffcf72',dir:'radial',cx:190,cy:222});
  o.push({pts:rect(0,228,W,H),grad:[[228,'#5a5d9a'],[300,'#35507e'],[400,'#1f3558']],dir:'horiz'});
  for(let i=0;i<9;i++){ const y=236+i*i*2.2, hw=26-i*1.8; o.push({pts:rect(190-hw,y,190+hw,y+2+i*.35),col:i<3?'#ffd58a':'#f2a86a',dir:'horiz'}); }
  o.push({pts:[[W+2,H+2],[430,H+2],[452,300],[486,226],[520,160],[620,140],[W+2,128]],cf:(x,y)=>C.mixc(C.hex('#8a5a52'),C.hex('#3e2b35'),C.clamp((y-150)/250)),dir:'angle',a:1.25});
  // ...grass cap, lighthouse (tapered tower + stripe bands + lamp + roof), rocks, foam lines
  return o; } }];
```

## Composition guidance

- Give each wallpaper a clear focal point placed off-centre (roughly on the thirds), with one light source such as a sun, moon or lit windows.
- Across a set, vary the horizon height (low horizon with a big sky, or high horizon with lots of land), the focal side, and the palette (warm dusk, cold night, bright day).
- Use leading lines: a road, a river, a sun reflection, or a path into the scene.
- Build depth with layers: hazy far range, mid hills, detailed foreground. Make the near layers darker or more saturated.
- Keep important detail away from the centre-bottom if the image is a desktop wallpaper (icons and the dock sit there), and away from the top of a phone wallpaper (the clock sits there).
- Small details such as stars, birds, windows and glints need their own small regions so the small-region pass paints them crisply.

For paper cut, also:

- Paper has no brushwork to carry detail, so every detail is its own piece stacked on top, such as snow caps, windows, doors and each tier of a pine.
- Keep to a limited palette of about 8 to 12 flat colours and simple, bold silhouettes.
- Pieces are separated only by their shadows, so give every depth band (far range, mid hills, near hills, water) a clear step in value from the band behind it.
- Replace `glowCF` halos with 2 or 3 flat concentric discs in progressively lighter tints around the sun or moon. A gradient halo cut from paper shows as a ghostly ring.
- Use `grad` for the sky and large water only. Use `cf` only for large pieces with a real edge, such as a shaded cliff.

## Workflow, including the polishing loop

1. Settle the scene, the resolution and the number of variations, then compute W.
2. Write `scene.js`, one entry per wallpaper.
3. Render a preview of each wallpaper at (s x W) by (s x 400) px, with s = 2 for landscape and s = 3 for portrait (for example 1422 x 800 for W = 711). This keeps the same W, so the preview shows exactly the painting the final render will produce, in about 2 seconds.
4. **Review each preview visually** with the Read tool. Fix what you see, re-render only the changed scenes, and review again. Repeat until clean. These are the problems found in earlier runs:
   - **(Oil) Linen showing through as brown flecks**: coverage is too thin. Raise the underpainting count (2400 x A) and the mid count (5200 x A). Do not lower them.
   - **Glow halos around small objects** (for example, glows behind houses looked like snowballs): drop the glow or make it much weaker. Only large light sources should get `glowCF` halos.
   - **Stripes that look like stairs**: evenly spaced, full-width ledges or strata look artificial. Use 3 or 4 short strata at irregular spacing, in a colour close to the base.
   - **Unreadable blobs**, such as a dark polygon on a cliff face: remove them or make their meaning clear.
   - **Broken or disconnected shapes**, such as a road drawn in pieces: the polygon is self-intersecting. Order the points as the left edge up, then the right edge down.
   - **Focal element hidden**, such as a sun behind a mesa: check the draw order and the overlap, and move the element into a gap.
   - **(Oil) Elements lost in the texture**, such as hay bales: add a darker shadow region offset beneath them for contrast.
   - **(Oil) Regions too thin to paint**: anything under about 1.5 logical units wide gets overpainted. Widen it or add it later in the list.
   - **(Paper cut) Ghostly ring around the sun**: a `glowCF` halo. Replace it with flat concentric discs.
   - **(Paper cut) Bands that merge**: two neighbouring pieces too close in value. Lighten the farther one or darken the nearer one.
   - **(Paper cut) Specks instead of details**: pieces under about 2.5 units across are swallowed by their own shadow and rim. Enlarge them or drop them.
   - **JS errors**: `render.js` prints PAGE ERROR. Common causes are a duplicate `const` inside `scene.js`, a region with no `col`, `grad` or `cf`, and `-x**2`, which must be written `-(x**2)`.
5. Render each wallpaper at the final resolution, passing a crop of about 240 x 135 logical units around the focal point, for example `node render.js 0 3840 2160 oil-lighthouse-sunset-3840x2160.png '' 70,150,240,135`. The empty `''` keeps the scene's own seed. Look at the `-crop.png` with the Read tool to check the brushwork or the cut edges at 1:1. Never Read the full-size file, which is tens of MB.
6. Deliver the finished files. Name them descriptively, starting with the style (for example `oil-lighthouse-sunset-3840x2160.png` or `papercut-lakeside-cabin-3840x2160.png`), and save them in the working directory or wherever the user asked. Delete the previews and crops. Give the paths with a one-line caption, and if a tool for sending files to the user is available, send the files with it too.
7. Offer next steps: re-render with a new seed (`node render.js i w h out.png 1234`) for a different stroke layout or different cut edges, render the same scene in the other style, try another aspect ratio (which needs the composition redone for the new W), or change the palette.

## Notes

- An oil PNG is about 19 MB at 4K and 70 MB at 8K; a paper-cut PNG is about 11 MB at 4K. If the user wants something smaller, give the output a `.jpg` name and `render.js` writes a JPEG at quality 92.
- To reproduce an image exactly, keep the same scene, seed and W. Any resolution with that W paints the same strokes; only the fine film grain differs.