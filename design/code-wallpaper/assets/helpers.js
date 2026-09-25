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
