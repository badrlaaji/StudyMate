"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Icon from "@/components/Icon";
import OpenCourse from "@/components/OpenCourse";
import type { Dict } from "@/lib/i18n";

const STEPS = ["queued", "indexing", "drafting", "ready"] as const;
const RUNNING = new Set(["queued", "indexing", "drafting"]);
const POLL_MS = 2000;

type Props = {
  courseId: string;
  initialState: string;
  initialDetail?: string;
  t: Dict;
  canDelete?: boolean;
  showOpen?: boolean;
};

// Processing of an uploaded course: steps, polling, retry, delete.
export default function CourseJob({
  courseId,
  initialState,
  initialDetail = "",
  t,
  canDelete = false,
  showOpen = true,
}: Props) {
  const router = useRouter();
  const [state, setState] = useState(initialState);
  const [detail, setDetail] = useState(initialDetail);
  const L = t.library;

  // Ask the API every 2 s while the course is being processed.
  useEffect(() => {
    if (!RUNNING.has(state)) return;
    const timer = setInterval(async () => {
      const response = await fetch(`/api/courses/${courseId}/status`);
      if (!response.ok) return;
      const body = await response.json();
      setDetail(body.detail);
      if (body.state !== state) {
        setState(body.state);
        if (!RUNNING.has(body.state)) router.refresh(); // counts on the card change
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [state, courseId, router]);

  async function retry() {
    const response = await fetch(`/api/courses/${courseId}/retry`, { method: "POST" });
    if (response.ok) setState("queued");
  }

  async function remove() {
    if (!window.confirm(L.confirmDelete)) return;
    const response = await fetch(`/api/courses/${courseId}`, { method: "DELETE" });
    if (response.ok) router.refresh();
  }

  const current = STEPS.indexOf(state as (typeof STEPS)[number]);
  return (
    <div className="stack" style={{ gap: "var(--space-3)" }}>
      {state !== "ready" && (
        // The status region wraps the list: role="status" on <ol> would drop its list items.
        <div role="status" aria-label={L.jobs[state as keyof typeof L.jobs] ?? state}>
          <ol className="steps">
          {STEPS.slice(0, 3).map((step, index) => {
            const status =
              state === "failed" ? "todo" : index < current ? "done" : index === current ? "active" : "todo";
            return (
              <li key={step} className="step" data-state={status}>
                {status === "done" && <Icon name="check" />}
                {L.jobs[step]}
              </li>
            );
          })}
          </ol>
        </div>
      )}
      {state === "failed" && (
        <p className="callout callout-warn" role="alert">
          <Icon name="alert" />
          <span>
            {L.jobs.failed}
            {detail ? ` — ${detail}` : ""}
          </span>
        </p>
      )}
      {state === "ready" && (
        <p className="callout callout-ok">
          <Icon name="check" />
          {L.readyText}
        </p>
      )}
      <div className="row">
        {state === "ready" && showOpen && <OpenCourse course={courseId} label={L.open} />}
        {state === "failed" && (
          <button type="button" className="btn btn-primary" onClick={retry}>
            <Icon name="refresh" />
            {L.retry}
          </button>
        )}
        {canDelete && !RUNNING.has(state) && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={remove}>
            <Icon name="cross" />
            {L.delete}
          </button>
        )}
      </div>
    </div>
  );
}
