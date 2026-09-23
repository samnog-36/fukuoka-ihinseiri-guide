import { requireDb, rowId, nowMs, safeJson } from "../../../_lib/db.js";
import { hashToken } from "../../../_lib/token.js";
import { json, clean, validEmail, corsHeaders, options, rateLimit, originAllowed } from "../../../_lib/public.js";

export function onRequestOptions(context){return options(context.request);}

async function getBusiness(env,token){
  const db=requireDb(env),hash=await hashToken(token);
  const row=await db.prepare("SELECT * FROM business_applications WHERE setup_token_hash=? AND status='承認'").bind(hash).first();
  if(!row) return null;
  if(row.setup_token_expires_at && Number(row.setup_token_expires_at)<Date.now()) return null;
  return row;
}

export async function onRequestGet(context){
  const cors=corsHeaders(context.request);
  const b=await getBusiness(context.env,context.params.token);
  if(!b) return json({ok:false,error:"invalid_or_expired_token"},404,cors);
  const db=requireDb(context.env);
  const ad=await db.prepare("SELECT * FROM advertisements WHERE business_id=?").bind(b.id).first();
  return json({ok:true,business:{
    id:b.id,companyName:b.company_name,contactPerson:b.contact_person,phone:b.phone,email:b.email,
    serviceArea:b.service_area,serviceContent:b.service_content
  },advertisement:ad?{
    ...ad,serviceGenres:safeJson(ad.service_genres_json,[])
  }:null},200,cors);
}

export async function onRequestPost(context){
  if(!originAllowed(context.request)) return json({ok:false,error:"origin_not_allowed"},403);
  const cors=corsHeaders(context.request);
  if(!(await rateLimit(context,"business_setup",20,60*60*1000))) return json({ok:false,error:"rate_limited"},429,cors);
  const b=await getBusiness(context.env,context.params.token);
  if(!b) return json({ok:false,error:"invalid_or_expired_token"},404,cors);
  let input;try{input=await context.request.json();}catch{return json({ok:false,error:"invalid_json"},400,cors);}
  const genres=Array.isArray(input.serviceGenres)?input.serviceGenres.map(x=>clean(x,80)).filter(Boolean).slice(0,12):[];
  if(!genres.length) return json({ok:false,error:"service_genres_required"},400,cors);
  const email=clean(input.email,240)||b.email;
  if(email && !validEmail(email)) return json({ok:false,error:"invalid_email"},400,cors);
  const db=requireDb(context.env),now=nowMs();
  const existing=await db.prepare("SELECT id FROM advertisements WHERE business_id=?").bind(b.id).first();
  if(existing){
    const websiteUrl=clean(input.websiteUrl,1000)||null;
    if(websiteUrl && !/^https?:\/\//i.test(websiteUrl)) return json({ok:false,error:"invalid_website_url"},400,cors);
    await db.prepare(`UPDATE advertisements SET
      company_name=?,catchphrase=?,description=?,phone=?,email=?,price_range=?,business_hours=?,qualifications=?,
      service_genres_json=?,service_area=?,website_url=?,updated_at=? WHERE business_id=?`)
      .bind(
        b.company_name,clean(input.catchphrase,200)||null,clean(input.description,3000)||null,
        clean(input.phone,80)||b.phone,email,clean(input.priceRange,240)||null,clean(input.businessHours,240)||null,
        clean(input.qualifications,1200)||null,JSON.stringify(genres),clean(input.serviceArea,1200)||b.service_area,websiteUrl,now,b.id
      ).run();
  }else{
    const websiteUrl=clean(input.websiteUrl,1000)||null;
    if(websiteUrl && !/^https?:\/\//i.test(websiteUrl)) return json({ok:false,error:"invalid_website_url"},400,cors);
    await db.prepare(`INSERT INTO advertisements
      (id,business_id,company_name,catchphrase,description,phone,email,price_range,business_hours,qualifications,service_genres_json,service_area,placements_json,website_url,is_active,created_at,updated_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, ?,0,?,?)`)
      .bind(
        rowId("ad"),b.id,b.company_name,clean(input.catchphrase,200)||null,clean(input.description,3000)||null,
        clean(input.phone,80)||b.phone,email,clean(input.priceRange,240)||null,clean(input.businessHours,240)||null,
        clean(input.qualifications,1200)||null,JSON.stringify(genres),clean(input.serviceArea,1200)||b.service_area,
        JSON.stringify(["article_middle"]),websiteUrl,now,now
      ).run();
  }
  return json({ok:true},200,cors);
}
