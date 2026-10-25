"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { Dict } from "@/lib/i18n";

// Daily goal in minutes; "today" follows the browser's time zone.
export default function GoalForm({ minutes, t }: { minutes: number; t: Dict }) {
  const router = useRouter();
  const [value, setValue] = useState(String(minutes));
  const [message, setMessage] = useState("");

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const response = await fetch("/api/study/goal", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ minutes: Number(value), timezone }),
    }).catch(() => null);
    setMessage(response?.ok ? t.goal.saved : t.goal.invalid);
    if (response?.ok) router.refresh();
  }

  return (
    <form onSubmit={save} className="row goal-form">
      <label className="field-label" htmlFor="goal-minutes">
        {t.goal.minutes}
      </label>
      <input
        id="goal-minutes"
        className="input"
        type="number"
        min={5}
        max={480}
        step={5}
        required
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit" className="btn btn-secondary btn-sm">
        {t.goal.save}
      </button>
      <span className="hint" aria-live="polite">
        {message}
      </span>
    </form>
  );
}
