import Link from "next/link";

import Icon from "@/components/Icon";
import type { Review } from "@/lib/api";
import { fmt, whenLabel, type Dict } from "@/lib/i18n";

const MAX_ROWS = 6;

// Spaced repetition: the next review of each practised notion, the most urgent first.
export default function NextReviews({ reviews, t }: { reviews: Review[]; t: Dict }) {
  return (
    <section className="card stack" aria-labelledby="reviews-title">
      <div className="page-head">
        <h2 id="reviews-title">{t.reviews.title}</h2>
        <p className="muted">{t.reviews.intro}</p>
      </div>
      {reviews.length === 0 ? (
        <p className="callout">
          <Icon name="info" />
          {t.reviews.empty}
        </p>
      ) : (
        <ol className="review-list">
          {reviews.slice(0, MAX_ROWS).map((row) => {
            const due = row.days_left <= 0;
            return (
              <li key={row.notion_id} className="review-row" data-due={due}>
                <span className={`badge ${due ? "badge-due" : ""}`}>
                  <Icon name={due ? "alert" : "dot"} />
                  {whenLabel(row.days_left, t)}
                </span>
                <strong className="notion-name">{row.name}</strong>
                <span className="hint">{row.reviews === 1 ? t.reviews.countOne : fmt(t.reviews.count, { count: row.reviews })}</span>
                <span className="row">
                  {row.pages[0] && (
                    <Link className="chip" href={`/study?page=${row.pages[0]}`} title={fmt(t.study.openPage, { page: row.pages[0] })}>
                      <Icon name="book" />
                      p. {row.pages[0]}
                    </Link>
                  )}
                  {due && (
                    <Link className="btn btn-sm btn-primary" href="/quiz">
                      <Icon name="quiz" />
                      {t.reviews.start}
                    </Link>
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
