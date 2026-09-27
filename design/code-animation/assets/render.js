// render.js: frame-exact capture of stage.html + scene.js in headless Chromium, plus review tools. Run from anywhere; paths resolve against the cwd.
//   node src/render.js video  --out=output/name.mp4 [--scale=1|--width=N|--size=WxH] [--fps=N] [--from=s --to=s] [--mblur=N] [--audio=file] [--qa]
//   node src/render.js stills --at=0,1.5,f90 [--scale=1] [--ref=refs/sheet.png --ref-opacity=.5 --ref-box=x,y,w,h]
//   node src/render.js sheet  [<video>] [--n=12] [--from=s --to=s]    contact sheet: n frames in one labelled grid, of the scene or of any video file
//   node src/render.js study  --from=s --to=s [--n=8] [--track=#a,#b]  motion study: onion skin of the moving parts + per-frame spacing dots
//   node src/render.js probe  <image> [--pick=x,y;x,y] [--bbox=x,y,w,h;…] [--crop=x,y,w,h]  size, palette, exact pixel colours, a figure's extent
//   node src/render.js qa     <video> [--loop]                         holds (frozen spans) and jumps (hard frame changes) with timecodes; --loop also checks the seam
//   node src/render.js audio  <file> [--json=src/audio.json [--fps=30]] duration, tempo + beat grid, strongest hits, energy jumps; --json writes per-frame curves
//   node src/render.js check                                           is playwright, a browser and a full ffmpeg available?
// Common: --scene=src/scene.js  --set=k=v,k2=v2 (global PARAMS in scene.js, for variants)  --dir=<review folder, default $TMPDIR/code-animation>. Output formats by extension: .mp4 .webm .mov (ProRes 4444, alpha) .gif, or a folder/ for PNGs.
const {chromium}=require('playwright'), fs=require('fs'), os=require('os'), path=require('path'), http=require('http'), {spawn,spawnSync,execFileSync}=require('child_process');
const argv=process.argv.slice(2), F={}, P=[];
// a list option given twice (--bbox=a --bbox=b) accumulates; any other option given twice is an error rather than silently keeping the last
const LISTS={bbox:';',pick:';',at:',',track:',',set:','};
for(const a of argv){ if(a.startsWith('--')){ const [k,v]=a.slice(2).split(/=(.*)/s), val=v===undefined?true:v;
    if(k in F){ if(LISTS[k]&&typeof val==='string') F[k]+=LISTS[k]+val; else { console.error(`--${k} is given twice`); process.exit(1); } } else F[k]=val; } else P.push(a); }
const cmd=P[0]||'video', dir=path.resolve(F.dir||path.join(os.tmpdir(),'code-animation'));
// typos fail loudly instead of being ignored: an unknown --flag, or a value given with a space (--size 1920x1080) instead of =
const KNOWN={video:'out scale width size fps from to mblur audio qa loop workers codec colors',stills:'at scale width size ref ref-opacity ref-box',sheet:'n from to',study:'from to n track',
  probe:'pick crop bbox bg colors',qa:'loop',audio:'json fps',check:''}, COMMON='scene set dir timeout', TAKES={probe:1,qa:1,audio:1,sheet:1};
if(KNOWN[cmd]!==undefined){ const ok=new Set((KNOWN[cmd]+' '+COMMON).split(' ').filter(Boolean)), bad=Object.keys(F).filter(k=>!ok.has(k)), extra=P.slice(1+(TAKES[cmd]||0));
  if(bad.length||extra.length){ console.error(`${bad.length?`unknown option${bad.length>1?'s':''} for ${cmd}: ${bad.map(k=>'--'+k).join(' ')}. `:''}${extra.length?`unexpected argument${extra.length>1?'s':''}: ${extra.join(' ')} (options take =, as in --size=1920x1080). `:''}Options for ${cmd}: ${[...ok].map(k=>'--'+k).join(' ')}`); process.exit(1); } }
const die=m=>{ console.error(m); process.exit(1); };
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
const num=(v,d)=>v===undefined||v===true||v===''?d:+v;

// ---- local http server over the filesystem: fonts, canvas pixel reads and ES modules all fail from file:// ----
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg',
  '.webp':'image/webp','.gif':'image/gif','.avif':'image/avif','.woff':'font/woff','.woff2':'font/woff2','.ttf':'font/ttf','.otf':'font/otf','.mp3':'audio/mpeg','.wav':'audio/wav','.glb':'model/gltf-binary','.gltf':'model/gltf+json'};
const serve=()=>new Promise(ok=>{ const s=http.createServer((q,r)=>{ const f=decodeURIComponent(new URL(q.url,'http://x').pathname).replace(/^\/([A-Za-z]:)/,'$1'); // /C:/… on Windows
  fs.readFile(f,(e,d)=>{ if(e){ r.writeHead(404); r.end(); return; } r.writeHead(200,{'content-type':MIME[path.extname(f).toLowerCase()]||'application/octet-stream','access-control-allow-origin':'*'}); r.end(d); }); });
  s.listen(0,'127.0.0.1',()=>ok(s)); });
const urlOf=(srv,f)=>`http://127.0.0.1:${srv.address().port}${path.resolve(f).split(path.sep).map(encodeURIComponent).join('/').replace(/^([^/])/,'/$1')}`;

// remote requests from the page (web fonts, CDN libraries, images) go through Node: it honours the system's proxy CA (NODE_EXTRA_CA_CERTS)
// where Chromium may not, and one download is shared by every page of the run
const REMOTE=new Map();
async function routeRemote(ctx){ await ctx.route(u=>/^https?:/.test(u.href)&&!/^https?:\/\/(127\.0\.0\.1|localhost)[:/]/.test(u.href), async r=>{
  const q=r.request(), key=q.method()==='GET'?q.url():null;
  try{ if(key&&REMOTE.has(key)) return r.fulfill(REMOTE.get(key)); const res=await r.fetch(), v={status:res.status(),headers:res.headers(),body:await res.body()};
    if(key&&res.ok()) REMOTE.set(key,v); await r.fulfill(v); }catch(e){ console.error(`remote request failed: ${q.url()} (${e.message.split('\n')[0]})`); await r.abort().catch(()=>{}); } }); }
const NOISE=/GL Driver Message|GroupMarkerNotSet|swiftshader|WebGL-0x|Automatic fallback to software WebGL/i;
const launch=()=>chromium.launch({args:['--force-color-profile=srgb','--font-render-hinting=none','--enable-unsafe-swiftshader']}).catch(()=>{ console.error('bundled Chromium unavailable, using installed Chrome'); return chromium.launch({channel:'chrome'}); });
// open the stage at a device scale factor so the output is W*dsf x H*dsf pixels
async function openStage(br,srv,dsf,extra='',quiet=false){
  const scene=path.resolve(F.scene||path.join(__dirname,'scene.js')); if(!fs.existsSync(scene)) die('no scene at '+scene);
  const ctx=await br.newContext({viewport:{width:1280,height:720},deviceScaleFactor:dsf}); await routeRemote(ctx); const page=await ctx.newPage(); let err=null;
  page.on('pageerror',e=>{ err=e.message; console.error('PAGE ERROR:',e.message); });
  page.on('console',m=>{ const ty=m.type(); if(ty==='error'||(ty==='warning'&&!quiet&&!NOISE.test(m.text()))) console.error(ty==='error'?'console:':'warning:',m.text()); });
  await page.goto(urlOf(srv,path.join(__dirname,'stage.html'))+'?render&scene='+encodeURIComponent(urlOf(srv,scene))+(F.set?'&set='+encodeURIComponent(F.set):'')+extra);
  await page.waitForFunction(()=>window.READY||window.LOAD_ERROR,null,{timeout:180000}).catch(()=>{});
  const meta=await page.evaluate(()=>{ const a=window.__anim; return a&&{W:a.W,H:a.H,fps:a.fps,duration:a.duration,frames:a.frames,background:a.background,audio:a.audio}; });
  if(err||!meta){ await br.close(); die('scene failed to load'+(err?'':' (no error thrown: is SCENE defined, and does setup() resolve?)')); }
  await page.setViewportSize({width:meta.W,height:meta.H});
  const limit=num(F.timeout,60)*1000; // one frame taking this long is a hang (an endless loop in render), not a slow frame
  const seek=async t=>{ let timer; try{ await Promise.race([page.evaluate(t=>window.__anim.seek(t),t),new Promise((_,no)=>{ timer=setTimeout(()=>no(new Error(`render(t) did not return within ${limit/1000} s (an endless loop? raise --timeout=s for genuinely heavy frames)`)),limit); })]); }
    catch(e){ err=err||e.message.split('\n')[0]; } finally{ clearTimeout(timer); } if(err){ await br.close(); die(`scene threw at t=${fmt(t)}s (frame ${Math.round(t*meta.fps)}): ${err}`); } };
  const shot=async(t,alpha)=>{ await seek(t); return page.screenshot({type:'png',omitBackground:!!alpha}); };
  await seek(0); await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  return {page,meta,seek,shot,ctx};
}
// a frame must come out the same after seeking elsewhere, and on every page: otherwise render(t) reads state, clocks or accumulated values
async function selfCheck(stages,t,meta,alpha){ const a=await stages[0].shot(t,alpha); await stages[0].seek(0); await stages[0].seek(lastT(meta));
  const again=[await stages[0].shot(t,alpha)]; if(stages[1]) again.push(await stages[1].shot(t,alpha));
  if(again.some(b=>!a.equals(b))) console.error(`WARNING: the frame at ${fmt(t)}s changed after seeking elsewhere${stages[1]?' or on another page':''}: render(t) depends on something besides t `+
    '(state carried between calls such as x+=v, Date or performance.now, or setup that differs per page). Frames will flicker or disagree between sheet, preview and final. See hard rules 1-2.'); }
async function sceneMeta(br,srv){ const s=await openStage(br,srv,1,'',true); await s.ctx.close(); return s.meta; }
// output size from --size / --width / --scale; the aspect must match the scene (compose a new scene for another aspect)
function outSize(meta,defScale=1){ let w,h; if(F.size){ [w,h]=F.size.split('x').map(Number); } else if(F.width){ w=+F.width; h=Math.round(w*meta.H/meta.W); } else { const k=num(F.scale,defScale); w=Math.round(meta.W*k); h=Math.round(meta.H*k); }
  if(Math.abs(h-w*meta.H/meta.W)>1.5) die(`--size ${w}x${h} does not match the scene aspect ${meta.W}x${meta.H}; compose a scene for that aspect instead of stretching`); return {w,h,dsf:w/meta.W}; }
const parseT=(v,meta)=>String(v).trim().startsWith('f')?+String(v).trim().slice(1)/meta.fps:+v;
const lastT=meta=>(meta.frames-1)/meta.fps;
const fmt=t=>(+t).toFixed(2);

// ---- a blank page for compositing (contact sheets, onion skins, motion blur, image probes) ----
async function composer(br){ const ctx=await br.newContext({deviceScaleFactor:1}); await routeRemote(ctx); const page=await ctx.newPage(); await page.setContent('<body style="margin:0"></body>'); await page.addScriptTag({content:HELP}); return page; }
const dataUrl=b=>'data:image/png;base64,'+b.toString('base64');
const fromDataUrl=u=>Buffer.from(u.split(',')[1],'base64');
const HELP=`window.load=u=>new Promise((ok,no)=>{ const i=new Image(); i.crossOrigin='anonymous'; i.onload=()=>ok(i); i.onerror=()=>no(new Error('cannot load image')); i.src=u; });
  window.pix=(i,w,h)=>{ const c=document.createElement('canvas'); c.width=w||i.naturalWidth; c.height=h||i.naturalHeight; const g=c.getContext('2d'); g.drawImage(i,0,0,c.width,c.height); return g.getImageData(0,0,c.width,c.height); };`;

// ---- ffmpeg: needs a full build (libx264, palettegen, freezedetect). Playwright's own ffmpeg can only write VP8 WebM from JPEG frames ----
function findFfmpeg(){ const c=[process.env.FFMPEG,'ffmpeg'];
  try{ c.push(execFileSync('python3',['-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],{stdio:['ignore','pipe','ignore']}).toString().trim()); }catch{}
  try{ c.push(require('ffmpeg-static')); }catch{}
  for(const f of c) if(f) try{ if(execFileSync(f,['-hide_banner','-encoders'],{stdio:['ignore','pipe','ignore']}).toString().includes('libx264')) return {bin:f,full:true}; }catch{}
  const roots=[process.env.PLAYWRIGHT_BROWSERS_PATH,path.join(os.homedir(),'.cache','ms-playwright'),path.join(os.homedir(),'Library','Caches','ms-playwright')].filter(Boolean);
  for(const r of roots) try{ for(const d of fs.readdirSync(r).filter(d=>d.startsWith('ffmpeg'))) for(const b of ['ffmpeg-linux','ffmpeg-mac','ffmpeg-win64.exe']) if(fs.existsSync(path.join(r,d,b))) return {bin:path.join(r,d,b),full:false}; }catch{}
  return null; }
const NOFF='No full ffmpeg found. Install one: `pip install imageio-ffmpeg` (bundles a static ffmpeg), or `npm i ffmpeg-static` in src/, or the system package; or set FFMPEG=/path/to/ffmpeg.\n'+
  'Without it you can still write a PNG sequence (--out=output/frames/) or, with Playwright\'s ffmpeg, a VP8 .webm.';
// a partial render (--from) starts the audio at the same point
function encoderArgs(ext,fps,alpha,audio,from=0){ const i=['-y','-hide_banner','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-c:v','png','-i','pipe:0'], a=audio?[...(from>0?['-ss',String(from)]:[]),'-i',audio]:[], m=audio?['-map','0:v','-map','1:a','-shortest']:[];
  if(ext==='.mp4') return [...i,...a,...m,'-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2','-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',...(audio?['-c:a','aac','-b:a','192k']:[])];
  if(ext==='.webm') return [...i,...a,...m,'-c:v','libvpx-vp9','-b:v','0','-crf','26','-row-mt','1','-pix_fmt',alpha?'yuva420p':'yuv420p',...(alpha?['-auto-alt-ref','0']:[]),...(audio?['-c:a','libopus','-b:a','160k']:[])];
  if(ext==='.mov') return [...i,...a,...m,...(F.codec==='png'?['-c:v','png','-pix_fmt',alpha?'rgba':'rgb24']:['-c:v','prores_ks','-profile:v','4','-pix_fmt',alpha?'yuva444p10le':'yuv444p10le','-vendor','apl0']),...(audio?['-c:a','pcm_s16le']:[])];
  if(ext==='.gif') return [...i,'-vf',`split[a][b];[a]palettegen=stats_mode=diff:max_colors=${clamp(num(F.colors,256)|0,2,256)}`+(alpha?':reserve_transparent=1':'')+'[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle'+(alpha?':alpha_threshold=128':''),'-loop','0'];
  die('unsupported output '+ext+' (use .mp4 .webm .mov .gif or a folder/)'); }

async function video(){ const out=F.out; if(!out) die('video needs --out=output/name.mp4 (or a folder/ for PNG frames)');
  const ext=path.extname(out).toLowerCase(), seq=!ext||out.endsWith('/'), ff=seq?null:findFfmpeg();
  if(F.codec&&(ext!=='.mov'||!['png','prores'].includes(F.codec))) die('--codec is for .mov only: --codec=prores (default, ProRes 4444) or --codec=png (lossless, several times smaller)');
  if(F.colors&&ext!=='.gif') die('--colors is for .gif only');
  if(!seq&&!ff) die(NOFF); if(!seq&&!ff.full&&ext!=='.webm') die(NOFF); if(F.audio&&F.audio!=='none'&&!fs.existsSync(F.audio)) die('no audio file '+F.audio);
  const srv=await serve(), br=await launch(), meta=await sceneMeta(br,srv), {w,h,dsf}=outSize(meta), fps=num(F.fps,meta.fps);
  // SCENE.audio is the default soundtrack (served from the filesystem, so its URL path is its file path); --audio=none renders silent
  if(F.audio==='none') delete F.audio; else if(!F.audio&&meta.audio&&!['.gif'].includes(ext)&&!seq){ F.audio=decodeURIComponent(new URL(meta.audio).pathname).replace(/^\/([A-Za-z]:)/,'$1');
    if(!fs.existsSync(F.audio)) die('SCENE.audio points at a missing file: '+F.audio); console.error('soundtrack from SCENE.audio: '+F.audio); }
  const from=num(F.from,0), to=Math.min(num(F.to,meta.duration),meta.duration); if(!(to>from)) die(`--from=${from} must be before --to=${to} (the scene lasts ${meta.duration} s)`);
  if(num(F.to,0)>meta.duration) console.error(`--to=${F.to} is past the end of the scene; rendering to ${meta.duration} s`);
  const n=Math.max(1,Math.round((to-from)*fps)), alpha=meta.background==='transparent'&&(seq||['.webm','.mov','.gif'].includes(ext)), mb=Math.max(1,num(F.mblur,1)|0);
  // parallel pages: each renders every nth frame; the writer takes them in order and workers stay at most 2 rounds ahead
  const nw=Math.max(1,Math.min(num(F.workers,Math.min(4,Math.max(1,os.cpus().length-1)))|0,Math.ceil(n/8)));
  const workers=await Promise.all(Array.from({length:nw},async()=>({st:await openStage(br,srv,dsf,'',true),comp:mb>1?await composer(br):null})));
  fs.mkdirSync(seq?out:path.dirname(path.resolve(out)),{recursive:true});
  await selfCheck(workers.map(w=>w.st),from+(n>>1)/fps,meta,alpha);
  let proc=null, errTxt='';
  if(!seq){ const lite=!ff.full; const args=lite?['-y','-hide_banner','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-c:v','mjpeg','-i','pipe:0','-c:v','libvpx','-b:v','12M','-crf','8','-deadline','good',out]:[...encoderArgs(ext,fps,alpha,F.audio,from),out];
    if(lite) console.error('using Playwright\'s limited ffmpeg: VP8 WebM, no alpha, no audio');
    proc=spawn(ff.bin,args,{stdio:['pipe','ignore','pipe']}); proc.stderr.on('data',d=>errTxt+=d); proc.stdin.on('error',()=>{}); }
  let exited=null; if(proc) proc.on('close',c=>{ exited=c; });
  const write=b=>new Promise(r=>{ if(exited!==null) die('ffmpeg exited early:\n'+errTxt.slice(-3000)); if(proc.stdin.write(b)) return r();
    const dead=()=>die('ffmpeg exited early:\n'+errTxt.slice(-3000)); proc.once('close',dead); proc.stdin.once('drain',()=>{ proc.off('close',dead); r(); }); });
  const lite=proc&&!ff.full, t0=Date.now(); let last=0, written=0;
  const frame=async({st,comp},t)=>{
    if(lite){ await st.seek(t); return st.page.screenshot({type:'jpeg',quality:95}); } // the limited ffmpeg only decodes JPEG
    if(mb<2) return st.shot(t,alpha);
    const subs=[]; for(let j=0;j<mb;j++){ const ts=t+((j+.5)/mb-.5)*.5/fps; // 180-degree shutter centred on the frame; a loop (--loop) wraps instead of clamping
      subs.push(dataUrl(await st.shot(F.loop?((ts%meta.duration)+meta.duration)%meta.duration:clamp(ts,0,meta.duration),alpha))); }
    return fromDataUrl(await comp.evaluate(async([urls,alpha])=>{ const imgs=await Promise.all(urls.map(load));
      const c=document.createElement('canvas'); c.width=imgs[0].naturalWidth; c.height=imgs[0].naturalHeight; const g=c.getContext('2d'), N=c.width*c.height;
      if(!alpha){ imgs.forEach((im,j)=>{ g.globalAlpha=1/(j+1); g.drawImage(im,0,0); }); return c.toDataURL('image/png'); } // opaque: running average on the GPU
      const acc=new Float64Array(N*4); // transparent: average premultiplied colour so edges do not fringe
      for(const im of imgs){ g.clearRect(0,0,c.width,c.height); g.drawImage(im,0,0); const d=g.getImageData(0,0,c.width,c.height).data; for(let p=0;p<N*4;p+=4){ const a=d[p+3]; acc[p]+=d[p]*a; acc[p+1]+=d[p+1]*a; acc[p+2]+=d[p+2]*a; acc[p+3]+=a; } }
      const o=g.createImageData(c.width,c.height); for(let p=0;p<N*4;p+=4){ const a=acc[p+3]; if(a>0){ o.data[p]=acc[p]/a; o.data[p+1]=acc[p+1]/a; o.data[p+2]=acc[p+2]/a; } o.data[p+3]=a/imgs.length; }
      g.putImageData(o,0,0); return c.toDataURL('image/png'); },[subs,alpha])); };
  const done=new Map(), wake=[]; let notify=()=>{};
  const tick=()=>{ const w=wake.splice(0); w.forEach(f=>f()); };
  const produce=async(k)=>{ for(let i=k;i<n;i+=nw){ while(i-written>=2*nw) await new Promise(r=>wake.push(r)); done.set(i,await frame(workers[k],from+i/fps)); notify(); } };
  const consume=async()=>{ for(let i=0;i<n;i++){ while(!done.has(i)) await new Promise(r=>{ notify=r; }); const png=done.get(i); done.delete(i);
      if(seq) fs.writeFileSync(path.join(out,`frame_${String(i).padStart(5,'0')}.png`),png); else await write(png);
      written=i+1; tick(); const pct=Math.floor((i+1)/n*10); if(pct>last){ last=pct; const el=(Date.now()-t0)/1000; console.error(`frame ${i+1}/${n}  ${el.toFixed(0)}s${i+1<n?`, about ${Math.ceil(el/(i+1)*(n-i-1))}s to go`:''}`); } } };
  await Promise.all([consume(),...workers.map((_,k)=>produce(k))]);
  if(proc){ proc.stdin.end(); const code=exited!==null?exited:await new Promise(r=>proc.on('close',r)); if(code) die('ffmpeg failed:\n'+errTxt.slice(-3000)); }
  await br.close(); srv.close();
  const [ow,oh]=ext==='.mp4'&&ff&&ff.full?[w-w%2,h-h%2]:[w,h]; // H.264 4:2:0 needs even sizes
  console.log(`wrote ${out}  ${ow}x${oh}${ow!==w||oh!==h?` (rounded down from ${w}x${h}: H.264 needs even sizes)`:''}  ${n} frames @ ${fps}fps  ${fmt(n/fps)}s${mb>1?'  mblur '+mb:''}${alpha?'  alpha':''}  in ${((Date.now()-t0)/1000).toFixed(1)}s on ${nw} page${nw>1?'s':''}`);
  if(F.qa&&!seq) qa(out); }

async function stills(){ if(!F.at) die('stills needs --at=0,1.5,f90 (seconds, or f<frame>)');
  const srv=await serve(), br=await launch(), meta=await sceneMeta(br,srv), {w,h,dsf}=outSize(meta);
  let extra=''; if(F.ref){ if(!fs.existsSync(F.ref)) die('no ref image '+F.ref); extra=`&ref=${encodeURIComponent(urlOf(srv,F.ref))}&refop=${num(F['ref-opacity'],.5)}`+(F['ref-box']?`&refbox=${F['ref-box']}`:''); }
  const st=await openStage(br,srv,dsf,extra); fs.mkdirSync(dir,{recursive:true});
  for(const v of String(F.at).split(',')){ const t=clamp(parseT(v,meta),0,meta.duration), f=path.join(dir,`still-${fmt(t)}s${F.ref?'-ref':''}.png`);
    fs.writeFileSync(f,await st.shot(t,meta.background==='transparent')); console.log(f); }
  await br.close(); srv.close(); }

// frames of a video file (a reference, or a finished render) as PNG buffers at the given times
function videoInfo(ff,file){ const r=spawnSync(ff.bin,['-hide_banner','-i',file],{encoding:'utf8'}).stderr||'', d=(r.match(/Duration: (\d+):(\d+):([\d.]+)/)||[]).slice(1).map(Number), v=r.match(/Video: .*?, (\d{2,5})x(\d{2,5})[^\n]*?, ([\d.]+) (?:fps|tbr)/);
  if(!d.length||!v) die(file+' is not a video ffmpeg can read'); return {duration:d[0]*3600+d[1]*60+d[2],W:+v[1],H:+v[2],fps:+v[3]}; }
function videoFrame(ff,file,t,w){ const r=spawnSync(ff.bin,['-hide_banner','-loglevel','error','-ss',String(t),'-i',file,'-frames:v','1','-vf',`scale=${w}:-2`,'-f','image2pipe','-c:v','png','pipe:1'],{maxBuffer:256<<20});
  if(r.status||!r.stdout.length) die('could not read a frame at '+fmt(t)+'s from '+file); return r.stdout; }
async function sheet(){ const vid=P[1], srv=await serve(), br=await launch(), n=Math.max(2,num(F.n,12)|0), shots=[]; let meta, from, to, cell;
  if(vid){ const ff=findFfmpeg(); if(!ff||!ff.full) die(NOFF); if(!fs.existsSync(vid)) die('no video '+vid); meta=videoInfo(ff,vid); cell=meta.W>=meta.H?480:300;
    from=num(F.from,0); to=Math.min(num(F.to,meta.duration),meta.duration-1/meta.fps);
    for(let k=0;k<n;k++){ const t=from+(to-from)*k/(n-1); shots.push({t,f:Math.round(t*meta.fps),u:dataUrl(videoFrame(ff,vid,t,cell))}); } }
  else { meta=await sceneMeta(br,srv); from=num(F.from,0); to=Math.min(num(F.to,meta.duration),lastT(meta)); cell=meta.W>=meta.H?480:300;
    const st=await openStage(br,srv,cell/meta.W); await selfCheck([st],Math.round((from+to)/2*meta.fps)/meta.fps,meta,false);
    for(let k=0;k<n;k++){ const t=Math.round((from+(to-from)*k/(n-1))*meta.fps)/meta.fps; shots.push({t,f:Math.round(t*meta.fps),u:dataUrl(await st.shot(t))}); } }
  const cols=Math.max(1,Math.min(n,Math.ceil(Math.sqrt(n*meta.H/meta.W*1.6)))), comp=await composer(br);
  await comp.setContent(`<body style="margin:0;background:#222;font:600 14px system-ui,sans-serif;color:#eee"><div id=g style="display:grid;grid-template-columns:repeat(${cols},${cell}px);gap:6px;padding:6px;width:max-content">`+
    shots.map(s=>`<div style="position:relative"><img src="${s.u}" style="display:block;width:${cell}px"><span style="position:absolute;left:4px;top:4px;background:#000b;padding:1px 5px">${fmt(s.t)}s · f${s.f}</span></div>`).join('')+'</div></body>');
  await comp.evaluate(()=>Promise.all([...document.images].map(i=>i.decode())));
  fs.mkdirSync(dir,{recursive:true}); const f=path.join(dir,`sheet-${vid?path.basename(vid).replace(/\.\w+$/,'')+'-':''}${fmt(from)}-${fmt(to)}.png`); await (await comp.$('#g')).screenshot({path:f}); console.log(f);
  await br.close(); srv.close(); }

async function study(){ const srv=await serve(), br=await launch(), meta=await sceneMeta(br,srv);
  if(F.from===undefined||F.to===undefined) die('study needs --from=s --to=s around one action (0.3 to 2 s works best)');
  const from=num(F.from,0), to=Math.min(num(F.to,meta.duration),meta.duration), n=Math.max(2,num(F.n,8)|0), dsf=Math.min(1,960/meta.W);
  const st=await openStage(br,srv,dsf), sels=F.track?String(F.track).split(',').filter(Boolean):[], urls=[], tracks=sels.map(()=>[]);
  for(let k=0;k<n;k++) urls.push(dataUrl(await st.shot(from+(to-from)*k/(n-1))));
  for(let t=from;t<=to+1e-9;t+=1/meta.fps){ await st.seek(t); const pts=await st.page.evaluate(sels=>{ const o=document.getElementById('stage').getBoundingClientRect();
      return sels.map(s=>{ const e=document.querySelector('#stage '+s)||document.querySelector(s); if(!e) return null; const r=e.getBoundingClientRect(); return [r.x+r.width/2-o.x,r.y+r.height/2-o.y]; }); },sels);
    pts.forEach((p,i)=>{ if(!p) die('--track selector not found: '+sels[i]); tracks[i].push(p); }); }
  const comp=await composer(br);
  const png=await comp.evaluate(async([urls,tracks,k])=>{ const imgs=await Promise.all(urls.map(load)), w=imgs[0].naturalWidth, h=imgs[0].naturalHeight, D=imgs.map(i=>pix(i).data), n=D.length, N=w*h;
    // background = per-pixel median across the samples; each sample's pixels that differ from it are its moving parts
    const bg=new Uint8ClampedArray(N*4), col=new Array(n); for(let p=0;p<N*4;p+=4){ for(let c=0;c<4;c++){ for(let j=0;j<n;j++) col[j]=D[j][p+c]; col.sort((a,b)=>a-b); bg[p+c]=col[n>>1]; } }
    const out=new Uint8ClampedArray(bg); for(let j=0;j<n;j++){ const a=j===n-1?1:.18+.5*j/(n-1), d=D[j];
      for(let p=0;p<N*4;p+=4) if(Math.abs(d[p]-bg[p])+Math.abs(d[p+1]-bg[p+1])+Math.abs(d[p+2]-bg[p+2])>36) for(let c=0;c<3;c++) out[p+c]=out[p+c]*(1-a)+d[p+c]*a; }
    const c=document.createElement('canvas'); c.width=w; c.height=h; const g=c.getContext('2d'); g.putImageData(new ImageData(out,w,h),0,0);
    const hues=['#ff2d6f','#00b8ff','#ffb300','#00d68f']; tracks.forEach((tr,i)=>{ g.strokeStyle=g.fillStyle=hues[i%4]; g.lineWidth=1; g.globalAlpha=.5; g.beginPath(); tr.forEach(([x,y],j)=>j?g.lineTo(x*k,y*k):g.moveTo(x*k,y*k)); g.stroke(); g.globalAlpha=1;
      tr.forEach(([x,y])=>{ g.beginPath(); g.arc(x*k,y*k,2.5,0,7); g.fill(); }); });
    return c.toDataURL('image/png'); },[urls,tracks,dsf]);
  fs.mkdirSync(dir,{recursive:true}); const f=path.join(dir,`study-${fmt(from)}-${fmt(to)}.png`); fs.writeFileSync(f,fromDataUrl(png)); console.log(f);
  if(sels.length) sels.forEach((s,i)=>{ const tr=tracks[i], sp=tr.slice(1).map((p,j)=>Math.hypot(p[0]-tr[j][0],p[1]-tr[j][1]));
    console.log(`${s}: ${tr.length} frames, spacing per frame (stage units) ${sp.map(v=>v.toFixed(1)).join(' ')}`); });
  await br.close(); srv.close(); }

async function probe(){ const img=P[1]; if(!img||!fs.existsSync(img)) die('probe needs an image path'); const srv=await serve(), br=await launch(), comp=await composer(br);
  const r=await comp.evaluate(async([u,pick,crop,k,bbox,bgHex])=>{ const i=await load(u), W=i.naturalWidth, H=i.naturalHeight, s=Math.min(1,240/Math.max(W,H)), d=pix(i,Math.max(1,Math.round(W*s)),Math.max(1,Math.round(H*s))).data;
    const hx=v=>'#'+v.map(c=>Math.round(c).toString(16).padStart(2,'0')).join(''), B=new Map(); let tot=0;
    for(let p=0;p<d.length;p+=4){ if(d[p+3]<128) continue; tot++; const key=(d[p]>>3)<<10|(d[p+1]>>3)<<5|(d[p+2]>>3), b=B.get(key)||[0,0,0,0]; b[0]+=d[p]; b[1]+=d[p+1]; b[2]+=d[p+2]; b[3]++; B.set(key,b); }
    const pal=[]; for(const b of [...B.values()].sort((a,b)=>b[3]-a[3])){ const c=[b[0]/b[3],b[1]/b[3],b[2]/b[3]], near=pal.find(q=>Math.hypot(q.c[0]-c[0],q.c[1]-c[1],q.c[2]-c[2])<34);
      if(near) near.n+=b[3]; else if(pal.length<k) pal.push({c,n:b[3]}); }
    const full=pix(i).data, picks=pick?pick.split(';').map(q=>{ const [x,y]=q.split(',').map(Number), p=(Math.round(y)*W+Math.round(x))*4; return `${x},${y} ${hx([full[p],full[p+1],full[p+2]])}${full[p+3]<255?' alpha '+full[p+3]:''}`; }):[];
    // tight box of the pixels in a region that differ from the background: a figure's extent on a sheet, or of one slice of it (head, torso, legs).
    // The background is --bg, else the image's most common colour (transparent for a mostly transparent image)
    const bgc=bgHex?[...[1,3,5].map(i=>parseInt(bgHex.replace('#','').padEnd(6,'0').slice(i-1,i+1),16)),255]:(tot/(d.length/4)<.5?[0,0,0,0]:[...pal[0].c,255]);
    const boxes=bbox?bbox.split(';').map(q=>{ const [x0,y0,w,h]=q.split(',').map(Number), at=(x,y)=>(Math.min(H-1,Math.max(0,y))*W+Math.min(W-1,Math.max(0,x)))*4;
      const bg=bgc; let a=1e9,b=1e9,c=-1,d=-1;
      for(let y=y0;y<y0+h;y++) for(let x=x0;x<x0+w;x++){ const p=at(x,y); if((bg[3]===0?full[p+3]>40:Math.abs(full[p]-bg[0])+Math.abs(full[p+1]-bg[1])+Math.abs(full[p+2]-bg[2])+Math.abs(full[p+3]-bg[3])>40)){ a=Math.min(a,x); b=Math.min(b,y); c=Math.max(c,x); d=Math.max(d,y); } }
      return c<0?`bbox ${q}: nothing but background`:`bbox ${q}: x ${a}..${c}, y ${b}..${d} (${c-a+1}x${d-b+1}, centre ${((a+c)/2).toFixed(1)},${((b+d)/2).toFixed(1)}, bottom centre ${((a+c)/2).toFixed(1)},${d})`; }):[];
    let cropUrl=null; if(crop){ const [x,y,w,h]=crop.split(',').map(Number), z=Math.max(1,Math.min(8,Math.floor(900/Math.max(w,h)))), c=document.createElement('canvas'); c.width=w*z; c.height=h*z; const g=c.getContext('2d');
      g.imageSmoothingEnabled=false; g.drawImage(i,x,y,w,h,0,0,w*z,h*z); cropUrl=c.toDataURL('image/png'); }
    return {W,H,pal:pal.sort((a,b)=>b.n-a.n).map(p=>`${hx(p.c)} ${(p.n/tot*100).toFixed(1)}%`),picks,boxes,cropUrl,opaque:tot/(d.length/4)}; },[urlOf(srv,img),F.pick||'',F.crop||'',num(F.colors,12),F.bbox||'',F.bg||'']);
  console.log(`${img}: ${r.W}x${r.H}${r.opaque<.99?`, ${((1-r.opaque)*100).toFixed(0)}% transparent`:''}\npalette (share of opaque pixels): ${r.pal.join('  ')}`); r.picks.forEach(p=>console.log('pick '+p)); r.boxes.forEach(b=>console.log(b));
  if(r.cropUrl){ fs.mkdirSync(dir,{recursive:true}); const f=path.join(dir,`crop-${path.basename(img).replace(/\.\w+$/,'')}-${F.crop.replace(/,/g,'_')}.png`); fs.writeFileSync(f,fromDataUrl(r.cropUrl)); console.log(f); }
  await br.close(); srv.close(); }

function qa(file,loop=F.loop){ const ff=findFfmpeg(); if(!ff||!ff.full) die(NOFF); if(!file||!fs.existsSync(file)) die('no file '+file);
  // freezedetect finds holds; the mean absolute difference between neighbouring frames (at 480 px wide) finds jumps
  const r=spawnSync(ff.bin,['-hide_banner','-nostats',...(loop?['-stream_loop','1']:[]),'-i',file,'-an','-vf','freezedetect=n=-60dB:d=0.4,scale=480:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG','-f','null','-'],{encoding:'utf8',maxBuffer:256<<20}).stderr||'';
  const holds=[], d=[]; let open=null, cur=null;
  for(const l of r.split('\n')){ let m; if((m=l.match(/freeze_start: ([\d.]+(?:e[-+]?\d+)?)/i))) open=+m[1]; else if((m=l.match(/freeze_end: ([\d.]+(?:e[-+]?\d+)?)/i))){ holds.push([open,+m[1]]); open=null; }
    else if((m=l.match(/pts_time:([\d.]+)/))) d.push(cur={t:+m[1],v:0}); else if(cur&&(m=l.match(/signalstats\.YAVG=([-\d.]+(?:e[-+]?\d+)?)/i))) cur.v=+m[1]; /* ffmpeg prints tiny values as 4.879e-06 */ } // luma only: tblend's chroma difference wraps around on near-identical frames
  const dur=(r.match(/Duration: (\d+):(\d+):([\d.]+)/)||[]).slice(1).map(Number), total=dur.length?dur[0]*3600+dur[1]*60+dur[2]:null; if(open!==null) holds.push([open,total]);
  // a jump: one frame changes far more than both neighbours (a cut, a pop, a visibility toggle, a motion that starts at full speed)
  const jumps=d.filter((f,i)=>{ const n=Math.max(i>0?d[i-1].v:0,i<d.length-1?d[i+1].v:0); return f.v>=.5&&f.v>=2.5*n; }); // under 0.5 (mean luma change at 480 px) is sub-pixel stepping, not a visible pop
  const fps=+(r.match(/, ([\d.]+) fps/)||[])[1]||30, gap=1.5/fps;
  // holds split only by single-frame flashes (a blinking element) read as one hold
  const hm=[]; for(const h of holds){ const l=hm[hm.length-1]; if(l&&l[1]!=null&&h[0]-l[1]<=gap){ l[1]=h[1]; l[2]=true; } else hm.push([h[0],h[1],false]); }
  // evenly spaced jumps of similar size (something flashing or cutting on a beat) collapse into one line
  const jl=[]; for(let i=0;i<jumps.length;){ let k=i+1; const step=k<jumps.length?jumps[k].t-jumps[i].t:0;
    while(k<jumps.length&&Math.abs(jumps[k].t-jumps[k-1].t-step)<=gap&&jumps[k].v<=jumps[i].v*2&&jumps[k].v>=jumps[i].v/2) k++;
    if(k-i>=3) jl.push(`${fmt(jumps[i].t)}–${fmt(jumps[k-1].t)}s every ${fmt((jumps[k-1].t-jumps[i].t)/(k-i-1))}s (${k-i}×, ${jumps[i].v.toFixed(1)})`); else { k=i+1; jl.push(`${fmt(jumps[i].t)}s (${jumps[i].v.toFixed(1)})`); } i=k; }
  console.log(`qa ${file}${total?`  ${fmt(total)}s`:''}\nholds (no visible change for >= 0.4 s): ${hm.length?hm.map(([a,b,f])=>`${fmt(a)}–${b==null?'end':fmt(b)}s${f?' (broken only by single changed frames)':''}`).join(', '):'none'}`+
    `\njumps (one frame changes far more than its neighbours): ${jl.length?jl.join(', '):'none'}`);
  if(loop&&total){ const seam=d.find(f=>Math.abs(f.t-total)<1e-3); // played twice: the frame at t=duration is the first frame again
    console.log(`loop seam: ${!seam?'not found':jumps.includes(seam)?`POPS (${seam.v.toFixed(1)}): the last frame does not lead into the first; make every motion periodic in duration`:'smooth'}  (times past the duration are the second play)`); } }

// music or voice-over: duration, tempo estimate with a beat grid, strongest hits, and where the energy jumps. Energy-based, so an estimate: timings the user gives win
function audio(){ const file=P[1], ff=findFfmpeg(); if(!ff||!ff.full) die(NOFF); if(!file||!fs.existsSync(file)) die('audio needs a file path');
  const r=spawnSync(ff.bin,['-hide_banner','-loglevel','error','-i',file,'-ac','1','-ar','22050','-f','f32le','pipe:1'],{maxBuffer:1<<30}); if(r.status) die('ffmpeg could not decode '+file+'\n'+r.stderr);
  const sr=22050, hop=256, n=Math.floor(r.stdout.length/4), x=new Float32Array(n); for(let i=0;i<n;i++) x[i]=r.stdout.readFloatLE(i*4);
  const fr=hop/sr, nf=Math.floor(n/hop), le=new Float64Array(nf); for(let f=0;f<nf;f++){ let e=0; for(let i=f*hop;i<(f+1)*hop;i++) e+=x[i]*x[i]; le[f]=10*Math.log10(e/hop+1e-10); }
  const floor=Math.min(...le), on=new Float64Array(nf); for(let f=0;f<nf;f++) on[f]=Math.max(0,le[f]-(f?le[f-1]:floor)); // a track that starts on a hit has an onset at 0
  const mean=on.reduce((a,b)=>a+b,0)/nf, sd=Math.sqrt(on.reduce((a,b)=>a+(b-mean)**2,0)/nf), peaks=[];
  for(let f=0;f<nf;f++){ if(on[f]<mean+1.5*sd) continue; let top=true; for(let k=Math.max(-6,-f);k<=6&&f+k<nf;k++) if(on[f+k]>on[f]) top=false; if(top) peaks.push([f*fr,on[f]]); }
  const strong=[]; for(const p of [...peaks].sort((a,b)=>b[1]-a[1])){ if(strong.length>=24) break; if(strong.every(q=>Math.abs(q[0]-p[0])>=.1)) strong.push(p); } strong.sort((a,b)=>a[0]-b[0]);
  const ac=L=>{ let c=0; for(let f=0;f+L<nf;f++) c+=on[f]*on[f+L]; return c/(nf-L); }, prior=L=>Math.exp(-.5*Math.log2(60/(L*fr)/120)**2); // mild prior toward 120 BPM breaks half/double ties
  let best=0, lag=0; for(let L=Math.round(60/180/fr);L<=Math.round(60/60/fr);L++){ const c=ac(L)*prior(L); if(c>best){ best=c; lag=L; } }
  if(lag){ const a=ac(lag-1), b=ac(lag), c=ac(lag+1), d=a-2*b+c; if(d<0) lag+=.5*(a-c)/d; } // parabolic refinement to a fractional lag
  let ph=0, bp=-1; for(let o=0;o<lag;o++){ let c=0; for(let k=0;o+k*lag<nf;k++) c+=on[Math.round(o+k*lag)]; if(c>bp){ bp=c; ph=o; } }
  const sec=Math.floor(n/sr), rms=[], hi=[]; for(let s=0;s<sec;s++){ let e=0, h=0; for(let i=s*sr+1;i<(s+1)*sr;i++){ e+=x[i]*x[i]; h+=(x[i]-x[i-1])**2; } rms.push(10*Math.log10(e/sr+1e-10)); hi.push(10*Math.log10(h/sr+1e-10)); } // loudness, and brightness (high-frequency energy)
  const bucket=Math.max(1,Math.ceil(rms.length/90)), lv=[]; for(let s=0;s<rms.length;s+=bucket) lv.push(Math.round(Math.max(...rms.slice(s,s+bucket))));
  const jumps=[]; for(const [v,what] of [[rms,'louder'],[hi,'brighter']]) for(let s=1;s<v.length;s++){ const w=v.slice(Math.max(0,s-2),s), before=v[s]>w[0]?Math.max(...w):Math.min(...w), d=v[s]-before, after=v[s+1]!==undefined?v[s+1]-before:d;
    if(Math.abs(d)>=3&&Math.sign(after)===Math.sign(d)&&Math.abs(after)>=2&&!jumps.some(j=>Math.abs(j.s-s)<=1&&Math.abs(j.d)>=Math.abs(d))) jumps.push({s,d,what:d>0?what:what==='louder'?'quieter':'darker'}); } // sustained, not one bar
  jumps.sort((a,b)=>Math.abs(b.d)-Math.abs(a.d)); const jtxt=jumps.filter((j,i,a)=>!a.slice(0,i).some(k=>Math.abs(k.s-j.s)<=1)).slice(0,6).sort((a,b)=>a.s-b.s).map(j=>{ // snap to the onset that starts the change
    let bi=-1, bv=0; for(let f=Math.max(0,Math.round((j.s-.7)/fr));f<Math.min(nf,Math.round((j.s+1)/fr));f++) if(on[f]>bv){ bv=on[f]; bi=f; }
    return `${bi>=0?fmt(bi*fr):j.s}s (${j.what} ${j.d>0?'+':''}${j.d.toFixed(0)} dB)`; });
  let bpm=lag?60/(lag*fr):0; if(bpm&&Math.abs(bpm-Math.round(bpm))<.35) bpm=Math.round(bpm); // most music sits on a whole BPM: snapping removes drift over long tracks
  const bt=bpm?60/bpm:0, onGrid=q=>{ const d=((q-ph*fr)%bt+bt)%bt; return Math.min(d,bt-d)<=.12*bt; };
  const first=(peaks.map(p=>p[0]).filter(onGrid).sort((a,b)=>a-b)[0])??ph*fr; // the earliest hit that sits on the grid, not the grid's phase
  if(F.json){ // per-frame curves for audio-reactive motion: M.sample(A.level, t, A.rate). 0..1, normalised to the track's own range
    const rate=num(F.fps,30), nfr=Math.ceil(n/sr*rate), lvl=[], low=[], high=[]; let lp=0;
    const lpc=1-Math.exp(-2*Math.PI*150/sr); // one-pole low-pass at 150 Hz for the bass band
    for(let k=0;k<nfr;k++){ let e=0, eb=0, eh=0; const a=Math.floor(k*sr/rate), b=Math.min(n,Math.floor((k+1)*sr/rate));
      for(let i=a;i<b;i++){ lp+=lpc*(x[i]-lp); e+=x[i]*x[i]; eb+=lp*lp; if(i) eh+=(x[i]-x[i-1])**2; } const m=Math.max(1,b-a); lvl.push(Math.sqrt(e/m)); low.push(Math.sqrt(eb/m)); high.push(Math.sqrt(eh/m)); }
    const norm=v=>{ const s=[...v].sort((p,q)=>p-q), lo=s[Math.floor(s.length*.02)], hi=s[Math.floor(s.length*.98)]||1; return v.map(q=>+clamp((q-lo)/((hi-lo)||1),0,1).toFixed(3)); };
    const beats=[]; if(bt) for(let q=first;q<n/sr-1e-6;q+=bt) beats.push(+q.toFixed(3));
    fs.mkdirSync(path.dirname(path.resolve(F.json)),{recursive:true});
    fs.writeFileSync(F.json,JSON.stringify({file:path.basename(file),duration:+(n/sr).toFixed(3),rate,bpm:+bpm.toFixed(2),beat:+bt.toFixed(4),beats,hits:peaks.map(p=>+p[0].toFixed(3)),level:norm(lvl),low:norm(low),high:norm(high)}));
    console.error(`wrote ${F.json}: level, low (bass), high (brightness) at ${rate} per second, 0..1; beats and hits in seconds`); }
  console.log(`audio ${file}  ${fmt(n/sr)}s\ntempo ≈ ${+bpm.toFixed(1)} BPM (beat every ${bt.toFixed(3)}s, first beat ${fmt(first)}s; half or double may be the felt tempo)`+
    `\nstrongest hits: ${strong.map(p=>fmt(p[0])).join(' ')}\nloudness per ${bucket>1?bucket+' s':'second'} (dB): ${lv.join(' ')}\nenergy jumps (sections start or drop): ${jtxt.join(', ')||'none'}`); }

// one-shot environment check before the first render
async function check(){ let ok=true; console.log('node '+process.version); console.log('playwright '+require.resolve('playwright'));
  try{ const br=await launch(); console.log('browser '+br.version()); await br.close(); }catch(e){ ok=false; console.log('browser FAILED: '+e.message.split('\n')[0]); }
  const ff=findFfmpeg(); console.log(ff?`ffmpeg ${ff.bin} (${ff.full?'full: mp4, gif, webm, mov, qa, audio':'limited: VP8 .webm only'})`:'ffmpeg none'); if(!ff||!ff.full) console.log(NOFF);
  process.exit(ok?0:1); }

const cmds={video,stills,sheet,study,probe,audio,check,qa:()=>qa(P[1])};
if(!cmds[cmd]) die('unknown command '+cmd+' (check | video | stills | sheet | study | probe | qa | audio)');
Promise.resolve(cmds[cmd]()).catch(e=>die(e.stack||e.message));
