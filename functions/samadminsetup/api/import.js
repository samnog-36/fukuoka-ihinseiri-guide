import { requireDb, nowMs, audit } from "../../_lib/db.js";

const allowed={
  inquiries:["id","name","phone","email","region","service_type","floor_plan","budget","preferred_timing","details","status","created_at","updated_at"],
  inquiry_memos:["id","inquiry_id","content","created_at"],
  business_applications:["id","company_name","contact_person","phone","email","service_area","service_content","status","setup_token_hash","setup_token_created_at","setup_token_expires_at","created_at","updated_at"],
  advertisements:["id","business_id","company_name","catchphrase","description","phone","email","price_range","business_hours","qualifications","logo_url","photo_url","service_genres_json","service_area","banner_url","is_active","created_at","updated_at"],
  ad_events:["id","ad_id","event_type","placement","page_url","page_genre","created_at"]
};
export async function onRequestPost(context){
  const db=requireDb(context.env);
  let data;try{data=await context.request.json();}catch{return Response.json({ok:false,error:"invalid_json"},{status:400});}
  const counts={};
  for(const [table,cols] of Object.entries(allowed)){
    const rows=Array.isArray(data[table])?data[table]:[];counts[table]=0;
    for(const row of rows){
      const values=cols.map(c=>row[c]??null),sql=`INSERT OR REPLACE INTO ${table} (${cols.join(",")}) VALUES (${cols.map(()=>"?").join(",")})`;
      await db.prepare(sql).bind(...values).run();counts[table]++;
    }
  }
  await db.prepare("INSERT OR REPLACE INTO migration_state (key,value_json,updated_at) VALUES ('last_import',?,?)").bind(JSON.stringify({counts,source:data.source||"manual_export"}),nowMs()).run();
  await audit(context.env,"migration.import","system","admin",{counts});
  return Response.json({ok:true,counts});
}
