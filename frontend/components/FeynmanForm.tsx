"use client";

import Link from "next/link";
import { useState } from "react";

import Icon from "@/components/Icon";
import type { Notion } from "@/lib/api";
import { fmt, type Dict, type Lang } from "@/lib/i18n";

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
const MAX_SCORE = 5;

type Props = { notions: Notion[]; lang: Lang; t: Dict; course: string; initialNotion?: string };

export default function FeynmanForm({ notions, lang, t, course, initialNotion }: Props) {
  const known = notions.some((n) => n.id === initialNotion);
  const [notionId, setNotionId] = useState(known ? initialNotion! : (notions[0]?.id ?? ""));
  const [explanation, setExplanation] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const notion = notions.find((n) => n.id === notionId);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/feynman", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ notion_id: notionId, explanation, lang, course }),
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
    <div className="feynman">
      <form onSubmit={submit} className="card stack">
        <div className="field">
          <label className="field-label" htmlFor="notion">
            {t.feynman.notion}
          </label>
          <select
            id="notion"
            className="select"
            value={notionId}
            onChange={(event) => {
              setNotionId(event.target.value);
              setResult(null);
            }}
          >
            {notions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {notion && (
            <span className="hint">
              {notion.section} · {fmt(t.feynman.ideas, { count: notion.key_ideas.length })}
            </span>
          )}
        </div>
        <div className="field">
          <label className="field-label" htmlFor="explanation">
            {t.feynman.explanation}
          </label>
          <textarea
            id="explanation"
            className="textarea"
            rows={10}
            value={explanation}
            onChange={(event) => setExplanation(event.target.value)}
            placeholder={t.feynman.placeholder}
            maxLength={4000}
            aria-describedby="chars"
          />
          <span id="chars" className="hint">
            {fmt(t.feynman.chars, { count: explanation.trim().length })}
          </span>
        </div>
        <button
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={busy || explanation.trim().length < MIN_CHARS}
          style={{ justifySelf: "start" }}
        >
          <Icon name="feynman" />
          {busy ? t.feynman.checking : t.feynman.submit}
        </button>
      </form>

      <section className="card stack" aria-labelledby="feedback-title" aria-live="polite" aria-busy={busy}>
        <h2 id="feedback-title">{t.feynman.resultTitle}</h2>
        {error && (
          <p className="callout callout-warn" role="alert">
            <Icon name="alert" />
            {error}
          </p>
        )}
        {!result && !error && <p className="muted">{busy ? t.feynman.checking : t.feynman.resultEmpty}</p>}
        {result && <Feedback result={result} t={t} />}
      </section>
    </div>
  );
}

function Feedback({ result, t }: { result: Result; t: Dict }) {
  return (
    <>
      <div className="gauge">
        <span className="eyebrow">{t.feynman.score}</span>
        <span className="gauge-value">
          {result.score}
          <small> / {MAX_SCORE}</small>
        </span>
        <div className="gauge-segments" aria-hidden="true">
          {Array.from({ length: MAX_SCORE }, (_, i) => (
            <span key={i} data-on={i < result.score} />
          ))}
        </div>
        <span className="hint">{result.recorded ? t.feynman.recorded : t.feynman.notRecorded}</span>
      </div>

      <Ideas title={t.feynman.covered} items={result.covered} ok />
      <Ideas title={t.feynman.missing} items={result.missing} ok={false} />

      <div className="stack" style={{ gap: "var(--space-2)" }}>
        <h3>{t.feynman.errors}</h3>
        {result.errors.length === 0 ? (
          <p className="muted">{t.feynman.noErrors}</p>
        ) : (
          <ul className="ideas">
            {result.errors.map((item) => (
              <li key={item} className="idea idea-miss">
                <Icon name="alert" />
                {item}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="stack" style={{ gap: "var(--space-2)" }}>
        <h3>{t.feynman.followUp}</h3>
        <p className="excerpt follow-up">{result.follow_up}</p>
      </div>

      <div className="stack" style={{ gap: "var(--space-2)" }}>
        <h3>{t.feynman.pages}</h3>
        <div className="row">
          {result.pages.map((page) => (
            <Link key={page} className="chip" href={`/study?page=${page}`} title={fmt(t.study.openPage, { page })}>
              <Icon name="book" />
              p. {page}
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}

function Ideas({ title, items, ok }: { title: string; items: string[]; ok: boolean }) {
  if (items.length === 0) return null;
  return (
    <div className="stack" style={{ gap: "var(--space-2)" }}>
      <h3>
        {title} <span className="muted">({items.length})</span>
      </h3>
      <ul className="ideas">
        {items.map((idea) => (
          <li key={idea} className={`idea ${ok ? "idea-ok" : "idea-miss"}`}>
            <Icon name={ok ? "check" : "cross"} />
            {idea}
          </li>
        ))}
      </ul>
    </div>
  );
}
