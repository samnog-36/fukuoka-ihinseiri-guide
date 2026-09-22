import { requireDb, getInquiryWithMemos, rowId, nowMs, audit } from "../../../_lib/db.js";

export async function onRequestGet(context){
  const row=await getInquiryWithMemos(context.env,context.params.id);
  return row?Response.json({ok:true,inquiry:row}):Response.json({ok:false,error:"not_found"},{status:404});
}

export async function onRequestPost(context){
  const db=requireDb(context.env),id=context.params.id;
  let d;try{d=await context.request.json();}catch{return Response.json({ok:false,error:"invalid_json"},{status:400});}
  if(d.action==="status"){
    if(!["未対応","対応中","完了"].includes(d.status)) return Response.json({ok:false,error:"invalid_status"},{status:400});
    await db.prepare("UPDATE inquiries SET status=?,updated_at=? WHERE id=?").bind(d.status,nowMs(),id).run();
    await audit(context.env,"inquiry.status","inquiry",id,{status:d.status});
  }else if(d.action==="memo"){
    const content=String(d.content||"").trim().slice(0,5000);
    if(!content) return Response.json({ok:false,error:"memo_required"},{status:400});
    await db.prepare("INSERT INTO inquiry_memos (id,inquiry_id,content,created_at) VALUES (?,?,?,?)")
      .bind(rowId("memo"),id,content,nowMs()).run();
    await audit(context.env,"inquiry.memo","inquiry",id,{length:content.length});
  }else return Response.json({ok:false,error:"invalid_action"},{status:400});
  return Response.json({ok:true,inquiry:await getInquiryWithMemos(context.env,id)});
}
