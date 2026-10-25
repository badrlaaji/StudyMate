// Presence mode in the public demo (data in the browser) and the trophy rules, at fixed dates.
import { describe, expect, it } from "vitest";

import { demoReply, findCourse, readCookie, readStudy, STUDY_COOKIE, type DemoCookies } from "@/lib/demo";
import { currentStreak, earned, isFlawless, localDay, longestStreak } from "@/lib/trophies";

const T0 = Date.parse("2026-01-05T09:00:00Z");
const NO_QUERY = new URLSearchParams();

// Call the demo like the browser does: keep the study cookie between calls.
function session() {
  const cookies: DemoCookies = {};
  return (method: string, path: string, body: unknown, now: number) => {
    const reply = demoReply(method, path, NO_QUERY, body, cookies, now);
    const study = reply.cookies.find((c) => c.startsWith(`${STUDY_COOKIE}=`));
    if (study) cookies.study = readCookie(study.split(";")[0], STUDY_COOKIE);
    return reply;
  };
}

describe("trophy rules", () => {
  const days = { "2026-01-01": 1800, "2026-01-02": 1800, "2026-01-03": 1800, "2026-01-05": 1800 };

  it("counts streaks of consecutive days", () => {
    expect(longestStreak(days, 1800)).toBe(3);
    expect(currentStreak(days, 1800, "2026-01-05")).toBe(1);
    expect(currentStreak(days, 1800, "2026-01-04")).toBe(3); // today not reached yet: yesterday's run
  });

  it("uses the goal's time zone for today", () => {
    const late = Date.parse("2026-01-01T23:30:00Z");
    expect(localDay(late, "UTC")).toBe("2026-01-01");
    expect(localDay(late, "Asia/Tokyo")).toBe("2026-01-02");
  });

  it("gives the six trophies at their thresholds", () => {
    expect(earned({ d: 599 }, 30, false)).toEqual([]);
    expect(earned(days, 30, false)).toEqual(["FIRST_STEPS", "GOAL_REACHED", "REGULAR"]);
    // 10 h in one day: the goal (8 h at most) is reached too
    expect(earned({ d: 36_000 }, 480, true)).toEqual(["FIRST_STEPS", "GOAL_REACHED", "MARATHON", "FLAWLESS"]);
  });

  it("flawless needs 5 answered questions, all correct", () => {
    const right = { answer_index: 1, chosen_index: 1 };
    expect(isFlawless(Array(5).fill(right))).toBe(true);
    expect(isFlawless(Array(4).fill(right))).toBe(false);
    expect(isFlawless([...Array(4).fill(right), { answer_index: 1, chosen_index: null }])).toBe(false);
  });
});

describe("demo presence mode", () => {
  it("counts a session and refuses more time than really passed", () => {
    const call = session();
    const started = call("POST", "study/sessions", { mode: "CAMERA" }, T0);
    expect(started.status).toBe(201);
    const id = (started.body as { id: number }).id;
    expect(call("PATCH", `study/sessions/${id}`, { active_seconds: 60 }, T0 + 60_000).status).toBe(200);
    const tooFast = call("PATCH", `study/sessions/${id}`, { active_seconds: 200 }, T0 + 120_000);
    expect(tooFast.status).toBe(400);
    expect(call("PATCH", `study/sessions/${id}`, { active_seconds: 30 }, T0 + 130_000).status).toBe(400); // down
  });

  it("unlocks First steps after 10 minutes and shows them in the summary", () => {
    const call = session();
    const id = (call("POST", "study/sessions", {}, T0).body as { id: number }).id;
    const reply = call("PATCH", `study/sessions/${id}`, { active_seconds: 600 }, T0 + 600_000);
    expect((reply.body as { newTrophies: string[] }).newTrophies).toEqual(["FIRST_STEPS"]);
    const summary = call("GET", "study/summary", null, T0 + 601_000).body as { todaySeconds: number; week: unknown[] };
    expect(summary.todaySeconds).toBe(600);
    expect(summary.week).toHaveLength(7);
    const trophies = call("GET", "trophies", null, T0 + 602_000).body as { code: string; obtainedAt: string | null }[];
    expect(trophies.filter((t) => t.obtainedAt).map((t) => t.code)).toEqual(["FIRST_STEPS"]);
  });

  it("keeps the goal between 5 and 480 minutes in a real time zone", () => {
    const call = session();
    expect(call("PUT", "study/goal", { minutes: 4, timezone: "UTC" }, T0).status).toBe(400);
    expect(call("PUT", "study/goal", { minutes: 481, timezone: "UTC" }, T0).status).toBe(400);
    expect(call("PUT", "study/goal", { minutes: 45, timezone: "Mars/Olympus" }, T0).status).toBe(400);
    expect(call("PUT", "study/goal", { minutes: 45, timezone: "Africa/Casablanca" }, T0).status).toBe(200);
    expect((call("GET", "study/summary", null, T0).body as { goalMinutes: number }).goalMinutes).toBe(45);
  });

  it("a flawless quiz of 5 unlocks Flawless; a skipped question prevents it", () => {
    const quiz = findCourse("data-science")!.quiz.en.slice(0, 5);
    const answers = (skip: boolean) =>
      quiz.map((q, i) => ({ notion_id: q.notion_id, answer_index: q.answer_index, chosen_index: skip && i === 0 ? null : q.answer_index }));
    const withSkip = demoReply("POST", "quiz/result", NO_QUERY, { answers: answers(true) }, {}, T0);
    expect(withSkip.cookies.some((c) => c.startsWith(STUDY_COOKIE))).toBe(false);
    const flawless = demoReply("POST", "quiz/result", NO_QUERY, { answers: answers(false) }, {}, T0);
    const study = flawless.cookies.find((c) => c.startsWith(STUDY_COOKIE))!;
    expect(Object.keys(readStudy(readCookie(study.split(";")[0], STUDY_COOKIE)).trophies)).toEqual(["FLAWLESS"]);
  });
});
