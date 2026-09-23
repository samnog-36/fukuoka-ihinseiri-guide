import { requireDb, safeJson } from "../../_lib/db.js";
export async function onRequestGet(context){
  const db=requireDb(context.env),since=Date.now()-30*24*60*60*1000;
  const ads=(await db.prepare(`SELECT a.*,
    SUM(CASE WHEN e.event_type='impression' AND e.created_at>=? THEN 1 ELSE 0 END) impressions,
    SUM(CASE WHEN e.event_type='click' AND e.created_at>=? THEN 1 ELSE 0 END) clicks,
    SUM(CASE WHEN e.event_type='phone_reveal' AND e.created_at>=? THEN 1 ELSE 0 END) phone_reveals,
    SUM(CASE WHEN e.event_type='email_reveal' AND e.created_at>=? THEN 1 ELSE 0 END) email_reveals
    FROM advertisements a LEFT JOIN ad_events e ON e.ad_id=a.id
    GROUP BY a.id ORDER BY a.created_at DESC`)
    .bind(since,since,since,since).all()).results||[];
  for(const a of ads){
    a.serviceGenres=safeJson(a.service_genres_json,[]);
    a.placements=safeJson(a.placements_json,[]);
    a.ctr=Number(a.impressions||0)?Number(a.clicks||0)/Number(a.impressions||0):0;
  }
  const summary=ads.reduce((s,a)=>({
    impressions:s.impressions+Number(a.impressions||0),
    clicks:s.clicks+Number(a.clicks||0),
    phoneReveals:s.phoneReveals+Number(a.phone_reveals||0),
    emailReveals:s.emailReveals+Number(a.email_reveals||0),
    active:s.active+(a.is_active?1:0),
    monthlyContractValue:s.monthlyContractValue+(a.is_active?Number(a.contract_price_monthly||0):0)
  }),{impressions:0,clicks:0,phoneReveals:0,emailReveals:0,active:0,monthlyContractValue:0});
  return Response.json({ok:true,summary,ads});
}
