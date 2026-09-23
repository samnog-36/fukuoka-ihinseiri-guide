import { requireDb } from "../../_lib/db.js";
export async function onRequestGet(context){
  const db=requireDb(context.env),tables=["inquiries","inquiry_memos","business_applications","advertisements","ad_events","ad_placements","audit_logs"];
  const data={exportedAt:new Date().toISOString(),schemaVersion:1};
  for(const table of tables)data[table]=(await db.prepare("SELECT * FROM "+table).all()).results||[];
  return new Response(JSON.stringify(data,null,2),{headers:{"content-type":"application/json","content-disposition":"attachment; filename=fukuoka-admin-export.json","cache-control":"no-store"}});
}
