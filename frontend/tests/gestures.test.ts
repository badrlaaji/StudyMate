// Gesture quiz rules: finger counting on real MediaPipe landmarks, and stabilisation.
import { describe, expect, it } from "vitest";

import hands from "./fixtures/hands.json";
import { cancel, countFingers, FIST_HOLD_MS, HOLD_MS, START, stabilize, toGesture, type Gesture, type Hold } from "@/lib/gestures";

describe("countFingers", () => {
  it.each(hands.map((h) => [h.name, h.expected, h.landmarks] as const))("%s: %i raised", (_, expected, landmarks) => {
    expect(countFingers(landmarks)).toBe(expected);
  });

  it("maps 0 fingers to a fist and no hand to null", () => {
    const fist = hands.find((h) => h.name === "thumbs_up")!.landmarks;
    expect(toGesture(fist)).toBe("fist"); // the thumb is ignored
    expect(toGesture(null)).toBeNull();
    expect(toGesture([])).toBeNull();
  });
});

// Feed (time, gesture) frames; return what fired and the last progress.
function play(frames: [number, Gesture][], hold: Hold = START) {
  const fired: Gesture[] = [];
  let progress = 0;
  for (const [now, value] of frames) {
    const step = stabilize(hold, value, now);
    hold = step.hold;
    progress = step.progress;
    if (step.fired !== null) fired.push(step.fired);
  }
  return { fired, progress, hold };
}

describe("stabilize", () => {
  it("answers once the same value is held for 1 s", () => {
    expect(play([[0, 3], [500, 3], [999, 3]]).fired).toEqual([]);
    expect(play([[0, 3], [500, 3], [999, 3]]).progress).toBeCloseTo(0.999);
    expect(play([[0, 3], [500, 3], [HOLD_MS, 3]]).fired).toEqual([3]);
  });

  it("needs 1.5 s for a fist (skip)", () => {
    expect(play([[0, "fist"], [HOLD_MS, "fist"]]).fired).toEqual([]);
    expect(play([[0, "fist"], [FIST_HOLD_MS, "fist"]]).fired).toEqual(["fist"]);
  });

  it("restarts when the value changes", () => {
    expect(play([[0, 2], [600, 3], [1200, 3]]).fired).toEqual([]);
    expect(play([[0, 2], [600, 3], [1600, 3]]).fired).toEqual([3]);
  });

  it("cancels when the hand leaves the camera", () => {
    expect(play([[0, "fist"], [1000, null], [1600, null]]).fired).toEqual([]);
    expect(play([[0, "fist"], [1000, null], [1100, "fist"], [2000, "fist"]]).fired).toEqual([]);
  });

  it("fires once: the gesture must change before firing again", () => {
    expect(play([[0, 1], [1000, 1], [3000, 1], [5000, 1]]).fired).toEqual([1]);
    expect(play([[0, 1], [1000, 1], [1100, 4], [2100, 4]]).fired).toEqual([1, 4]);
  });

  it("Escape cancels the countdown like removing the hand", () => {
    const started = play([[0, 2], [700, 2]]).hold;
    expect(play([[800, 2], [2000, 2]], cancel(started)).fired).toEqual([]);
    expect(play([[800, 2], [900, null], [1000, 2], [2000, 2]], cancel(started)).fired).toEqual([2]);
  });
});
