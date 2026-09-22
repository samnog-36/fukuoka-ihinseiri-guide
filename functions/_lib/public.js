import { requireDb, nowMs } from "./db.js";

export function json(data,status=200,extra={}){
  return new Response(JSON.stringify(data),{
    status,
    headers:{
      "content-type":"application/json; charset=utf-8",
      "cache-control":"no-store",
      ...extra
    }
  });
}

export function clean(value,max=2000){
  return String(value ?? "").trim().slice(0,max);
}

export function validEmail(value){
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value||""));
}

export function corsHeaders(request){
  const origin=request.headers.get("Origin")||"";
  const allowed=new Set([
    "https://fukuoka-ihinseiri-guide.com",
    "https://www.fukuoka-ihinseiri-guide.com"
  ]);
  return allowed.has(origin)?{
    "Access-Control-Allow-Origin":origin,
    "Vary":"Origin",
    "Access-Control-Allow-Methods":"GET,POST,OPTIONS",
    "Access-Control-Allow-Headers":"Content-Type",
    "Access-Control-Max-Age":"86400"
  }:{};
}

export function options(request){
  return new Response(null,{status:204,headers:corsHeaders(request)});
}

async function sha256(text){
  const bytes=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text));
  return [...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,"0")).join("");
}

export async function rateLimit(context,scope,limit=12,windowMs=15*60*1000){
  const db=requireDb(context.env);
  const ip=context.request.headers.get("CF-Connecting-IP")||"unknown";
  const salt=String(context.env.RATE_LIMIT_SALT||"fukuoka-ihinseiri");
  const key=await sha256(scope+"|"+salt+"|"+ip);
  const bucket=Math.floor(nowMs()/windowMs);
  const id=key+":"+bucket;
  await db.prepare(
    "INSERT INTO rate_limits (id, scope, count, bucket, updated_at) VALUES (?, ?, 1, ?, ?) ON CONFLICT(id) DO UPDATE SET count=count+1, updated_at=excluded.updated_at"
  ).bind(id,scope,bucket,nowMs()).run();
  const row=await db.prepare("SELECT count FROM rate_limits WHERE id=?").bind(id).first();
  return Number(row?.count||0)<=limit;
}
