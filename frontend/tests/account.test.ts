// Accounts in Next.js: the JWT stays in an HttpOnly cookie and is relayed as a bearer token.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "@/app/api/[...path]/route";
import { accountFromToken, bearer, clearSessionCookie, sessionCookie } from "@/lib/account";

const NOW = Date.parse("2026-10-25T12:00:00Z");

// An unsigned token with the claims Spring puts in (the signature is Spring's job).
function token(claims: object): string {
  const part = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${part({ alg: "HS256" })}.${part(claims)}.signature`;
}

const ADA = token({ sub: "7", email: "ada@example.org", exp: NOW / 1000 + 3600 });

describe("account from the token", () => {
  it("reads who is signed in", () => {
    expect(accountFromToken(ADA, NOW)).toEqual({ userId: 7, email: "ada@example.org", expiresAt: NOW + 3600_000 });
  });

  it("treats an expired, broken or missing token as signed out", () => {
    expect(accountFromToken(token({ sub: "7", email: "a@b.c", exp: NOW / 1000 - 1 }), NOW)).toBeNull();
    expect(accountFromToken("not-a-token", NOW)).toBeNull();
    expect(accountFromToken(undefined, NOW)).toBeNull();
  });

  it("builds the cookie and the header", () => {
    const cookie = sessionCookie("abc", NOW + 3600_000, true, NOW);
    expect(cookie).toContain("session=abc");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=Lax");
    expect(cookie).toContain("Max-Age=3600");
    expect(cookie).toContain("Secure");
    expect(sessionCookie("abc", NOW, false, NOW)).not.toContain("Secure");
    expect(clearSessionCookie()).toContain("Max-Age=0");
    expect(bearer("abc")).toEqual({ authorization: "Bearer abc" });
    expect(bearer(undefined)).toEqual({});
  });
});

describe("proxy", () => {
  const FRESH = token({ sub: "7", email: "ada@example.org", exp: Math.floor(Date.now() / 1000) + 3600 });
  const calls: { url: string; headers: Record<string, string> }[] = [];

  beforeEach(() => {
    calls.length = 0;
    vi.stubGlobal("fetch", async (url: string, init: RequestInit) => {
      calls.push({ url, headers: (init.headers ?? {}) as Record<string, string> });
      if (url.endsWith("/auth/login")) return Response.json({ token: FRESH, userId: 7 });
      return Response.json({ notions: [], status: "ok" });
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  function call(handler: typeof GET, method: string, path: string, cookie?: string) {
    const headers: Record<string, string> = { "content-type": "application/json" };
    if (cookie) headers.cookie = cookie;
    const body = method === "POST" ? JSON.stringify({ email: "ada@example.org", password: "correct horse" }) : undefined;
    const request = new Request(`http://localhost:3000/api/${path}`, { method, headers, body });
    return handler(request, { params: Promise.resolve({ path: path.split("/") }) });
  }

  it("relays the session cookie as a bearer token", async () => {
    await call(GET, "GET", "mastery", `lang=fr; session=${FRESH}`);
    expect(calls[0].headers.authorization).toBe(`Bearer ${FRESH}`);
  });

  it("sends no token when signed out", async () => {
    await call(GET, "GET", "mastery");
    expect(calls[0].headers.authorization).toBeUndefined();
  });

  it("login sets an HttpOnly cookie and never returns the token to the page", async () => {
    const response = await call(POST, "POST", "auth/login");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    const body = await response.json();
    expect(body).toEqual({ email: "ada@example.org" });
    expect(JSON.stringify(body)).not.toContain(FRESH);
  });

  it("logout clears the cookie without calling the API", async () => {
    const response = await call(POST, "POST", "auth/logout", `session=${FRESH}`);
    expect(response.status).toBe(204);
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
    expect(calls).toEqual([]);
  });
});
