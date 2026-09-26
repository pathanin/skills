// motion.js: deterministic motion toolkit. Every function is a pure function of its arguments, so a frame depends only on t.
// Exposes one global, M. In scene.js, destructure what you use: const {kf,seg,ease,tf}=M;
(function(){
const M={}, PI=Math.PI;
M.TAU=PI*2;
M.clamp=(v,a=0,b=1)=>v<a?a:v>b?b:v;
M.lerp=(a,b,u)=>a+(b-a)*u;
M.invLerp=(a,b,v)=>a===b?0:(v-a)/(b-a);
M.remap=(v,a,b,c,d,e)=>{ const u=M.clamp(M.invLerp(a,b,v)); return M.lerp(c,d,e?e(u):u); };
M.smoothstep=(a,b,v)=>{ const u=M.clamp(M.invLerp(a,b,v)); return u*u*(3-2*u); };
M.deg=r=>r*180/PI; M.rad=d=>d*PI/180;

// ---- easing: u in [0,1] -> [0,1] (back/elastic/spring overshoot) ----
const E={linear:u=>u};
const trio=(name,fin)=>{ E['in'+name]=fin; E['out'+name]=u=>1-fin(1-u); E['inOut'+name]=u=>u<.5?fin(2*u)/2:1-fin(2-2*u)/2; };
trio('Quad',u=>u*u); trio('Cubic',u=>u**3); trio('Quart',u=>u**4); trio('Quint',u=>u**5);
trio('Sine',u=>1-Math.cos(u*PI/2)); trio('Expo',u=>u<=0?0:2**(10*u-10)); trio('Circ',u=>1-Math.sqrt(1-u*u));
E.back=(s=1.70158)=>{ const o={}; const fin=u=>(s+1)*u**3-s*u*u; o.in=fin; o.out=u=>1-fin(1-u); o.inOut=u=>u<.5?fin(2*u)/2:1-fin(2-2*u)/2; return o; };
{ const b=E.back(); E.inBack=b.in; E.outBack=b.out; E.inOutBack=b.inOut; }
E.elastic=(amp=1,period=.3)=>{ const s=period/(2*PI)*Math.asin(1/Math.max(1,amp)), a=Math.max(1,amp);
  const out=u=>u<=0?0:u>=1?1:a*2**(-10*u)*Math.sin((u-s)*2*PI/period)+1; return {out, in:u=>1-out(1-u), inOut:u=>u<.5?(1-out(1-2*u))/2:(1+out(2*u-1))/2}; };
{ const e=E.elastic(); E.inElastic=e.in; E.outElastic=e.out; E.inOutElastic=e.inOut; }
E.outBounce=u=>{ const n=7.5625, d=2.75; if(u<1/d) return n*u*u; if(u<2/d) return n*(u-=1.5/d)*u+.75; if(u<2.5/d) return n*(u-=2.25/d)*u+.9375; return n*(u-=2.625/d)*u+.984375; };
E.inBounce=u=>1-E.outBounce(1-u); E.inOutBounce=u=>u<.5?(1-E.outBounce(1-2*u))/2:(1+E.outBounce(2*u-1))/2;
// CSS-style cubic-bezier(x1,y1,x2,y2)
E.bezier=(x1,y1,x2,y2)=>{ const bx=(t,a,b)=>3*a*t*(1-t)**2+3*b*t*t*(1-t)+t**3, dx=t=>3*x1*(1-t)**2+6*(x2-x1)*t*(1-t)+3*(1-x2)*t*t;
  return u=>{ if(u<=0) return 0; if(u>=1) return 1; let t=u; for(let i=0;i<8;i++){ const d=dx(t); if(Math.abs(d)<1e-6) break; t-=(bx(t,x1,x2)-u)/d; }
    if(!(t>=0&&t<=1)||Math.abs(bx(t,x1,x2)-u)>1e-5){ let a=0,b=1; for(let i=0;i<40;i++){ t=(a+b)/2; bx(t,x1,x2)<u?a=t:b=t; } } return bx(t,y1,y2); }; };
E.css=E.bezier(.25,.1,.25,1); E.material=E.bezier(.2,0,0,1); E.snappy=E.bezier(.16,1,.3,1); E.anticipate=E.bezier(.36,-.35,.6,1);
E.steps=(n)=>u=>u>=1?1:Math.floor(u*n)/n;
// spring as an ease: damping ratio z (0.2 wobbly .. 1 no overshoot), settles by u=1
E.spring=(z=.45)=>{ const f=u=>springAt(u,6.9/Math.max(z,.08),z), end=f(1); return u=>u<=0?0:u>=1?1:f(u)+(1-end)*u; };
M.ease=E;

// ---- time windows ----
// progress of t through [t0,t1], clamped, then eased
M.seg=(t,t0,t1,e=E.linear)=>e(M.clamp(M.invLerp(t0,t1,t)));
// element i of a staggered group: starts at start+i*each, lasts dur
M.stagger=(t,i,start,each,dur,e=E.linear)=>M.seg(t,start+i*each,start+i*each+dur,e);
// which shot is active: durs = [2,3.5,1.5] -> {i, t: local time, u: 0..1 within the shot, start, dur}
M.shots=(t,durs)=>{ let s=0; for(let i=0;i<durs.length;i++){ if(t<s+durs[i]||i===durs.length-1) return {i,t:t-s,u:M.clamp((t-s)/durs[i]),start:s,dur:durs[i]}; s+=durs[i]; } };
// hand-drawn "on twos": hold each drawing for 1/fps s (12 = twos at 24fps, 8 = threes)
M.quantize=(t,fps=12)=>Math.floor(t*fps+1e-9)/fps;
M.loop=(t,period)=>((t%period)+period)%period;
M.pingpong=(t,period)=>{ const u=M.loop(t,2*period); return u<period?u:2*period-u; };

// ---- interpolation of any value: number, array, object, '#hex' colour (mixed in OKLab), or a string of numbers with the same shape ----
const hexRe=/^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i;
const parseHex=h=>{ h=h.slice(1); if(h.length<5) h=[...h].map(c=>c+c).join(''); const n=[0,2,4,6].map(i=>i<h.length?parseInt(h.slice(i,i+2),16):255); return [n[0],n[1],n[2],n[3]/255]; };
const toHex=([r,g,b,a=1])=>'#'+[r,g,b].map(v=>Math.round(M.clamp(v,0,255)).toString(16).padStart(2,'0')).join('')+(a<1?Math.round(M.clamp(a)*255).toString(16).padStart(2,'0'):'');
const lin=c=>(c/=255)<=.04045?c/12.92:((c+.055)/1.055)**2.4, gam=c=>255*(c<=.0031308?12.92*c:1.055*c**(1/2.4)-.055);
const toLab=([r,g,b])=>{ [r,g,b]=[lin(r),lin(g),lin(b)]; const l=Math.cbrt(.4122214708*r+.5363325363*g+.0514459929*b), m=Math.cbrt(.2119034982*r+.6806995451*g+.1073969566*b), s=Math.cbrt(.0883024619*r+.2817188376*g+.6299787005*b);
  return [.2104542553*l+.793617785*m-.0040720468*s, 1.9779984951*l-2.428592205*m+.4505937099*s, .0259040371*l+.7827717662*m-.808675766*s]; };
const fromLab=([L,a,b])=>{ const l=(L+.3963377774*a+.2158037573*b)**3, m=(L-.1055613458*a-.0638541728*b)**3, s=(L-.0894841775*a-1.291485548*b)**3;
  return [gam(4.0767416621*l-3.3077115913*m+.2309699292*s), gam(-1.2684380046*l+2.6097574011*m-.3413193965*s), gam(-.0041960863*l-.7034186147*m+1.707614701*s)]; };
M.color=(a,b,u)=>{ const A=parseHex(a), B=parseHex(b), la=toLab(A), lb=toLab(B); return toHex([...fromLab(la.map((v,i)=>M.lerp(v,lb[i],u))), M.lerp(A[3],B[3],u)]); };
M.rgb=h=>parseHex(h).slice(0,3); M.hex=toHex;
const numRe=/-?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/gi;
M.mix=(a,b,u)=>{
  if(typeof a==='number') return a+(b-a)*u;
  if(Array.isArray(a)) return a.map((v,i)=>M.mix(v,b[i],u));
  if(typeof a==='string'){ if(hexRe.test(a)&&hexRe.test(b)) return M.color(a,b,u);
    const na=a.match(numRe)||[], nb=b.match(numRe)||[], sa=a.split(numRe), sb=b.split(numRe);
    if(na.length===nb.length&&sa.join('\u0000')===sb.join('\u0000')) return sa.map((s,i)=>i<na.length?s+(+(+na[i]+(nb[i]-na[i])*u).toFixed(4)):s).join('');
    return u<.5?a:b; }
  if(a&&typeof a==='object'){ const o={}; for(const k in a) o[k]=k in b?M.mix(a[k],b[k],u):a[k]; return o; }
  return u<.5?a:b; };

// keyframes: keys = [[time, value, ease?], ...] sorted by time. A key's ease shapes the segment that ARRIVES at it (default inOutCubic).
// inOut eases stop at every key: that is pose-to-pose with a settle. To pass through a key without stopping use M.spline.
M.kf=(t,keys,def=E.inOutCubic)=>{ if(t<=keys[0][0]) return keys[0][1]; const n=keys.length; if(t>=keys[n-1][0]) return keys[n-1][1];
  let i=1; while(keys[i][0]<t) i++; const [t0,v0]=keys[i-1], [t1,v1,e=def]=keys[i]; return M.mix(v0,v1,e(M.invLerp(t0,t1,t))); };
// smooth curve THROUGH keys (cubic Hermite, Catmull-Rom tangents scaled for uneven key times); numbers or arrays. Ends ease in and out.
M.spline=(t,keys)=>{ const n=keys.length; if(t<=keys[0][0]) return keys[0][1]; if(t>=keys[n-1][0]) return keys[n-1][1];
  let i=1; while(keys[i][0]<t) i++; const [t0,p0]=keys[i-1], [t1,p1]=keys[i], h=t1-t0, u=(t-t0)/h;
  const tan=j=>{ if(j<=0||j>=n-1) return null; const [ta,pa]=keys[j-1], [tb,pb]=keys[j+1]; return Array.isArray(pb)?pb.map((v,k)=>(v-pa[k])/(tb-ta)):(pb-pa)/(tb-ta); };
  const m0=tan(i-1), m1=tan(i), h00=2*u**3-3*u*u+1, h10=u**3-2*u*u+u, h01=-2*u**3+3*u*u, h11=u**3-u*u;
  const f=(a,b,ma,mb)=>h00*a+h10*h*(ma||0)+h01*b+h11*h*(mb||0);
  return Array.isArray(p0)?p0.map((v,k)=>f(v,p1[k],m0&&m0[k],m1&&m1[k])):f(p0,p1,m0,m1); };

// ---- physics without state (closed form, so any t can be sought directly) ----
function springAt(t,w,z){ if(t<=0) return 0; if(z<1){ const wd=w*Math.sqrt(1-z*z); return 1-Math.exp(-z*w*t)*(Math.cos(wd*t)+z*w/wd*Math.sin(wd*t)); }
  if(z===1) return 1-Math.exp(-w*t)*(1+w*t); const r=Math.sqrt(z*z-1), r1=-w*(z-r), r2=-w*(z+r); return 1+(r2*Math.exp(r1*t)-r1*Math.exp(r2*t))/(r1-r2); }
// damped spring response 0 -> 1 at time t (s) after release. freq in Hz, z damping ratio (0.3 bouncy, 0.7 firm, 1 no overshoot)
M.spring=(t,freq=2,z=.4)=>springAt(t,2*PI*freq,z);
// point on a thrown arc: from p0 to p1 with apex height h above the higher end, u in [0,1] (u should be linear in time: gravity is in the shape)
M.arc=(u,[x0,y0],[x1,y1],h)=>{ const top=Math.min(y0,y1)-h, a=Math.sqrt(Math.max(0,y0-top)), b=Math.sqrt(Math.max(0,y1-top)), s=a/(a+b||1);
  const y=u<s?top+(y0-top)*((s-u)/s)**2:top+(y1-top)*((u-s)/(1-s||1))**2; return [M.lerp(x0,x1,u),y]; };
// squash and stretch that keeps area: k>1 stretches along the axis, returns [along, across]
M.squash=k=>[k,1/k];

// ---- deterministic randomness ----
M.hash=(n,seed=0)=>{ let h=Math.imul((n|0)^0x9e3779b9,0x85ebca6b)^Math.imul(seed|0,0xc2b2ae35); h^=h>>>16; h=Math.imul(h,0x7feb352d); h^=h>>>15; h=Math.imul(h,0x846ca68b); h^=h>>>16; return (h>>>0)/4294967296; };
M.rng=(seed=1)=>{ let s=seed>>>0; const r=()=>{ s=(s+0x6d2b79f5)>>>0; let q=Math.imul(s^s>>>15,1|s); q=q+Math.imul(q^q>>>7,61|q)^q; return ((q^q>>>14)>>>0)/4294967296; };
  r.range=(a,b)=>a+r()*(b-a); r.int=(a,b)=>Math.floor(a+r()*(b-a+1)); r.pick=arr=>arr[Math.floor(r()*arr.length)]; return r; };
// smooth 1D value noise in [-1,1]
M.noise=(x,seed=0)=>{ const i=Math.floor(x), f=x-i, u=f*f*(3-2*f); return M.lerp(M.hash(i,seed),M.hash(i+1,seed),u)*2-1; };
// organic drift: amp * noise at freq Hz, two octaves. Use for idle sway, camera handheld, flicker
M.wiggle=(t,freq=1,amp=1,seed=0)=>amp*(M.noise(t*freq,seed)*.7+M.noise(t*freq*2.3+17.1,seed+1)*.3);

// ---- DOM / SVG ----
const SVGNS='http://www.w3.org/2000/svg';
const setA=(el,a)=>{ for(const k in a){ const v=a[k]; if(v==null) el.removeAttribute(k); else if(k==='text') el.textContent=v; else el.setAttribute(k,v); } return el; };
M.set=setA;
M.svg=(tag,attrs={},parent)=>{ const el=setA(document.createElementNS(SVGNS,tag),attrs); if(parent) parent.appendChild(el); return el; };
M.html=(tag,attrs={},parent)=>{ const el=setA(document.createElement(tag),attrs); if(parent) parent.appendChild(el); return el; };
const f4=v=>+(+v).toFixed(4);
// transform with a pivot: the local point (ox,oy) moves to (x+ox, y+oy), and rotation r (deg), scale s / sx,sy and skew skx happen around it.
// sa rotates the scale axis, so squash and stretch can point along the motion: tf(el,{sx:1.3,sy:1/1.3,sa:angleOfVelocity})
M.tf=(el,{x=0,y=0,r=0,s=1,sx=1,sy=1,sa=0,skx=0,ox=0,oy=0,o}={})=>{ const X=sx*s, Y=sy*s, svgEl=el instanceof SVGElement;
  if(svgEl){ let str=`translate(${f4(x+ox)} ${f4(y+oy)})`; if(r) str+=` rotate(${f4(r)})`; if(X!==1||Y!==1) str+=sa?` rotate(${f4(sa)}) scale(${f4(X)} ${f4(Y)}) rotate(${f4(-sa)})`:` scale(${f4(X)} ${f4(Y)})`;
    if(skx) str+=` skewX(${f4(skx)})`; if(ox||oy) str+=` translate(${f4(-ox)} ${f4(-oy)})`; el.setAttribute('transform',str); }
  else { let str=`translate(${f4(x+ox)}px,${f4(y+oy)}px)`; if(r) str+=` rotate(${f4(r)}deg)`; if(X!==1||Y!==1) str+=sa?` rotate(${f4(sa)}deg) scale(${f4(X)},${f4(Y)}) rotate(${f4(-sa)}deg)`:` scale(${f4(X)},${f4(Y)})`;
    if(skx) str+=` skewX(${f4(skx)}deg)`; if(ox||oy) str+=` translate(${f4(-ox)}px,${f4(-oy)}px)`; el.style.transformOrigin='0 0'; el.style.transform=str; }
  if(o!==undefined) el.style.opacity=f4(M.clamp(o)); return el; };
// trim a stroked path like After Effects' Trim Paths: show only the part between start and end (0..1 of its length)
M.trim=(el,start,end)=>{ if(!el.hasAttribute('pathLength')) el.setAttribute('pathLength',1000); const a=M.clamp(Math.min(start,end))*1000, b=M.clamp(Math.max(start,end))*1000;
  el.style.strokeDasharray=`${f4(b-a)} 2000`; el.style.strokeDashoffset=f4(-a); el.style.visibility=b-a<.01?'hidden':''; return el; };
// point and tangent angle (deg) at u (0..1) along an SVG path, in the path's own coordinates
M.along=(path,u)=>{ const L=path.getTotalLength(), d=M.clamp(u)*L, p=path.getPointAtLength(d), q=path.getPointAtLength(Math.min(L,d+.5)), p0=path.getPointAtLength(Math.max(0,d-.5));
  return {x:p.x, y:p.y, a:M.deg(Math.atan2(q.y-p0.y,q.x-p0.x))}; };
// map point (x,y) in el's local coordinates into target's coordinates (default: the root <svg>). Attach props to hands, emit particles from a mouth.
M.pointIn=(el,x,y,target)=>{ const svg=el.ownerSVGElement||el, tgt=target||svg, m=(tgt.getCTM()||svg.getCTM()).inverse().multiply(el.getCTM());
  const p=new DOMPoint(x,y).matrixTransform(m); return [p.x,p.y]; };
// two-bone IK: root (ax,ay), target (tx,ty), bone lengths l1,l2, bend +1 / -1 picks the elbow side.
// Returns a1 = absolute angle of bone 1, a2 = angle of bone 2 relative to bone 1 (deg, 0 = +x axis), and the joint position.
// Subtract the angle each bone was DRAWN at (e.g. 90 for a limb drawn pointing down) before passing to tf.
M.ik2=(ax,ay,tx,ty,l1,l2,bend=1)=>{ const dx=tx-ax, dy=ty-ay, d=Math.max(1e-9,M.clamp(Math.hypot(dx,dy),Math.abs(l1-l2),l1+l2)), base=Math.atan2(dy,dx);
  const A=Math.acos(M.clamp((l1*l1+d*d-l2*l2)/(2*l1*d),-1,1)), a1=base-bend*A, jx=ax+l1*Math.cos(a1), jy=ay+l1*Math.sin(a1);
  const ex=ax+d*Math.cos(base), ey=ay+d*Math.sin(base), a2=Math.atan2(ey-jy,ex-jx)-a1; return {a1:M.deg(a1), a2:M.deg(Math.atan2(Math.sin(a2),Math.cos(a2))), jx, jy, ex, ey}; };
// split an HTML element's text into inline-block spans for per-letter or per-word animation. Returns the spans in reading order.
// Child elements (<br>, <b>, <em>, coloured <span>s) are kept; in 'chars' mode each word is an unbreakable wrapper, so lines never break mid-word.
M.split=(el,by='chars')=>{ const out=[], ib='display:inline-block;white-space:pre';
  const walk=node=>{ for(const ch of [...node.childNodes]){
    if(ch.nodeType===1){ if(ch.tagName!=='BR') walk(ch); continue; } if(ch.nodeType!==3) continue;
    const frag=document.createDocumentFragment();
    for(const w of ch.textContent.split(/(\s+)/)){ if(!w) continue; if(/^\s+$/.test(w)){ frag.appendChild(document.createTextNode(w)); continue; }
      if(by==='words'){ const s=M.html('span',{style:ib},frag); s.textContent=w; out.push(s); continue; }
      const word=M.html('span',{style:'display:inline-block;white-space:nowrap'},frag); for(const c of w){ const s=M.html('span',{style:ib},word); s.textContent=c; out.push(s); } }
    ch.replaceWith(frag); } };
  walk(el); return out; };

window.M=M;
})();
