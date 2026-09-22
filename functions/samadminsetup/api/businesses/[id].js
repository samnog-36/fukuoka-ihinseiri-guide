import { requireDb, nowMs, audit, safeJson } from "../../../_lib/db.js";
import { newSetupToken, hashToken } from "../../../_lib/token.js";

export async function onRequestGet(context){
  const db=requireDb(context.env);
  const b=await db.prepare("SELECT * FROM business_applications WHERE id=?").bind(context.params.id).first();
  if(!b)return Response.json({ok:false,error:"not_found"},{status:404});
  const ad=await db.prepare("SELECT * FROM advertisements WHERE business_id=?").bind(b.id).first();
  if(ad)ad.serviceGenres=safeJson(ad.service_genres_json,[]);
  return Response.json({ok:true,business:b,advertisement:ad||null});
}

export async function onRequestPost(context){
  const db=requireDb(context.env),id=context.params.id;
  let d;try{d=await context.request.json();}catch{return Response.json({ok:false,error:"invalid_json"},{status:400});}
  if(d.action!=="status"||!["未対応","承認","却下"].includes(d.status)) return Response.json({ok:false,error:"invalid_action"},{status:400});
  let setupUrl=null,now=nowMs();
  if(d.status==="承認"){
    const token=newSetupToken(),hash=await hashToken(token),expires=now+30*24*60*60*1000;
    await db.prepare("UPDATE business_applications SET status='承認',setup_token_hash=?,setup_token_created_at=?,setup_token_expires_at=?,updated_at=? WHERE id=?")
      .bind(hash,now,expires,now,id).run();
    setupUrl="https://fukuoka-ihinseiri-guide.com/business/setup/"+token;
  }else{
    await db.prepare("UPDATE business_applications SET status=?,setup_token_hash=NULL,setup_token_created_at=NULL,setup_token_expires_at=NULL,updated_at=? WHERE id=?")
      .bind(d.status,now,id).run();
  }
  await audit(context.env,"business.status","business_application",id,{status:d.status});
  return Response.json({ok:true,status:d.status,setupUrl});
}
