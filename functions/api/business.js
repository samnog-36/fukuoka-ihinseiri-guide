import { requireDb, rowId, nowMs } from "../_lib/db.js";
import { json, clean, validEmail, corsHeaders, options, rateLimit, originAllowed } from "../_lib/public.js";

export function onRequestOptions(context){ return options(context.request); }

export async function onRequestPost(context){
  if(!originAllowed(context.request)) return json({ok:false,error:"origin_not_allowed"},403);
  const cors=corsHeaders(context.request);
  if(!(await rateLimit(context,"business",6,30*60*1000))) return json({ok:false,error:"rate_limited"},429,cors);
  let input;
  try{input=await context.request.json();}catch{return json({ok:false,error:"invalid_json"},400,cors);}
  if(input?.json) input=input.json;
  const d={
    companyName:clean(input.companyName,200),
    contactPerson:clean(input.contactPerson,120),
    phone:clean(input.phone,80),
    email:clean(input.email,240),
    serviceArea:clean(input.serviceArea,1200),
    serviceContent:clean(input.serviceContent,1200)
  };
  if(!d.companyName||!d.contactPerson||!d.phone||!validEmail(d.email)||!d.serviceArea||!d.serviceContent)
    return json({ok:false,error:"validation_failed"},400,cors);

  const db=requireDb(context.env),id=rowId("biz"),now=nowMs();
  await db.prepare(`INSERT INTO business_applications
    (id,company_name,contact_person,phone,email,service_area,service_content,status,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,'未対応',?,?)`)
    .bind(id,d.companyName,d.contactPerson,d.phone,d.email,d.serviceArea,d.serviceContent,now,now).run();
  return json({ok:true,id},200,cors);
}
