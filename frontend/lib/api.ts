// Server-side calls to FastAPI (API_URL is never sent to the browser).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type Notion = {
  id: string;
  name: string;
  chapter: number;
  section: string;
  pages: number[];
  key_ideas: string[];
};

export async function getNotions(lang: string): Promise<Notion[]> {
  try {
    const response = await fetch(`${API_URL}/notions?lang=${lang}`, { cache: "no-store" });
    return response.ok ? await response.json() : [];
  } catch {
    return []; // API down: the page still renders
  }
}

export type Mastery = { notionId: string; average: number; count: number; level: string };
export type PlanRow = { notion_id: string; name: string; score: number; pages: number[]; action: string };

export async function getMastery(): Promise<{ notions: Mastery[]; status: string }> {
  try {
    const response = await fetch(`${API_URL}/mastery`, { cache: "no-store" });
    return response.ok ? await response.json() : { notions: [], status: "degraded" };
  } catch {
    return { notions: [], status: "degraded" };
  }
}

export async function getPlan(lang: string): Promise<{ plan: PlanRow[]; status: string }> {
  try {
    const response = await fetch(`${API_URL}/plan?lang=${lang}`, { cache: "no-store" });
    return response.ok ? await response.json() : { plan: [], status: "degraded" };
  } catch {
    return { plan: [], status: "degraded" };
  }
}
