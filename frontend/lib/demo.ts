// Public demo (DEMO_MODE=1): Next.js answers by itself from demo/data.json.
// The answers were computed once by scripts/build_demo.py with the real pipeline.
// No FastAPI, no database, no LLM call, no key: scores stay in a browser cookie.
import data from "@/demo/data.json";
import { addDays, CODES, currentStreak, earned, isFlawless, localDay, validZone, type Days } from "@/lib/trophies";

export const SCORES_COOKIE = "demo_scores";
export const STUDY_COOKIE = "demo_study";
const SLACK_S = 2; // same tolerance as Spring between two updates
const KEEP_DAYS = 60; // older days are dropped (cookie size)
const ONE_YEAR_S = 31536000;
// Same mastery rules as Spring (core/MasteryService.java).
const LAST_SCORES = 3;
const WEAK_BELOW = 3;
const MASTERED_FROM = 4;
const PLAN_SIZE = 5;
const MAX_QUIZ = 5;
// Same fallback rules as the router (agent/router.py).
const QUIZ_RULE = /\b(quiz+|qcm|test me|teste-moi|interroge-moi)\b/i;
const PLAN_RULE =
  /\b(plan de révision|study plan|revision plan|what should i (review|study)|quoi réviser|que dois-je réviser|weak topics|notions faibles)\b/i;
const READ_ONLY = "The public demo is read-only: install StudyMate locally to add a course or an account.";

type Lang = "en" | "fr";
type DemoCourse = (typeof data)["courses"][number];
type QuizQuestion = DemoCourse["quiz"]["en"][number];
type Answer = { notion_id: string; answer_index: number; chosen_index: number | null }; // null = skipped
// course -> notion -> last scores, newest first
export type Scores = Record<string, Record<string, number[]>>;
export type Mastery = { notionId: string; average: number; count: number; level: string };
export type DemoReply = { status: number; body: unknown; cookies: string[] };
// Presence mode in the demo: the estimated study time stays in this browser.
export type Study = {
  goal: { minutes: number; timezone: string };
  days: Days;
  session: { id: number; startedAt: number; endedAt: number; active: number } | null;
  trophies: Record<string, string>; // code -> ISO date
  flawless: boolean;
};
const NEW_STUDY: Study = { goal: { minutes: 30, timezone: "UTC" }, days: {}, session: null, trophies: {}, flawless: false };

export function isDemo(): boolean {
  return process.env.DEMO_MODE === "1";
}

function toLang(value: unknown): Lang {
  return value === "fr" ? "fr" : "en";
}

// The course asked for, else the default one (null if the id is unknown).
export function findCourse(id?: string | null): DemoCourse | null {
  const wanted = id || data.default;
  return data.courses.find((course) => course.id === wanted) ?? null;
}

// Compare questions without case, extra spaces or final punctuation.
export function normalize(text: string): string {
  return text.toLowerCase().replace(/\s+/g, " ").replace(/[\s?!.]+$/, "").trim();
}

// One cookie value from a Cookie header ("a=1; b=2").
export function readCookie(header: string | null, name: string): string | undefined {
  for (const part of (header ?? "").split(";")) {
    const [key, ...value] = part.trim().split("=");
    if (key === name) return value.join("=");
  }
  return undefined;
}

// Scores from the cookie; anything unreadable counts as no score.
export function readScores(value: string | undefined): Scores {
  try {
    const scores = JSON.parse(decodeURIComponent(value ?? ""));
    return scores && typeof scores === "object" && !Array.isArray(scores) ? scores : {};
  } catch {
    return {};
  }
}

export function scoresCookie(scores: Scores): string {
  const value = encodeURIComponent(JSON.stringify(scores));
  return `${SCORES_COOKIE}=${value}; Path=/; Max-Age=${ONE_YEAR_S}; SameSite=Lax; HttpOnly`;
}

export function readStudy(value: string | undefined): Study {
  try {
    const study = JSON.parse(decodeURIComponent(value ?? ""));
    return study && typeof study === "object" && study.goal && study.days ? { ...NEW_STUDY, ...study } : NEW_STUDY;
  } catch {
    return NEW_STUDY;
  }
}

export function studyCookie(study: Study): string {
  const days = Object.fromEntries(Object.entries(study.days).sort().slice(-KEEP_DAYS));
  const value = encodeURIComponent(JSON.stringify({ ...study, days }));
  return `${STUDY_COOKIE}=${value}; Path=/; Max-Age=${ONE_YEAR_S}; SameSite=Lax; HttpOnly`;
}

// Save the trophies newly deserved; return the study state and their codes.
export function award(study: Study, now: number): { study: Study; fresh: string[] } {
  const fresh = earned(study.days, study.goal.minutes, study.flawless).filter((code) => !study.trophies[code]);
  const trophies = { ...study.trophies, ...Object.fromEntries(fresh.map((code) => [code, new Date(now).toISOString()])) };
  return { study: { ...study, trophies }, fresh };
}

// Same answer as Spring's GET /api/study/summary.
export function studySummary(study: Study, now: number) {
  const { minutes, timezone } = study.goal;
  const goalSeconds = minutes * 60;
  const today = localDay(now, timezone);
  const week = Array.from({ length: 7 }, (_, i) => addDays(today, i - 6)).map((date) => {
    const seconds = study.days[date] ?? 0;
    return { date, seconds, reached: seconds >= goalSeconds };
  });
  const todaySeconds = study.days[today] ?? 0;
  return {
    goalMinutes: minutes,
    timezone,
    todaySeconds,
    goalReachedToday: todaySeconds >= goalSeconds,
    streakDays: currentStreak(study.days, goalSeconds, today),
    totalSeconds: Object.values(study.days).reduce((a, b) => a + b, 0),
    week,
  };
}

// PATCH a session: same checks as Spring (never down, never faster than real time).
function updateSession(study: Study, id: number, total: number, now: number): DemoReply {
  const session = study.session;
  if (!session || session.id !== id) return json({ detail: "No such session." }, 404);
  const added = total - session.active;
  const elapsed = Math.floor((now - session.endedAt) / 1000);
  if (!Number.isInteger(total) || added < 0) return json({ detail: "Active time cannot go down." }, 400);
  if (added > elapsed + SLACK_S) return json({ detail: `Added ${added} s but only ${elapsed} s passed.` }, 400);
  const day = localDay(session.startedAt, study.goal.timezone); // counted on the day it started
  const days = { ...study.days, [day]: (study.days[day] ?? 0) + added };
  const updated = { ...study, days, session: { ...session, active: total, endedAt: now } };
  const { study: saved, fresh } = award(updated, now);
  const view = { id, mode: "MANUAL", startedAt: new Date(session.startedAt).toISOString(), activeSeconds: total, newTrophies: fresh };
  return json(view, 200, [studyCookie(saved)]);
}

function studyReply(method: string, path: string, body: any, study: Study, course: string, now: number): DemoReply | null {
  if (path === "study/sessions" && method === "POST") {
    const session = { id: now, startedAt: now, endedAt: now, active: 0 };
    const view = { id: now, courseId: course, mode: body?.mode ?? "MANUAL", startedAt: new Date(now).toISOString(), activeSeconds: 0, newTrophies: [] };
    return json(view, 201, [studyCookie({ ...study, session })]);
  }
  const match = path.match(/^study\/sessions\/(\d+)$/);
  if (match && method === "PATCH") return updateSession(study, Number(match[1]), Number(body?.active_seconds), now);
  if (path === "study/goal" && method === "PUT") {
    const minutes = Number(body?.minutes);
    const timezone = String(body?.timezone ?? "");
    if (!Number.isInteger(minutes) || minutes < 5 || minutes > 480 || !validZone(timezone)) {
      return json({ detail: "The goal is 5 to 480 minutes, in a known time zone." }, 400);
    }
    const { study: saved } = award({ ...study, goal: { minutes, timezone } }, now);
    return json({ minutes, timezone }, 200, [studyCookie(saved)]);
  }
  if (path === "study/summary") return json(studySummary(study, now));
  if (path === "trophies") return json(CODES.map((code) => ({ code, obtainedAt: study.trophies[code] ?? null })));
  return null;
}

// Add a 0-5 score; only the last 3 are kept (all the mastery rule reads).
export function addScore(scores: Scores, course: string, notionId: string, score: number): Scores {
  const notions = scores[course] ?? {};
  const last = [score, ...(notions[notionId] ?? [])].slice(0, LAST_SCORES);
  return { ...scores, [course]: { ...notions, [notionId]: last } };
}

export function level(average: number): string {
  if (average < WEAK_BELOW) return "WEAK";
  return average >= MASTERED_FROM ? "MASTERED" : "LEARNING";
}

// Mastery of every scored notion of a course, weakest first.
export function mastery(scores: Scores, course: string): Mastery[] {
  return Object.entries(scores[course] ?? {})
    .filter(([, last]) => Array.isArray(last) && last.length > 0)
    .map(([notionId, last]) => {
      const average = Math.round((last.reduce((a, b) => a + b, 0) / last.length) * 100) / 100;
      return { notionId, average, count: last.length, level: level(average) };
    })
    .sort((a, b) => a.average - b.average);
}

// Revision plan without LLM: weak notions first, with pages to re-read.
export function plan(scores: Scores, course: DemoCourse, lang: Lang) {
  const byId = new Map(course.notions.map((notion) => [notion.id, notion]));
  return mastery(scores, course.id)
    .filter((m) => m.level === "WEAK" && byId.has(m.notionId))
    .slice(0, PLAN_SIZE)
    .map((m) => {
      const notion = byId.get(m.notionId)!;
      const name = lang === "fr" ? notion.name_fr : notion.name_en;
      return { notion_id: notion.id, name, score: m.average, pages: notion.pages, action: "quiz" };
    });
}

// Grade by code: per notion, round half up of 5 x correct / asked.
export function notionScores(answers: Answer[]): Record<string, number> {
  const asked: Record<string, number> = {};
  const correct: Record<string, number> = {};
  for (const answer of answers) {
    if (answer.chosen_index === null || answer.chosen_index === undefined) continue; // skipped: not graded
    asked[answer.notion_id] = (asked[answer.notion_id] ?? 0) + 1;
    correct[answer.notion_id] = (correct[answer.notion_id] ?? 0) + Number(answer.chosen_index === answer.answer_index);
  }
  return Object.fromEntries(Object.keys(asked).map((id) => [id, Math.floor((5 * correct[id]) / asked[id] + 0.5)]));
}

// Questions of weak notions first, the others in random order.
export function pickQuiz(scores: Scores, course: DemoCourse, n: number, lang: Lang, random = Math.random): QuizQuestion[] {
  const weak = mastery(scores, course.id)
    .filter((m) => m.level === "WEAK")
    .map((m) => m.notionId);
  const pool = course.quiz[lang]
    .map((question) => ({ question, key: random() }))
    .sort((a, b) => a.key - b.key)
    .map((item) => item.question);
  const rank = (q: QuizQuestion) => (weak.includes(q.notion_id) ? weak.indexOf(q.notion_id) : weak.length);
  return pool.sort((a, b) => rank(a) - rank(b)).slice(0, Math.min(Math.max(n, 1), MAX_QUIZ));
}

// A stored answer, else the router rules (quiz, plan), else "demo_only".
export function chat(scores: Scores, course: DemoCourse, message: string, lang: Lang) {
  const stored = course.answers.find((item) => normalize(item.question) === normalize(message));
  if (stored) return stored.response;
  const base = { course: course.id, lang, answer: null, citations: [], quiz: null, plan: null };
  if (QUIZ_RULE.test(message)) return { ...base, route: "quiz", status: "ok", quiz: pickQuiz(scores, course, 3, lang) };
  if (PLAN_RULE.test(message)) return { ...base, route: "plan", status: "ok", plan: plan(scores, course, lang) };
  return { ...base, route: "answer", status: "demo_only" };
}

// The example questions and explanations offered by the demo pages.
export function demoPrompts(course: string, lang: Lang): string[] {
  const answers = findCourse(course)?.answers ?? [];
  return [...answers.filter((a) => a.lang === lang), ...answers.filter((a) => a.lang !== lang)].map((a) => a.question);
}

export function demoExplanations(course: string) {
  return (findCourse(course)?.feynman ?? []).map(({ notion_id, lang, explanation }) => ({ notion_id, lang, explanation }));
}

function courseRow(course: DemoCourse, lang: Lang) {
  return {
    id: course.id,
    title: course.title,
    scope: lang === "fr" ? course.scope_fr : course.scope_en,
    book_lang: course.book_lang,
    license: course.license,
    attribution: course.attribution,
    book_url: course.book_url,
    pdf_url: course.pdf_url,
    default: course.id === data.default,
    pdf: false, // the demo has no local PDF: the reader links to the book online
    chunks: course.chunks,
    notions: course.notions.length,
    validated: true,
    uploaded: false,
    job: null,
    job_detail: "",
  };
}

function notionRow(notion: DemoCourse["notions"][number], lang: Lang) {
  return {
    id: notion.id,
    name: lang === "fr" ? notion.name_fr : notion.name_en,
    chapter: notion.chapter,
    section: notion.section,
    pages: notion.pages,
    key_ideas: notion.key_ideas.map((idea) => (lang === "fr" ? idea.fr : idea.en)),
  };
}

function json(body: unknown, status = 200, cookies: string[] = []): DemoReply {
  return { status, body, cookies };
}

export type DemoCookies = { scores?: string; study?: string };

// The whole /api/* contract, answered from the demo data (no network).
export function demoReply(
  method: string,
  path: string,
  query: URLSearchParams,
  body: any,
  cookies: DemoCookies = {},
  now = Date.now(),
): DemoReply {
  const scores = readScores(cookies.scores);
  const study = readStudy(cookies.study);
  const lang = toLang(query.get("lang") ?? body?.lang);
  if (path === "health") return json({ status: "ok", database: false, spring: false, demo: true });
  if (path === "courses" && method === "GET") return json(data.courses.map((c) => courseRow(c, lang)));
  if (path === "uploads" || path.startsWith("courses") || path.startsWith("auth") || path === "me") {
    return json({ detail: READ_ONLY }, 403); // no uploads and no accounts in the public demo
  }
  if (path === "book.pdf") return json({ detail: "No local PDF in the demo." }, 404);

  const course = findCourse(query.get("course") ?? body?.course);
  if (!course) return json({ detail: "Unknown course" }, 404);
  const known = new Set(course.notions.map((notion) => notion.id));
  const presence = studyReply(method, path, body, study, course.id, now);
  if (presence) return presence;

  if (path === "notions") return json(course.notions.map((n) => notionRow(n, lang)));
  if (path === "mastery") return json({ notions: mastery(scores, course.id), status: "ok" });
  if (path === "plan") return json({ plan: plan(scores, course, lang), status: "ok" });
  if (path === "review") return json({ reviews: [], status: "demo" }); // FSRS needs dated scores
  if (path === "chat" && typeof body?.message === "string") return json(chat(scores, course, body.message, lang));
  if (path === "quiz") return json({ questions: pickQuiz(scores, course, Number(body?.n) || 3, lang), status: "ok" });
  if (path === "quiz/result" && Array.isArray(body?.answers)) {
    const results = notionScores(body.answers.filter((a: Answer) => known.has(a.notion_id)));
    const saved = Object.entries(results).reduce((acc, [id, score]) => addScore(acc, course.id, id, score), scores);
    const skipped = body.answers.filter((a: Answer) => a.chosen_index === null || a.chosen_index === undefined).length;
    const cookies = [scoresCookie(saved)];
    if (isFlawless(body.answers)) cookies.push(studyCookie(award({ ...study, flawless: true }, now).study));
    return json({ scores: results, recorded: true, skipped }, 200, cookies);
  }
  if (path === "feynman" && typeof body?.explanation === "string") {
    const example = course.feynman.find(
      (item) => item.notion_id === body.notion_id && normalize(item.explanation) === normalize(body.explanation),
    );
    if (!example) return json({ detail: "demo_only" }, 400);
    const saved = addScore(scores, course.id, example.notion_id, example.result.score);
    return json({ ...example.result, recorded: true }, 200, [scoresCookie(saved)]);
  }
  return json({ detail: "Bad request" }, 400);
}
