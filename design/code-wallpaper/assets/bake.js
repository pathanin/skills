// bakes an image into img.js as IMG={w,h,d:Uint8Array RGB}, so a paint-over scene can sample it synchronously
// usage: node src/bake.js <image> [--max=1600] [--bg=#ffffff]   writes img.js next to this script
// the long side is capped at --max px (the painting never needs more, and it keeps img.js and the filters small); transparency composites over --bg
const {chromium}=require('playwright'), fs=require('fs'), path=require('path');
const args=process.argv.slice(2), F=Object.fromEntries(args.filter(a=>a.startsWith('--')).map(a=>a.slice(2).split(/=(.*)/))), [src]=args.filter(a=>!a.startsWith('--'));
const max=+(F.max||1600), bg=F.bg||'#ffffff';
if(!src||!fs.existsSync(src)){ console.error('image not found:',src||'(none given)'); process.exit(1); }
const mime={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.gif':'image/gif','.bmp':'image/bmp','.avif':'image/avif'}[path.extname(src).toLowerCase()]||'image/png';
(async()=>{ const br=await chromium.launch().catch(()=>chromium.launch({channel:'chrome'})), p=await br.newPage();
  const r=await p.evaluate(async([u,max,bg])=>{ const im=new Image(); im.src=u; await im.decode();
    const s=Math.min(1,max/Math.max(im.width,im.height)), w=Math.round(im.width*s), h=Math.round(im.height*s), c=document.createElement('canvas'); c.width=w; c.height=h;
    const g=c.getContext('2d'); g.imageSmoothingQuality='high'; g.fillStyle=bg; g.fillRect(0,0,w,h); g.drawImage(im,0,0,w,h);
    const a=g.getImageData(0,0,w,h).data, o=new Uint8Array(w*h*3); for(let i=0,j=0;i<a.length;i+=4){ o[j++]=a[i]; o[j++]=a[i+1]; o[j++]=a[i+2]; }
    let b=''; for(let i=0;i<o.length;i+=32768) b+=String.fromCharCode(...o.subarray(i,i+32768)); return {w,h,b:btoa(b)};
  },['data:'+mime+';base64,'+fs.readFileSync(src).toString('base64'),max,bg]).catch(e=>({err:e.message}));
  await br.close(); if(r.err){ console.error('cannot decode image:',src,r.err); process.exit(1); }
  const out=path.join(__dirname,'img.js'); fs.writeFileSync(out,`const IMG={w:${r.w},h:${r.h},d:Uint8Array.from(atob("${r.b}"),c=>c.charCodeAt(0))};\n`);
  console.log('baked',src,r.w+'x'+r.h,'->',out); })();
