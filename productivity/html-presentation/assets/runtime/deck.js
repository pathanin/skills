(function(){
  const slides=[...document.querySelectorAll('.slide')], stage=document.querySelector('.stage'), hud=document.getElementById('hud');
  const qs=new URLSearchParams(location.search);
  let i=Math.max(0,Math.min(slides.length-1,(parseInt(location.hash.slice(1))||1)-1));
  function fit(){ if(document.body.classList.contains('shot')||document.body.classList.contains('flat'))return;
    const s=Math.min(innerWidth/1280,innerHeight/720); stage.style.transform=`scale(${s}) translate(-50%,-50%)`;
    stage.style.transformOrigin='0 0'; stage.style.left='50%'; stage.style.top='50%'; }
  // entrance animation: elements rise in reading order (top to bottom, then left to right), < 1 s in total
  const still=qs.has('shot')||qs.has('flat')||qs.has('qa')||matchMedia('(prefers-reduced-motion: reduce)').matches;
  function animate(sl){ if(still)return;
    if(!sl.dataset.prepped){ sl.dataset.prepped=1;
      [...sl.children].forEach(el=>{ if(!el.dataset.name||el.matches('.rv-pin,.rv-pop,.tbl'))return;   // tables animate per row
        const L=parseFloat(el.style.left)||0,T=parseFloat(el.style.top)||0,W=parseFloat(el.style.width)||0,H=parseFloat(el.style.height)||0;
        if(W>=1200&&H>=650)return;                                   // slide background
        const panel=el.matches('.pic')||(W*H>60000&&!el.textContent.trim());   // screenshots and panels: fade + settle, no rise
        el.classList.add('a',panel?'a-panel':'a-rise');
        el.style.setProperty('--d',Math.round(Math.min(650,Math.max(0,T-50)*0.85+L*0.08))+'ms');
        });
      sl.querySelectorAll('.tbl tr').forEach((tr,k)=>{tr.classList.add('a','a-row');tr.style.setProperty('--d',(320+k*55)+'ms');}); }
    sl.classList.remove('anim'); void sl.offsetWidth; sl.classList.add('anim'); }
  function stopVideos(sl){ sl.querySelectorAll('video').forEach(v=>{v.pause();try{v.currentTime=0;}catch(e){}v.closest('.vid').classList.remove('playing');}); }
  function show(n){ n=Math.max(0,Math.min(slides.length-1,n)); if(slides[i])stopVideos(slides[i]);
    slides.forEach((s,k)=>s.classList.toggle('on',k===n)); i=n; hud.textContent=(n+1)+' / '+slides.length;
    animate(slides[n]);
    if(!document.body.classList.contains('shot')) slides[n].querySelectorAll('.pic.vid').forEach(box=>{   // clips start on entering the slide and loop
      const v=box.querySelector('video'); v.muted=true; v.loop=true; box.classList.add('playing'); v.play().catch(()=>box.classList.remove('playing')); });
    if(location.hash!=='#'+(n+1))history.replaceState(null,'','#'+(n+1)); }
  document.addEventListener('keydown',e=>{
    if(['ArrowRight','PageDown',' '].includes(e.key)){show(i+1);e.preventDefault();}
    else if(['ArrowLeft','PageUp','Backspace'].includes(e.key)){show(i-1);e.preventDefault();}
    else if(e.key==='Home')show(0); else if(e.key==='End')show(slides.length-1);
    else if(e.code==='KeyF'||e.key==='f'||e.key==='ด'||e.key==='Enter'){ e.preventDefault();   // F key on either layout (f / ด) or Enter: toggle fullscreen
      if(document.fullscreenElement)document.exitFullscreen(); else if(document.documentElement.requestFullscreen)document.documentElement.requestFullscreen(); } });
  document.querySelectorAll('.pic.vid').forEach(box=>{ const v=box.querySelector('video');
    box.addEventListener('click',e=>{e.stopPropagation(); if(v.paused){box.classList.add('playing');v.play();} else v.pause();});
    v.addEventListener('ended',()=>{box.classList.remove('playing');v.load();}); });
  addEventListener('hashchange',()=>show((parseInt(location.hash.slice(1))||1)-1));
  addEventListener('resize',fit);
  if(qs.has('shot')){document.body.classList.add('shot');}
  if(qs.has('flat')||qs.has('qa')){document.body.classList.add('flat');slides.forEach(s=>s.classList.add('on'));}
  fit(); if(!qs.has('flat')&&!qs.has('qa'))show(i);
  if(qs.has('qa')){ document.fonts.ready.then(()=>{ const out=[];
    out.push('font400 '+document.fonts.check('16px "DeckFont"')+' font700 '+document.fonts.check('bold 16px "DeckFont"'));
    slides.forEach((s,k)=>{ s.querySelectorAll('.tx').forEach(t=>{
        const host=t.parentElement; const over=t.scrollHeight-t.clientHeight, wover=t.scrollWidth-t.clientWidth;
        if(over>1||wover>1) out.push(`s${k+1} [${host.dataset.name}] over h${over} w${wover}: `+t.textContent.slice(0,50)); });
      s.querySelectorAll('.cell').forEach(c=>{ const td=c.parentElement; if(td.scrollHeight>td.clientHeight+1) out.push(`s${k+1} table cell taller than row: `+c.textContent.slice(0,40)); }); });
    const pre=document.getElementById('qa'); pre.textContent=out.join('\n'); pre.dataset.done='1'; }); }
})();
