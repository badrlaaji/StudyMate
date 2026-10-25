// The 6 trophies, same rules as Spring (core/TrophyRules.java); used by the public demo,
// where the study time stays in the browser. Days are "YYYY-MM-DD" in the goal's time zone.

export const CODES = ["FIRST_STEPS", "GOAL_REACHED", "REGULAR", "PERFECT_WEEK", "MARATHON", "FLAWLESS"] as const;
export type Code = (typeof CODES)[number];
export type Days = Record<string, number>; // day -> active seconds

const FIRST_STEPS_SECONDS = 10 * 60;
const MARATHON_SECONDS = 10 * 3600;
const FLAWLESS_MIN_QUESTIONS = 5;
const DAY_MS = 86_400_000;

export function addDays(day: string, n: number): string {
  return new Date(Date.parse(`${day}T00:00:00Z`) + n * DAY_MS).toISOString().slice(0, 10);
}

// "Today" in a time zone, e.g. 23:30 UTC is already tomorrow in Tokyo.
export function localDay(now: number, timezone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

export function validZone(timezone: string): boolean {
  try {
    localDay(0, timezone);
    return true;
  } catch {
    return false; // RangeError: unknown time zone
  }
}

export function longestStreak(days: Days, goalSeconds: number): number {
  let best = 0;
  let run = 0;
  let previous: string | null = null;
  for (const day of Object.keys(days).sort()) {
    if (days[day] < goalSeconds) run = 0;
    else {
      run = previous !== null && addDays(previous, 1) === day && run > 0 ? run + 1 : 1;
      best = Math.max(best, run);
    }
    previous = day;
  }
  return best;
}

// Days in a row at the goal, ending today (or yesterday while today is not reached yet).
export function currentStreak(days: Days, goalSeconds: number, today: string): number {
  let day = (days[today] ?? 0) >= goalSeconds ? today : addDays(today, -1);
  let streak = 0;
  while ((days[day] ?? 0) >= goalSeconds) {
    streak += 1;
    day = addDays(day, -1);
  }
  return streak;
}

// A quiz of 5+ questions, all answered and all correct (a skipped question breaks it).
export function isFlawless(answers: { answer_index: number; chosen_index: number | null }[]): boolean {
  return answers.length >= FLAWLESS_MIN_QUESTIONS && answers.every((a) => a.chosen_index === a.answer_index);
}

export function earned(days: Days, goalMinutes: number, flawless: boolean): Code[] {
  const total = Object.values(days).reduce((a, b) => a + b, 0);
  const streak = longestStreak(days, goalMinutes * 60);
  const codes: Code[] = [];
  if (total >= FIRST_STEPS_SECONDS) codes.push("FIRST_STEPS");
  if (streak >= 1) codes.push("GOAL_REACHED");
  if (streak >= 3) codes.push("REGULAR");
  if (streak >= 7) codes.push("PERFECT_WEEK");
  if (total >= MARATHON_SECONDS) codes.push("MARATHON");
  if (flawless) codes.push("FLAWLESS");
  return codes;
}
