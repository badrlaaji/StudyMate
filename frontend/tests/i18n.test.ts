// Interface texts that depend on numbers.
import { describe, expect, it } from "vitest";

import { DICTS, whenLabel } from "@/lib/i18n";

describe("next review label", () => {
  it("says late, today, tomorrow or in N days", () => {
    const t = DICTS.en;
    expect([-3, -1, 0, 1, 5].map((days) => whenLabel(days, t))).toEqual([
      "3 days late",
      "1 day late",
      "Due today",
      "Tomorrow",
      "In 5 days",
    ]);
  });

  it("has every key in French too", () => {
    expect(whenLabel(-2, DICTS.fr)).toBe("2 jours de retard");
    expect(Object.keys(DICTS.fr.reviews)).toEqual(Object.keys(DICTS.en.reviews));
  });
});
