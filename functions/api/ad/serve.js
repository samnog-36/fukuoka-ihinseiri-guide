import { requireDb, safeJson } from "../../_lib/db.js";
import { json, clean, corsHeaders, options } from "../../_lib/public.js";

const alias={
  ihinseiri:"遺品整理",cost:"遺品整理","費用":"遺品整理","費用相場":"遺品整理",
  seizenseiri:"生前整理",tokushu:"特殊清掃","tokushu-seisou":"特殊清掃",
  kuyo:"供養","遺品供養":"供養",area:"遺品整理","地域別":"遺品整理","地域情報":"遺品整理"
};
function norm(v){v=clean(v,80);return alias[v]||v;}

export function onRequestOptions(context){return options(context.request);}
export async function onRequestGet(context){
  const cors=corsHeaders(context.request),url=new URL(context.request.url);
  const genre=norm(url.searchParams.get("genre")||"");
  const placement=clean(url.searchParams.get("placement")||"article_middle",80);
  const db=requireDb(context.env),now=Date.now();

  const slot=await db.prepare("SELECT key,is_active FROM ad_placements WHERE key=?").bind(placement).first();
  if(slot && !slot.is_active) return json({ad:null,placement},200,cors);

  const rows=(await db.prepare(
    "SELECT * FROM advertisements WHERE is_active=1 AND (starts_at IS NULL OR starts_at<=?) AND (ends_at IS NULL OR ends_at>=?) ORDER BY updated_at DESC LIMIT 200"
  ).bind(now,now).all()).results||[];

  const eligible=rows.filter(r=>{
    const gs=safeJson(r.service_genres_json,[]).map(norm);
    const ps=safeJson(r.placements_json,[]);
    const genreOk=!genre||gs.includes(genre);
    const placementOk=ps.includes(placement);
    return genreOk&&placementOk;
  });
  if(!eligible.length) return json({ad:null,placement},200,cors);

  const ad=eligible[Math.floor(Math.random()*eligible.length)];
  return json({ad:{
    id:ad.id,companyName:ad.company_name,catchphrase:ad.catchphrase,description:ad.description,
    priceRange:ad.price_range,businessHours:ad.business_hours,serviceArea:ad.service_area,
    serviceGenres:safeJson(ad.service_genres_json,[]),placements:safeJson(ad.placements_json,[]),
    photoUrl:ad.photo_url,logoUrl:ad.logo_url,bannerUrl:ad.banner_url,websiteUrl:ad.website_url
  },placement},200,cors);
}
