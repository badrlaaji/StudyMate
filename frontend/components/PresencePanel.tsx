"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import Icon from "@/components/Icon";
import { fmt, type Dict } from "@/lib/i18n";
import {
  activeSeconds,
  advance,
  duration,
  FRAME_MS,
  isPaused,
  onFrame,
  onVisibility,
  pause,
  resume,
  start,
  SYNC_MS,
  type Presence,
} from "@/lib/presence";

// Face detection only says "a face is there or not"; the model comes from Google's official host.
const WASM_PATH = "/mediapipe";
const FACE_MODEL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite";

type Detector = { detectForVideo: (v: HTMLVideoElement, t: number) => { detections: unknown[] }; close: () => void };
type Props = { t: Dict; course: string; canSave: boolean };

export default function PresencePanel({ t, course, canSave }: Props) {
  const [useCamera, setUseCamera] = useState(false); // off by default
  const [cameraStatus, setCameraStatus] = useState<"off" | "loading" | "on" | "error">("off");
  const [presence, setPresence] = useState<Presence | null>(null);
  const [message, setMessage] = useState("");
  const current = useRef<Presence | null>(null);
  const sessionId = useRef<number | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const detector = useRef<Detector | null>(null);

  // Send the total of active seconds (never an image); announce new trophies.
  async function sync(): Promise<boolean> {
    if (sessionId.current === null || !current.current) return false;
    const response = await fetch(`/api/study/sessions/${sessionId.current}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ active_seconds: activeSeconds(current.current) }),
    }).catch(() => null);
    if (!response?.ok) return false;
    const body: { newTrophies: string[] } = await response.json();
    const names = body.newTrophies.map((code) => t.trophies.names[code as keyof Dict["trophies"]["names"]] ?? code);
    if (names.length > 0) setMessage(names.map((name) => fmt(t.presence.trophy, { name })).join(" · "));
    return true;
  }

  // Every state change goes through here: a new pause sends the total at once.
  function update(next: Presence) {
    const before = current.current;
    current.current = next;
    setPresence(next);
    if (before && !isPaused(before.state) && isPaused(next.state)) sync();
  }

  async function begin() {
    setMessage("");
    const response = await fetch("/api/study/sessions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ course, mode: useCamera ? "CAMERA" : "MANUAL" }),
    }).catch(() => null);
    if (!response?.ok) {
      setMessage(t.presence.notSaved);
      return;
    }
    sessionId.current = (await response.json()).id;
    update(start(Date.now(), useCamera));
  }

  async function end() {
    if (current.current) current.current = advance(current.current, Date.now());
    const saved = await sync();
    const seconds = current.current ? activeSeconds(current.current) : 0;
    setMessage(saved ? fmt(t.presence.stopped, { time: duration(seconds) }) : t.presence.notSaved);
    sessionId.current = null;
    current.current = null;
    setPresence(null);
  }

  const running = presence !== null;

  // Clock (and camera frame) once a second, sync every minute, pause when the tab is hidden.
  useEffect(() => {
    if (!running) return;
    const clock = setInterval(() => {
      const p = current.current;
      if (!p) return;
      const now = Date.now();
      const camera = detector.current && video.current && video.current.readyState >= 2;
      if (p.camera && camera) {
        const face = detector.current!.detectForVideo(video.current!, performance.now()).detections.length > 0;
        update(onFrame(p, now, face));
      } else {
        update(advance(p, now));
      }
    }, FRAME_MS);
    const every = setInterval(sync, SYNC_MS);
    const onHidden = () => current.current && update(onVisibility(current.current, Date.now(), document.hidden));
    document.addEventListener("visibilitychange", onHidden);
    return () => {
      clearInterval(clock);
      clearInterval(every);
      document.removeEventListener("visibilitychange", onHidden);
    };
    // update and sync only read refs: one setup per running session.
  }, [running]);

  // Camera: started with the session if chosen, released as soon as it stops.
  useEffect(() => {
    if (!running || !presence?.camera) return;
    let stopped = false;
    let stream: MediaStream | null = null;
    async function open() {
      setCameraStatus("loading");
      try {
        // 640x480: at 320x240 a face at desk distance is too small for the short-range model (tested).
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
        const { FilesetResolver, FaceDetector } = await import("@mediapipe/tasks-vision");
        const vision = await FilesetResolver.forVisionTasks(WASM_PATH);
        const face = await FaceDetector.createFromOptions(vision, { baseOptions: { modelAssetPath: FACE_MODEL }, runningMode: "VIDEO" });
        if (stopped || !video.current) return face.close();
        video.current.srcObject = stream;
        await video.current.play();
        detector.current = face;
        setCameraStatus("on");
      } catch {
        if (stopped) return;
        setCameraStatus("error"); // the manual timer goes on
        if (current.current) update({ ...current.current, camera: false });
      }
    }
    open();
    return () => {
      stopped = true;
      stream?.getTracks().forEach((track) => track.stop());
      detector.current?.close();
      detector.current = null;
      setCameraStatus("off");
    };
  }, [running, presence?.camera]);

  const seconds = presence ? activeSeconds(presence) : 0;
  return (
    <section className="card presence stack" aria-labelledby="presence-title">
      <div className="row">
        <h2 id="presence-title" className="gesture-title">
          <Icon name="progress" />
          {t.presence.title}
        </h2>
        <span className="spacer" />
        {cameraStatus === "on" && (
          <span className="badge badge-live">
            <Icon name="dot" />
            {t.presence.cameraOn}
          </span>
        )}
      </div>
      {!canSave ? (
        <p className="callout">
          <Icon name="info" />
          <span>
            {t.presence.signIn} <Link href="/login">{t.account.signIn}</Link>
          </span>
        </p>
      ) : !running ? (
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          <p className="muted">{t.presence.lede}</p>
          <label className="check">
            <input type="checkbox" checked={useCamera} onChange={(e) => setUseCamera(e.target.checked)} />
            {t.presence.camera}
          </label>
          <p className="hint">{t.presence.privacy}</p>
          <button type="button" className="btn btn-primary" onClick={begin} style={{ justifySelf: "start" }}>
            <Icon name="arrow" />
            {t.presence.start}
          </button>
        </div>
      ) : (
        <div className="presence-live">
          {presence.camera && <video ref={video} className="presence-video" muted playsInline aria-hidden="true" />}
          <div className="stack" style={{ gap: "var(--space-1)" }}>
            <span className={`badge ${isPaused(presence.state) ? "" : "badge-ok"}`}>
              <Icon name={isPaused(presence.state) ? "minus" : "check"} />
              {t.presence.states[presence.state]}
            </span>
            <span className="eyebrow">{t.presence.estimated}</span>
            <strong className="presence-time" role="timer" aria-live="off">
              {duration(seconds)}
            </strong>
          </div>
          <div className="row">
            {presence.state === "PAUSE_MANUAL" ? (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => update(resume(presence, Date.now()))}>
                {t.presence.resume}
              </button>
            ) : (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => update(pause(presence, Date.now()))}>
                {t.presence.pause}
              </button>
            )}
            <button type="button" className="btn btn-ghost btn-sm" onClick={end}>
              {t.presence.stop}
            </button>
          </div>
        </div>
      )}
      {cameraStatus === "error" && (
        <p className="callout callout-warn" role="alert">
          <Icon name="alert" />
          {t.presence.cameraError}
        </p>
      )}
      <p className="gesture-message" aria-live="polite">
        {running ? t.presence.states[presence.state] : ""} {message}
      </p>
    </section>
  );
}
