import { requireDb, nowMs, audit, safeJson } from "../../../_lib/db.js";
export async function onRequestGet(context){
  const db=requireDb(context.env),id=context.params.id,since=Date.now()-30*24*60*60*1000;
  const ad=await db.prepare("SELECT * FROM advertisements WHERE id=?").bind(id).first();
  if(!ad)return Response.json({ok:false,error:"not_found"},{status:404});
  ad.serviceGenres=safeJson(ad.service_genres_json,[]);
  const daily=(await db.prepare(`SELECT date(created_at/1000,'unixepoch') day,event_type,COUNT(*) count
    FROM ad_events WHERE ad_id=? AND created_at>=? GROUP BY day,event_type ORDER BY day`).bind(id,since).all()).results||[];
  const placements=(await db.prepare(`SELECT placement,event_type,COUNT(*) count
    FROM ad_events WHERE ad_id=? AND created_at>=? GROUP BY placement,event_type ORDER BY count DESC`).bind(id,since).all()).results||[];
  return Response.json({ok:true,ad,daily,placements});
}
export async function onRequestPost(context){
  const db=requireDb(context.env),id=context.params.id;
  let d;try{d=await context.request.json();}catch{return Response.json({ok:false,error:"invalid_json"},{status:400});}
  if(d.action==="toggle"){
    const active=d.active?1:0;
    await db.prepare("UPDATE advertisements SET is_active=?,updated_at=? WHERE id=?").bind(active,nowMs(),id).run();
    await audit(context.env,"ad.toggle","advertisement",id,{active:Boolean(active)});
    return Response.json({ok:true,active:Boolean(active)});
  }
  if(d.action==="banner"){
    await db.prepare("UPDATE advertisements SET banner_url=?,updated_at=? WHERE id=?").bind(String(d.bannerUrl||"").trim()||null,nowMs(),id).run();
    await audit(context.env,"ad.banner","advertisement",id,{});
    return Response.json({ok:true});
  }
  return Response.json({ok:false,error:"invalid_action"},{status:400});
}
