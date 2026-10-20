// Server-side calls to FastAPI (API_URL is never sent to the browser).
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

// GET a JSON body; the fallback keeps the page rendering when the API is down.
async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    return response.ok ? await response.json() : fallback;
  } catch {
    return fallback;
  }
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
