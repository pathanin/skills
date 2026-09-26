// End-to-end check of the shipped assets: copies stage.html, motion.js and render.js into a temp project with test scenes,
// then asserts the behaviours SKILL.md promises (frame-exact seeking, clock-driven CSS, hi-DPI layers, motion.js maths, every CLI command).
// usage: NODE_PATH=<dir containing playwright> node scripts/test.js     (video/qa/audio checks are skipped without a full ffmpeg)
const {chromium}=require('playwright'), fs=require('fs'), os=require('os'), path=require('path'), crypto=require('crypto'), {spawnSync}=require('child_process');
const ASSETS=path.join(__dirname,'..','assets'), T=fs.mkdtempSync(path.join(os.tmpdir(),'ca-test-')), SRC=path.join(T,'src'), REV=path.join(T,'review');
fs.mkdirSync(SRC); for(const f of ['stage.html','motion.js','render.js']) fs.copyFileSync(path.join(ASSETS,f),path.join(SRC,f));
const W=(f,s)=>fs.writeFileSync(path.join(SRC,f),s);
// main test scene: SVG ball on a clock, CSS @keyframes box, hi-DPI canvas square, HTML title, a rig for pivot/IK checks
W('scene.js',`
const SCENE={ width:640, height:360, fps:30, duration:4, background:'#ffffff',
  setup(stage){
    const st=document.createElement('style'); st.textContent='@keyframes mv{from{transform:translateX(0)}to{transform:translateX(200px)}} #box{animation:mv 2s linear infinite alternate}'; document.head.appendChild(st);
    stage.add('<rect id="ball" x="0" y="20" width="20" height="20" fill="#ff0000"/>');
    stage.add('<g id="arm"><rect x="0" y="-5" width="100" height="10" fill="#0000ff"/></g><circle id="pin" r="3" fill="none"/>');
    stage.html.innerHTML='<div id="box" style="position:absolute;left:0;top:300px;width:20px;height:20px;background:#00ff00"></div><div id="title" style="position:absolute;left:300px;top:10px;font:20px sans-serif">Hello world</div><div id="t2" style="position:absolute;left:0;top:200px;width:120px;font:20px sans-serif">What if <b>light</b><br>woke you up</div>';
    this.g=stage.canvas('fx','over'); this.spans=M.split(stage.$('#title')); this.r=M.rng(7); this.stars=Array.from({length:5},()=>[this.r()*640,this.r()*360]);
  },
  render(t,stage){
    M.tf(stage.$('#ball'),{x:100*t});                                          // left edge at 100*t
    M.tf(stage.$('#arm'),{x:300,y:180,r:90*M.seg(t,0,1),ox:0,oy:0});            // rotates about its root at (300,180)
    const g=this.g; g.clear(); g.fillStyle='#000000'; g.fillRect(600,300,10,10); // 10x10 stage units
    this.spans.forEach((s,i)=>M.tf(s,{y:10*(1-M.stagger(t,i,0,.1,.5))}));
  } };`);
W('scene-cut.js',`const SCENE={ width:320, height:180, fps:30, duration:3, background:'#000000', setup(stage){ stage.add('<rect id="r" width="40" height="40" fill="#ffffff"/>'); },
  render(t,stage){ const s=M.shots(t,[1,1,1]); stage.$('#r').setAttribute('fill',s.i===2?'#ff00ff':'#ffffff'); M.tf(stage.$('#r'),{x:s.i===1?140:40+200*s.u*(s.i===0?1:0)+(s.i===2?100*s.u:0),y:70}); } };`); // shot 1 holds, shot 2 cuts
fs.mkdirSync(path.join(T,'refs'));
const LOGO=c=>`<?xml version="1.0"?>\n<!-- Illustrator-style export: shared class names and ids -->\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100"><defs><style>.cls-1{fill:${c}}rect{stroke:none}</style>
  <linearGradient id="g1"><stop offset="0" stop-color="${c}"/><stop offset="1" stop-color="${c}"/></linearGradient></defs><rect class="cls-1" width="50" height="100"/><rect x="50" width="50" height="100" fill="url(#g1)"/></svg>`;
fs.writeFileSync(path.join(T,'refs','red.svg'),LOGO('#ff0000')); fs.writeFileSync(path.join(T,'refs','blue.svg'),LOGO('#0000ff'));
W('scene-load.js',`const SCENE={ width:300, height:120, duration:1, background:PARAMS.bg||'#ffffff', async setup(stage){
  const a=await stage.load('../refs/red.svg'), b=await stage.load('../refs/blue.svg'), c=await stage.load('../refs/red.svg'); M.set(b,{x:100}); M.set(c,{x:200}); }, render(){} };`);
W('scene-font.js',`const SCENE={ width:320, height:180, duration:1, setup(stage){ stage.add('<text x="10" y="90" font-family="NoSuchFont" font-size="30">hello</text>'); }, render(){} };`);
W('scene-hang.js',`const SCENE={ width:320, height:180, duration:1, render(t){ if(t>.5) while(true){} } };`);
W('scene-norender.js',`const SCENE={ width:320, height:180, duration:1 };`);
W('scene-state.js',`let x=0; const SCENE={ width:320, height:180, duration:1, setup(stage){ stage.add('<rect id="r" width="20" height="20" fill="#f00"/>'); }, render(t,stage){ x+=5; M.tf(stage.$('#r'),{x:x%300}); } };`);
W('scene-rnd.js',`const SCENE={ width:320, height:180, duration:1, setup(stage){ this.p=Array.from({length:30},()=>stage.add('<circle r="4" fill="#00f"/>')); this.xy=this.p.map(()=>[Math.random()*320,Math.random()*180]); },
  render(t,stage){ this.p.forEach((c,i)=>M.tf(c,{x:this.xy[i][0]+Math.random()*3,y:this.xy[i][1]})); } };`);
W('scene-bad.js',`const SCENE={ width:320, height:180, fps:30, duration:2, render(t){ if(t>1) null.x; } };`);
W('scene-alpha.js',`const SCENE={ width:320, height:180, fps:30, duration:1, background:'transparent', setup(stage){ stage.add('<circle id="c" cx="160" cy="90" r="40" fill="#ff8800"/>'); }, render(t,stage){ M.tf(stage.$('#c'),{x:50*t}); } };`);

let fails=0; const ok=(name,cond,info='')=>{ console.log(`${cond?'ok  ':'FAIL'} ${name}${info?'  ('+info+')':''}`); if(!cond) fails++; };
const cli=(args,env={})=>{ const r=spawnSync(process.execPath,[path.join(SRC,'render.js'),...args,'--dir='+REV],{cwd:T,env:{...process.env,...env},encoding:'utf8',timeout:300000}); return {code:r.status,out:(r.stdout||'')+(r.stderr||'')}; };
const hash=b=>crypto.createHash('md5').update(b).digest('hex');
const ffBin=(()=>{ for(const c of [process.env.FFMPEG,'ffmpeg']) if(c&&spawnSync(c,['-hide_banner','-encoders'],{encoding:'utf8'}).stdout?.includes('libx264')) return c;
  const r=spawnSync('python3',['-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],{encoding:'utf8'}); return r.status===0?r.stdout.trim():null; })();

(async()=>{
  // ---- direct page checks through a local server (mirrors render.js) ----
  const http=require('http'), srv=http.createServer((q,r)=>{ const f=decodeURIComponent(new URL(q.url,'http://x').pathname);
    fs.readFile(f,(e,d)=>{ if(e){ r.writeHead(404); r.end(); } else { r.writeHead(200,{'content-type':f.endsWith('.html')?'text/html':'text/javascript'}); r.end(d); } }); });
  await new Promise(r=>srv.listen(0,'127.0.0.1',r)); const url=f=>`http://127.0.0.1:${srv.address().port}${f}`;
  const br=await chromium.launch().catch(()=>chromium.launch({channel:'chrome'}));
  const open=async(dsf,scene='scene.js')=>{ const ctx=await br.newContext({viewport:{width:640,height:360},deviceScaleFactor:dsf}), p=await ctx.newPage(); let err=null; p.on('pageerror',e=>err=e.message);
    await p.goto(url(path.join(SRC,'stage.html'))+'?render&scene='+encodeURIComponent(url(path.join(SRC,scene)))); await p.waitForFunction(()=>window.READY||window.LOAD_ERROR); return {p,err:()=>err}; };
  const pixels=async(p,pts)=>{ const png=await p.screenshot(); return p.evaluate(async([u,pts])=>{ const i=new Image(); i.src=u; await i.decode(); const c=document.createElement('canvas'); c.width=i.width; c.height=i.height; const g=c.getContext('2d'); g.drawImage(i,0,0);
    return pts.map(([x,y])=>[...g.getImageData(x,y,1,1).data].slice(0,3)); },['data:image/png;base64,'+png.toString('base64'),pts]); };
  const {p,err}=await open(1);
  ok('scene loads without errors',!err(),err()||'');
  const seek=t=>p.evaluate(t=>window.__anim.seek(t),t);
  await seek(1); const a=hash(await p.screenshot()); await seek(3); await seek(0.2); await seek(1); const b=hash(await p.screenshot());
  ok('a frame is identical whatever was sought before it',a===b);
  await seek(1.5); let px=await pixels(p,[[149,30],[151,30],[169,30],[171,30]]);
  ok('SVG follows the clock (ball left edge at 100*t)',px[0][0]>200&&px[0][1]>200&&px[1][1]<60&&px[2][1]<60&&px[3][1]>200,JSON.stringify(px));
  await seek(1); px=await pixels(p,[[95,310],[105,310],[118,310],[125,310]]);
  ok('CSS @keyframes follow the clock (box at 100 px at t=1)',px[0][1]>200&&px[0][0]>200&&px[1][1]>200&&px[1][0]<60&&px[3][0]>200,JSON.stringify(px));
  await seek(1); const pin=await p.evaluate(()=>{ const r=stage.$('#arm').getBoundingClientRect(); return [r.x,r.y,r.width,r.height]; });
  ok('tf rotates about the pivot (arm hangs down from 300,180 at 90 deg)',Math.abs(pin[0]-295)<1&&Math.abs(pin[1]-180)<1&&Math.abs(pin[3]-100)<1,pin.map(v=>v.toFixed(1)).join(','));
  ok('M.pointIn maps a local point through the rig',await p.evaluate(()=>{ const [x,y]=M.pointIn(stage.$('#arm'),100,0); return Math.abs(x-300)<.01&&Math.abs(y-280)<.01; }));
  await seek(0); const spans=await p.evaluate(()=>stage.$$('#title span span').length); ok('M.split wraps each non-space character',spans===10,spans+' spans');
  const sp2=await p.evaluate(()=>{ const el=stage.$('#t2'), w=M.split(el,'words'); return {n:w.length,text:el.innerText.replace(/\s+/g,' '),br:!!el.querySelector('br'),b:el.querySelector('b span')?.textContent,
    lines:new Set(w.map(s=>Math.round(s.getBoundingClientRect().top))).size}; });
  ok('M.split keeps <br> and inline markup, and splits words',sp2.n===6&&sp2.br&&sp2.b==='light'&&sp2.text==='What if light woke you up',JSON.stringify(sp2));
  const nobreak=await p.evaluate(()=>{ const d=M.html('div',{style:'position:absolute;width:90px;font:20px sans-serif'},stage.html); d.textContent='abc defghij klm'; const c=M.split(d);
    const byWord=[[0,3],[3,10],[10,13]].map(([a,b])=>new Set(c.slice(a,b).map(s=>Math.round(s.getBoundingClientRect().top))).size); d.remove(); return byWord; });
  ok('M.split by chars never breaks a line inside a word',nobreak.every(n=>n===1),JSON.stringify(nobreak));
  const {p:p2}=await open(2); await p2.evaluate(()=>window.__anim.seek(0)); px=await pixels(p2,[[1199,599],[1201,601],[1218,618],[1221,621]]);
  ok('canvas layers are hi-DPI and drawn in stage units (10 units = 20 px at 2x)',px[0][0]>200&&px[1][0]<60&&px[2][0]<60&&px[3][0]>200,JSON.stringify(px));

  // ---- motion.js maths ----
  const m=await p.evaluate(()=>{ const E=M.ease, names=Object.keys(E).filter(k=>typeof E[k]==='function'&&E[k].length===1&&!['back','elastic','steps','spring','bezier'].includes(k));
    const endsBad=names.filter(k=>Math.abs(E[k](0))>1e-6||Math.abs(E[k](1)-1)>1e-6);
    const kf=[M.kf(0,[[0,0],[1,10],[2,0]]),M.kf(1,[[0,0],[1,10],[2,0]]),M.kf(.5,[[0,0],[1,10,E.linear]]),M.kf(5,[[0,0],[1,10]])];
    const keys=[[0,0],[1,10],[3,-4],[4,2]], sp=keys.map(([t])=>M.spline(t,keys)), smooth=Math.abs((M.spline(1+1e-4,keys)-M.spline(1-1e-4,keys))/2e-4)>0;
    const col=M.mix('#000000','#ffffff',.5), path=M.mix('M0 0 L10 20','M10 10 L30 40',.5), bad=M.mix('M0 0','M0 0 L1 1',.4);
    const spr=[M.spring(0),M.spring(10),Math.max(...Array.from({length:200},(_,i)=>M.spring(i/100,2,.3)))], se=E.spring(.4);
    const ik=M.ik2(0,0,120,50,100,60,1), ex=100*Math.cos(M.rad(ik.a1))+60*Math.cos(M.rad(ik.a1+ik.a2)), ey=100*Math.sin(M.rad(ik.a1))+60*Math.sin(M.rad(ik.a1+ik.a2));
    const far=M.ik2(0,0,500,0,100,60), r1=M.rng(3), r2=M.rng(3), seqA=[r1(),r1(),r1()], seqB=[r2(),r2(),r2()];
    const arcP=[M.arc(0,[0,100],[200,100],50),M.arc(.5,[0,100],[200,100],50),M.arc(1,[0,100],[200,100],50)], bz=E.bezier(.25,.1,.25,1);
    return {endsBad, kf, sp, smooth, col, path, bad, spr, se:[se(0),se(1),Math.max(...Array.from({length:100},(_,i)=>se(i/100)))], ikErr:Math.hypot(ex-120,ey-50), far:far.a1, seqA, seqB,
      hash:[M.hash(5,1),M.hash(5,1),M.hash(6,1)], noise:Math.max(...Array.from({length:500},(_,i)=>Math.abs(M.noise(i*.037,2)))), arcP, bz:[bz(0),bz(.5),bz(1)],
      samp:[M.sample([[0,0],[10,20]],.05,10),M.sample([1,2,3],5,10)], shots:M.shots(2.5,[1,2,3]), q:M.quantize(.49,12), loop:M.loop(-1,3), stag:M.stagger(1.3,2,1,.1,.2), sq:M.squash(1.25) }; });
  ok('every easing starts at 0 and ends at 1',m.endsBad.length===0,m.endsBad.join(','));
  ok('M.kf holds before, hits keys, eases between, holds after',m.kf[0]===0&&m.kf[1]===10&&m.kf[2]===5&&m.kf[3]===10,m.kf.join(','));
  ok('M.spline passes through every key without stopping',m.sp.join()==='0,10,-4,2'&&m.smooth,m.sp.join(','));
  ok('M.mix blends colours and same-shape path strings, switches otherwise',/^#[0-9a-f]{6}$/.test(m.col)&&m.col!=='#000000'&&m.path==='M5 5 L20 30'&&m.bad==='M0 0',m.col+' | '+m.path);
  ok('M.spring starts at 0, settles at 1, overshoots when underdamped',m.spr[0]===0&&Math.abs(m.spr[1]-1)<1e-3&&m.spr[2]>1.1,m.spr.map(v=>v.toFixed(3)).join(','));
  ok('ease.spring ends exactly at 1 and overshoots',m.se[0]===0&&m.se[1]===1&&m.se[2]>1,m.se.map(v=>v.toFixed(3)).join(','));
  ok('M.ik2 reaches a reachable target',m.ikErr<1e-6,m.ikErr.toExponential(2));
  ok('M.ik2 straightens toward an unreachable target',Math.abs(m.far)<1e-3,String(m.far));
  ok('M.rng and M.hash are deterministic',JSON.stringify(m.seqA)===JSON.stringify(m.seqB)&&m.hash[0]===m.hash[1]&&m.hash[0]!==m.hash[2]);
  ok('M.noise stays in [-1,1]',m.noise<=1,m.noise.toFixed(3));
  ok('M.arc starts, peaks and lands where asked',m.arcP[0][1]===100&&Math.abs(m.arcP[1][1]-50)<1e-9&&m.arcP[2][0]===200&&m.arcP[2][1]===100,JSON.stringify(m.arcP));
  ok('ease.bezier matches CSS ease at the ends and midpoint',m.bz[0]===0&&m.bz[2]===1&&Math.abs(m.bz[1]-.8024)<.01,m.bz.map(v=>v.toFixed(4)).join(','));
  ok('M.sample interpolates baked samples and holds the last one',JSON.stringify(m.samp)==='[[5,10],3]',JSON.stringify(m.samp));
  ok('time helpers: shots, quantize, loop, stagger, squash',m.shots.i===1&&m.shots.t===1.5&&Math.abs(m.q-5/12)<1e-9&&m.loop===2&&Math.abs(m.stag-.5)<1e-9&&m.sq[0]*m.sq[1]===1,JSON.stringify(m.shots));
  await br.close(); srv.close();

  // ---- CLI ----
  let r=cli(['check']); ok('check reports browser and ffmpeg',r.code===0&&/browser \d/.test(r.out)&&/ffmpeg/.test(r.out),r.out.split('\n').slice(2).join(' | '));
  r=cli(['stills','--at=0.5,f45']); ok('stills writes one PNG per time (seconds or f<frame>)',r.code===0&&fs.existsSync(path.join(REV,'still-0.50s.png'))&&fs.existsSync(path.join(REV,'still-1.50s.png')),r.out.trim());
  r=cli(['stills','--at=1','--ref='+path.join(REV,'still-0.50s.png')]); ok('stills --ref overlays the reference',r.code===0&&fs.existsSync(path.join(REV,'still-1.00s-ref.png')));
  r=cli(['stills','--at=1','--size=640x480']); ok('a size with another aspect is refused',r.code!==0&&/aspect/.test(r.out));
  r=cli(['sheet','--n=6']); ok('sheet writes a contact sheet',r.code===0&&/sheet-0\.00-3\.97\.png/.test(r.out),r.out.trim());
  r=cli(['study','--from=0','--to=1','--track=#ball']); const sp=(r.out.match(/spacing per frame \(stage units\) ([\d. ]+)/)||[])[1]||'';
  ok('study tracks one dot per frame with the true spacing',r.code===0&&sp.trim().split(' ').length===30&&sp.trim().split(' ').every(v=>Math.abs(v-3.3)<.05),sp.slice(0,40));
  r=cli(['probe',path.join(REV,'still-0.50s.png'),'--pick=60,30']); ok('probe reports size, palette and exact picks',r.code===0&&/640x360/.test(r.out)&&/#ffffff/.test(r.out)&&/pick 60,30 #ff0000/.test(r.out),r.out.split('\n')[2]);
  r=cli(['stills','--at=0','--scene=src/scene-load.js']); r=cli(['probe',path.join(REV,'still-0.00s.png'),'--pick=25,50;75,50;125,50;175,50;225,50;275,50']);
  ok('stage.load scopes each file\'s styles and renames colliding ids',(r.out.match(/pick \S+ (#\w+)/g)||[]).map(v=>v.split(' ').pop()).join()==='#ff0000,#ff0000,#0000ff,#0000ff,#ff0000,#ff0000',r.out.split('\n').filter(l=>l.startsWith('pick')).map(l=>l.split(' ').pop()).join(','));
  r=cli(['stills','--at=0','--scene=src/scene-load.js','--set=bg=transparent']); r=cli(['probe',path.join(REV,'still-0.00s.png'),'--pick=150,50;150,110']);
  ok('--set reaches the scene as PARAMS; a transparent background is really transparent',/pick 150,50 #0000ff/.test(r.out)&&/pick 150,110 #\w+ alpha 0/.test(r.out),r.out.split('\n')[0]);
  r=cli(['probe',path.join(REV,'still-0.50s.png'),'--bbox=30,5,60,50']); ok('probe --bbox finds a figure\'s exact extent',/bbox 30,5,60,50: x 50\.\.69, y 20\.\.39/.test(r.out),r.out.split('\n').pop()||r.out.split('\n').slice(-2)[0]);
  r=cli(['stills','--at=0','--scene=src/scene-font.js']); const r2=cli(['stills','--at=0']);
  ok('a missing font is reported once; installed and generic fonts are not',(r.out.match(/FONT FALLBACK: "NoSuchFont"/g)||[]).length===1&&!/FONT FALLBACK/.test(r2.out),r.out.split('\n')[0].slice(0,80));
  r=cli(['sheet','--scene=src/scene-bad.js']); ok('a throwing scene names the time and frame',r.code!==0&&/scene threw at t=(1\.\d+|2\.00)s \(frame \d+\)/.test(r.out),r.out.trim().split('\n').pop());
  r=cli(['video','--scene=src/scene-hang.js','--out=out/h/','--timeout=3']); ok('a render that never returns is stopped and named',r.code!==0&&/did not return within 3 s/.test(r.out)&&/scene threw at t=0\.[5-9]\d*s \(frame (1[6-9]|2\d)\)/.test(r.out),r.out.trim().split('\n').pop());
  r=cli(['stills','--at=0','--scene=src/scene-norender.js']); ok('a scene without render() is refused with the reason',r.code!==0&&/SCENE.render\(t,stage\) is missing/.test(r.out));
  r=cli(['video','--out=x.mp4','--size','1920x1080']); ok('an option given with a space is refused',r.code!==0&&/unexpected argument: 1920x1080/.test(r.out));
  r=cli(['video','--output=x.mp4']); ok('an unknown option is refused and the valid ones listed',r.code!==0&&/unknown option for video: --output/.test(r.out)&&/--out /.test(r.out));
  r=cli(['video','--out=out/range/','--from=3.5','--to=9']); ok('--to past the end is clamped with a note',r.code===0&&/past the end/.test(r.out)&&fs.readdirSync(path.join(T,'out/range')).length===15);
  r=cli(['video','--out=out/range2/','--from=5']); ok('--from after the end is refused',r.code!==0&&/must be before/.test(r.out));
  r=cli(['video','--scene=src/scene-cut.js','--out=out/w1/','--workers=1']); const r4=cli(['video','--scene=src/scene-cut.js','--out=out/w4/','--workers=4']);
  const same=r.code===0&&r4.code===0&&/on 4 pages/.test(r4.out)&&fs.readdirSync(path.join(T,'out/w1')).every(f=>hash(fs.readFileSync(path.join(T,'out/w1',f)))===hash(fs.readFileSync(path.join(T,'out/w4',f))));
  ok('parallel pages write the same frames in the same order as one page',same,r4.out.trim().split('\n').pop());
  r=cli(['sheet','--scene=src/scene-state.js','--n=3']); ok('state carried between render calls is reported',/WARNING: the frame at [\d.]+s changed/.test(r.out),r.out.split('\n')[0].slice(0,90));
  r=cli(['video','--scene=src/scene-rnd.js','--out=out/rnd/','--workers=2']); const r1=cli(['video','--scene=src/scene-rnd.js','--out=out/rnd1/','--workers=1']);
  ok('Math.random is seeded: no warning, and pages and runs agree frame for frame',r.code===0&&!/WARNING/.test(r.out)&&fs.readdirSync(path.join(T,'out/rnd')).every(f=>hash(fs.readFileSync(path.join(T,'out/rnd',f)))===hash(fs.readFileSync(path.join(T,'out/rnd1',f)))));
  r=cli(['sheet','--n=3']); ok('a pure scene passes the self-check silently',r.code===0&&!/WARNING/.test(r.out));
  r=cli(['video','--scene=src/scene-cut.js','--out=out/frames/','--to=0.5']); ok('video to a folder writes a PNG sequence',r.code===0&&fs.readdirSync(path.join(T,'out/frames')).length===15);
  if(!ffBin){ console.log('skip  video/qa/audio checks: no full ffmpeg (pip install imageio-ffmpeg)'); }
  else {
    r=cli(['video','--scene=src/scene-cut.js','--out=out/cut.mp4','--qa']); const info=spawnSync(ffBin,['-hide_banner','-i',path.join(T,'out/cut.mp4')],{encoding:'utf8'}).stderr;
    ok('video writes an H.264 MP4 of the right length',r.code===0&&/h264/.test(info)&&/Duration: 00:00:03\.00/.test(info),(info.match(/Duration: [^,]+/)||[''])[0]);
    const vs=cli(['sheet','out/cut.mp4','--n=4']); ok('sheet reads a video file',vs.code===0&&/sheet-cut-0\.00-2\.97\.png/.test(vs.out),vs.out.trim());
    ok('qa finds the planned hold (1-2 s) and both pops (1 s, 2 s)',/holds[^\n]*1\.00–2\.00s/.test(r.out)&&/jumps[^\n]*1\.00s[^\n]*2\.00s/.test(r.out),r.out.split('\n').filter(l=>/^(holds|jumps)/.test(l)).join(' | '));
    r=cli(['video','--out=out/smooth.mp4','--scale=.5','--qa']); ok('qa reports no jumps on smooth motion',r.code===0&&/jumps[^\n]*none/.test(r.out),r.out.split('\n').filter(l=>/^jumps/.test(l)).join(''));
    W('scene-loop.js',`const SCENE={width:320,height:180,fps:30,duration:2,background:'#223',setup(s){s.add('<circle id="c" r="20" fill="#fc0"/>')},render(t,s){M.tf(s.$('#c'),{x:160+100*Math.sin(M.TAU*t/2),y:90})}};`);
    r=cli(['video','--scene=src/scene-loop.js','--out=out/loop.mp4','--qa','--loop']); ok('qa --loop passes a periodic loop',r.code===0&&/loop seam: smooth/.test(r.out));
    r=cli(['qa','out/cut.mp4','--loop']); ok('qa --loop catches a seam that pops',/loop seam: POPS/.test(r.out),r.out.split('\n').pop()||r.out.split('\n').slice(-2)[0]);
    r=cli(['video','--scene=src/scene-alpha.js','--out=out/a.webm']); const wi=spawnSync(ffBin,['-hide_banner','-c:v','libvpx-vp9','-i',path.join(T,'out/a.webm')],{encoding:'utf8'}).stderr;
    spawnSync(ffBin,['-y','-loglevel','error','-c:v','libvpx-vp9','-i',path.join(T,'out/a.webm'),'-frames:v','1',path.join(T,'out/a-f0.png')]); const pa=cli(['probe',path.join(T,'out/a-f0.png'),'--pick=5,5;160,90']);
    ok('a transparent scene keeps real alpha in WebM',r.code===0&&/yuva420p/.test(wi)&&/pick 5,5 #\w+ alpha 0/.test(pa.out)&&/pick 160,90 #f[ef][78]/.test(pa.out),pa.out.split('\n').filter(l=>l.startsWith('pick')).join(' | '));
    r=cli(['video','--scene=src/scene-alpha.js','--out=out/a.gif','--fps=20']); ok('GIF export works',r.code===0&&fs.statSync(path.join(T,'out/a.gif')).size>1000);
    r=cli(['video','--scene=src/scene-cut.js','--out=out/mb.mp4','--to=0.3','--mblur=3']); ok('motion blur renders',r.code===0&&/mblur 3/.test(r.out),r.out.trim().split('\n').pop());
    const wav=path.join(T,'click.wav'); spawnSync(ffBin,['-y','-loglevel','error','-f','lavfi','-i',"aevalsrc='if(lt(mod(t-0.25\\,0.5)\\,0.03)*gte(t\\,0.25)\\,0.6*sin(2*PI*880*t)\\,0)':s=44100:d=6",wav]);
    r=cli(['audio',wav]); const bpm=+(r.out.match(/tempo ≈ ([\d.]+)/)||[])[1];
    ok('audio finds a 120 BPM click track and its hits',r.code===0&&Math.abs(bpm-120)<2&&/strongest hits: 0\.2\d 0\.7\d/.test(r.out),r.out.split('\n').slice(1,3).join(' | '));
    r=cli(['video','--scene=src/scene-cut.js','--out=out/aud.mp4','--audio='+wav]); ok('video muxes audio',r.code===0&&/Audio: aac/.test(spawnSync(ffBin,['-hide_banner','-i',path.join(T,'out/aud.mp4')],{encoding:'utf8'}).stderr));
  }
  console.log(fails?`${fails} FAILED`:'ALL PASSED','  tmp:',T); process.exit(fails?1:0); })();
