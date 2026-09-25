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
