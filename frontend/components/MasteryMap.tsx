"use client";

import Link from "next/link";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Mastery, Notion, PlanRow } from "@/lib/api";
import type { Dict } from "@/lib/i18n";

type Level = keyof Dict["map"]["levels"];

// Colours come from the CSS variables (light and dark mode).
const COLORS: Record<Level, string> = {
  WEAK: "var(--weak)",
  LEARNING: "var(--learning)",
  MASTERED: "var(--mastered)",
  NONE: "var(--line)",
};

type Props = { notions: Notion[]; mastery: Mastery[]; plan: PlanRow[]; degraded: boolean; t: Dict };

export default function MasteryMap({ notions, mastery, plan, degraded, t }: Props) {
  const byId = new Map(mastery.map((m) => [m.notionId, m]));
  const names = new Map(notions.map((n) => [n.id, n.name]));
  const chart = mastery.map((m) => ({ name: names.get(m.notionId) ?? m.notionId, average: m.average, level: m.level as Level }));

  return (
    <>
      {degraded && <p className="muted" role="status">{t.map.degraded}</p>}
      <ul className="tiles">
        {notions.map((notion) => {
          const m = byId.get(notion.id);
          const level: Level = (m?.level as Level) ?? "NONE";
          return (
            <li key={notion.id} className="card tile" style={{ borderLeftColor: COLORS[level] }}>
              <strong>{notion.name}</strong>
              <p className="muted">
                {t.map.levels[level]}
                {m ? ` · ${t.map.average} ${m.average.toFixed(1)} / 5` : ""}
              </p>
              <p className="tile-actions">
                <Link href={`/feynman?notion=${notion.id}`}>{t.map.explain}</Link>
                <Link href="/quiz">{t.map.quiz}</Link>
                <a href={`/api/book.pdf#page=${notion.pages[0]}`} target="_blank" rel="noreferrer">
                  {t.map.read} p.{notion.pages[0]}
                </a>
              </p>
            </li>
          );
        })}
      </ul>

      <section className="card" aria-label={t.map.plan}>
        <h2>{t.map.plan}</h2>
        {plan.length === 0 ? (
          <p className="muted">{t.map.planEmpty}</p>
        ) : (
          <ol>
            {plan.map((row) => (
              <li key={row.notion_id}>
                <strong>{row.name}</strong> ({row.score.toFixed(1)} / 5) — {t.map.pages}{" "}
                {row.pages.slice(0, 3).map((page) => (
                  <a key={page} href={`/api/book.pdf#page=${page}`} target="_blank" rel="noreferrer" style={{ marginRight: "0.4rem" }}>
                    p.{page}
                  </a>
                ))}
                · <Link href="/quiz">{t.map.quiz}</Link>
              </li>
            ))}
          </ol>
        )}
      </section>

      {chart.length > 0 && (
        <section className="card" style={{ marginTop: "1rem" }}>
          <h2>{t.map.chart}</h2>
          <div style={{ width: "100%", height: 40 + chart.length * 32 }}>
            <ResponsiveContainer>
              <BarChart data={chart} layout="vertical" margin={{ left: 24, right: 24 }}>
                <XAxis type="number" domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} stroke="var(--muted)" />
                <YAxis type="category" dataKey="name" width={220} stroke="var(--muted)" />
                <Tooltip />
                <Bar dataKey="average" isAnimationActive={false}>
                  {chart.map((row) => (
                    <Cell key={row.name} fill={COLORS[row.level]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
    </>
  );
}
