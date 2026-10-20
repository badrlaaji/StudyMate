"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Icon from "@/components/Icon";
import { fmt, type Dict, type Lang } from "@/lib/i18n";

type Question = {
  notion_id: string;
  question: string;
  options: string[];
  answer_index: number;
  page: number;
  explanation: string;
};
type Answer = { notion_id: string; answer_index: number; chosen_index: number };
type Result = { scores: Record<string, number>; recorded: boolean };
const QUIZ_SIZE = 3;

type Props = { lang: Lang; t: Dict; course: string; names: Record<string, string> };

export default function QuizRunner({ lang, t, course, names }: Props) {
  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function start() {
    setBusy(true);
    setError("");
    setQuestions(null);
    setResult(null);
    setAnswers([]);
    setIndex(0);
    setChosen(null);
    try {
      const response = await fetch("/api/quiz", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ n: QUIZ_SIZE, lang, course }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const body = await response.json();
      setQuestions(body.questions);
      setDegraded(body.status === "degraded");
    } catch {
      setError(t.study.error);
    } finally {
      setBusy(false);
    }
  }

  // Correction by code: compare the chosen option with the answer key.
  const choose = useCallback(
    (option: number) => {
      if (!questions || chosen !== null || option >= questions[index].options.length) return;
      const question = questions[index];
      setChosen(option);
      setAnswers((old) => [...old, { notion_id: question.notion_id, answer_index: question.answer_index, chosen_index: option }]);
    },
    [questions, index, chosen],
  );

  const next = useCallback(async () => {
    if (!questions || chosen === null) return;
    if (index + 1 < questions.length) {
      setIndex(index + 1);
      setChosen(null);
      return;
    }
    const response = await fetch("/api/quiz/result", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ answers, course }),
    });
    setResult(response.ok ? await response.json() : { scores: {}, recorded: false });
  }, [questions, chosen, index, answers, course]);

  // Keys 1 to 4 answer the current question; Enter goes to the next one.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.target instanceof HTMLButtonElement && event.key === "Enter") return; // native click
      const option = Number(event.key) - 1;
      if (option >= 0 && option <= 3) choose(option);
      if (event.key === "Enter") next();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [choose, next]);

  if (!questions) {
    return (
      <section className="card quiz stack" style={{ justifyItems: "start" }}>
        <p className="muted">{t.quiz.keys}</p>
        <div className="row">
          <kbd>1</kbd>
          <kbd>2</kbd>
          <kbd>3</kbd>
          <kbd>4</kbd>
          <kbd>↵</kbd>
        </div>
        <button type="button" className="btn btn-primary btn-lg" onClick={start} disabled={busy}>
          <Icon name="quiz" />
          {busy ? t.quiz.loading : t.quiz.start}
        </button>
        {error && (
          <p className="callout callout-warn" role="alert">
            <Icon name="alert" />
            {error}
          </p>
        )}
      </section>
    );
  }
  if (questions.length === 0) {
    return (
      <section className="card quiz stack" style={{ justifyItems: "start" }}>
        <p role="alert">{t.quiz.empty}</p>
        <button type="button" className="btn btn-secondary" onClick={start}>
          <Icon name="refresh" />
          {t.quiz.again}
        </button>
      </section>
    );
  }
  if (result) {
    return (
      <section className="card quiz stack" aria-live="polite">
        <h2>{t.quiz.resultTitle}</h2>
        <ul className="result-list">
          {Object.entries(result.scores).map(([notion, score]) => (
            <li key={notion} className="result-row">
              <strong>{names[notion] ?? notion}</strong>
              <span className="hint">{score} / 5</span>
              <div className="meter" aria-hidden="true">
                <span style={{ width: `${(score / 5) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
        <p className="hint">{result.recorded ? t.quiz.recorded : t.quiz.notRecorded}</p>
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={start}>
            <Icon name="refresh" />
            {t.quiz.again}
          </button>
          <Link className="btn btn-secondary" href="/">
            <Icon name="progress" />
            {t.nav.map}
          </Link>
        </div>
      </section>
    );
  }

  const question = questions[index];
  const isCorrect = chosen === question.answer_index;
  return (
    <section className="card quiz stack" aria-labelledby="quiz-question">
      {degraded && (
        <p className="callout callout-warn">
          <Icon name="alert" />
          {t.quiz.degraded}
        </p>
      )}
      <div className="stack" style={{ gap: "var(--space-2)" }}>
        <span className="eyebrow">
          {fmt(t.quiz.question, { index: index + 1, total: questions.length })} · {names[question.notion_id] ?? ""}
        </span>
        <div className="progress" aria-hidden="true">
          <span style={{ width: `${((index + (chosen === null ? 0 : 1)) / questions.length) * 100}%` }} />
        </div>
      </div>
      <h2 id="quiz-question" className="quiz-question">
        {question.question}
      </h2>
      <ol className="options">
        {question.options.map((option, i) => (
          <li key={i}>
            <button
              type="button"
              className={`option ${optionClass(i, chosen, question.answer_index)}`}
              onClick={() => choose(i)}
              disabled={chosen !== null}
            >
              <kbd>{i + 1}</kbd>
              <span>{option}</span>
              <OptionMark i={i} chosen={chosen} answer={question.answer_index} t={t} />
            </button>
          </li>
        ))}
      </ol>
      <div aria-live="polite">
        {chosen !== null && (
          <div className="feedback">
            <p>
              <strong>{isCorrect ? t.quiz.correct : t.quiz.wrong}</strong> {question.explanation}
            </p>
            <div className="row">
              <span className="hint">{t.quiz.source}</span>
              <Link className="chip" href={`/study?page=${question.page}`} title={fmt(t.study.openPage, { page: question.page })}>
                <Icon name="book" />
                p. {question.page}
              </Link>
              <span className="spacer" />
              <button type="button" className="btn btn-primary" onClick={next} autoFocus>
                {index + 1 < questions.length ? t.quiz.next : t.quiz.finish}
                <Icon name="arrow" />
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

// After an answer: a check on the right option, a cross on a wrong choice (not colour only).
function OptionMark({ i, chosen, answer, t }: { i: number; chosen: number | null; answer: number; t: Dict }) {
  if (chosen === null || (i !== answer && i !== chosen)) return <span />;
  const right = i === answer;
  return (
    <span className="mark">
      <Icon name={right ? "check" : "cross"} label={right ? t.quiz.correct : t.quiz.wrong} />
    </span>
  );
}

function optionClass(i: number, chosen: number | null, answer: number): string {
  if (chosen === null) return "";
  if (i === answer) return "is-correct";
  return i === chosen ? "is-wrong" : "";
}
