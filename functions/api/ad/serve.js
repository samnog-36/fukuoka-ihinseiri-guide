import { requireDb, safeJson } from "../../_lib/db.js";
import { json, clean, corsHeaders, options } from "../../_lib/public.js";

const alias={
  ihinseiri:"遺品整理",cost:"遺品整理",seizenseiri:"生前整理",tokushu:"特殊清掃","tokushu-seisou":"特殊清掃",
  kuyo:"供養",area:"遺品整理"
};
function norm(v){v=clean(v,80);return alias[v]||v;}

export function onRequestOptions(context){return options(context.request);}
export async function onRequestGet(context){
  const cors=corsHeaders(context.request),url=new URL(context.request.url),genre=norm(url.searchParams.get("genre")||"");
  const db=requireDb(context.env);
  const rows=(await db.prepare("SELECT * FROM advertisements WHERE is_active=1 ORDER BY updated_at DESC LIMIT 200").all()).results||[];
  const eligible=rows.filter(r=>{
    const gs=safeJson(r.service_genres_json,[]).map(norm);
    return !genre||gs.includes(genre);
  });
  if(!eligible.length) return json({ad:null},200,cors);
  const ad=eligible[Math.floor(Math.random()*eligible.length)];
  return json({ad:{
    id:ad.id,companyName:ad.company_name,catchphrase:ad.catchphrase,description:ad.description,
    priceRange:ad.price_range,businessHours:ad.business_hours,serviceArea:ad.service_area,
    serviceGenres:safeJson(ad.service_genres_json,[]),photoUrl:ad.photo_url,logoUrl:ad.logo_url,bannerUrl:ad.banner_url
  }},200,cors);
}
