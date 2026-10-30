// Small shared play: a ring that follows the cursor and swells over anything pressable, and labels whose letters
// scramble for a moment when you point at them. Off for touch (the ring) and reduced motion (both).
const CALM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const GLYPHS='アイウエオカキクケコ01#%&*+=/<>ABCDEFXYZ';
function scramble(el,text){                              // global: pages call it for their own readouts
  text=text??el.dataset.text??el.textContent;el.dataset.text=text;
  if(CALM){el.textContent=text;return}
  clearInterval(el._scr);let i=0;const n=text.length;
  el._scr=setInterval(()=>{i+=Math.max(1,n/9);el.textContent=[...text].map((c,k)=>k<i||c===' '?c:GLYPHS[Math.random()*GLYPHS.length|0]).join('');
    if(i>=n){clearInterval(el._scr);el.textContent=text}},28)}
(()=>{const hook=()=>document.querySelectorAll('.seg button,.card h2,[data-scramble]').forEach(el=>{if(el._sc)return;el._sc=1;
    el.addEventListener('mouseenter',()=>{if(el.children.length===0)scramble(el)})});
 hook();new MutationObserver(hook).observe(document.body,{childList:true,subtree:true});
 if(CALM||matchMedia('(pointer:coarse)').matches)return;
 const c=document.createElement('div');c.id='cur';document.body.append(c);let x=0,y=0,tx=0,ty=0,raf=0;
 const loop=()=>{x+=(tx-x)*.28;y+=(ty-y)*.28;c.style.transform=`translate(${x}px,${y}px)`;raf=Math.abs(tx-x)+Math.abs(ty-y)>.3?requestAnimationFrame(loop):0};
 addEventListener('pointermove',e=>{tx=e.clientX;ty=e.clientY;c.classList.add('on');c.classList.toggle('big',!!e.target.closest('button,a,select,input,.row,.chip,[data-go],.reg,.lg'));if(!raf)raf=requestAnimationFrame(loop)},{passive:true});
 document.addEventListener('pointerleave',()=>c.classList.remove('on'));
})();
