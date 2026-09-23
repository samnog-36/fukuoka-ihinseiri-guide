(function(){
  const API="/api/ad";
  const alias={
    ihinseiri:"遺品整理",cost:"遺品整理","費用":"遺品整理","費用相場":"遺品整理",
    seizenseiri:"生前整理",tokushu:"特殊清掃","tokushu-seisou":"特殊清掃",
    kuyo:"供養","遺品供養":"供養",area:"遺品整理","地域別":"遺品整理","地域情報":"遺品整理"
  };
  const genre=v=>alias[v]||v||"";
  const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const safeUrl=v=>{try{const u=new URL(String(v||""),location.origin);return /^https?:$/.test(u.protocol)?u.href:""}catch{return""}};
  function post(path,body){
    return fetch(API+path,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body),keepalive:true}).catch(()=>null);
  }
  function injectStyle(){
    if(document.getElementById("fkg-ad-style"))return;
    const st=document.createElement("style");st.id="fkg-ad-style";
    st.textContent=`
      .fkg-ad-card{border:1px solid #dce6df;border-radius:16px;background:#fff;margin:22px 0;overflow:hidden;box-shadow:0 10px 28px rgba(24,56,43,.08);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif}
      .fkg-ad-media{width:100%;aspect-ratio:16/7;object-fit:cover;display:block;background:#edf3ef}
      .fkg-ad-body{padding:18px}
      .fkg-ad-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
      .fkg-ad-label{font-size:10px;color:#718078;font-weight:800;letter-spacing:.08em}
      .fkg-ad-company{font-size:19px;font-weight:900;color:#1c2923;margin-top:4px;line-height:1.35}
      .fkg-ad-catch{color:#2f6b53;font-weight:800;margin-top:7px;line-height:1.5}
      .fkg-ad-desc{font-size:13px;line-height:1.75;color:#56635d;margin:11px 0}
      .fkg-ad-meta{font-size:12px;color:#66736d;display:grid;gap:5px}
      .fkg-ad-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:15px}
      .fkg-ad-btn{border-radius:9px;padding:10px 13px;font-weight:800;font-size:12px;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center}
      .fkg-ad-btn.primary{border:0;background:#1d6f50;color:#fff}
      .fkg-ad-btn.secondary{border:1px solid #b9c8c0;background:#fff;color:#245b46}
      .fkg-ad-btn.web{border:1px solid #d1d9d4;background:#f7faf8;color:#334c40}
      .fkg-ad-foot{font-size:9px;color:#8a9790;margin-top:12px;line-height:1.5}
      @media(max-width:640px){.fkg-ad-body{padding:15px}.fkg-ad-company{font-size:17px}.fkg-ad-actions{display:grid;grid-template-columns:1fr 1fr}.fkg-ad-btn{justify-content:center}.fkg-ad-btn.web{grid-column:1/-1}}
    `;
    document.head.appendChild(st);
  }
  function impressionKey(adId,placement){
    return "fkg-ad-imp:"+adId+":"+placement+":"+location.pathname;
  }
  async function render(slot){
    injectStyle();
    const placement=slot.dataset.placement||"article_middle",g=genre(slot.dataset.genre);
    try{
      const r=await fetch(API+"/serve?genre="+encodeURIComponent(g)+"&placement="+encodeURIComponent(placement),{cache:"no-store"});
      const d=await r.json();if(!r.ok||!d.ad){slot.innerHTML="";return}
      const a=d.ad,img=safeUrl(a.bannerUrl||a.photoUrl),web=safeUrl(a.websiteUrl);
      slot.innerHTML='<div class="fkg-ad-card">'+
        (img?'<img class="fkg-ad-media" src="'+esc(img)+'" alt="" loading="lazy">':'')+
        '<div class="fkg-ad-body"><div class="fkg-ad-head"><div><div class="fkg-ad-label">スポンサー広告</div><div class="fkg-ad-company">'+esc(a.companyName)+'</div></div></div>'+
        (a.catchphrase?'<div class="fkg-ad-catch">'+esc(a.catchphrase)+'</div>':'')+
        (a.description?'<p class="fkg-ad-desc">'+esc(a.description)+'</p>':'')+
        '<div class="fkg-ad-meta">'+
        (a.priceRange?'<div>料金目安：'+esc(a.priceRange)+'</div>':'')+
        (a.businessHours?'<div>営業時間：'+esc(a.businessHours)+'</div>':'')+
        (a.serviceArea?'<div>対応エリア：'+esc(a.serviceArea)+'</div>':'')+
        '</div><div class="fkg-ad-actions">'+
        '<button class="fkg-ad-btn primary" data-k="phone">電話番号を表示</button>'+
        '<button class="fkg-ad-btn secondary" data-k="email">メールを表示</button>'+
        (web?'<a class="fkg-ad-btn web" data-k="website" href="'+esc(web)+'" target="_blank" rel="nofollow sponsored noopener">公式サイトを見る</a>':'')+
        '</div><div class="fkg-ad-foot">この枠は掲載事業者による広告です。掲載内容は事業者から提供された情報をもとに表示しています。</div></div></div>';

      try{
        const key=impressionKey(a.id,placement);
        if(!sessionStorage.getItem(key)){
          sessionStorage.setItem(key,"1");
          post("/track",{adId:a.id,eventType:"impression",placement,pageUrl:location.href,pageGenre:g});
        }
      }catch{
        post("/track",{adId:a.id,eventType:"impression",placement,pageUrl:location.href,pageGenre:g});
      }

      slot.querySelectorAll("button[data-k]").forEach(b=>b.onclick=async()=>{
        const kind=b.dataset.k;
        post("/track",{adId:a.id,eventType:"click",placement,pageUrl:location.href,pageGenre:g});
        const rr=await fetch(API+"/reveal",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({adId:a.id,kind,placement,pageUrl:location.href,pageGenre:g})});
        const x=await rr.json();if(!rr.ok||!x.value)return;
        b.textContent=x.value;
        if(kind==="phone")b.onclick=()=>location.href="tel:"+x.value.replace(/[^0-9+]/g,"");
        else b.onclick=()=>location.href="mailto:"+x.value;
      });

      const website=slot.querySelector('[data-k="website"]');
      if(website)website.addEventListener("click",()=>post("/track",{adId:a.id,eventType:"click",placement,pageUrl:location.href,pageGenre:g}),{once:true});
    }catch{
      slot.innerHTML="";
    }
  }
  document.addEventListener("DOMContentLoaded",()=>document.querySelectorAll(".fkg-ad").forEach(render));
})();