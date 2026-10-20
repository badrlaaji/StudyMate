"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

import type { Dict, Lang } from "@/lib/i18n";

// react-pdf runs only in the browser and is loaded when the panel first opens.
const PdfViewer = dynamic(() => import("@/components/PdfViewer"), { ssr: false });

type Citation = { page: number; excerpt: string };
type PlanRow = { notion_id: string; name: string; score: number; pages: number[] };
type Reply = {
  route: string;
  answer: string | null;
  citations: Citation[];
  status: string;
  plan?: PlanRow[] | null;
};
type Message = { role: "user" | "assistant"; text: string; reply?: Reply };

// No streaming (citations are checked before display): the step labels only follow time.
const STEP_DELAYS_MS = { write: 1500, verify: 4000 };

export default function StudyDesk({ lang, t }: { lang: Lang; t: Dict }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState<keyof Dict["study"]["steps"]>("search");
  const [opened, setOpened] = useState<Citation | null>(null);
  const input = useRef<HTMLInputElement>(null);

  // "/" focuses the question box, unless the user is already typing somewhere.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const typing = event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement;
      if (event.key === "/" && !typing) {
        event.preventDefault();
        input.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy) return;
    setMessages((old) => [...old, { role: "user", text }]);
    setQuestion("");
    setBusy(true);
    setStep("search");
    const timers = [
      setTimeout(() => setStep("write"), STEP_DELAYS_MS.write),
      setTimeout(() => setStep("verify"), STEP_DELAYS_MS.verify),
    ];
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: text, lang }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const reply: Reply = await response.json();
      setMessages((old) => [...old, { role: "assistant", text: reply.answer ?? "", reply }]);
      if (reply.citations.length > 0) setOpened(reply.citations[0]);
    } catch {
      setMessages((old) => [...old, { role: "assistant", text: t.study.error }]);
    } finally {
      timers.forEach(clearTimeout);
      setBusy(false);
    }
  }

  return (
    <div className="study">
      <section aria-label={t.study.title}>
        <h1>{t.study.title}</h1>
        <div className="messages" aria-live="polite">
          {messages.length === 0 && <p className="muted">{t.study.empty}</p>}
          {messages.map((message, index) => (
            <article key={index} className="card">
              <strong>{message.role === "user" ? t.study.you : t.study.assistant}</strong>
              {message.reply && <Badges reply={message.reply} t={t} />}
              <p>{message.text}</p>
              {message.reply?.route === "quiz" && <a href="/quiz">{t.chat.goQuiz}</a>}
              {message.reply?.route === "plan" && (
                <>
                  <p>{t.chat.plan}</p>
                  <ol>
                    {(message.reply.plan ?? []).map((row) => (
                      <li key={row.notion_id}>
                        {row.name} ({row.score.toFixed(1)} / 5), p.{row.pages[0]}
                      </li>
                    ))}
                  </ol>
                </>
              )}
              {message.reply?.citations.map((citation) => (
                <button
                  key={citation.page}
                  type="button"
                  className="page-link"
                  onClick={() => setOpened(citation)}
                  aria-label={`${t.study.openPage} ${citation.page}`}
                >
                  [p.{citation.page}]
                </button>
              ))}
            </article>
          ))}
          {busy && <p className="muted" role="status">{t.study.steps[step]}</p>}
        </div>
        <form className="ask" onSubmit={ask}>
          <label htmlFor="question" className="sr-only">
            {t.study.placeholder}
          </label>
          <input
            id="question"
            ref={input}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t.study.placeholder}
            maxLength={2000}
          />
          <button type="submit" disabled={busy}>
            {t.study.ask}
          </button>
        </form>
      </section>
      <aside className="pdf-panel card" aria-label={t.study.pdfTitle}>
        {opened ? (
          <>
            <p>
              <strong>
                {t.study.pdfTitle}, {t.pdf.page} {opened.page}
              </strong>{" "}
              (<a href={`/api/book.pdf#page=${opened.page}`} target="_blank" rel="noreferrer">
                {t.study.newTab}
              </a>){" "}
              <button type="button" className="secondary" onClick={() => setOpened(null)}>
                {t.study.close}
              </button>
            </p>
            <blockquote className="excerpt">{opened.excerpt}…</blockquote>
            <PdfViewer page={opened.page} excerpt={opened.excerpt} loadingText={t.pdf.loading} errorText={t.pdf.error} />
          </>
        ) : (
          <p className="muted">{t.study.pdfTitle}</p>
        )}
      </aside>
    </div>
  );
}

function Badges({ reply, t }: { reply: Reply; t: Dict }) {
  return (
    <p>
      <span className="badge">
        {t.study.route}: {reply.route}
      </span>
      {reply.status === "ok" && reply.citations.length > 0 && <span className="badge ok">{t.study.verified}</span>}
      {reply.status === "not_found" && <span className="badge">{t.study.notFound}</span>}
      {reply.status === "degraded" && <span className="badge">{t.study.degraded}</span>}
    </p>
  );
}
