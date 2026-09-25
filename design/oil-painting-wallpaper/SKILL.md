---
name: oil-painting-wallpaper
description: Manual-only oil-painting wallpaper render, invoked with /oil-painting-wallpaper. Paints an oil-on-linen style landscape entirely in code (polygon scene + multi-bristle stroke engine in headless Chromium) and exports a PNG at any resolution — 4K, ultrawide, or phone.
argument-hint: "[scene, resolution, number of variations]"
disable-model-invocation: true
---

# Oil-painting wallpaper

Draw a landscape as an oil painting, entirely in code, and export it as a PNG at the size the user asks for. The scene is a list of flat-coloured polygons. A stroke engine then paints over them with thousands of directional, multi-bristle brush strokes on a woven linen ground, running headless Chromium through Playwright.

## Inputs to settle first

- **Scene**: the subject, time of day, mood and any must-have elements. If the user gives only a theme ("a beach"), pick the palette and composition yourself.
- **Resolution**: default 3840 x 2160 (4K UHD). Common alternatives: 2560 x 1440, 5120 x 2160 (ultrawide), 1170 x 2532 or 1080 x 1920 (phone), 6016 x 3384 (6K). Stay at or below about 8000 px per side, because Chromium's canvas limit is roughly 16384 px per side and 268M px in total.
- **How many variations**: each one is a new scene or a new seed.

If any of these is missing and the user is present, ask once. Otherwise use the defaults and state them.

## Coordinate system

- The logical canvas height is always H = 400. The logical width is W = round(400 x width / height), so W is 711 for 16:9, 948 for 21:9 and 225 for 9:16.
- **Compose the scene for the actual W.** A scene built for 711 does not reflow into portrait. For a new aspect ratio, place every element again (horizon, focal point, trees) relative to W.
- Stroke sizes are in logical units, so the texture looks the same at every resolution. Stroke counts scale with the area W x H.

## Files (create in a working folder)

### engine.html (use verbatim)

```html
<!doctype html><html><body style="margin:0;background:#000">
<canvas id="cv"></canvas>
<script src="scene.js"></script>
<script>
'use strict';
const Q=new URLSearchParams(location.search);
const PX=+Q.get('w')||3840, PY=+Q.get('h')||2160, H=400, W=Math.round(H*PX/PY), k=PX/W;
const clamp=(v,a=0,b=1)=>v<a?a:v>b?b:v, lerp=(a,b,t)=>a+(b-a)*t;
const SC=SCENES[+Q.get('s')||0];
if(Q.get('seed')) SC.seed=+Q.get('seed');
let seed=SC.seed; const R=()=>{ seed=(seed*1664525+1013904223)>>>0; return seed/4294967296; };
const rnd=(a=1,b)=>b===undefined?R()*a:a+R()*(b-a);
const hex=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
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
b.fillStyle=SC.ground||'#b98d63'; b.fillRect(0,0,W,H);
b.save(); b.globalAlpha=.08; b.strokeStyle='#3b2a1a'; b.lineWidth=.3;
for(let i=0;i<Math.max(W,H);i+=1){ b.beginPath(); b.moveTo(0,i); b.lineTo(W,i); b.stroke(); b.beginPath(); b.moveTo(i,0); b.lineTo(i,H); b.stroke(); } b.restore();
const A=W*H/(400*400);
let n=0; const add=s=>{ paintStroke(b,s); n++; };
for(let i=0,N=Math.round(2400*A);i<N;i++) add(oilStroke(rnd(W),rnd(H),rnd(14,24),rnd(8,11)));
for(let i=0,N=Math.round(5200*A);i<N;i++) add(oilStroke(rnd(W),rnd(H),rnd(7,12),rnd(3.5,5.5)));
for(let i=0,N=Math.round(3500*A);i<N;i++) add(oilStroke(rnd(W),rnd(H),rnd(4,8),rnd(1.8,3)));
let e=0; const N3=Math.round(1050*A*1.4); while(e<N3){ const x=rnd(W), y=rnd(H), r=idAt(x,y); if(r!==idAt(x+3,y)||r!==idAt(x,y+3)||r!==idAt(x-3,y)||r!==idAt(x,y-3)){ add(oilStroke(x,y,rnd(4,8),rnd(1.8,3))); e++; } }
REG.forEach((r,ri)=>{ if(r.area<900){ const m=r.area<30?12:40; for(let q=0;q<m;q++){ const x=rnd(r.box[0],r.box[2]), y=rnd(r.box[1],r.box[3]); if(idAt(x,y)===ri) add(oilStroke(x,y,rnd(2,6),r.area<30?rnd(.8,1.4):rnd(1.2,2))); } } });
b.setTransform(1,0,0,1,0,0);
const g=document.createElement('canvas'); g.width=g.height=256; const gc=g.getContext('2d'), d=gc.createImageData(256,256);
for(let i=0;i<d.data.length;i+=4){ const v=R()*255; d.data[i]=d.data[i+1]=d.data[i+2]=v; d.data[i+3]=255; } gc.putImageData(d,0,0);
b.save(); b.globalCompositeOperation='multiply'; b.globalAlpha=.07; b.fillStyle=b.createPattern(g,'repeat'); b.fillRect(0,0,PX,PY); b.restore();
window.DONE=n;
</script></body></html>
```

The engine paints in these passes:

1. A linen ground with a woven grid.
2. A broad underpainting pass.
3. A mid pass.
4. A fine detail pass.
5. Edge strokes placed on region borders.
6. Extra strokes inside small regions such as windows and stars.
7. A multiply grain layer at full resolution.

The per-bristle lines, the highlight bristle and the shadow bristle are what make the strokes read as oil paint.

### render.js (use verbatim)

```js
// usage: node render.js <scene_index> <width> <height> <out.png> [seed]
const {chromium}=require('playwright'), fs=require('fs'), path=require('path');
const [i='0',w='3840',h='2160',out='wallpaper.png',seed='']=process.argv.slice(2);
(async()=>{ const br=await chromium.launch(); const p=await br.newPage();
  let err=null; p.on('pageerror',e=>{ err=e.message; console.error('PAGE ERROR:',e.message); });
  await p.goto(`file://${path.join(__dirname,'engine.html')}?s=${i}&w=${w}&h=${h}${seed?'&seed='+seed:''}`);
  const t0=Date.now(); while(!(await p.evaluate('window.DONE'))){ if(err) process.exit(1); if(Date.now()-t0>600000) throw 'timeout'; await p.waitForTimeout(500); }
  const url=await p.evaluate(()=>document.getElementById('cv').toDataURL('image/png'));
  fs.writeFileSync(out,Buffer.from(url.split(',')[1],'base64')); console.log('wrote',out,w+'x'+h,'strokes',await p.evaluate('window.DONE')); await br.close(); })();
```

Run it with `NODE_PATH=$(npm root -g) node render.js 0 3840 2160 out.png`. Playwright and Chromium are preinstalled in the cloud sandbox; do not run `playwright install`. A 4K render takes only a few seconds.

### scene.js (write per request)

`scene.js` defines `const SCENES=[...]`. Each entry is `{name, seed, ground?, build(C)}`, and `build` returns the regions **back to front** (later regions are painted on top). `C` provides `{W,H,rnd,hex,mixc,gradAt,lerp,clamp}`. Always use `C.rnd`, never `Math.random`, so a seed reproduces the same image exactly.

Each region is `{pts:[[x,y],...], dir, ...colour}`:

- **Colour** is one of three options:
  - `col:'#hex'` for a flat colour.
  - `grad:[[y,'#hex'],...]` for a vertical gradient, used for skies, sea and ground.
  - `cf:(x,y)=>[r,g,b]` for any colour function, used for glows, light beams and shaded cliffs.
- **Stroke direction (`dir`)**:
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
const TAU=Math.PI*2;   // the engine does NOT declare TAU; declare it only here
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
  o.push({pts:rect(0,0,W,240),grad:sky,dir:'sky'});
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

## Workflow, including the polishing loop

1. Settle the scene, the resolution and the number of variations, then compute W.
2. Write `scene.js`, one entry per wallpaper.
3. Render each wallpaper at the final resolution.
4. **Review each render visually.** Make a downscaled preview (for example 1280 px wide with PIL) and a 1:1 crop of the focal area, then look at both with the Read tool.
5. Fix what you see, re-render only the changed scenes, and review again. Repeat until clean. These are the problems found in earlier runs:
   - **Linen showing through as brown flecks**: coverage is too thin. Raise the underpainting count (2400 x A) and the mid count (5200 x A). Do not lower them.
   - **Glow halos around small objects** (for example, glows behind houses looked like snowballs): drop the glow or make it much weaker. Only large light sources should get `glowCF` halos.
   - **Stripes that look like stairs**: evenly spaced, full-width ledges or strata look artificial. Use 3 or 4 short strata at irregular spacing, in a colour close to the base.
   - **Unreadable blobs**, such as a dark polygon on a cliff face: remove them or make their meaning clear.
   - **Broken or disconnected shapes**, such as a road drawn in pieces: the polygon is self-intersecting. Order the points as the left edge up, then the right edge down.
   - **Focal element hidden**, such as a sun behind a mesa: check the draw order and the overlap, and move the element into a gap.
   - **Elements lost in the texture**, such as hay bales: add a darker shadow region offset beneath them for contrast.
   - **Regions too thin to paint**: anything under about 1.5 logical units wide gets overpainted. Widen it or add it later in the list.
   - **JS errors**: `render.js` prints PAGE ERROR. Common causes are a duplicate `const` (such as TAU) and `-x**2`, which must be written `-(x**2)`.
6. Deliver the PNGs. Name them descriptively (for example `oil-lighthouse-sunset-3840x2160.png`), put them in the outputs folder, and send them together with a one-line caption.
7. Offer next steps: re-render with a new seed (`node render.js i w h out.png 1234`) for a different stroke layout, try another aspect ratio (which needs the composition redone for the new W), or change the palette.

## Notes

- File size is about 20 MB per PNG at 4K. If the user wants something smaller, convert to a high-quality JPEG (quality 92) with PIL.
- To reproduce an image exactly, keep the same scene, seed and resolution. Changing the resolution changes the stroke count, so the texture will differ slightly.