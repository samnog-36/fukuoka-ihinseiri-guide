import { requireDb } from "../../_lib/db.js";
export async function onRequestGet(context){
  const db=requireDb(context.env);
  const rows=(await db.prepare(`SELECT b.*,
    a.id ad_id,a.is_active ad_is_active,a.updated_at ad_updated_at
    FROM business_applications b LEFT JOIN advertisements a ON a.business_id=b.id
    ORDER BY b.created_at DESC LIMIT 500`).all()).results||[];
  const counts=(await db.prepare(`SELECT COUNT(*) total,
    SUM(CASE WHEN status='未対応' THEN 1 ELSE 0 END) pending,
    SUM(CASE WHEN status='承認' THEN 1 ELSE 0 END) approved,
    SUM(CASE WHEN status='却下' THEN 1 ELSE 0 END) rejected
    FROM business_applications`).first())||{};
  return Response.json({ok:true,counts,businesses:rows});
}
