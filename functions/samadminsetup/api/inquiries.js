async function fromKv(env) {
  const listed = await env.INQUIRIES_KV.list({ prefix: "inquiry:", limit: 100 });
  const rows = [];
  for (const key of listed.keys || []) {
    const value = await env.INQUIRIES_KV.get(key.name, "json");
    if (value) rows.push(value);
  }
  rows.sort((a,b) => String(b.receivedAt || "").localeCompare(String(a.receivedAt || "")));
  return rows;
}

async function fromLegacy(env) {
  if (!env.MANUS_INQUIRIES_LIST_URL) return null;
  const headers = { "accept": "application/json" };
  if (env.MANUS_ADMIN_BEARER_TOKEN) {
    headers.authorization = "Bearer " + env.MANUS_ADMIN_BEARER_TOKEN;
  }
  const res = await fetch(env.MANUS_INQUIRIES_LIST_URL, { headers });
  if (!res.ok) throw new Error("legacy_inquiry_list_failed:" + res.status);
  return await res.json();
}

export async function onRequestGet(context) {
  const { env } = context;
  try {
    if (env.INQUIRIES_KV) {
      const rows = await fromKv(env);
      return Response.json({ connected: true, source: "cloudflare_kv", inquiries: rows });
    }
    const legacy = await fromLegacy(env);
    if (legacy !== null) {
      return Response.json({ connected: true, source: "legacy_manus", inquiries: legacy });
    }
    return Response.json({
      connected: false,
      source: "legacy_manus_submit_only",
      inquiries: [],
      message: "問い合わせ送信先は確認済みですが、旧Manus DBの一覧取得APIは未接続です。"
    });
  } catch (error) {
    return Response.json({ connected: false, inquiries: [], error: String(error) }, { status: 502 });
  }
}
