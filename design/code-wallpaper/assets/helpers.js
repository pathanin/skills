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
