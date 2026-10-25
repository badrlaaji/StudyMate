// The browser only talks to these /api/* routes; they forward to FastAPI (server side).
// Public demo (DEMO_MODE=1): answered here from the demo data, nothing leaves the server.
import { demoReply, isDemo, readCookie, SCORES_COOKIE } from "@/lib/demo";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const ALLOWED = [
  /^(health|courses|chat|notions|feynman|quiz|quiz\/result|mastery|plan|book\.pdf|uploads)$/,
  /^courses\/[a-z0-9-]+(\/(status|retry))?$/, // status, retry and delete of a course
];

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: Request, context: Context): Promise<Response> {
  const { path } = await context.params;
  const target = path.join("/");
  if (!ALLOWED.some((rule) => rule.test(target))) {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }
  if (isDemo()) return demo(request, target);
  const search = new URL(request.url).search;
  const init: RequestInit = { method: request.method, cache: "no-store" };
  if (request.method === "POST") {
    // JSON for most calls, the raw PDF bytes for /uploads.
    init.body = await request.arrayBuffer();
    init.headers = { "content-type": request.headers.get("content-type") ?? "application/json" };
  }
  try {
    const response = await fetch(`${API_URL}/${target}${search}`, init);
    const type = response.headers.get("content-type") ?? "application/json";
    const body = response.status === 204 ? null : response.body;
    return new Response(body, { status: response.status, headers: { "content-type": type } });
  } catch {
    return Response.json({ detail: "API unavailable" }, { status: 502 });
  }
}

async function demo(request: Request, target: string): Promise<Response> {
  const body = request.method === "POST" ? await request.json().catch(() => null) : null;
  const cookie = readCookie(request.headers.get("cookie"), SCORES_COOKIE);
  const reply = demoReply(request.method, target, new URL(request.url).searchParams, body, cookie);
  const headers = reply.cookie ? { "set-cookie": reply.cookie } : undefined;
  return Response.json(reply.body, { status: reply.status, headers });
}

export const GET = forward;
export const POST = forward;
export const DELETE = forward;
