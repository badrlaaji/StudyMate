"use client";

import { useEffect, useRef, useState } from "react";

import Icon from "@/components/Icon";
import { cameraProblem, type CameraProblem } from "@/lib/camera";
import { cancel, FINGERS, raisedFingers, START, stabilize, toGesture, WRIST, type Gesture, type Hold, type Point } from "@/lib/gestures";
import { fmt, type Dict } from "@/lib/i18n";

// The WASM runtime is served by our site (scripts/copy-mediapipe.mjs); the model comes
// from Google's official, versioned URL. Camera frames never leave the browser.
const WASM_PATH = "/mediapipe";
const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";
const FRAME_MS = 66; // about 15 detections per second
const RING = 2 * Math.PI * 26;

type Status = "off" | "loading" | "on" | "error";
type Connection = { start: number; end: number };
type Landmarker = { detectForVideo: (v: HTMLVideoElement, t: number) => { landmarks: Point[][] }; close: () => void };
type Props = {
  mode: "answer" | "next"; // waiting for an answer, or showing the correction
  onAnswer: (option: number) => void; // 1 to 4, same function as the keys
  onSkip: () => void; // same function as P and the Skip button
  onNext: () => void; // same function as Enter
  t: Dict;
};

export default function GestureCam({ mode, onAnswer, onSkip, onNext, t }: Props) {
  const [enabled, setEnabled] = useState(false); // camera off by default
  const [status, setStatus] = useState<Status>("off");
  const [gesture, setGesture] = useState<Gesture>(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [problem, setProblem] = useState<CameraProblem | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const hold = useRef<Hold>(START);
  const actions = useRef({ mode, onAnswer, onSkip, onNext });

  useEffect(() => {
    actions.current = { mode, onAnswer, onSkip, onNext };
  });

  // One stabilised gesture -> the same action as the keyboard.
  function fire(value: Gesture) {
    const { mode, onAnswer, onSkip, onNext } = actions.current;
    if (mode === "answer" && value === "fist") {
      onSkip();
      setMessage(t.gesture.skipped);
    } else if (mode === "answer" && typeof value === "number") {
      onAnswer(value);
      setMessage(fmt(t.gesture.answered, { n: value }));
    } else if (mode === "next" && value === 4) {
      onNext();
    }
  }

  function onFrame(value: Gesture, now: number) {
    const step = stabilize(hold.current, value, now);
    if (step.hold.value !== hold.current.value) setMessage(holdText(value, actions.current.mode, t));
    hold.current = step.hold;
    setGesture(value);
    setProgress(step.progress);
    if (step.fired !== null) fire(step.fired);
  }

  // Escape cancels the countdown, like removing the hand.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && status === "on") {
        hold.current = cancel(hold.current);
        setProgress(0);
        setMessage(t.gesture.cancelled);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [status, t]);

  // Camera + hand landmarker, only while enabled; everything is released when turned off.
  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let frame = 0;
    let last = 0;
    let stream: MediaStream | null = null;
    let landmarker: Landmarker | null = null;
    let connections: Connection[] = [];

    // Idempotent: safe from the cleanup, from a failure, or after a late await.
    function release() {
      cancelAnimationFrame(frame);
      stream?.getTracks().forEach((track) => track.stop());
      stream = null;
      landmarker?.close();
      landmarker = null;
    }

    function fail(error: unknown, phase: "camera" | "model") {
      release();
      if (stopped) return;
      setProblem(cameraProblem(error, phase, window.isSecureContext && Boolean(navigator.mediaDevices)));
      setStatus("error");
    }

    async function start() {
      setStatus("loading");
      setProblem(null);
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
      } catch (error) {
        return fail(error, "camera");
      }
      if (stopped) return release(); // turned off while the browser was asking
      try {
        const { FilesetResolver, HandLandmarker } = await import("@mediapipe/tasks-vision");
        const vision = await FilesetResolver.forVisionTasks(WASM_PATH);
        landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: MODEL_URL },
          runningMode: "VIDEO",
          numHands: 1,
        });
        connections = HandLandmarker.HAND_CONNECTIONS;
        if (stopped || !video.current) return release();
        video.current.srcObject = stream;
        await video.current.play();
      } catch (error) {
        return fail(error, "model");
      }
      setStatus("on");
      const loop = (now: number) => {
        if (stopped || !video.current || !landmarker) return;
        if (now - last >= FRAME_MS && video.current.readyState >= 2) {
          last = now;
          let hand: Point[] | null = null;
          try {
            hand = landmarker.detectForVideo(video.current, now).landmarks[0] ?? null;
          } catch (error) {
            return fail(error, "model"); // a silent stop would look like "nothing happens"
          }
          drawHand(canvas.current, video.current, hand, connections);
          onFrame(toGesture(hand), now);
        }
        frame = requestAnimationFrame(loop);
      };
      frame = requestAnimationFrame(loop);
    }

    start();
    return () => {
      stopped = true;
      release();
      hold.current = START;
      setStatus("off");
      setGesture(null);
      setProgress(0);
    };
    // onFrame only reads refs: the camera starts once each time it is turned on.
  }, [enabled]);

  const label = gesture === null ? "–" : gesture === "fist" ? "✊" : String(gesture);
  const detected = gesture === null ? t.gesture.noHand : gesture === "fist" ? t.gesture.fist : fmt(t.gesture.fingers, { n: gesture });
  return (
    <section className="card gesture stack" aria-labelledby="gesture-title">
      <div className="row">
        <h2 id="gesture-title" className="gesture-title">
          <Icon name="spark" />
          {t.gesture.title}
        </h2>
        <span className="spacer" />
        {status === "on" && (
          <span className="badge badge-live">
            <Icon name="dot" />
            {t.gesture.on}
          </span>
        )}
        <button type="button" className={`btn btn-sm ${enabled ? "btn-secondary" : "btn-primary"}`} aria-pressed={enabled} onClick={() => setEnabled(!enabled)}>
          {enabled ? t.gesture.disable : t.gesture.enable}
        </button>
      </div>
      <p className="hint">{t.gesture.privacy}</p>
      {enabled && (
        <div className="gesture-live">
          <div className="gesture-view">
            <video ref={video} muted playsInline aria-label={t.gesture.preview} />
            <canvas ref={canvas} className="gesture-skeleton" aria-hidden="true" />
            {status === "on" && <span className="gesture-detected">{detected}</span>}
            <svg viewBox="0 0 60 60" className="gesture-ring" aria-hidden="true">
              <circle cx="30" cy="30" r="26" className="ring-track" />
              <circle cx="30" cy="30" r="26" className="ring-value" strokeDasharray={RING} strokeDashoffset={RING * (1 - progress)} />
              <text x="30" y="36" textAnchor="middle">
                {label}
              </text>
            </svg>
          </div>
          <div className="stack" style={{ gap: "var(--space-2)" }}>
            {status === "loading" && <p className="muted">{t.gesture.loading}</p>}
            {status === "error" && (
              <p className="callout callout-warn" role="alert">
                <Icon name="alert" />
                <span>
                  {problem && t.camera[problem]} {t.gesture.error}
                </span>
              </p>
            )}
            <p className="hint">{mode === "answer" ? t.gesture.help : t.gesture.nextHelp}</p>
            <p className="hint">{t.gesture.fingerNames}</p>
            <p className="gesture-message" aria-live="polite">
              {message}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

// What the countdown will do, announced once when the gesture changes.
function holdText(value: Gesture, mode: "answer" | "next", t: Dict): string {
  if (value === null) return t.gesture.noHand;
  if (mode === "next") return value === 4 ? t.gesture.holdNext : "";
  return value === "fist" ? t.gesture.holdSkip : fmt(t.gesture.hold, { n: value });
}

// The camera preview: the 21 landmarks and their links, raised finger tips in the accent
// colour. Drawn in the video's own pixels; CSS mirrors and crops it exactly like the video.
function drawHand(target: HTMLCanvasElement | null, source: HTMLVideoElement, hand: Point[] | null, connections: Connection[]) {
  const context = target?.getContext("2d");
  if (!target || !context) return;
  if (target.width !== source.videoWidth) target.width = source.videoWidth;
  if (target.height !== source.videoHeight) target.height = source.videoHeight;
  context.clearRect(0, 0, target.width, target.height);
  if (!hand) return;
  const style = getComputedStyle(target);
  const at = (i: number) => [hand[i].x * target.width, hand[i].y * target.height] as const;
  context.lineWidth = 3;
  context.strokeStyle = "rgba(255, 255, 255, 0.85)";
  for (const { start, end } of connections) {
    context.beginPath();
    context.moveTo(...at(start));
    context.lineTo(...at(end));
    context.stroke();
  }
  const raised = raisedFingers(hand);
  const tips = new Map(FINGERS.map(({ tip }, i) => [tip, raised[i]]));
  hand.forEach((_, i) => {
    const up = tips.get(i);
    context.beginPath();
    context.arc(...at(i), up ? 9 : i === WRIST ? 6 : 4, 0, 2 * Math.PI);
    context.fillStyle = up ? style.getPropertyValue("--accent").trim() || "#5b3df5" : up === false ? "#9ea2b3" : "#ffffff";
    context.fill();
  });
}
