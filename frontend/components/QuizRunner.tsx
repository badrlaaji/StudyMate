"use client";

import { useCallback, useEffect, useState } from "react";

import { colon, type Dict, type Lang } from "@/lib/i18n";

type Question = {
  notion_id: string;
  question: string;
  options: string[];
  answer_index: number;
  page: number;
  explanation: string;
};
type Answer = { notion_id: string; answer_index: number; chosen_index: number };
const QUIZ_SIZE = 3;

export default function QuizRunner({ lang, t }: { lang: Lang; t: Dict }) {
  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [result, setResult] = useState<{ scores: Record<string, number>; recorded: boolean } | null>(null);
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
        body: JSON.stringify({ n: QUIZ_SIZE, lang }),
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

  // Keys 1 to 4 answer the current question.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const option = Number(event.key) - 1;
      if (option >= 0 && option <= 3) choose(option);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [choose]);

  async function next() {
    if (!questions) return;
    if (index + 1 < questions.length) {
      setIndex(index + 1);
      setChosen(null);
      return;
    }
    const response = await fetch("/api/quiz/result", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ answers }),
    });
    setResult(response.ok ? await response.json() : { scores: {}, recorded: false });
  }

  if (!questions) {
    return (
      <div className="card">
        <button type="button" onClick={start} disabled={busy}>
          {busy ? t.quiz.loading : t.quiz.start}
        </button>
        {error && <p role="alert">{error}</p>}
      </div>
    );
  }
  if (questions.length === 0) {
    return <p role="alert">{t.quiz.empty}</p>;
  }
  if (result) {
    return (
      <section className="card" aria-live="polite">
        <h2>{result.recorded ? t.quiz.scores : t.quiz.notRecorded}</h2>
        <ul>
          {Object.entries(result.scores).map(([notion, score]) => (
            <li key={notion}>
              {notion} : {score} / 5
            </li>
          ))}
        </ul>
        <button type="button" onClick={start}>
          {t.quiz.again}
        </button>
      </section>
    );
  }

  const question = questions[index];
  const isCorrect = chosen === question.answer_index;
  return (
    <section className="card">
      {degraded && <p className="muted">{t.quiz.degraded}</p>}
      <p className="muted">
        {t.quiz.question} {index + 1} {t.quiz.of} {questions.length}
      </p>
      <h2>{question.question}</h2>
      <ol className="options">
        {question.options.map((option, i) => (
          <li key={i}>
            <button
              type="button"
              className={optionClass(i, chosen, question.answer_index)}
              onClick={() => choose(i)}
              disabled={chosen !== null}
            >
              {optionMark(i, chosen, question.answer_index)}
              {i + 1}. {option}
            </button>
          </li>
        ))}
      </ol>
      <div aria-live="polite">
        {chosen !== null && (
          <>
            <p>
              <strong>{isCorrect ? t.quiz.correct : t.quiz.wrong}</strong> {question.explanation}
            </p>
            <p>
              {t.quiz.source}
              {colon(lang)}
              <a href={`/api/book.pdf#page=${question.page}`} target="_blank" rel="noreferrer">
                p.{question.page}
              </a>
            </p>
            <button type="button" onClick={next}>
              {index + 1 < questions.length ? t.quiz.next : t.quiz.finish}
            </button>
          </>
        )}
      </div>
    </section>
  );
}

// After an answer: ✓ on the right option, ✗ on a wrong choice (not colour only).
function optionMark(i: number, chosen: number | null, answer: number): string {
  if (chosen === null) return "";
  if (i === answer) return "✓ ";
  return i === chosen ? "✗ " : "";
}

function optionClass(i: number, chosen: number | null, answer: number): string {
  if (chosen === null || i !== answer) return "secondary";
  return "";
}
