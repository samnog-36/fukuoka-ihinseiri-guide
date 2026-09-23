import { requireDb, nowMs, audit } from "../../_lib/db.js";

export async function onRequestGet(context){
  const db=requireDb(context.env);
  try{
    const placements=(await db.prepare(
      "SELECT key,label,description,monthly_price,is_active,sort_order,updated_at FROM ad_placements ORDER BY sort_order,key"
    ).all()).results||[];
    return Response.json({ok:true,schemaReady:true,placements});
  }catch(e){
    return Response.json({ok:true,schemaReady:false,placements:[],error:"ad_sales_schema_not_applied"});
  }
}

export async function onRequestPost(context){
  const db=requireDb(context.env);
  try{ await db.prepare("SELECT key FROM ad_placements LIMIT 1").first(); }
  catch{ return Response.json({ok:false,error:"ad_sales_schema_not_applied"},{status:503}); }
  let d;try{d=await context.request.json();}catch{return Response.json({ok:false,error:"invalid_json"},{status:400});}
  if(d.action!=="update_placement") return Response.json({ok:false,error:"invalid_action"},{status:400});

  const key=String(d.key||"").trim();
  const allowed=new Set(["article_top","article_middle","article_bottom","sidebar"]);
  if(!allowed.has(key)) return Response.json({ok:false,error:"invalid_placement"},{status:400});

  const price=Math.max(0,Math.round(Number(d.monthlyPrice||0)));
  const active=d.active?1:0;
  const description=String(d.description||"").trim().slice(0,500)||null;

  await db.prepare(
    "UPDATE ad_placements SET monthly_price=?,is_active=?,description=?,updated_at=? WHERE key=?"
  ).bind(price,active,description,nowMs(),key).run();

  await audit(context.env,"ad_placement.update","ad_placement",key,{monthlyPrice:price,active:Boolean(active)});
  return Response.json({ok:true,key,monthlyPrice:price,active:Boolean(active)});
}
