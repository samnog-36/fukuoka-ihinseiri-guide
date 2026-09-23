import { requireDb } from "../../_lib/db.js";
import { json, corsHeaders, options } from "../../_lib/public.js";

export function onRequestOptions(context){ return options(context.request); }

export async function onRequestGet(context){
  const cors=corsHeaders(context.request);
  const db=requireDb(context.env);
  try{
    const rows=(await db.prepare(
      "SELECT key,label,description,monthly_price,sort_order FROM ad_placements WHERE is_active=1 ORDER BY sort_order,key"
    ).all()).results||[];
    return json({
      ok:true,
      placements:rows.map(r=>({
        key:r.key,
        label:r.label,
        description:r.description,
        monthlyPrice:Number(r.monthly_price||0)
      }))
    },200,cors);
  }catch{
    return json({ok:true,placements:[]},200,cors);
  }
}
