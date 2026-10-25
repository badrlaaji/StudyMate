// Public demo: every /api/* route answers from demo/data.json, and nothing leaves the server.
import net from "node:net";
import { readFileSync } from "node:fs";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import data from "@/demo/data.json";
import { DELETE, GET, POST } from "@/app/api/[...path]/route";
import { getCourses, getMastery, getNotions, getPlan } from "@/lib/api";
import {
  addScore,
  chat,
  findCourse,
  level,
  mastery,
  normalize,
  notionScores,
  pickQuiz,
  plan,
  readCookie,
  readScores,
  scoresCookie,
  SCORES_COOKIE,
  type Scores,
} from "@/lib/demo";

// Server components read the cookie with next/headers: no request scope in a unit test.
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));

const course = findCourse("data-science")!;
const stored = course.answers.find((a) => a.response.status === "ok")!;
const example = course.feynman[0];
const outgoing: string[] = [];

// Trap both fetch and raw sockets: any outgoing request is recorded, then fails the test.
beforeEach(() => {
  process.env.DEMO_MODE = "1";
  outgoing.length = 0;
  vi.stubGlobal("fetch", async (url: unknown) => {
    outgoing.push(`fetch ${String(url)}`);
    throw new Error("network is forbidden in demo mode");
  });
  vi.spyOn(net.Socket.prototype, "connect").mockImplementation(function (this: net.Socket, ...args: unknown[]) {
    outgoing.push(`socket ${JSON.stringify(args[0])}`);
    throw new Error("network is forbidden in demo mode");
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete process.env.DEMO_MODE;
  expect(outgoing).toEqual([]);
});

type Handler = typeof GET;
type Options = { body?: unknown; cookie?: string; query?: string };

function call(handler: Handler, method: string, path: string, { body, cookie, query = "" }: Options = {}) {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (cookie) headers.cookie = cookie;
  const request = new Request(`http://localhost:3000/api/${path}${query}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return handler(request, { params: Promise.resolve({ path: path.split("/") }) });
}

// "demo_scores=...; Path=/..." -> the "demo_scores=..." part, as the browser sends it back.
function cookieFrom(response: Response): string {
  return (response.headers.get("set-cookie") ?? "").split(";")[0];
}

describe("demo routes, without network", () => {
  it("the trap works: outside the demo, the proxy does call the API", async () => {
    delete process.env.DEMO_MODE;
    expect((await call(GET, "GET", "health")).status).toBe(502);
    expect(outgoing).toEqual(["fetch http://localhost:8000/health"]);
    outgoing.length = 0; // expected here, so it must not fail the check after the test
  });

  it("answers the read routes", async () => {
    const health = await (await call(GET, "GET", "health")).json();
    expect(health.demo).toBe(true);
    const courses = await (await call(GET, "GET", "courses", { query: "?lang=fr" })).json();
    expect(courses.map((c: { id: string }) => c.id)).toEqual(data.courses.map((c) => c.id));
    expect(courses[0].scope).toBe(data.courses[0].scope_fr);
    const notions = await (await call(GET, "GET", "notions", { query: "?lang=fr&course=data-science" })).json();
    expect(notions[0].name).toBe(course.notions[0].name_fr);
    expect((await call(GET, "GET", "mastery")).status).toBe(200);
    expect((await call(GET, "GET", "plan")).status).toBe(200);
    expect((await (await call(GET, "GET", "review")).json()).status).toBe("demo"); // FSRS: full version
  });

  it("serves a stored answer with its verified citations", async () => {
    const response = await call(POST, "POST", "chat", { body: { message: stored.question, course: "data-science" } });
    const reply = await response.json();
    expect(reply.status).toBe("ok");
    expect(reply.citations.length).toBeGreaterThan(0);
  });

  it("refuses the write routes and has no local PDF", async () => {
    expect((await call(POST, "POST", "uploads")).status).toBe(403);
    expect((await call(DELETE, "DELETE", "courses/data-science")).status).toBe(403);
    expect((await call(GET, "GET", "book.pdf")).status).toBe(404);
    expect((await call(GET, "GET", "secret")).status).toBe(404); // still the allow-list
  });

  it("grades the example explanation and keeps the score in a cookie", async () => {
    const body = { notion_id: example.notion_id, explanation: example.explanation, lang: example.lang };
    const response = await call(POST, "POST", "feynman", { body });
    expect((await response.json()).score).toBe(example.result.score);
    expect(readScores(readCookie(cookieFrom(response), SCORES_COOKIE))).toEqual({
      "data-science": { [example.notion_id]: [example.result.score] },
    });
    const other = await call(POST, "POST", "feynman", { body: { ...body, explanation: "Something else entirely here." } });
    expect(other.status).toBe(400);
  });

  it("closes the loop: quiz result -> cookie -> weak notion in the plan and first in the next quiz", async () => {
    const question = course.quiz.en[0];
    const wrong = (question.answer_index + 1) % 4;
    const answers = [{ notion_id: question.notion_id, answer_index: question.answer_index, chosen_index: wrong }];
    const result = await call(POST, "POST", "quiz/result", { body: { answers, course: "data-science" } });
    expect((await result.json()).scores).toEqual({ [question.notion_id]: 0 });
    const cookie = cookieFrom(result);
    const planned = await (await call(GET, "GET", "plan", { cookie, query: "?course=data-science" })).json();
    expect(planned.plan[0].notion_id).toBe(question.notion_id);
    const quiz = await (await call(POST, "POST", "quiz", { cookie, body: { n: 3, lang: "en", course: "data-science" } })).json();
    expect(quiz.questions[0].notion_id).toBe(question.notion_id);
  });

  it("feeds the server pages through the same data", async () => {
    expect((await getCourses("en")).length).toBe(data.courses.length);
    expect((await getNotions("en", "statistics")).length).toBe(findCourse("statistics")!.notions.length);
    expect((await getMastery("data-science")).status).toBe("ok");
    expect((await getPlan("en", "data-science")).plan).toEqual([]);
  });
});

describe("demo chat", () => {
  it("matches a question without case or final punctuation", () => {
    expect(normalize("  What IS  this ?")).toBe("what is this");
    expect(chat({}, course, stored.question.toUpperCase() + " ?", "en")).toBe(stored.response);
  });

  it("routes quiz and plan requests with the router rules", () => {
    expect(chat({}, course, "Quiz me on my weak spots", "en").route).toBe("quiz");
    expect(chat({}, course, "Que dois-je réviser ?", "fr").route).toBe("plan");
  });

  it("says demo_only for any other question", () => {
    const reply = chat({}, course, "Explain transformers to me", "en");
    expect(reply.status).toBe("demo_only");
    expect(reply.citations).toEqual([]);
  });
});

describe("mastery rules (same as Spring)", () => {
  it("keeps the last 3 scores, newest first", () => {
    let scores: Scores = {};
    for (const score of [0, 1, 1, 5]) scores = addScore(scores, "c", "n", score);
    expect(scores.c.n).toEqual([5, 1, 1]);
    expect(mastery(scores, "c")).toEqual([{ notionId: "n", average: 2.33, count: 3, level: "WEAK" }]);
  });

  it("uses the thresholds weak < 3, mastered >= 4", () => {
    expect([level(2.99), level(3), level(3.99), level(4)]).toEqual(["WEAK", "LEARNING", "LEARNING", "MASTERED"]);
  });

  it("grades a quiz per notion, rounding halves up", () => {
    const answer = (notion_id: string, ok: boolean) => ({ notion_id, answer_index: 0, chosen_index: ok ? 0 : 1 });
    const scores = notionScores([answer("a", true), answer("a", false), answer("b", true), answer("b", true), answer("b", false)]);
    expect(scores).toEqual({ a: 3, b: 3 }); // 2.5 -> 3, 3.33 -> 3
  });

  it("plans the weak notions only, weakest first, with localized names", () => {
    const [first, second, third] = course.notions;
    let scores: Scores = {};
    scores = addScore(scores, course.id, first.id, 2);
    scores = addScore(scores, course.id, second.id, 1);
    scores = addScore(scores, course.id, third.id, 5);
    const rows = plan(scores, course, "fr");
    expect(rows.map((r) => r.notion_id)).toEqual([second.id, first.id]);
    expect(rows[0].name).toBe(second.name_fr);
  });

  it("picks at most 5 questions, the weak notion first", () => {
    const weakId = course.quiz.en[5].notion_id;
    const scores = addScore({}, course.id, weakId, 0);
    const picked = pickQuiz(scores, course, 9, "en", () => 0.5);
    expect(picked.length).toBe(5);
    expect(picked[0].notion_id).toBe(weakId);
  });

  it("ignores an unreadable cookie", () => {
    expect(readScores("not json")).toEqual({});
    expect(readScores(undefined)).toEqual({});
    const value = readCookie(scoresCookie({ c: { n: [4] } }).split(";")[0], SCORES_COOKIE);
    expect(readScores(value)).toEqual({ c: { n: [4] } });
  });
});

describe("no key on the demo side", () => {
  it("has no secret in the demo data", () => {
    const text = JSON.stringify(data);
    for (const pattern of [/AIza[0-9A-Za-z_-]{20,}/, /\bhf_[A-Za-z0-9]{20,}/, /\bsk-[A-Za-z0-9]{20,}/, /postgres(ql)?(\+\w+)?:\/\//, /API_KEY/]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it("reads no environment variable but DEMO_MODE", () => {
    const source = readFileSync(new URL("../lib/demo.ts", import.meta.url), "utf-8");
    expect([...source.matchAll(/process\.env\.(\w+)/g)].map((m) => m[1])).toEqual(["DEMO_MODE"]);
  });
});
