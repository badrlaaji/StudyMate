// Why the camera could not start, from the browser's error (pure: tested without a camera).
// Names from the getUserMedia spec (DOMException.name); Chrome's old names are kept too.

export type CameraProblem = "insecure" | "denied" | "busy" | "missing" | "model";

const DENIED = ["NotAllowedError", "SecurityError", "PermissionDeniedError"];
const BUSY = ["NotReadableError", "AbortError", "TrackStartError"];
const MISSING = ["NotFoundError", "OverconstrainedError", "DevicesNotFoundError"];

// phase "camera": getUserMedia failed; phase "model": the WASM runtime or the model failed.
export function cameraProblem(error: unknown, phase: "camera" | "model", secure: boolean): CameraProblem {
  if (!secure) return "insecure"; // no camera outside localhost / HTTPS
  if (phase === "model") return "model";
  const name = error instanceof Error || error instanceof DOMException ? error.name : "";
  if (DENIED.includes(name)) return "denied";
  if (BUSY.includes(name)) return "busy";
  if (MISSING.includes(name)) return "missing";
  return "busy";
}
