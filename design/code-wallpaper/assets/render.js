// usage: node render.js <scene_index> <width> <height> <out.png|out.jpg> [seed] [crop] [--tseed=N] [--crop-out=path]
// a .jpg name writes JPEG at quality .92; crop "x,y,w,h" (logical units) also writes a full-resolution crop to --crop-out
// (default: the system temp dir, so crops never land next to the finished file); --seed= and --crop= work as flags too
const {chromium}=require('playwright'), fs=require('fs'), os=require('os'), path=require('path'), {pathToFileURL}=require('url');
const args=process.argv.slice(2), F=Object.fromEntries(args.filter(a=>a.startsWith('--')).map(a=>a.slice(2).split(/=(.*)/))), P=args.filter(a=>!a.startsWith('--'));
const [i='0',w='3840',h='2160',out='wallpaper.png']=P, seed=F.seed||P[4]||'', crop=F.crop||P[5]||'', tseed=F.tseed||'';
const cropOut=F['crop-out']||path.join(os.tmpdir(),path.basename(out).replace(/\.\w+$/,'')+'-crop.png');
const save=(f,u)=>fs.writeFileSync(f,Buffer.from(u.split(',')[1],'base64'));
(async()=>{ const br=await chromium.launch().catch(()=>{ console.error('bundled Chromium unavailable, using installed Chrome'); return chromium.launch({channel:'chrome'}); });
  const p=await br.newPage();
  let err=null; p.on('pageerror',e=>{ err=e.message; console.error('PAGE ERROR:',e.message); });
  // the engine paints synchronously during page load, so the navigation timeout must cover the whole render
  await p.goto(`${pathToFileURL(path.join(__dirname,'engine.html'))}?s=${i}&w=${w}&h=${h}${seed?'&seed='+seed:''}${tseed?'&tseed='+tseed:''}`,{timeout:600000});
  const n=await p.evaluate('window.DONE'); if(err||!n){ await br.close(); process.exit(1); }
  save(out,await p.evaluate(j=>document.getElementById('cv').toDataURL(j?'image/jpeg':'image/png',.92),/\.jpe?g$/i.test(out)));
  if(crop){ save(cropOut,await p.evaluate(c=>{ const cv=document.getElementById('cv'), k=cv.height/400, [cx,cy,cw,ch]=c.split(',').map(v=>Math.round(+v*k));
    const o=document.createElement('canvas'); o.width=cw; o.height=ch; o.getContext('2d').drawImage(cv,cx,cy,cw,ch,0,0,cw,ch); return o.toDataURL('image/png'); },crop)); console.log('crop',cropOut); }
  console.log('wrote',out,w+'x'+h,'strokes',n); await br.close(); })();
