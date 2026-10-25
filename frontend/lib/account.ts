// Accounts: the JWT signed by Spring lives in an HttpOnly cookie that page scripts cannot read.
// Next.js turns it into "Authorization: Bearer <token>" for FastAPI, which relays it to Spring.
export const SESSION_COOKIE = "session";

export type Account = { userId: number; email: string; expiresAt: number };

// Who is signed in, for display only: Spring checks the signature on every data request.
export function accountFromToken(token: string | undefined, now = Date.now()): Account | null {
  try {
    const payload = JSON.parse(Buffer.from((token ?? "").split(".")[1] ?? "", "base64url").toString("utf-8"));
    const expiresAt = Number(payload.exp) * 1000;
    if (!payload.sub || !payload.email || !(expiresAt > now)) return null;
    return { userId: Number(payload.sub), email: String(payload.email), expiresAt };
  } catch {
    return null;
  }
}

export function bearer(token: string | undefined): Record<string, string> {
  return token ? { authorization: `Bearer ${token}` } : {};
}

// Set-Cookie for the token (HttpOnly, SameSite=Lax); Secure when the site is served over HTTPS.
export function sessionCookie(token: string, expiresAt: number, secure: boolean, now = Date.now()): string {
  const maxAge = Math.max(0, Math.floor((expiresAt - now) / 1000));
  return `${SESSION_COOKIE}=${token}; Path=/; Max-Age=${maxAge}; HttpOnly; SameSite=Lax${secure ? "; Secure" : ""}`;
}

export function clearSessionCookie(): string {
  return `${SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`;
}
