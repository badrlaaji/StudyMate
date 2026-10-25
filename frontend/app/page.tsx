import Link from "next/link";

import Icon from "@/components/Icon";
import MasteryMap from "@/components/MasteryMap";
import StudyProgress from "@/components/StudyProgress";
import { getMastery, getNotions, getPlan, getReviews, getStudySummary, getTrophies } from "@/lib/api";
import { isDemo } from "@/lib/demo";
import { getSession } from "@/lib/lang";

export default async function ProgressPage() {
  const { lang, t, course, account } = await getSession();
  if (!course) return <ApiDown text={t.study.error} />;
  const presence = account !== null || isDemo(); // study time needs an account (or the demo)
  const [notions, mastery, plan, review, summary, trophies] = await Promise.all([
    getNotions(lang, course.id),
    getMastery(course.id),
    getPlan(lang, course.id),
    getReviews(lang, course.id),
    presence ? getStudySummary() : Promise.resolve(null),
    presence ? getTrophies() : Promise.resolve([]),
  ]);
  return (
    <div className="page">
      <header className="page-head">
        <span className="eyebrow">{t.map.eyebrow}</span>
        <h1>{course.title}</h1>
        <p className="lede">
          {course.scope}. {t.map.intro}
        </p>
      </header>
      {mastery.status === "signed_out" && (
        <p className="callout" role="status">
          <Icon name="info" />
          <span>
            {t.account.progress} <Link href="/login">{t.account.signIn}</Link>
          </span>
        </p>
      )}
      {mastery.status === "degraded" && (
        <p className="callout callout-warn" role="status">
          <Icon name="alert" />
          {t.map.degraded}
        </p>
      )}
      {summary && <StudyProgress summary={summary} trophies={trophies} t={t} lang={lang} />}
      {notions.length === 0 ? (
        <p className="callout">
          <Icon name="info" />
          <span>
            {t.map.noNotions}
            <code className="code">uv run python -m course.add {course.id}</code>
          </span>
        </p>
      ) : (
        <MasteryMap
          notions={notions}
          mastery={mastery.notions}
          plan={plan.plan}
          reviews={review.status === "ok" ? review.reviews : null}
          t={t}
        />
      )}
    </div>
  );
}

function ApiDown({ text }: { text: string }) {
  return (
    <div className="page">
      <p className="callout callout-warn" role="alert">
        <Icon name="alert" />
        {text}
      </p>
    </div>
  );
}
