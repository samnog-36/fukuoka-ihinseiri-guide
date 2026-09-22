import { requireDb } from "../../_lib/db.js";

export async function onRequestGet(context){
  const db=requireDb(context.env);
  const status=new URL(context.request.url).searchParams.get("status")||"";
  const where=["未対応","対応中","完了"].includes(status)?" WHERE status=?":"";
  const stmt=db.prepare(`SELECT id,name,phone,email,region,service_type,floor_plan,budget,preferred_timing,details,status,created_at,updated_at
    FROM inquiries${where} ORDER BY created_at DESC LIMIT 500`);
  const rows=(where?await stmt.bind(status).all():await stmt.all()).results||[];
  const counts=(await db.prepare(`SELECT
    COUNT(*) total,
    SUM(CASE WHEN status='未対応' THEN 1 ELSE 0 END) pending,
    SUM(CASE WHEN status='対応中' THEN 1 ELSE 0 END) working,
    SUM(CASE WHEN status='完了' THEN 1 ELSE 0 END) done
    FROM inquiries`).first())||{};
  return Response.json({connected:true,source:"cloudflare_d1",counts,inquiries:rows});
}
