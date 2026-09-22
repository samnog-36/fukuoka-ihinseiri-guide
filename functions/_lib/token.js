export async function hashToken(token){
  const bytes=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(String(token)));
  return [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,"0")).join("");
}
export function newSetupToken(){
  const bytes=crypto.getRandomValues(new Uint8Array(24));
  return [...bytes].map(b=>b.toString(16).padStart(2,"0")).join("");
}
