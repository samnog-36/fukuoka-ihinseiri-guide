import { requireDb, rowId, nowMs } from "../../_lib/db.js";
import { json, clean, corsHeaders, options, rateLimit } from "../../_lib/public.js";

export function onRequestOptions(context){return options(context.request);}
export async function onRequestPost(context){
  const cors=corsHeaders(context.request);
  if(!(await rateLimit(context,"ad_event",120,15*60*1000))) return json({ok:false,error:"rate_limited"},429,cors);
  let d;try{d=await context.request.json();}catch{return json({ok:false,error:"invalid_json"},400,cors);}
  const type=clean(d.eventType,40);
  if(!["impression","click","phone_reveal","email_reveal"].includes(type)) return json({ok:false,error:"invalid_event"},400,cors);
  const db=requireDb(context.env);
  const ad=await db.prepare("SELECT id FROM advertisements WHERE id=? AND is_active=1").bind(clean(d.adId,100)).first();
  if(!ad) return json({ok:false,error:"ad_not_found"},404,cors);
  await db.prepare("INSERT INTO ad_events (id,ad_id,event_type,placement,page_url,page_genre,created_at) VALUES (?,?,?,?,?,?,?)")
    .bind(rowId("evt"),ad.id,type,clean(d.placement,80)||null,clean(d.pageUrl,1000)||null,clean(d.pageGenre,120)||null,nowMs()).run();
  return json({ok:true},200,cors);
}
