"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import Icon from "@/components/Icon";
import { fmt, pdfUrl, type Dict, type Lang } from "@/lib/i18n";

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
type Step = keyof Dict["study"]["steps"];

// No streaming (citations are checked before display): the steps only follow time.
const STEPS: { step: Step; afterMs: number }[] = [
  { step: "route", afterMs: 0 },
  { step: "search", afterMs: 700 },
  { step: "write", afterMs: 1600 },
  { step: "verify", afterMs: 3800 },
];

type Props = {
  lang: Lang;
  t: Dict;
  course: string;
  scope: string;
  examples: string[];
  initialPage?: number;
};

export default function StudyDesk({ lang, t, course, scope, examples, initialPage }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState<Step>("route");
  const [opened, setOpened] = useState<Citation | null>(initialPage ? { page: initialPage, excerpt: "" } : null);
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const reader = useRef<HTMLElement>(null);

  // On narrow screens the book is below the chat: scroll to it when a page opens.
  function openPage(citation: Citation) {
    setOpened(citation);
    if (window.matchMedia("(max-width: 1180px)").matches) {
      setTimeout(() => reader.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    }
  }

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

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function ask(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setMessages((old) => [...old, { role: "user", text: message }]);
    setQuestion("");
    setBusy(true);
    const timers = STEPS.map(({ step, afterMs }) => setTimeout(() => setStep(step), afterMs));
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message, lang, course }),
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

  function onComposerKey(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      ask(question);
    }
  }

  const suggestions = [
    ...examples.slice(0, 2).map((name) => fmt(t.study.explainNotion, { name })),
    t.study.quizMe,
    t.study.whatToReview,
  ];

  return (
    <div className="study">
      <section className="chat" aria-labelledby="study-title">
        <header className="page-head">
          <h1 id="study-title">{t.study.title}</h1>
          <p className="lede">{t.study.lede}</p>
        </header>

        <div className="thread" aria-live="polite">
          {messages.length === 0 && (
            <div className="card empty-chat">
              <h2>{t.study.emptyTitle}</h2>
              <p className="muted">{fmt(t.study.emptyText, { scope })}</p>
              <div className="suggestions">
                <span className="eyebrow">{t.study.try}</span>
                {suggestions.map((text) => (
                  <button key={text} type="button" className="suggestion" onClick={() => ask(text)}>
                    <Icon name="spark" />
                    {text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, index) =>
            message.role === "user" ? (
              <p key={index} className="msg msg-user">
                <span className="sr-only">{t.study.you}: </span>
                {message.text}
              </p>
            ) : (
              <article key={index} className="msg msg-bot">
                <span className="sr-only">{t.study.assistant}</span>
                {message.reply && <Badges reply={message.reply} t={t} />}
                {message.text && <p className="msg-text">{message.text}</p>}
                {message.reply?.route === "quiz" && message.reply.status !== "no_notions" && (
                  <Link className="btn btn-primary btn-sm" href="/quiz" style={{ justifySelf: "start" }}>
                    <Icon name="quiz" />
                    {t.study.goQuiz}
                  </Link>
                )}
                {message.reply?.route === "plan" && <PlanList plan={message.reply.plan ?? []} t={t} />}
                {message.reply && message.reply.citations.length > 0 && (
                  <div className="cites">
                    {message.reply.citations.map((citation) => (
                      <button
                        key={citation.page}
                        type="button"
                        className="chip"
                        aria-pressed={opened?.page === citation.page}
                        onClick={() => openPage(citation)}
                        title={fmt(t.study.openPage, { page: citation.page })}
                      >
                        <Icon name="book" />
                        p. {citation.page}
                      </button>
                    ))}
                  </div>
                )}
              </article>
            ),
          )}

          {busy && (
            <div role="status" aria-label={t.study.steps[step]}>
            <ol className="steps">
              {STEPS.map((item, i) => {
                const current = STEPS.findIndex((s) => s.step === step);
                const state = i < current ? "done" : i === current ? "active" : "todo";
                return (
                  <li key={item.step} className="step" data-state={state}>
                    {state === "done" && <Icon name="check" />}
                    {t.study.steps[item.step]}
                  </li>
                );
              })}
            </ol>
            </div>
          )}
          <div ref={end} />
        </div>

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            ask(question);
          }}
        >
          <label htmlFor="question" className="sr-only">
            {t.study.placeholder}
          </label>
          <textarea
            id="question"
            ref={input}
            rows={1}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={onComposerKey}
            placeholder={t.study.placeholder}
            maxLength={2000}
            aria-describedby="composer-hint"
          />
          <button type="submit" className="btn btn-primary" disabled={busy || !question.trim()}>
            <Icon name="send" />
            {t.study.ask}
          </button>
          <p id="composer-hint" className="hint" style={{ gridColumn: "1 / -1", padding: "0 var(--space-3) var(--space-1)" }}>
            {t.study.shortcut}
          </p>
        </form>
      </section>

      <aside ref={reader} className="card reader" aria-label={t.reader.title} data-empty={!opened}>
        {opened ? (
          <>
            <div className="reader-head">
              <span className="eyebrow">{t.reader.title}</span>
              <h2 style={{ fontSize: "var(--text-lg)" }}>{fmt(t.reader.page, { page: opened.page })}</h2>
              <span className="spacer" />
              <a className="btn btn-sm btn-ghost" href={pdfUrl(course, opened.page)} target="_blank" rel="noreferrer">
                <Icon name="external" />
                {t.reader.newTab}
              </a>
              <button type="button" className="btn btn-sm btn-ghost icon-btn" onClick={() => setOpened(null)} title={t.reader.close}>
                <Icon name="cross" label={t.reader.close} />
              </button>
            </div>
            {opened.excerpt && <blockquote className="excerpt">{opened.excerpt}…</blockquote>}
            <div className="pdf-frame">
              <PdfViewer
                course={course}
                page={opened.page}
                excerpt={opened.excerpt}
                loadingText={t.reader.loading}
                errorText={t.reader.error}
              />
            </div>
          </>
        ) : (
          <div className="reader-empty">
            <Icon name="book" />
            <h2 style={{ fontSize: "var(--text-lg)", color: "var(--ink)" }}>{t.reader.emptyTitle}</h2>
            <p style={{ maxWidth: "36ch" }}>{t.reader.emptyText}</p>
          </div>
        )}
      </aside>
    </div>
  );
}

function Badges({ reply, t }: { reply: Reply; t: Dict }) {
  const route = t.study.routes[reply.route as keyof Dict["study"]["routes"]] ?? reply.route;
  return (
    <div className="msg-meta">
      <span className="badge badge-route">
        <Icon name="spark" />
        {t.study.agent}: {route}
      </span>
      {reply.status === "ok" && reply.citations.length > 0 && (
        <span className="badge badge-ok">
          <Icon name="shield" />
          {t.study.verified}
        </span>
      )}
      {reply.status === "not_found" && (
        <span className="badge">
          <Icon name="info" />
          {t.study.notFound}
        </span>
      )}
      {reply.status === "no_notions" && (
        <span className="badge">
          <Icon name="info" />
          {t.study.noNotions}
        </span>
      )}
      {reply.status === "degraded" && (
        <span className="badge">
          <Icon name="alert" />
          {t.study.degraded}
        </span>
      )}
    </div>
  );
}

function PlanList({ plan, t }: { plan: PlanRow[]; t: Dict }) {
  if (plan.length === 0) return <p className="muted">{t.study.noPlan}</p>;
  return (
    <div className="stack" style={{ gap: "var(--space-2)" }}>
      <strong>{t.study.plan}</strong>
      <ol className="result-list">
        {plan.map((row) => (
          <li key={row.notion_id} className="result-row">
            <span>{row.name}</span>
            <span className="hint">{row.score.toFixed(1)} / 5</span>
            <div className="meter meter-WEAK" aria-hidden="true">
              <span style={{ width: `${(row.score / 5) * 100}%` }} />
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
