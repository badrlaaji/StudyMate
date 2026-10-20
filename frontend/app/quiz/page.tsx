import Icon from "@/components/Icon";
import QuizRunner from "@/components/QuizRunner";
import { getNotions } from "@/lib/api";
import { getSession } from "@/lib/lang";

export default async function QuizPage() {
  const { lang, t, course } = await getSession();
  const notions = course ? await getNotions(lang, course.id) : [];
  const names = Object.fromEntries(notions.map((notion) => [notion.id, notion.name]));
  return (
    <div className="page">
      <header className="page-head quiz">
        <span className="eyebrow">{course?.title}</span>
        <h1>{t.quiz.title}</h1>
        <p className="lede">{t.quiz.lede}</p>
      </header>
      {course && notions.length > 0 ? (
        <QuizRunner key={course.id} lang={lang} t={t} course={course.id} names={names} />
      ) : (
        <p className="callout quiz">
          <Icon name="info" />
          <span>
            {t.map.noNotions}
            <code className="code">uv run python -m course.add {course?.id ?? "<id>"}</code>
          </span>
        </p>
      )}
    </div>
  );
}
