import Icon from "@/components/Icon";
import OpenCourse from "@/components/OpenCourse";
import type { Course } from "@/lib/api";
import { fmt, type Dict } from "@/lib/i18n";
import { getSession } from "@/lib/lang";

export default async function LibraryPage() {
  const { t, courses, course } = await getSession();
  return (
    <div className="page">
      <header className="page-head">
        <h1>{t.library.title}</h1>
        <p className="lede">{t.library.lede}</p>
      </header>
      {courses.length === 0 && (
        <p className="callout callout-warn" role="alert">
          <Icon name="alert" />
          {t.study.error}
        </p>
      )}
      <ul className="courses" style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {courses.map((item) => (
          <li key={item.id} className="card course-card" data-current={item.id === course?.id}>
            <div className="course-cover">{item.title}</div>
            <div className="stack" style={{ gap: "var(--space-1)" }}>
              <strong>{item.scope}</strong>
              <span className="hint">
                {item.attribution} · {item.license}
              </span>
            </div>
            <Readiness course={item} t={t} />
            <div className="row">
              {item.id === course?.id ? (
                <span className="badge badge-route">
                  <Icon name="check" />
                  {t.library.current}
                </span>
              ) : (
                <OpenCourse course={item.id} label={t.library.open} />
              )}
              <a className="btn btn-ghost btn-sm" href={item.book_url} target="_blank" rel="noreferrer">
                <Icon name="external" />
                {t.library.bookPage}
              </a>
            </div>
          </li>
        ))}
      </ul>

      <section className="card stack" aria-labelledby="add-title">
        <div className="card-title" style={{ marginBottom: 0 }}>
          <Icon name="plus" />
          <h2 id="add-title">{t.library.addTitle}</h2>
        </div>
        <p className="muted">{t.library.addIntro}</p>
        <ol className="steps-add">
          <li>
            <div>
              {t.library.add1}
              <code className="code">{`{ "id": "statistics", "title": "Introductory Statistics 2e",
  "pdf_url": "https://assets.openstax.org/…/introductory-statistics-2e_-_WEB.pdf",
  "license": "CC BY-NC-SA 4.0", "chapters": [12], … }`}</code>
            </div>
          </li>
          <li>
            <div>
              {t.library.add2}
              <code className="code">uv run python -m course.add statistics</code>
            </div>
          </li>
          <li>
            <div>{t.library.add3}</div>
          </li>
        </ol>
      </section>
    </div>
  );
}

function Readiness({ course, t }: { course: Course; t: Dict }) {
  const indexed =
    course.chunks === null
      ? t.library.dbDown
      : course.chunks > 0
        ? fmt(t.library.indexed, { count: course.chunks })
        : t.library.notIndexed;
  const notions =
    course.notions > 0
      ? `${fmt(t.library.notions, { count: course.notions })} (${course.validated ? t.library.validated : t.library.draft})`
      : t.library.noNotions;
  const items: [boolean, string][] = [
    [course.pdf, course.pdf ? t.library.pdf : t.library.noPdf],
    [(course.chunks ?? 0) > 0, indexed],
    [course.notions > 0, notions],
  ];
  return (
    <ul className="checklist">
      {items.map(([done, text]) => (
        <li key={text} className={done ? "check-yes" : "check-no"}>
          <Icon name={done ? "check" : "minus"} />
          {text}
        </li>
      ))}
    </ul>
  );
}
