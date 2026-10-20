// The browser only talks to these /api/* routes; they forward to FastAPI (server side).
const API_URL = process.env.API_URL ?? "http://localhost:8000";
const ALLOWED = new Set([
  "health",
  "courses",
  "chat",
  "notions",
  "feynman",
  "quiz",
  "quiz/result",
  "mastery",
  "plan",
  "book.pdf",
]);

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: Request, context: Context): Promise<Response> {
  const { path } = await context.params;
  const target = path.join("/");
  if (!ALLOWED.has(target)) {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }
  const search = new URL(request.url).search;
  const init: RequestInit = { method: request.method, cache: "no-store" };
  if (request.method === "POST") {
    init.body = await request.text();
    init.headers = { "content-type": "application/json" };
  }
  try {
    const response = await fetch(`${API_URL}/${target}${search}`, init);
    const type = response.headers.get("content-type") ?? "application/json";
    return new Response(response.body, { status: response.status, headers: { "content-type": type } });
  } catch {
    return Response.json({ detail: "API unavailable" }, { status: 502 });
  }
}

export const GET = forward;
export const POST = forward;
