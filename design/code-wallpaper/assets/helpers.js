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
// pointed horizontal sliver: glints, reflection rows, wave caps
const lens=(cx,cy,w,h)=>[[cx-w/2,cy],[cx-w/4,cy-h/2],[cx+w/4,cy-h/2],[cx+w/2,cy],[cx+w/4,cy+h/2],[cx-w/4,cy+h/2]];
// ribbon along a polyline [[x,y,width],...]: cables, rivers, rigging
const strip=P=>{ const L=[],R=[]; P.forEach((p,i)=>{ const a=P[Math.max(0,i-1)], b=P[Math.min(P.length-1,i+1)], d=Math.hypot(b[0]-a[0],b[1]-a[1])||1, nx=-(b[1]-a[1])/d*p[2]/2, ny=(b[0]-a[0])/d*p[2]/2;
  L.push([p[0]+nx,p[1]+ny]); R.unshift([p[0]-nx,p[1]-ny]); }); return L.concat(R); };
// flat-bottomed cloud, w wide and h tall above cy
const cloud=(cx,cy,w,h,ph=0)=>Array.from({length:25},(_,i)=>{ const u=i/12-1; return [cx+u*w/2,cy-h*Math.sqrt(1-u*u)*(1+.25*Math.sin(u*7+ph))]; });
// smooth bump for terrain profiles: 1 at c, falling off over w
const hump=(x,c,w)=>Math.exp(-(((x-c)/w)**2));
// four-point sparkle star
const star4=(x,y,r,q=r*.28)=>Array.from({length:8},(_,k)=>{ const a=k/8*TAU-Math.PI/2, rr=k%2?q:r; return [x+Math.cos(a)*rr,y+Math.sin(a)*rr]; });
// receding structure (bridge, road, fence, pier): t=0 at screen x0 at scale 1, t=1 at x1 where depth is Z times greater.
// x(t) places evenly spaced world points, t(X) inverts it, s(X) is the size scale at screen X, z(t) the depth
const persp=(x0,x1,Z)=>{ const z=t=>1+t*(Z-1), x=t=>x0+(x1-x0)*t*Z/z(t), t=X=>{ const u=(X-x0)/(x1-x0); return u/(Z-u*(Z-1)); }; return {z,x,t,s:X=>1/z(t(X))}; };
// paint over a baked image (IMG, from bake.js): returns one full-canvas region whose strokes take their colour from the image.
// The image covers the canvas at one scale (centred, cropped, never stretched). detail: error (0..255) above which a smaller brush repaints,
// higher is looser; mass: how far a brush's colour is simplified, in units per unit of brush width; angle: stroke direction where the image
// is flat (default: its dominant edge direction); dots: highlight dots
function paintOver(C,{detail=11,mass=.6,angle=null,dots=false}={}){ const {W,H}=C;
  if(typeof IMG==='undefined') throw new Error('paintOver: img.js is missing, run node src/bake.js <image> first');
  const IW=IMG.w, IH=IMG.h, s=Math.max(W/IW,H/IH), ip=1/s, ox=(W-IW*s)/2, oy=(H-IH*s)/2;
  const samp=(a,st,x,y)=>{ const u=C.clamp((x-ox)*ip-.5,0,IW-1.001), v=C.clamp((y-oy)*ip-.5,0,IH-1.001), x0=u|0, y0=v|0, fx=u-x0, fy=v-y0, q=(y0*IW+x0)*st, r=q+IW*st;
    return [0,1,2].map(c=>a[q+c]*(1-fx)*(1-fy)+a[q+st+c]*fx*(1-fy)+a[r+c]*(1-fx)*fy+a[r+st+c]*fx*fy); };
  const img=(x,y)=>samp(IMG.d,3,x,y), lum=c=>.3*c[0]+.59*c[1]+.11*c[2];
  // mass drawing: the image simplified at 4 scales by an edge-preserving (Kuwahara) filter, so a big brush near an edge takes its own side's colour, not a mix
  const S1=IW+1, SA=[0,1,2,3,4].map(()=>new Float64Array(S1*(IH+1)));
  for(let y=0;y<IH;y++) for(let x=0;x<IW;x++){ const i=(y*IW+x)*3, L=.3*IMG.d[i]+.59*IMG.d[i+1]+.11*IMG.d[i+2], v=[IMG.d[i],IMG.d[i+1],IMG.d[i+2],L,L*L], q=(y+1)*S1+x+1;
    for(let c=0;c<5;c++) SA[c][q]=v[c]+SA[c][q-1]+SA[c][q-S1]-SA[c][q-S1-1]; }
  const box=(c,x0,y0,x1,y1)=>SA[c][(y1+1)*S1+x1+1]-SA[c][y0*S1+x1+1]-SA[c][(y1+1)*S1+x0]+SA[c][y0*S1+x0];
  const kuw=R=>{ const out=new Uint8ClampedArray(IW*IH*4);
    for(let y=0;y<IH;y++) for(let x=0;x<IW;x++){ let best=1e18, m;
      for(const [ax,ay] of [[-1,-1],[1,-1],[-1,1],[1,1]]){ const x0=Math.max(0,Math.min(x,x+ax*R)), x1=Math.min(IW-1,Math.max(x,x+ax*R)), y0=Math.max(0,Math.min(y,y+ay*R)), y1=Math.min(IH-1,Math.max(y,y+ay*R)), n=(x1-x0+1)*(y1-y0+1);
        const mu=box(3,x0,y0,x1,y1)/n, va=box(4,x0,y0,x1,y1)/n-mu*mu; if(va<best){ best=va; m=[0,1,2].map(c=>box(c,x0,y0,x1,y1)/n); } }
      const o=(y*IW+x)*4; out[o]=m[0]; out[o+1]=m[1]; out[o+2]=m[2]; out[o+3]=255; } return out; };
  const SG=[.75,1.5,3,6], LV=SG.map(su=>kuw(Math.max(1,Math.round(su*ip*1.3)))); // no blur after: at the coarse levels it would put a grey rim back around every edge
  const cfs=(x,y,w)=>{ const su=w*mass; return su<.5?img(x,y):samp(LV[C.clamp(Math.round(Math.log2(su/.75)),0,SG.length-1)],4,x,y); };
  // strokes follow the image's edges: structure-tensor orientation on a 1-unit grid, easing to the fallback angle where the image is flat
  const GW=Math.ceil(W), GH=H, Lm=new Float32Array(GW*GH), at=(a,x,y)=>a[C.clamp(y,0,GH-1)*GW+C.clamp(x,0,GW-1)];
  for(let y=0;y<GH;y++) for(let x=0;x<GW;x++) Lm[y*GW+x]=lum(img(x+.5,y+.5));
  const J=[0,1,2].map(()=>new Float32Array(GW*GH)), G=new Float32Array(GW*GH);
  for(let y=0;y<GH;y++) for(let x=0;x<GW;x++){ const gx=at(Lm,x+1,y)-at(Lm,x-1,y), gy=at(Lm,x,y+1)-at(Lm,x,y-1), q=y*GW+x; J[0][q]=gx*gx; J[1][q]=gx*gy; J[2][q]=gy*gy; G[q]=Math.hypot(gx,gy); }
  const sum=a=>a.reduce((p,v)=>p+v,0), a0=angle??.5*Math.atan2(2*sum(J[1]),sum(J[0])-sum(J[2]))+Math.PI/2, gn=a0+Math.PI/2, eps=40;
  J[0].forEach((v,q)=>{ J[0][q]+=eps*Math.cos(gn)**2; J[1][q]+=eps*Math.cos(gn)*Math.sin(gn); J[2][q]+=eps*Math.sin(gn)**2; });
  const blur=(a,R)=>{ const t=new Float32Array(a.length); for(let y=0;y<GH;y++) for(let x=0;x<GW;x++){ let v=0; for(let d=-R;d<=R;d++) v+=at(a,x+d,y); t[y*GW+x]=v; }
    for(let y=0;y<GH;y++) for(let x=0;x<GW;x++){ let v=0; for(let d=-R;d<=R;d++) v+=at(t,x,y+d); a[y*GW+x]=v/(2*R+1)**2; } };
  J.forEach(a=>blur(a,3)); const AN=J[0].map((_,q)=>.5*Math.atan2(2*J[1][q],J[0][q]-J[2][q])+Math.PI/2);
  // openness follows the image's own edge energy, blurred wide: slabs where it is flat, smaller brushes where it is busy, and no line where they meet
  blur(G,8); const g0=[...G].sort((a,b)=>a-b)[Math.floor(G.length*.75)]||1, e=(x,y)=>1-Math.exp(-at(G,Math.floor(x),Math.floor(y))/g0);
  return [{pts:rect(0,0,W,H),cf:img,cfs,dir:'fn',af:(x,y)=>at(AN,Math.floor(x),Math.floor(y)),bsf:(x,y)=>C.clamp(1-.75*e(x,y)),T:detail,
    hl:dots?(x,y)=>lum(img(x,y))-lum(samp(LV[1],4,x,y))>28:null}]; }
