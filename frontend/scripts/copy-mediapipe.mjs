// Copy the MediaPipe WASM runtime into public/mediapipe (served by our own site, not a CDN).
// Runs before `next dev` and `next build`; the folder is generated, never committed.
import { copyFileSync, mkdirSync } from "node:fs";

const FROM = new URL("../node_modules/@mediapipe/tasks-vision/wasm/", import.meta.url);
const TO = new URL("../public/mediapipe/", import.meta.url);
// The SIMD build, plus the fallback for browsers without WebAssembly SIMD.
const FILES = ["vision_wasm_internal.js", "vision_wasm_internal.wasm", "vision_wasm_nosimd_internal.js", "vision_wasm_nosimd_internal.wasm"];

mkdirSync(TO, { recursive: true });
for (const name of FILES) copyFileSync(new URL(name, FROM), new URL(name, TO));
console.log(`MediaPipe WASM copied to public/mediapipe (${FILES.length} files)`);
