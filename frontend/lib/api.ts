// Server-side calls to FastAPI (API_URL is never sent to the browser).
// Public demo (DEMO_MODE=1): the same answers come from the demo data, without network.
import { cookies } from "next/headers";

import { bearer, SESSION_COOKIE } from "@/lib/account";
import { demoReply, isDemo, SCORES_COOKIE } from "@/lib/demo";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type Course = {
  id: string;
  title: string;
  scope: string;
  book_lang: string;
  license: string;
  attribution: string;
  book_url: string;
  default: boolean;
  pdf: boolean;
  chunks: number | null;
  notions: number;
  validated: boolean;
  uploaded: boolean;
  job: string | null; // uploaded course: queued, indexing, drafting, ready or failed
  job_detail: string;
  pdf_url?: string | null; // demo: the book PDF online (no local copy)
};

export type Notion = {
  id: string;
  name: string;
  chapter: number;
  section: string;
  pages: number[];
  key_ideas: string[];
};

export type Mastery = { notionId: string; average: number; count: number; level: string };
export type PlanRow = { notion_id: string; name: string; score: number; pages: number[]; action: string };
// Spaced repetition (FSRS): next review of a notion; days_left <= 0 = due now.
export type Review = { notion_id: string; name: string; due: string; days_left: number; reviews: number; pages: number[] };

// GET a JSON body; the fallback keeps the page rendering when the API is down.
async function getJson<T>(path: string, fallback: T): Promise<T> {
  if (isDemo()) return getDemo(path, fallback);
  try {
    const token = (await cookies()).get(SESSION_COOKIE)?.value; // the user's JWT, relayed as is
    const response = await fetch(`${API_URL}${path}`, { cache: "no-store", headers: bearer(token) });
    return response.ok ? await response.json() : fallback;
  } catch {
    return fallback;
  }
}

async function getDemo<T>(path: string, fallback: T): Promise<T> {
  const url = new URL(path, "http://demo");
  const cookie = (await cookies()).get(SCORES_COOKIE)?.value;
  const reply = demoReply("GET", url.pathname.slice(1), url.searchParams, null, cookie);
  return reply.status === 200 ? (reply.body as T) : fallback;
}

export function getCourses(lang: string): Promise<Course[]> {
  return getJson(`/courses?lang=${lang}`, []);
}

export function getNotions(lang: string, course: string): Promise<Notion[]> {
  return getJson(`/notions?lang=${lang}&course=${course}`, []);
}

export function getMastery(course: string): Promise<{ notions: Mastery[]; status: string }> {
  return getJson(`/mastery?course=${course}`, { notions: [], status: "degraded" });
}

export function getPlan(lang: string, course: string): Promise<{ plan: PlanRow[]; status: string }> {
  return getJson(`/plan?lang=${lang}&course=${course}`, { plan: [], status: "degraded" });
}

export function getReviews(lang: string, course: string): Promise<{ reviews: Review[]; status: string }> {
  return getJson(`/review?lang=${lang}&course=${course}`, { reviews: [], status: "degraded" });
}
