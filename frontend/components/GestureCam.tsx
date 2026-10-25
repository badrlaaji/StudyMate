"use client";

import { useEffect, useRef, useState } from "react";

import Icon from "@/components/Icon";
import { cancel, START, stabilize, toGesture, type Gesture, type Hold } from "@/lib/gestures";
import { fmt, type Dict } from "@/lib/i18n";

// The WASM runtime is served by our site (scripts/copy-mediapipe.mjs); the model comes
// from Google's official, versioned URL. Camera frames never leave the browser.
const WASM_PATH = "/mediapipe";
const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";
const FRAME_MS = 66; // about 15 detections per second
const RING = 2 * Math.PI * 26;

type Status = "off" | "loading" | "on" | "error";
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
  const video = useRef<HTMLVideoElement>(null);
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
    let landmarker: { detectForVideo: (v: HTMLVideoElement, t: number) => { landmarks: { x: number; y: number }[][] }; close: () => void } | null = null;

    async function start() {
      setStatus("loading");
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
        const { FilesetResolver, HandLandmarker } = await import("@mediapipe/tasks-vision");
        const vision = await FilesetResolver.forVisionTasks(WASM_PATH);
        landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: MODEL_URL },
          runningMode: "VIDEO",
          numHands: 1,
        });
        if (stopped || !video.current) return;
        video.current.srcObject = stream;
        await video.current.play();
        setStatus("on");
        const loop = (now: number) => {
          if (stopped || !video.current || !landmarker) return;
          if (now - last >= FRAME_MS && video.current.readyState >= 2) {
            last = now;
            const result = landmarker.detectForVideo(video.current, now);
            onFrame(toGesture(result.landmarks[0] ?? null), now);
          }
          frame = requestAnimationFrame(loop);
        };
        frame = requestAnimationFrame(loop);
      } catch {
        if (!stopped) setStatus("error");
      }
    }

    start();
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      stream?.getTracks().forEach((track) => track.stop());
      landmarker?.close();
      hold.current = START;
      setStatus("off");
      setGesture(null);
      setProgress(0);
    };
    // onFrame only reads refs: the camera starts once each time it is turned on.
  }, [enabled]);

  const label = gesture === null ? "–" : gesture === "fist" ? "✊" : String(gesture);
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
                {t.gesture.error}
              </p>
            )}
            <p className="hint">{mode === "answer" ? t.gesture.help : t.gesture.nextHelp}</p>
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
