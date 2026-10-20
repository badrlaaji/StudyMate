import Link from "next/link";

import Icon, { LEVEL_ICONS } from "@/components/Icon";
import ScoreChart from "@/components/LazyScoreChart";
import type { Mastery, Notion, PlanRow } from "@/lib/api";
import { fmt, type Dict } from "@/lib/i18n";

type Level = keyof Dict["levels"];
const LEVELS: Level[] = ["MASTERED", "LEARNING", "WEAK", "NONE"];
const RING_RADIUS = 70;

type Props = { notions: Notion[]; mastery: Mastery[]; plan: PlanRow[]; t: Dict };

// Dashboard of one course: overall progress, what to review next, every notion.
export default function MasteryMap({ notions, mastery, plan, t }: Props) {
  const byId = new Map(mastery.map((m) => [m.notionId, m]));
  const levelOf = (id: string): Level => (byId.get(id)?.level as Level) ?? "NONE";
  const counts = Object.fromEntries(LEVELS.map((l) => [l, notions.filter((n) => levelOf(n.id) === l).length]));
  const total = notions.length;
  const share = total ? counts.MASTERED / total : 0;
  const names = new Map(notions.map((n) => [n.id, n.name]));
  const chart = mastery
    .filter((m) => names.has(m.notionId))
    .map((m) => ({ name: names.get(m.notionId) ?? m.notionId, average: m.average, count: m.count }));

  return (
    <>
      <section className="card hero" aria-label={t.map.distribution}>
        <ProgressRing share={share} t={t} />
        <div className="stack">
          <p className="muted">{fmt(t.map.ofNotions, { done: counts.MASTERED, total })}</p>
          <div className="distribution" aria-hidden="true">
            {LEVELS.filter((l) => counts[l] > 0).map((l) => (
              <span key={l} className={`seg-${l}`} style={{ flexGrow: counts[l] }} />
            ))}
          </div>
          <ul className="stats" style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {LEVELS.map((l) => (
              <li key={l} className={`stat stat-${l}`}>
                <span className="stat-value">{counts[l]}</span>
                <span className="stat-label">
                  <Icon name={LEVEL_ICONS[l]} />
                  {t.levels[l]}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="stack" aria-labelledby="next-title">
        <div className="page-head">
          <h2 id="next-title">{t.map.next}</h2>
          <p className="muted">{t.map.nextIntro}</p>
        </div>
        {plan.length === 0 ? (
          <p className="callout">
            <Icon name="info" />
            {t.map.nextEmpty}
          </p>
        ) : (
          <ol className="next-list">
            {plan.map((row, index) => (
              <li key={row.notion_id} className="next-card">
                <div className="row">
                  <span className="next-rank">#{index + 1}</span>
                  <LevelPill level="WEAK" t={t} />
                </div>
                <strong className="notion-name">{row.name}</strong>
                <Meter value={row.score} level="WEAK" label={fmt(t.map.average, { value: row.score.toFixed(1) })} />
                <div className="row">
                  {row.pages.slice(0, 3).map((page) => (
                    <PageChip key={page} page={page} t={t} />
                  ))}
                </div>
                <div className="notion-actions">
                  <Link className="btn btn-sm btn-primary" href={`/feynman?notion=${row.notion_id}`}>
                    <Icon name="feynman" />
                    {t.map.explain}
                  </Link>
                  <Link className="btn btn-sm btn-secondary" href="/quiz">
                    <Icon name="quiz" />
                    {t.map.quiz}
                  </Link>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      {chart.length > 0 && (
        <section className="card" aria-labelledby="chart-title">
          <div className="page-head" style={{ marginBottom: "var(--space-4)" }}>
            <h2 id="chart-title">{t.map.chart}</h2>
            <p className="muted">{t.map.chartIntro}</p>
          </div>
          <ScoreChart rows={chart} reviewLabel={t.map.reviewLine} masteredLabel={t.map.masteredLine} />
        </section>
      )}

      <section className="stack" aria-labelledby="all-title">
        <h2 id="all-title">{t.map.all}</h2>
        {groupBySection(notions).map(([section, items]) => (
          <div key={section}>
            <div className="section-title">
              <h3>{section}</h3>
              <span className="muted">{items.length}</span>
            </div>
            <ul className="notion-grid">
              {items.map((notion) => {
                const level = levelOf(notion.id);
                const m = byId.get(notion.id);
                return (
                  <li key={notion.id} className="notion">
                    <LevelPill level={level} t={t} />
                    <span className="notion-name">{notion.name}</span>
                    {m && (
                      <Meter
                        value={m.average}
                        level={level}
                        label={`${fmt(t.map.average, { value: m.average.toFixed(1) })} · ${fmt(t.map.scores, { count: m.count })}`}
                      />
                    )}
                    <div className="notion-actions">
                      <Link className="btn btn-sm btn-secondary" href={`/feynman?notion=${notion.id}`}>
                        {t.map.explain}
                      </Link>
                      <Link className="btn btn-sm btn-ghost" href="/quiz">
                        {t.map.quiz}
                      </Link>
                      <PageChip page={notion.pages[0]} t={t} />
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </section>

    </>
  );
}

function ProgressRing({ share, t }: { share: number; t: Dict }) {
  const length = 2 * Math.PI * RING_RADIUS;
  const percent = Math.round(share * 100);
  return (
    <div className="ring">
      <svg viewBox="0 0 168 168" aria-hidden="true">
        <circle className="ring-track" cx="84" cy="84" r={RING_RADIUS} fill="none" strokeWidth="14" />
        <circle
          className="ring-fill"
          cx="84"
          cy="84"
          r={RING_RADIUS}
          fill="none"
          strokeWidth="14"
          strokeDasharray={length}
          strokeDashoffset={length * (1 - share)}
          opacity={share > 0 ? 1 : 0}
        />
      </svg>
      <div className="ring-label">
        <span className="ring-value">{fmt(t.map.percent, { value: percent })}</span>
        <span className="ring-caption">{t.map.mastered}</span>
      </div>
    </div>
  );
}

function LevelPill({ level, t }: { level: Level; t: Dict }) {
  return (
    <span className={`pill pill-${level}`} style={{ justifySelf: "start" }}>
      <Icon name={LEVEL_ICONS[level]} />
      {t.levels[level]}
    </span>
  );
}

function Meter({ value, level, label }: { value: number; level: Level; label: string }) {
  return (
    <div className="stack" style={{ gap: "var(--space-1)" }}>
      <div className={`meter meter-${level}`} aria-hidden="true">
        <span style={{ width: `${(value / 5) * 100}%` }} />
      </div>
      <span className="hint">{label}</span>
    </div>
  );
}

// Opens the page in the study desk's book panel.
function PageChip({ page, t, label }: { page: number; t: Dict; label?: string }) {
  return (
    <Link className="chip" href={`/study?page=${page}`} title={fmt(t.study.openPage, { page })}>
      <Icon name="book" />
      {label ?? `p. ${page}`}
    </Link>
  );
}

function groupBySection(notions: Notion[]): [string, Notion[]][] {
  const groups = new Map<string, Notion[]>();
  for (const notion of notions) {
    groups.set(notion.section, [...(groups.get(notion.section) ?? []), notion]);
  }
  return [...groups.entries()];
}
