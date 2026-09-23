import { requireDb, rowId, nowMs } from "../_lib/db.js";
import { json, clean, validEmail, corsHeaders, options, rateLimit, originAllowed } from "../_lib/public.js";

export function onRequestOptions(context){ return options(context.request); }

export async function onRequestPost(context){
  if(!originAllowed(context.request)) return json({ok:false,error:"origin_not_allowed"},403);
  const cors=corsHeaders(context.request);
  if(!(await rateLimit(context,"inquiry",8,15*60*1000))) return json({ok:false,error:"rate_limited"},429,cors);

  let input;
  try{ input=await context.request.json(); }catch{ return json({ok:false,error:"invalid_json"},400,cors); }
  if(input?.json) input=input.json;

  const data={
    name:clean(input.name,120),
    phone:clean(input.phone,80),
    email:clean(input.email,240),
    region:clean(input.region,120),
    serviceType:clean(input.serviceType,120),
    floorPlan:clean(input.floorPlan,120)||null,
    budget:clean(input.budget,120)||null,
    preferredTiming:clean(input.preferredTiming,120)||null,
    details:clean(input.details,5000)||null
  };
  if(!data.name||!data.phone||!validEmail(data.email)||!data.region||!data.serviceType){
    return json({ok:false,error:"validation_failed"},400,cors);
  }

  const db=requireDb(context.env);
  const id=rowId("inq"), now=nowMs();
  await db.prepare(`INSERT INTO inquiries
    (id,name,phone,email,region,service_type,floor_plan,budget,preferred_timing,details,status,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,'未対応',?,?)`)
    .bind(id,data.name,data.phone,data.email,data.region,data.serviceType,data.floorPlan,data.budget,data.preferredTiming,data.details,now,now).run();

  return json({ok:true,id},200,cors);
}
