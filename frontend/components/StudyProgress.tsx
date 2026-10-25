import GoalForm from "@/components/GoalForm";
import Icon from "@/components/Icon";
import type { StudySummary, TrophyRow } from "@/lib/api";
import { fmt, type Dict, type Lang } from "@/lib/i18n";
import { duration } from "@/lib/presence";

type Props = { summary: StudySummary; trophies: TrophyRow[]; t: Dict; lang: Lang };

// Presence mode on the progress page: today against the goal, the streak, 7 days, trophies.
export default function StudyProgress({ summary, trophies, t, lang }: Props) {
  const goalSeconds = summary.goalMinutes * 60;
  const share = Math.min(1, summary.todaySeconds / goalSeconds);
  const streak = summary.streakDays === 1 ? t.goal.streakOne : fmt(t.goal.streak, { count: summary.streakDays });
  const day = (date: string) => new Date(`${date}T12:00:00Z`).toLocaleDateString(lang, { weekday: "short", timeZone: "UTC" });
  return (
    <>
      <section className="card stack" aria-labelledby="goal-title">
        <div className="page-head">
          <h2 id="goal-title">{t.goal.title}</h2>
          <p className="muted">
            {fmt(t.goal.today, { time: duration(summary.todaySeconds), goal: summary.goalMinutes })}
            {summary.goalReachedToday && (
              <span className="badge badge-ok" style={{ marginLeft: "var(--space-2)" }}>
                <Icon name="check" />
                {t.goal.reached}
              </span>
            )}
          </p>
        </div>
        <div className="meter meter-goal" role="img" aria-label={`${Math.round(share * 100)} %`}>
          <span style={{ width: `${share * 100}%` }} />
        </div>
        <p className="row hint">
          <span>{streak}</span>
          <span>·</span>
          <span>{fmt(t.goal.total, { time: duration(summary.totalSeconds) })}</span>
        </p>
        <div>
          <h3 className="field-label">{t.goal.week}</h3>
          <ol className="week" aria-label={t.goal.week}>
            {summary.week.map((d) => (
              <li key={d.date} data-reached={d.reached} title={`${d.date}: ${duration(d.seconds)}`}>
                <span className="week-bar" style={{ height: `${Math.min(100, (d.seconds / goalSeconds) * 100)}%` }} />
                <span className="week-day">{day(d.date)}</span>
                <span className="sr-only">
                  {d.date}: {duration(d.seconds)}
                  {d.reached ? `, ${t.goal.reached}` : ""}
                </span>
              </li>
            ))}
          </ol>
        </div>
        <GoalForm minutes={summary.goalMinutes} t={t} />
        <p className="hint">{fmt(t.goal.zone, { zone: summary.timezone })}</p>
      </section>

      <section className="card stack" aria-labelledby="trophies-title">
        <h2 id="trophies-title">{t.trophies.title}</h2>
        <ul className="trophies">
          {trophies.map(({ code, obtainedAt }) => {
            const key = code as keyof Dict["trophies"]["names"];
            return (
              <li key={code} className="trophy" data-won={obtainedAt !== null}>
                <Icon name={obtainedAt ? "check" : "minus"} />
                <strong>{t.trophies.names[key] ?? code}</strong>
                <span className="hint">{t.trophies.rules[key]}</span>
                <span className="hint">
                  {obtainedAt ? fmt(t.trophies.won, { date: new Date(obtainedAt).toLocaleDateString(lang) }) : t.trophies.locked}
                </span>
              </li>
            );
          })}
        </ul>
      </section>
    </>
  );
}
