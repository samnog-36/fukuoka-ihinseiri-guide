(function(){
  const API="/api/ad";
  const alias={ihinseiri:"遺品整理",cost:"遺品整理",seizenseiri:"生前整理",tokushu:"特殊清掃","tokushu-seisou":"特殊清掃",kuyo:"供養",area:"遺品整理"};
  function genre(v){return alias[v]||v||""}
  function post(path,body){return fetch(API+path,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body),keepalive:true}).catch(()=>null)}
  function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
  async function render(slot){
    const placement=slot.dataset.placement||"article_middle",g=genre(slot.dataset.genre);
    try{
      const r=await fetch(API+"/serve?genre="+encodeURIComponent(g),{cache:"no-store"});const d=await r.json();if(!d.ad)return;
      const a=d.ad;slot.innerHTML='<div style="border:1px solid #dce6df;border-radius:14px;padding:18px;background:#fff;margin:20px 0;box-shadow:0 6px 18px rgba(0,0,0,.04)"><div style="font-size:10px;color:#788;font-weight:700">広告</div><div style="font-size:18px;font-weight:800;margin-top:5px">'+esc(a.companyName)+'</div>'+(a.catchphrase?'<div style="color:#2f6b53;font-weight:700;margin-top:5px">'+esc(a.catchphrase)+'</div>':'')+(a.description?'<p style="font-size:13px;line-height:1.7;color:#566;margin:10px 0">'+esc(a.description)+'</p>':'')+'<div style="font-size:12px;color:#667;display:grid;gap:5px">'+(a.priceRange?'<div>料金目安：'+esc(a.priceRange)+'</div>':'')+(a.businessHours?'<div>営業時間：'+esc(a.businessHours)+'</div>':'')+(a.serviceArea?'<div>対応エリア：'+esc(a.serviceArea)+'</div>':'')+'</div><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:13px"><button data-k="phone" style="border:0;border-radius:9px;padding:10px 13px;background:#1d6f50;color:#fff;font-weight:700">電話番号を表示</button><button data-k="email" style="border:1px solid #b9c8c0;border-radius:9px;padding:10px 13px;background:#fff;color:#245b46;font-weight:700">メールを表示</button></div></div>';
      post("/track",{adId:a.id,eventType:"impression",placement,pageUrl:location.href,pageGenre:g});
      slot.querySelectorAll("button[data-k]").forEach(b=>b.onclick=async()=>{
        const kind=b.dataset.k;post("/track",{adId:a.id,eventType:"click",placement,pageUrl:location.href,pageGenre:g});
        const rr=await fetch(API+"/reveal",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({adId:a.id,kind,placement,pageUrl:location.href,pageGenre:g})});const x=await rr.json();
        if(!rr.ok||!x.value)return;b.textContent=x.value;if(kind==="phone")b.onclick=()=>location.href="tel:"+x.value.replace(/[^0-9+]/g,"");else b.onclick=()=>location.href="mailto:"+x.value;
      });
    }catch(e){}
  }
  document.addEventListener("DOMContentLoaded",()=>document.querySelectorAll(".fkg-ad").forEach(render));
})();