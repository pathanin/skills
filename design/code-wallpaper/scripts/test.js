// End-to-end check of the shipped assets: copies engine.html, render.js and helpers.js into a temp dir with a test scene,
// renders through Playwright and the CLI, and asserts the behaviours SKILL.md promises.
// usage: NODE_PATH=<dir containing playwright> node scripts/test.js
const {chromium}=require('playwright'), fs=require('fs'), os=require('os'), path=require('path'), crypto=require('crypto'), {execFileSync}=require('child_process'), {pathToFileURL}=require('url');
const ASSETS=path.join(__dirname,'..','assets'), T=fs.mkdtempSync(path.join(os.tmpdir(),'cw-test-'));
for(const f of ['engine.html','render.js','helpers.js','bake.js']) fs.copyFileSync(path.join(ASSETS,f),path.join(T,f));
fs.writeFileSync(path.join(T,'scene.js'),`
const SCENES=[
  { name:'t-paper', seed:11, style:'papercut', build(C){ const {W,H}=C, o=[]; window.BUILD=[];
    const r=(a,b)=>{ const v=C.rnd(a,b); window.BUILD.push(v); return v; };
    o.push({pts:[[0,0],[W,0],[W,H],[0,H]],col:'#20304a'});
    for(let i=0;i<12;i++){ const x=r(160,W-20), y=r(20,H-20), s=r(4,10); o.push({pts:[[x-s,y-s],[x+s,y-s],[x+s,y+s],[x-s,y+s]],col:'#6a7a9a'}); }
    o.push({pts:[[300,300],[380,300],[380,380],[300,380]],cf:(x,y)=>[x%255,y%255,90]});
    o.push({pts:[[99.1,20],[100.9,20],[100.9,380],[99.1,380]],col:'#00c800'}); // 1.8-wide strip
    o.push({pts:[[20,20],[60,20],[60,60],[20,60]],col:[200,0,200]}); // colour given as an array
    return o; } },
  { name:'t-oil', seed:11, build(C){ const {W,H}=C; return [{pts:[[0,0],[W,0],[W,H],[0,H]],grad:[[0,'#335'],[400,'#a86']],dir:'sky'},{pts:[[200,200],[300,200],[300,300],[200,300]],col:'#c33'}]; } },
  { name:'t-helpers', seed:5, style:'papercut', build(C){ const {W,H}=C, P=persp(100,500,2.5), o=[{pts:rect(0,0,W,H),col:'#223'}];
    o.push({pts:lens(200,200,40,4),col:'#fff'},{pts:strip([[50,50,3],[150,80,3],[250,60,3]]),col:'#f80'},{pts:cloud(400,100,90,12,1),col:'#88a'},{pts:star4(600,80,6),col:'#ffe'});
    if(Math.abs(P.x(0)-100)>1e-9||Math.abs(P.x(1)-500)>1e-9||Math.abs(P.t(P.x(.3))-.3)>1e-9||Math.abs(P.s(500)-.4)>1e-9||hump(0,0,5)!==1) throw new Error('helper math');
    return o; } },
  { name:'t-nan', seed:5, style:'papercut', build(C){ const {W,H}=C; return [{pts:[[0,0],[W,0],[W,H],[0,H]],col:'#223'},{pts:[[10,10],[(-2/170)**2.5,50],[60,60]],col:'#fff'}]; } },
  { name:'t-oil-thin', seed:11, build(C){ const {W,H}=C; return [{pts:[[0,0],[W,0],[W,H],[0,H]],grad:[[0,'#35507a'],[400,'#c9a27a']],dir:'sky'},
    {pts:rect(199.9,40,202.1,360),col:'#00c800',dir:'vert'},                                   // hanger: 2.2 wide (the Golden Gate's oil hangers), bbox < 900 (small-region pass)
    {pts:rect(129.8,60,133.3,315),col:'#00c800',dir:'vert'},                                   // wide hanger: 3.5 x 255, the Golden Gate's most broken one
    {pts:strip([[250,80,2.6],[650,330,2.6]]),col:'#00c800',dir:'angle',a:Math.atan2(250,400)},
    // a real scene has hundreds of regions sharing the edge pass; 400 small squares along the bottom, clear of the measured strips, dilute it the same way
    ...Array.from({length:404},(_,i)=>({pts:rect(2+(i%101)*7,364+(i/101|0)*9,7+(i%101)*7,369+(i/101|0)*9),col:'#6a4a8a'}))]; } }, // cable: 2.6 wide, bbox > 900
  // a comb of 2-wide hangers 14 apart in front of an open sky, like a suspension bridge's
  { name:'t-oil-comb', seed:11, build(C){ const {W,H}=C; return [{pts:rect(0,0,W,H),grad:[[0,'#35507a'],[400,'#c9a27a']],dir:'sky'},
    ...Array.from({length:21},(_,i)=>({pts:rect(299+i*14,40,301+i*14,300),col:'#c8402a',dir:'vert'}))]; } },
  { name:'t-oil-bs0', seed:11, build(C){ const {W,H}=C; return [{pts:rect(0,0,W,H),grad:[[0,'#335'],[400,'#a86']],dir:'sky'},{pts:rect(200,200,300,300),col:'#c33',bs:0}]; } },
  { name:'t-paintover', seed:3, build(C){ return paintOver(C); } },                                                    // 7: needs img.js (baked below)
  { name:'t-grey', seed:11, build(C){ const {W,H}=C; return [{pts:rect(0,0,W,H),col:'#888888',dir:'sky'},{pts:rect(200,150,300,250),col:'#888888',bs:0}]; } }, // 8: flat grey; square = small strokes only
  // 9: lost and found edges: a square close in value to the sky (hue differs only), and one far from it in value
  { name:'t-edges', seed:11, build(C){ const {W,H}=C; return [{pts:rect(0,0,W,H),col:'#8a7a9a',dir:'horiz'},{pts:rect(200,140,300,260),col:'#9a8a6a',dir:'horiz'},{pts:rect(450,140,550,260),col:'#f0d0a0',dir:'horiz'},{pts:rect(620,180,646,206),col:'#9a8a6a',dir:'horiz'}]; } }, // last: a house-sized near-value square
  // 10: impasto in the lights, thin paint in the darks: a dark field beside a light one
  { name:'t-impasto', seed:11, build(C){ const {W,H}=C; return [{pts:rect(0,0,W,H),col:'#283040',dir:'horiz',bs:1},{pts:rect(W/2,-2,W+2,H+2),col:'#e8dcc0',dir:'horiz',bs:1}]; } },
];`);

let fails=0; const ok=(name,cond,detail='')=>{ console.log((cond?'PASS ':'FAIL ')+name+(detail?'  ('+detail+')':'')); if(!cond) fails++; };
const hash=s=>crypto.createHash('sha1').update(s).digest('hex').slice(0,12);
const render=async(br,q)=>{ const p=await br.newPage(); let err=null; p.on('pageerror',e=>err=e.message);
  await p.goto(pathToFileURL(path.join(T,'engine.html'))+'?'+q,{timeout:600000});
  const r=await p.evaluate(()=>({done:window.DONE, build:window.BUILD, url:document.getElementById('cv').toDataURL()}));
  r.err=err; r.hash=hash(r.url||''); r.page=p; return r; };
const cli=(args,env={})=>{ try{ return {out:execFileSync('node',[path.join(T,'render.js'),...args],{cwd:T,env:{...process.env,...env},stdio:['ignore','pipe','pipe']}).toString(),code:0}; }
  catch(e){ return {out:String(e.stdout)+String(e.stderr),code:e.status}; } };

const bake=(args)=>{ try{ return {out:execFileSync('node',[path.join(T,'bake.js'),...args],{cwd:T,stdio:['ignore','pipe','pipe']}).toString(),code:0}; }
  catch(e){ return {out:String(e.stdout)+String(e.stderr),code:e.status}; } };
const readIMG=f=>require('vm').runInNewContext(fs.readFileSync(f,'utf8')+';IMG',{atob,Uint8Array});
// draws an image in the browser with canvas code and saves it (png or jpeg)
const mkimg=async(br,w,h,draw,file)=>{ const p=await br.newPage(); const u=await p.evaluate(([w,h,draw,t])=>{ const c=document.createElement('canvas'); c.width=w; c.height=h;
  new Function('g','w','h',draw)(c.getContext('2d'),w,h); return c.toDataURL(t,.95); },[w,h,draw,/\.jpe?g$/.test(file)?'image/jpeg':'image/png']); fs.writeFileSync(file,Buffer.from(u.split(',')[1],'base64')); await p.close(); };
// the paint-over reference: 4:3, light ground, a dark disc, a red diagonal band, a vertical gradient at the bottom
const REF=`g.fillStyle='#d8d0c0'; g.fillRect(0,0,w,h); const gr=g.createLinearGradient(0,450,0,600); gr.addColorStop(0,'#d8d0c0'); gr.addColorStop(1,'#40506a'); g.fillStyle=gr; g.fillRect(0,450,w,150);
  g.fillStyle='#b02828'; g.beginPath(); g.moveTo(480,0); g.lineTo(560,0); g.lineTo(800,300); g.lineTo(800,400); g.closePath(); g.fill(); g.fillStyle='#2a2226'; g.beginPath(); g.arc(300,300,90,0,7); g.fill();`;

(async()=>{ const br=await chromium.launch().catch(()=>chromium.launch({channel:'chrome'}));
  const a=await render(br,'s=0&w=711&h=400&seed=11&tseed=1'), a2=await render(br,'s=0&w=711&h=400&seed=11&tseed=1'),
        b=await render(br,'s=0&w=711&h=400&seed=11&tseed=2'), c=await render(br,'s=0&w=711&h=400&seed=12&tseed=1');
  ok('paper cut renders without errors',!a.err&&a.done>0,a.err||'pieces '+a.done);
  ok('same seed + tseed is deterministic',a.hash===a2.hash);
  ok('tseed keeps the layout',JSON.stringify(a.build)===JSON.stringify(b.build));
  ok('tseed changes the cut edges',a.hash!==b.hash);
  ok('seed changes the layout',JSON.stringify(a.build)!==JSON.stringify(c.build));

  // thin strip: narrowest painted row of the 1.8-unit green strip at 4K (k = 5.4 px per unit)
  const big=await render(br,'s=0&w=3840&h=2160&seed=11');
  const minW=await big.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400, g=cv.getContext('2d'), x0=Math.round(95*k), w=Math.round(10*k);
    let min=1e9, max=0; for(let y=Math.round(40*k);y<Math.round(360*k);y++){ const d=g.getImageData(x0,y,w,1).data; let n=0;
      for(let i=0;i<d.length;i+=4) if(d[i+1]-Math.max(d[i],d[i+2])>60) n++; min=Math.min(min,n/k); max=Math.max(max,n/k); } return [min,max]; });
  const px=await big.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400; return [...cv.getContext('2d').getImageData(Math.round(40*k),Math.round(40*k),1,1).data]; });
  ok('colour array paints',px[0]>150&&px[1]<60&&px[2]>150,'centre '+px.slice(0,3));
  ok('thin strip keeps its width (min >= 1.25 units)',minW[0]>=1.25,'min '+minW[0].toFixed(2)+' of 1.8');

  const oil=await render(br,'s=1&w=711&h=400');
  ok('oil still paints strokes',!oil.err&&oil.done>1000,oil.err||'strokes '+oil.done);
  const oil2=await render(br,'s=1&w=711&h=400'), oil3=await render(br,'s=1&w=711&h=400&tseed=9');
  ok('oil: same seed + tseed is deterministic',oil.hash===oil2.hash);
  ok('oil: tseed changes the brushwork',oil.hash!==oil3.hash);

  // 4K oil: the flat #c33 square keeps its colour under lighting, has no linen holes, and the preview shows the same painting
  const t0=Date.now(), o4=await render(br,'s=1&w=3840&h=2160'), secs=(Date.now()-t0)/1000;
  ok('oil: 4K render under 40 s',!o4.err&&secs<40,secs.toFixed(1)+' s');
  const stats=await o4.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400, d=cv.getContext('2d').getImageData(Math.round(215*k),Math.round(215*k),Math.round(70*k),Math.round(70*k)).data;
    let s=[0,0,0], holes=0, glint=0; for(let i=0;i<d.length;i+=4){ for(let c=0;c<3;c++) s[c]+=d[i+c]; if(Math.abs(d[i]-0xb9)+Math.abs(d[i+1]-0x8d)+Math.abs(d[i+2]-0x63)<60) holes++; if(d[i+1]>115&&d[i+2]>110) glint++; }
    const n=d.length/4; return {mean:s.map(v=>v/n), holes:holes/n, glint:glint/n}; });
  const dev=Math.max(...stats.mean.map((v,c)=>Math.abs(v-[0xcc,0x33,0x33][c])));
  ok('oil: flat region keeps its colour (max channel error <= 14)',dev<=14,'mean '+stats.mean.map(v=>v.toFixed(0))+' vs 204,51,51');
  ok('oil: no linen holes in a painted region (< 1%)',stats.holes<.01,(stats.holes*100).toFixed(2)+'%');
  ok('oil: the relief is lit (specular glints on the red paint, 0.2%..8%)',stats.glint>.002&&stats.glint<.08,(stats.glint*100).toFixed(2)+'%');
  const cells=async(r,px)=>r.page.evaluate(px=>{ const cv=document.getElementById('cv'), k=cv.height/400, g=cv.getContext('2d'), o=[];
    for(let cy=0;cy<5;cy++) for(let cx=0;cx<8;cx++){ const d=g.getImageData(Math.round(cx*88*k),Math.round(cy*80*k),Math.round(88*k),Math.round(80*k)).data; const s=[0,0,0];
      for(let i=0;i<d.length;i+=4) for(let c=0;c<3;c++) s[c]+=d[i+c]; o.push(s.map(v=>v/(d.length/4))); } return o; },px);
  const pv=await render(br,'s=1&w=1422&h=800'), cA=await cells(pv), cB=await cells(o4);
  const cellErr=Math.max(...cA.map((a,i)=>Math.max(...a.map((v,c)=>Math.abs(v-cB[i][c])))));
  ok('oil: preview matches the 4K render cell by cell (max error <= 10)',cellErr<=10,'max '+cellErr.toFixed(1));
  // oil thin regions in front of a busy sky, at 4K: the background's strokes must not cut through them, and their own strokes must not smear sideways
  const thin=await render(br,'s=4&w=3840&h=2160');
  const tm=await thin.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400, Wp=cv.width, d=cv.getContext('2d').getImageData(0,0,Wp,cv.height).data;
    const green=(x,y)=>{ const i=((y*k|0)*Wp+(x*k|0))*4; return d[i+1]-Math.max(d[i],d[i+2])>60; };
    const line=(x0,y0,x1,y1)=>{ const L=Math.hypot(x1-x0,y1-y0), ux=(x1-x0)/L, uy=(y1-y0)/L, nx=-uy, ny=ux; let cov=0, n=0, gap=0, maxGap=0, bleed=0, nb=0;
      for(let s=0;s<=L;s+=.25){ const cx=x0+ux*s, cy=y0+uy*s; let gp=0, np=0; // a sample is covered when half of the 1x1-unit window on the centre line is strip paint
        for(let a=-.5;a<=.5;a+=1/k) for(let b=-.5;b<=.5;b+=1/k){ np++; if(green(cx+ux*a+nx*b,cy+uy*a+ny*b)) gp++; }
        n++; if(gp/np>=.5){ cov++; gap=0; } else { gap+=.25; maxGap=Math.max(maxGap,gap); }
        for(const sd of [-1,1]) for(let o=3;o<=6;o+=1/k){ nb++; if(green(cx+nx*o*sd,cy+ny*o*sd)) bleed++; } }
      return {cov:cov/n, maxGap, bleed:bleed/nb}; };
    return {hanger:line(201,50,201,350), 'wide hanger':line(131.55,68,131.55,307), cable:line(262,87.5,638,322.5)}; });
  for(const [name,m] of Object.entries(tm)){
    ok(`oil: thin ${name} stays unbroken (centre coverage >= 97%, longest gap <= 0.75 units)`,m.cov>=.97&&m.maxGap<=.75,(m.cov*100).toFixed(1)+'%, gap '+m.maxGap.toFixed(2));
    ok(`oil: thin ${name} does not smear into the sky 3-6 units away (<= 1%)`,m.bleed<=.01,(m.bleed*100).toFixed(2)+'%'); }
  // stroke size follows the subject: slabs in open areas, fine strokes on thin ones; big strokes stay visible, and don't spill past their region
  const pvs=await pv.page.evaluate(()=>window.VIS(10,10,190,190,0));
  ok('oil: open sky shows big strokes (>= 30% of it from strokes 12+ units wide, p90 >= 16)',pvs.big>=.3&&pvs.p90>=16,(pvs.big*100).toFixed(0)+'%, p90 '+pvs.p90);
  const comb=await render(br,'s=5&w=1422&h=800'), cs=await comb.page.evaluate(()=>window.VIS(300,60,580,280,0));
  ok('oil: sky between hangers 14 apart still shows big strokes (>= 20%)',cs.big>=.2,(cs.big*100).toFixed(0)+'%');
  const bs0=await render(br,'s=6&w=1422&h=800'), sq=await bs0.page.evaluate(()=>window.VIS(205,205,295,295,1)), sq1=await pv.page.evaluate(()=>window.VIS(205,205,295,295,1));
  ok('oil: bs:0 keeps slabs off a region that would get them (< 3% big, was >= 30%)',sq.big<.03&&sq1.big>=.3,(sq.big*100).toFixed(1)+'% vs '+(sq1.big*100).toFixed(0)+'%');
  const hv=await thin.page.evaluate(()=>window.VIS(200.5,50,201.5,350,1));
  ok('oil: the core of a 2.2-wide hanger is painted with strokes no wider than 3 units (p90)',hv.p90<=3,'p90 '+hv.p90);
  const spill=await o4.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400, Wp=cv.width, d=cv.getContext('2d').getImageData(0,0,Wp,cv.height).data; let n=0, red=0;
    for(let y=190;y<310;y+=.25) for(let x=190;x<310;x+=.25){ const o=Math.max(200-x,x-300,200-y,y-300); if(o<3||o>6) continue; const i=((y*k|0)*Wp+(x*k|0))*4; n++; if(Math.max(d[i+1],d[i+2])<.45*d[i]) red++; } return red/n; }); // a hue test (#c33 has G/R .25, the sky's orange >= .58), so lit sky doesn't count
  ok('oil: the square does not spill 3-6 units into the sky behind it (<= 1%)',spill<=.01,(spill*100).toFixed(2)+'%');
  // edges: averaged across rows, a border between near values blends over a wider band than one between far values (which stays found).
  // Measured on R-B, which the lighting barely moves: sky -16, near square +48 (within 9 levels of the sky's value), far square +80 (82 levels lighter)
  const ed=await render(br,'s=9&w=3840&h=2160'), ew=await ed.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400, Wp=cv.width, d=cv.getContext('2d').getImageData(0,0,Wp,cv.height).data;
    const width=(x0,y0=160,y1=240)=>{ const P=[]; for(let o=-8;o<=8;o+=.25){ let t=0, n=0; for(let y=y0;y<y1;y+=1/k){ const i=((y*k|0)*Wp+((x0+o)*k|0))*4; t+=d[i]-d[i+2]; n++; } P.push([o,t/n]); }
      const lo=P[0][1], hi=P[P.length-1][1], at=f=>{ const g=lo+(hi-lo)*f; for(let j=1;j<P.length;j++) if((P[j][1]-g)*(hi-lo)>=0) return P[j][0]; return 8; }; return at(.85)-at(.15); };
    return {near:width(200), far:width(450), small:width(620,183,203)}; });
  ok('oil: a border between near values is lost (blend band >= 3 units, >= 2x the far one)',ew.near>=3&&ew.near>=2*ew.far,ew.near.toFixed(2)+' vs '+ew.far.toFixed(2));
  ok('oil: a border between far values stays found (band <= 2 units)',ew.far<=2,ew.far.toFixed(2));
  ok('oil: a small shape near in value stays found, as a house keeps its silhouette (band <= 2 units)',ew.small<=2,ew.small.toFixed(2));
  // impasto in the lights, thin paint in the darks: mean paint height over a dark field and a light one (1.8x before darks went thin)
  const im=await render(br,'s=10&w=3840&h=2160'), th=await im.page.evaluate(()=>({dark:window.THK(100,140,220,260), light:window.THK(480,140,600,260)}));
  ok('oil: impasto in the lights, thin paint in the darks (light paint >= 1.95x as thick, the weave counted)',th.light>=1.95*th.dark,(th.light/th.dark).toFixed(2)+'x');
  const hl=await render(br,'s=2&w=711&h=400');
  ok('helpers.js is loaded before scene.js',!hl.err&&hl.done>0,hl.err||'');
  const nan=await render(br,'s=3&w=711&h=400');
  ok('a non-finite point is reported, not silently dropped',/non-finite/.test(nan.err||''),nan.err||'no error');
  ok('scenes render with no img.js present',!fs.existsSync(path.join(T,'img.js'))&&!oil.err&&!a.err);

  // oil technique: stroke colour varies in value, not hue, so a flat grey stays grey (no green/pink confetti); small strokes carry thinner paint and don't glint more
  const grey=await render(br,'s=8&w=3840&h=2160');
  const gs=await grey.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400, g=cv.getContext('2d');
    const at=(x0,y0,w,h)=>{ const d=g.getImageData(Math.round(x0*k),Math.round(y0*k),Math.round(w*k),Math.round(h*k)).data; let n=0, s=0, s2=0, gl=0;
      for(let i=0;i<d.length;i+=4){ const v=d[i]-d[i+1]; if(Math.abs(v)<30){ n++; s+=v; s2+=v*v; } if(Math.min(d[i],d[i+1],d[i+2])>205) gl++; } return {sd:Math.sqrt(s2/n-(s/n)**2), glint:gl/(d.length/4)}; };
    // warm light, cool shadow: over 1x1-unit blocks (glints excluded), lighter paint leans warm (R-B rises with value)
    const temp=(x0,y0,w,h)=>{ const B=Math.round(k), S=Math.round(w*k), d=g.getImageData(Math.round(x0*k),Math.round(y0*k),S,Math.round(h*k)).data, P=[];
      for(let by=0;by+B<=Math.round(h*k);by+=B) for(let bx=0;bx+B<=S;bx+=B){ let l=0, t=0, sk=false; for(let y=by;y<by+B;y++) for(let x=bx;x<bx+B;x++){ const i=(y*S+x)*4; if(Math.min(d[i],d[i+1],d[i+2])>180) sk=true; l+=d[i]+d[i+1]+d[i+2]; t+=d[i]-d[i+2]; } if(!sk) P.push([l,t]); }
      const n=P.length, ml=P.reduce((a,p)=>a+p[0],0)/n, mt=P.reduce((a,p)=>a+p[1],0)/n; let c=0, vl=0, vt=0; for(const [l,t] of P){ c+=(l-ml)*(t-mt); vl+=(l-ml)**2; vt+=(t-mt)**2; } return c/Math.sqrt(vl*vt); };
    return {open:at(400,100,200,200), square:at(205,155,90,90), temp:temp(400,100,200,200)}; });
  ok('oil: lighter strokes lean warm, darker ones cool (correlation of R-B with value >= .3)',gs.temp>=.3,'r '+gs.temp.toFixed(2));
  ok('oil: a flat grey varies mainly in value, not hue (sd of R-G <= 3.5)',gs.open.sd<=3.5,'sd '+gs.open.sd.toFixed(2));
  ok('oil: small strokes do not glint more than big ones (<= 1.5x)',gs.square.glint<=1.5*gs.open.glint+.002,(gs.square.glint*100).toFixed(2)+'% vs '+(gs.open.glint*100).toFixed(2)+'%');

  // paint-over: bake an image into img.js, then paint it
  const rb=bake(['nope.png']);
  ok('bake: a missing image fails with a clear message',rb.code!==0&&/not found/i.test(rb.out),rb.out.trim().split('\n').pop());
  await mkimg(br,3000,2000,REF,path.join(T,'big.jpg'));
  const rj=bake(['big.jpg']), IJ=rj.code===0&&readIMG(path.join(T,'img.js'));
  ok('bake: a JPEG bakes, capped at 1600 px on the long side',IJ&&Math.max(IJ.w,IJ.h)===1600&&IJ.d.length===IJ.w*IJ.h*3,rj.out.trim());
  await mkimg(br,100,100,`g.fillStyle='#000'; g.fillRect(50,0,50,100);`,path.join(T,'alpha.png'));
  const ra=bake(['alpha.png']), IA=ra.code===0&&readIMG(path.join(T,'img.js'));
  ok('bake: transparent pixels composite over white, not black',IA&&IA.d[(50*100+10)*3]>240&&IA.d[(50*100+90)*3]<15,ra.out.trim());
  await mkimg(br,800,600,REF,path.join(T,'ref.png'));
  ok('bake: PNG',bake(['ref.png']).code===0);
  const po=await render(br,'s=7&w=1422&h=800'), po2=await render(br,'s=7&w=1422&h=800'), po3=await render(br,'s=7&w=1422&h=800&tseed=9');
  ok('paint-over renders',!po.err&&po.done>1000,po.err||'strokes '+po.done);
  ok('paint-over: deterministic, and tseed changes the brushwork',po.hash===po2.hash&&po.hash!==po3.hash);
  // the 4:3 image covers the 16:9 canvas at one scale (cropped top and bottom): the disc stays round, centred at (266.7, 200), radius 80
  const disc=await po.page.evaluate(()=>{ const cv=document.getElementById('cv'), k=cv.height/400, d=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data; let x0=1e9,x1=0,y0=1e9,y1=0;
    for(let y=100;y<300;y+=.5) for(let x=150;x<380;x+=.5){ const i=((y*k|0)*cv.width+(x*k|0))*4; if(d[i]+d[i+1]+d[i+2]<200&&d[i]-d[i+2]<40){ x0=Math.min(x0,x); x1=Math.max(x1,x); y0=Math.min(y0,y); y1=Math.max(y1,y); } }
    return {w:x1-x0, h:y1-y0, cx:(x0+x1)/2, cy:(y0+y1)/2}; });
  ok('paint-over: a 4:3 image on 16:9 is cropped, not stretched (disc round, in place)',Math.abs(disc.w/disc.h-1)<=.1&&Math.abs(disc.cx-266.7)<=4&&Math.abs(disc.cy-200)<=4,
    `${disc.w}x${disc.h} at ${disc.cx},${disc.cy}`);
  const refCells=await po.page.evaluate(async src=>{ const im=new Image(); im.src=src; await im.decode(); const c=document.createElement('canvas'); c.width=704; c.height=400; const g=c.getContext('2d'), s=Math.max(711/800,400/600);
    g.drawImage(im,(711-800*s)/2,(400-600*s)/2,800*s,600*s); const o=[]; for(let cy=0;cy<5;cy++) for(let cx=0;cx<8;cx++){ const d=g.getImageData(cx*88,cy*80,88,80).data, m=[0,0,0];
      for(let i=0;i<d.length;i+=4) for(let q=0;q<3;q++) m[q]+=d[i+q]; o.push(m.map(v=>v/(d.length/4))); } return o; },'data:image/png;base64,'+fs.readFileSync(path.join(T,'ref.png')).toString('base64'));
  const pA=await cells(po), po4=await render(br,'s=7&w=3840&h=2160'), pB=await cells(po4);
  const fid=Math.max(...pA.map((a,i)=>Math.max(...a.map((v,c)=>Math.abs(v-refCells[i][c])))));
  ok('paint-over: colours follow the image (cell means within 25)',fid<=25,'max '+fid.toFixed(1));
  const pErr=Math.max(...pA.map((a,i)=>Math.max(...a.map((v,c)=>Math.abs(v-pB[i][c])))));
  ok('paint-over: preview matches the 4K render cell by cell (max error <= 10)',pErr<=10,'max '+pErr.toFixed(1));
  // no forced outline: the share of small strokes (< 3.2 wide, on top) in the band just outside the disc. Calibrated by eye: 27% drew a visible ridge of
  // thin light strokes around the disc (and the hair in a real image); ~9% shows none. Some small strokes along a hard edge are normal brushwork
  const halo=await po4.page.evaluate(()=>{ let b=0,nb=0,f=0,nf=0; for(let a=0;a<6.283;a+=.01) for(let r=81.5;r<=84.5;r+=.5){ nb++; if(window.TWAT(266.7+r*Math.cos(a),200+r*Math.sin(a))<3.2) b++; }
    for(let y=20;y<100;y+=.5) for(let x=20;x<120;x+=.5){ nf++; if(window.TWAT(x,y)<3.2) f++; } return {band:b/nb, far:f/nf}; });
  ok('paint-over: no band of small strokes along an edge (<= 12%, open ground for scale)',halo.band<=.12,(halo.band*100).toFixed(1)+'% vs '+(halo.far*100).toFixed(1)+'%');
  await br.close();

  // CLI: positional seed + crop still work, --crop-out picks the crop path, crops never land next to the output
  fs.mkdirSync(path.join(T,'out')); fs.mkdirSync(path.join(T,'crops'));
  const r1=cli(['0','711','400','out/a.png','11','0,0,100,100','--crop-out=crops/a-crop.png']);
  ok('CLI writes output and crop to --crop-out',r1.code===0&&fs.existsSync(path.join(T,'out/a.png'))&&fs.existsSync(path.join(T,'crops/a-crop.png')),r1.out.trim());
  const r2=cli(['0','711','400','out/b.png','11','0,0,100,100']);
  ok('CLI keeps crops out of the output folder',r2.code===0&&!fs.existsSync(path.join(T,'out/b-crop.png'))&&/crop/.test(r2.out),r2.out.trim());
  const r3=cli(['0','711','400','out/t1.png','11','','--tseed=1']), r4=cli(['0','711','400','out/t2.png','11','','--tseed=2']);
  ok('CLI --tseed changes the image',r3.code===0&&r4.code===0&&hash(fs.readFileSync(path.join(T,'out/t1.png')))!==hash(fs.readFileSync(path.join(T,'out/t2.png'))));
  const empty=fs.mkdtempSync(path.join(os.tmpdir(),'cw-nobrowser-'));
  const r5=cli(['0','711','400','out/chrome.png'],{PLAYWRIGHT_BROWSERS_PATH:empty});
  ok('CLI falls back to installed Chrome when no bundled browser',r5.code===0&&fs.existsSync(path.join(T,'out/chrome.png')),r5.out.trim().split('\n').slice(-1)[0]);

  console.log(fails?`${fails} FAILED`:'ALL PASSED', ' tmp:',T); process.exit(fails?1:0); })();
