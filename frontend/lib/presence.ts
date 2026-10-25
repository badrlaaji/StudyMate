// Presence mode: estimated study time from timestamps only (pure functions, no camera here).
// ACTIVE counts; PAUSE_ABSENT (no face for 5 s), PAUSE_TAB (page hidden) and PAUSE_MANUAL do not.
// The camera only says "a face is there or not", once per second: no identification, no image kept.

export type PresenceState = "ACTIVE" | "PAUSE_ABSENT" | "PAUSE_TAB" | "PAUSE_MANUAL";
export type Presence = {
  state: PresenceState;
  activeMs: number;
  last: number; // time of the last update
  lastFaceAt: number; // last frame with a face (camera mode)
  faceSince: number | null; // face back since (to resume after 1 s)
  camera: boolean;
};

export const ABSENT_MS = 5000; // no face for 5 s -> pause
export const RETURN_MS = 1000; // a face for 1 s -> resume
export const SYNC_MS = 60_000; // send the total every 60 s (and at every pause)
export const FRAME_MS = 1000; // one camera frame per second

export function start(now: number, camera: boolean): Presence {
  return { state: "ACTIVE", activeMs: 0, last: now, lastFaceAt: now, faceSince: null, camera };
}

// Time passes: only ACTIVE time counts, measured as a difference of timestamps.
export function advance(p: Presence, now: number): Presence {
  const added = p.state === "ACTIVE" ? Math.max(0, now - p.last) : 0;
  return { ...p, activeMs: p.activeMs + added, last: now };
}

// One camera frame: is a face there?
export function onFrame(p: Presence, now: number, face: boolean): Presence {
  const next = advance(p, now);
  if (face) {
    if (next.state !== "PAUSE_ABSENT") return { ...next, lastFaceAt: now, faceSince: null };
    const since = next.faceSince ?? now;
    if (now - since >= RETURN_MS) return { ...next, state: "ACTIVE", lastFaceAt: now, faceSince: null };
    return { ...next, lastFaceAt: now, faceSince: since };
  }
  if (next.state === "ACTIVE" && now - next.lastFaceAt >= ABSENT_MS) {
    // the seconds without a face before the pause do not count either
    const away = now - next.lastFaceAt;
    return { ...next, state: "PAUSE_ABSENT", activeMs: Math.max(0, next.activeMs - away), faceSince: null };
  }
  return { ...next, faceSince: null };
}

// Page Visibility API: another tab or a minimised window pauses; coming back resumes.
export function onVisibility(p: Presence, now: number, hidden: boolean): Presence {
  const next = advance(p, now);
  if (hidden) return next.state === "PAUSE_MANUAL" ? next : { ...next, state: "PAUSE_TAB" };
  if (next.state !== "PAUSE_TAB") return next;
  return { ...next, state: "ACTIVE", lastFaceAt: now, faceSince: null };
}

export function pause(p: Presence, now: number): Presence {
  return { ...advance(p, now), state: "PAUSE_MANUAL" };
}

export function resume(p: Presence, now: number): Presence {
  return { ...advance(p, now), state: "ACTIVE", lastFaceAt: now, faceSince: null };
}

export function activeSeconds(p: Presence): number {
  return Math.floor(p.activeMs / 1000);
}

export function isPaused(state: PresenceState): boolean {
  return state !== "ACTIVE";
}

// "12 min 05 s" / "1 h 02 min": the estimated study time, as text.
export function duration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h} h ${String(m).padStart(2, "0")} min`;
  return `${m} min ${String(s).padStart(2, "0")} s`;
}
