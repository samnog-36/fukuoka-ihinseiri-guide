const DEFAULT_MANUS_SUBMIT = "https://fukuokaguide-afgvbgyb.manus.space/api/trpc/inquiry.submit";

function clean(value, max = 2000) {
  return String(value ?? "").trim().slice(0, max);
}

function validEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export async function onRequestPost(context) {
  let input;
  try {
    input = await context.request.json();
  } catch {
    return Response.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const data = {
    name: clean(input.name, 120),
    phone: clean(input.phone, 80),
    email: clean(input.email, 240),
    region: clean(input.region, 120),
    serviceType: clean(input.serviceType, 120),
    floorPlan: clean(input.floorPlan, 120) || undefined,
    budget: clean(input.budget, 120) || undefined,
    preferredTiming: clean(input.preferredTiming, 120) || undefined,
    details: clean(input.details, 5000)
  };

  if (!data.name || !data.phone || !validEmail(data.email) || !data.region || !data.serviceType || !data.details) {
    return Response.json({ ok: false, error: "validation_failed" }, { status: 400 });
  }

  const receivedAt = new Date().toISOString();
  const id = crypto.randomUUID();
  let stored = false;
  let forwarded = false;

  if (context.env.INQUIRIES_KV) {
    await context.env.INQUIRIES_KV.put(
      "inquiry:" + receivedAt + ":" + id,
      JSON.stringify({ id, receivedAt, status: "未対応", ...data })
    );
    stored = true;
  }

  const submitUrl = context.env.MANUS_SUBMIT_URL || DEFAULT_MANUS_SUBMIT;
  try {
    const res = await fetch(submitUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ json: data })
    });
    forwarded = res.ok;
  } catch {
    forwarded = false;
  }

  if (!stored && !forwarded) {
    return Response.json({ ok: false, error: "delivery_failed" }, { status: 502 });
  }

  return Response.json({ ok: true, stored, forwarded, id });
}
