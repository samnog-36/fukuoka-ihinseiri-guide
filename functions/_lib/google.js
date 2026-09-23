function b64url(input) {
  const bytes = typeof input === "string" ? new TextEncoder().encode(input) : new Uint8Array(input);
  let binary = "";
  bytes.forEach(b => binary += String.fromCharCode(b));
  return btoa(binary).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function pemBytes(pem) {
  const body = pem.replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\s/g, "");
  const raw = atob(body);
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}

export async function getGoogleAccessToken(serviceAccountJson) {
  const sa = typeof serviceAccountJson === "string" ? JSON.parse(serviceAccountJson) : serviceAccountJson;
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claims = b64url(JSON.stringify({
    iss: sa.client_email,
    scope: "https://www.googleapis.com/auth/webmasters.readonly",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600
  }));
  const signingInput = header + "." + claims;
  const key = await crypto.subtle.importKey(
    "pkcs8",
    pemBytes(sa.private_key),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(signingInput)
  );
  const assertion = signingInput + "." + b64url(signature);

  const body = new URLSearchParams({
    grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
    assertion
  });
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body
  });
  if (!res.ok) throw new Error("google_token_failed:" + res.status);
  return (await res.json()).access_token;
}

function fmtDate(d) {
  return d.toISOString().slice(0, 10);
}

function addDays(date, days) {
  const d = new Date(date);
  d.setUTCDate(d.getUTCDate() + days);
  return d;
}

async function query(token, siteUrl, body) {
  const url = "https://searchconsole.googleapis.com/webmasters/v3/sites/" +
    encodeURIComponent(siteUrl) + "/searchAnalytics/query";
  const res = await fetch(url, {
    method: "POST",
    headers: { authorization: "Bearer " + token, "content-type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error("search_console_query_failed:" + res.status + ":" + await res.text());
  return await res.json();
}

function oneRow(result) {
  const r = (result.rows || [])[0] || {};
  return {
    clicks: Number(r.clicks || 0),
    impressions: Number(r.impressions || 0),
    ctr: Number(r.ctr || 0),
    position: Number(r.position || 0)
  };
}

export async function getSearchConsoleDashboard(env) {
  if (!env.GOOGLE_SERVICE_ACCOUNT_JSON || !env.SEARCH_CONSOLE_SITE_URL) {
    return { configured: false };
  }
  const token = await getGoogleAccessToken(env.GOOGLE_SERVICE_ACCOUNT_JSON);
  const end = addDays(new Date(), -2);
  const currentStart = addDays(end, -27);
  const previousEnd = addDays(currentStart, -1);
  const previousStart = addDays(previousEnd, -27);
  const trendStart = addDays(end, -89);

  const currentBody = { startDate: fmtDate(currentStart), endDate: fmtDate(end), dataState: "final" };
  const previousBody = { startDate: fmtDate(previousStart), endDate: fmtDate(previousEnd), dataState: "final" };

  const [current, previous, trend, pages, previousPages, queries, previousQueries, queryPages] = await Promise.all([
    query(token, env.SEARCH_CONSOLE_SITE_URL, currentBody),
    query(token, env.SEARCH_CONSOLE_SITE_URL, previousBody),
    query(token, env.SEARCH_CONSOLE_SITE_URL, { ...currentBody, startDate: fmtDate(trendStart), dimensions: ["date"], rowLimit: 1000 }),
    query(token, env.SEARCH_CONSOLE_SITE_URL, { ...currentBody, dimensions: ["page"], rowLimit: 20 }),
    query(token, env.SEARCH_CONSOLE_SITE_URL, { ...previousBody, dimensions: ["page"], rowLimit: 250 }),
    query(token, env.SEARCH_CONSOLE_SITE_URL, { ...currentBody, dimensions: ["query"], rowLimit: 30 }),
    query(token, env.SEARCH_CONSOLE_SITE_URL, { ...previousBody, dimensions: ["query"], rowLimit: 250 }),
    query(token, env.SEARCH_CONSOLE_SITE_URL, { ...currentBody, dimensions: ["query", "page"], rowLimit: 250 })
  ]);

  const metric = r => ({
    clicks: Number(r?.clicks || 0),
    impressions: Number(r?.impressions || 0),
    ctr: Number(r?.ctr || 0),
    position: Number(r?.position || 0)
  });
  const previousPageMap = new Map((previousPages.rows || []).map(r => [r.keys?.[0] || "", metric(r)]));
  const previousQueryMap = new Map((previousQueries.rows || []).map(r => [r.keys?.[0] || "", metric(r)]));
  const queryPageMap = new Map();
  for (const r of queryPages.rows || []) {
    const q = r.keys?.[0] || "";
    if (q && !queryPageMap.has(q)) queryPageMap.set(q, r.keys?.[1] || "");
  }

  return {
    configured: true,
    ranges: {
      current: [fmtDate(currentStart), fmtDate(end)],
      previous: [fmtDate(previousStart), fmtDate(previousEnd)]
    },
    current: oneRow(current),
    previous: oneRow(previous),
    trend: (trend.rows || []).map(r => ({
      date: r.keys?.[0] || "",
      clicks: Number(r.clicks || 0),
      impressions: Number(r.impressions || 0),
      ctr: Number(r.ctr || 0),
      position: Number(r.position || 0)
    })),
    topPages: (pages.rows || []).map(r => {
      const page = r.keys?.[0] || "";
      return {
        page,
        ...metric(r),
        previous: previousPageMap.get(page) || { clicks: 0, impressions: 0, ctr: 0, position: 0 }
      };
    }),
    topQueries: (queries.rows || []).map(r => {
      const queryText = r.keys?.[0] || "";
      return {
        query: queryText,
        page: queryPageMap.get(queryText) || "",
        ...metric(r),
        previous: previousQueryMap.get(queryText) || { clicks: 0, impressions: 0, ctr: 0, position: 0 }
      };
    })
  };
}
