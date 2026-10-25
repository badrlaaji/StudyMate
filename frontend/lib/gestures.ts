// Gesture quiz: pure rules on the 21 MediaPipe hand landmarks (no camera, no React here).
// Indices from MediaPipe's HandLandmark enum: wrist 0, finger tips 8/12/16/20, middle joints
// (PIP) 6/10/14/18. The thumb (1-4) is ignored, so an open hand counts as 4.

export type Point = { x: number; y: number };
export type Gesture = 1 | 2 | 3 | 4 | "fist" | null; // null = no hand

export const WRIST = 0;
export const FINGERS = [
  { tip: 8, pip: 6 }, // index
  { tip: 12, pip: 10 }, // middle
  { tip: 16, pip: 14 }, // ring
  { tip: 20, pip: 18 }, // pinky
];
export const HOLD_MS = 1000; // same value for 1 s to answer
export const FIST_HOLD_MS = 1500; // a fist held 1.5 s skips the question

function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

// A raised finger: its tip is farther from the wrist than its middle joint.
export function countFingers(hand: Point[]): number {
  const wrist = hand[WRIST];
  return FINGERS.filter(({ tip, pip }) => distance(hand[tip], wrist) > distance(hand[pip], wrist)).length;
}

export function toGesture(hand: Point[] | null): Gesture {
  if (!hand || hand.length < 21) return null;
  const count = countFingers(hand);
  return count === 0 ? "fist" : (count as 1 | 2 | 3 | 4);
}

// Stabilisation: a gesture fires once it has stayed the same for its hold time.
// After firing (or Escape), the gesture must change before it can fire again.
export type Hold = { value: Gesture; since: number; armed: boolean };
export const START: Hold = { value: null, since: 0, armed: true };

export function holdTime(value: Gesture): number {
  return value === "fist" ? FIST_HOLD_MS : HOLD_MS;
}

export function stabilize(hold: Hold, value: Gesture, now: number): { hold: Hold; progress: number; fired: Gesture } {
  if (value !== hold.value) {
    // a new gesture (or the hand left the camera): restart the countdown
    return { hold: { value, since: now, armed: true }, progress: 0, fired: null };
  }
  if (value === null || !hold.armed) return { hold, progress: 0, fired: null };
  const progress = Math.min(1, (now - hold.since) / holdTime(value));
  if (progress < 1) return { hold, progress, fired: null };
  return { hold: { ...hold, armed: false }, progress: 1, fired: value };
}

// Escape: cancel the countdown; the same gesture will not fire until it changes.
export function cancel(hold: Hold): Hold {
  return { ...hold, armed: false };
}
