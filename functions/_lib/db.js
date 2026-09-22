export function nowMs(){ return Date.now(); }

export function requireDb(env){
  if(!env.DB) throw new Error("D1 binding DB is not configured");
  return env.DB;
}

export async function audit(env, action, entityType, entityId, details={}){
  const db=requireDb(env);
  await db.prepare(
    "INSERT INTO audit_logs (action, entity_type, entity_id, details_json, created_at) VALUES (?, ?, ?, ?, ?)"
  ).bind(action, entityType, String(entityId ?? ""), JSON.stringify(details), nowMs()).run();
}

export async function getInquiryWithMemos(env,id){
  const db=requireDb(env);
  const inquiry=await db.prepare("SELECT * FROM inquiries WHERE id=?").bind(id).first();
  if(!inquiry) return null;
  const memos=await db.prepare(
    "SELECT * FROM inquiry_memos WHERE inquiry_id=? ORDER BY created_at DESC"
  ).bind(id).all();
  return {...inquiry,memos:memos.results||[]};
}

export function rowId(prefix="id"){
  return prefix+"_"+crypto.randomUUID().replaceAll("-","");
}

export function safeJson(value,fallback=[]){
  try{return JSON.parse(value||"")}catch{return fallback}
}
