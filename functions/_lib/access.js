function base64UrlToBytes(value) {
  let s = value.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const raw = atob(s);
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}

function decodePart(value) {
  return JSON.parse(new TextDecoder().decode(base64UrlToBytes(value)));
}

function normalizeDomain(value) {
  if (!value) return "";
  const v = value.replace(/\/+$/, "");
  return v.startsWith("https://") ? v : "https://" + v;
}

export async function verifyAdminRequest(request, env) {
  const expectedEmail = String(env.ADMIN_EMAIL || "").toLowerCase();
  const teamDomain = normalizeDomain(env.CF_ACCESS_TEAM_DOMAIN);
  const expectedAud = String(env.CF_ACCESS_AUD || "");

  if (!expectedEmail || !teamDomain || !expectedAud) {
    return { ok: false, status: 503, reason: "admin_auth_not_configured" };
  }

  const token = request.headers.get("Cf-Access-Jwt-Assertion");
  if (!token) return { ok: false, status: 401, reason: "missing_access_jwt" };

  const parts = token.split(".");
  if (parts.length !== 3) return { ok: false, status: 401, reason: "invalid_jwt" };

  let header, payload;
  try {
    header = decodePart(parts[0]);
    payload = decodePart(parts[1]);
  } catch {
    return { ok: false, status: 401, reason: "invalid_jwt_payload" };
  }

  const now = Math.floor(Date.now() / 1000);
  const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  const issuer = String(payload.iss || "").replace(/\/+$/, "");
  if (!aud.includes(expectedAud)) return { ok: false, status: 403, reason: "wrong_audience" };
  if (issuer !== teamDomain) return { ok: false, status: 403, reason: "wrong_issuer" };
  if (payload.exp && payload.exp < now) return { ok: false, status: 401, reason: "expired" };
  if (payload.nbf && payload.nbf > now) return { ok: false, status: 401, reason: "not_yet_valid" };
  if (String(payload.email || "").toLowerCase() !== expectedEmail) {
    return { ok: false, status: 403, reason: "email_not_allowed" };
  }

  const certRes = await fetch(teamDomain + "/cdn-cgi/access/certs", { cf: { cacheTtl: 3600 } });
  if (!certRes.ok) return { ok: false, status: 503, reason: "cert_fetch_failed" };
  const certs = await certRes.json();
  const jwk = (certs.keys || []).find(k => k.kid === header.kid);
  if (!jwk) return { ok: false, status: 401, reason: "signing_key_not_found" };

  const key = await crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"]
  );
  const signed = new TextEncoder().encode(parts[0] + "." + parts[1]);
  const signature = base64UrlToBytes(parts[2]);
  const valid = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, signature, signed);
  if (!valid) return { ok: false, status: 401, reason: "bad_signature" };

  return { ok: true, email: expectedEmail, payload };
}

export async function requireAdmin(request, env) {
  const result = await verifyAdminRequest(request, env);
  if (result.ok) return null;
  return new Response(JSON.stringify({ ok: false, error: result.reason }), {
    status: result.status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  });
}
