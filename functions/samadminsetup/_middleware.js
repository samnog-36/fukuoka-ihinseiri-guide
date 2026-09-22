import { requireAdmin } from "../_lib/access.js";

export async function onRequest(context) {
  const denied = await requireAdmin(context.request, context.env);
  if (denied) return denied;
  return context.next();
}
