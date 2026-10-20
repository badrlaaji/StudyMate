"use client";

import { useState } from "react";

import type { Notion } from "@/lib/api";
import type { Dict, Lang } from "@/lib/i18n";

type Result = {
  covered: string[];
  missing: string[];
  errors: string[];
  score: number;
  follow_up: string;
  pages: number[];
  recorded: boolean;
};

const MIN_CHARS = 20;

export default function FeynmanForm({
  notions,
  lang,
  t,
  initialNotion,
}: {
  notions: Notion[];
  lang: Lang;
  t: Dict;
  initialNotion?: string;
}) {
  const [notionId, setNotionId] = useState(initialNotion ?? notions[0]?.id ?? "");
  const [explanation, setExplanation] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/feynman", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ notion_id: notionId, explanation, lang }),
      });
      if (!response.ok) throw new Error(String(response.status));
      setResult(await response.json());
    } catch {
      setError(t.study.error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form onSubmit={submit} className="card">
        <p>
          <label htmlFor="notion">{t.feynman.notion}</label>{" "}
          <select id="notion" value={notionId} onChange={(event) => setNotionId(event.target.value)}>
            {notions.map((notion) => (
              <option key={notion.id} value={notion.id}>
                {notion.name}
              </option>
            ))}
          </select>
        </p>
        <label htmlFor="explanation" className="sr-only">
          {t.feynman.placeholder}
        </label>
        <textarea
          id="explanation"
          rows={8}
          style={{ width: "100%" }}
          value={explanation}
          onChange={(event) => setExplanation(event.target.value)}
          placeholder={t.feynman.placeholder}
          maxLength={4000}
        />
        <p>
          <button type="submit" disabled={busy || explanation.trim().length < MIN_CHARS}>
            {busy ? t.feynman.checking : t.feynman.submit}
          </button>
        </p>
      </form>
      <div aria-live="polite">
        {error && <p role="alert">{error}</p>}
        {result && (
          <section className="card" style={{ marginTop: "1rem" }}>
            <h2>
              {t.feynman.score}
              {lang === "fr" ? " : " : ": "}
              {result.score} / 5
            </h2>
            {!result.recorded && <p className="muted">{t.feynman.notRecorded}</p>}
            <h3>{t.feynman.covered}</h3>
            <ul>{result.covered.map((idea) => <li key={idea}>✓ {idea}</li>)}</ul>
            <h3>{t.feynman.missing}</h3>
            <ul>{result.missing.map((idea) => <li key={idea}>✗ {idea}</li>)}</ul>
            <h3>{t.feynman.errors}</h3>
            {result.errors.length === 0 ? (
              <p>{t.feynman.noErrors}</p>
            ) : (
              <ul>{result.errors.map((item) => <li key={item}>{item}</li>)}</ul>
            )}
            <h3>{t.feynman.followUp}</h3>
            <p className="excerpt">{result.follow_up}</p>
            <h3>{t.feynman.pages}</h3>
            <p>
              {result.pages.map((page) => (
                <a key={page} href={`/api/book.pdf#page=${page}`} target="_blank" rel="noreferrer" style={{ marginRight: "0.5rem" }}>
                  p.{page}
                </a>
              ))}
            </p>
          </section>
        )}
      </div>
    </>
  );
}
