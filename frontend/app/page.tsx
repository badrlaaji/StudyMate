import Icon from "@/components/Icon";
import MasteryMap from "@/components/MasteryMap";
import { getMastery, getNotions, getPlan } from "@/lib/api";
import { getSession } from "@/lib/lang";

export default async function ProgressPage() {
  const { lang, t, course } = await getSession();
  if (!course) return <ApiDown text={t.study.error} />;
  const [notions, mastery, plan] = await Promise.all([
    getNotions(lang, course.id),
    getMastery(course.id),
    getPlan(lang, course.id),
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
      {mastery.status === "degraded" && (
        <p className="callout callout-warn" role="status">
          <Icon name="alert" />
          {t.map.degraded}
        </p>
      )}
      {notions.length === 0 ? (
        <p className="callout">
          <Icon name="info" />
          <span>
            {t.map.noNotions}
            <code className="code">uv run python -m course.add {course.id}</code>
          </span>
        </p>
      ) : (
        <MasteryMap notions={notions} mastery={mastery.notions} plan={plan.plan} t={t} />
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
