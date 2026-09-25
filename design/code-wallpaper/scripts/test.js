// End-to-end check of the shipped assets: copies engine.html, render.js and helpers.js into a temp dir with a test scene,
// renders through Playwright and the CLI, and asserts the behaviours SKILL.md promises.
// usage: NODE_PATH=<dir containing playwright> node scripts/test.js
const {chromium}=require('playwright'), fs=require('fs'), os=require('os'), path=require('path'), crypto=require('crypto'), {execFileSync}=require('child_process'), {pathToFileURL}=require('url');
const ASSETS=path.join(__dirname,'..','assets'), T=fs.mkdtempSync(path.join(os.tmpdir(),'cw-test-'));
for(const f of ['engine.html','render.js','helpers.js']) fs.copyFileSync(path.join(ASSETS,f),path.join(T,f));
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
];`);

let fails=0; const ok=(name,cond,detail='')=>{ console.log((cond?'PASS ':'FAIL ')+name+(detail?'  ('+detail+')':'')); if(!cond) fails++; };
const hash=s=>crypto.createHash('sha1').update(s).digest('hex').slice(0,12);
const render=async(br,q)=>{ const p=await br.newPage(); let err=null; p.on('pageerror',e=>err=e.message);
  await p.goto(pathToFileURL(path.join(T,'engine.html'))+'?'+q,{timeout:600000});
  const r=await p.evaluate(()=>({done:window.DONE, build:window.BUILD, url:document.getElementById('cv').toDataURL()}));
  r.err=err; r.hash=hash(r.url||''); r.page=p; return r; };
const cli=(args,env={})=>{ try{ return {out:execFileSync('node',[path.join(T,'render.js'),...args],{cwd:T,env:{...process.env,...env},stdio:['ignore','pipe','pipe']}).toString(),code:0}; }
  catch(e){ return {out:String(e.stdout)+String(e.stderr),code:e.status}; } };

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
  const hl=await render(br,'s=2&w=711&h=400');
  ok('helpers.js is loaded before scene.js',!hl.err&&hl.done>0,hl.err||'');
  const nan=await render(br,'s=3&w=711&h=400');
  ok('a non-finite point is reported, not silently dropped',/non-finite/.test(nan.err||''),nan.err||'no error');
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
