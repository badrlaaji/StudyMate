// Presence state machine: time from timestamp differences, pauses and resumes.
import { describe, expect, it } from "vitest";

import { activeSeconds, duration, onFrame, onVisibility, pause, resume, start, type Presence } from "@/lib/presence";

// Camera frames once per second: face (true) or not (false), from t0 = 0.
function frames(p: Presence, faces: boolean[], from = 1000): Presence {
  return faces.reduce((acc, face, i) => onFrame(acc, from + i * 1000, face), p);
}

describe("presence", () => {
  it("counts the time while a face is there", () => {
    const p = frames(start(0, true), Array(10).fill(true));
    expect(p.state).toBe("ACTIVE");
    expect(activeSeconds(p)).toBe(10);
  });

  it("pauses after 5 s without a face, and those 5 s do not count", () => {
    const p = frames(start(0, true), [true, true, true, false, false, false, false, false]); // face last seen at 3 s
    expect(p.state).toBe("PAUSE_ABSENT");
    expect(activeSeconds(p)).toBe(3);
  });

  it("4 s away is not a pause", () => {
    const p = frames(start(0, true), [true, false, false, false, false]); // last face at 1 s, now 5 s
    expect(p.state).toBe("ACTIVE");
  });

  it("resumes after 1 s with a face; the time away is not counted", () => {
    let p = frames(start(0, true), [true, true, true, false, false, false, false, false]); // paused at 8 s
    p = onFrame(p, 20_000, true); // back at 20 s
    expect(p.state).toBe("PAUSE_ABSENT");
    p = onFrame(p, 21_000, true);
    expect(p.state).toBe("ACTIVE");
    p = onFrame(p, 31_000, true);
    expect(activeSeconds(p)).toBe(3 + 10);
  });

  it("a hidden tab pauses, coming back resumes", () => {
    let p = start(0, false); // manual mode: no camera
    p = onVisibility(p, 30_000, true);
    expect(p.state).toBe("PAUSE_TAB");
    p = onVisibility(p, 90_000, false);
    expect(p.state).toBe("ACTIVE");
    p = resume(p, 100_000);
    expect(activeSeconds(p)).toBe(30 + 10);
  });

  it("a manual pause survives a tab switch", () => {
    let p = pause(start(0, false), 10_000);
    p = onVisibility(p, 20_000, true);
    p = onVisibility(p, 30_000, false);
    expect(p.state).toBe("PAUSE_MANUAL");
    expect(activeSeconds(resume(p, 40_000))).toBe(10);
  });

  it("formats the estimated time", () => {
    expect(duration(725)).toBe("12 min 05 s");
    expect(duration(3720)).toBe("1 h 02 min");
  });
});
