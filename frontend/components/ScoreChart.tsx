"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Row = { name: string; average: number; count: number };
const ROW_HEIGHT = 34;
const MAX_LABEL_WIDTH = 240;

// One series, one hue: bar length is the average; the 3 and 4 thresholds are lines.
export default function ScoreChart({
  rows,
  reviewLabel,
  masteredLabel,
}: {
  rows: Row[];
  reviewLabel: string;
  masteredLabel: string;
}) {
  const data = [...rows].sort((a, b) => a.average - b.average);
  const box = useRef<HTMLDivElement>(null);
  const [labelWidth, setLabelWidth] = useState(MAX_LABEL_WIDTH);

  // Notion names take at most 38 % of the width (phones keep room for the bars).
  useEffect(() => {
    const element = box.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setLabelWidth(Math.min(MAX_LABEL_WIDTH, Math.round(entry.contentRect.width * 0.38)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={box} style={{ width: "100%", height: 56 + data.length * ROW_HEIGHT }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 24, right: 16, bottom: 0, left: 8 }} barCategoryGap={8}>
          <CartesianGrid horizontal={false} stroke="var(--line)" />
          <XAxis
            type="number"
            domain={[0, 5]}
            ticks={[0, 1, 2, 3, 4, 5]}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={labelWidth}
            tick={{ fill: "var(--ink)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <ReferenceLine
            x={3}
            stroke="var(--weak)"
            strokeDasharray="4 4"
            label={{ value: reviewLabel, position: "top", fill: "var(--muted)", fontSize: 11 }}
          />
          <ReferenceLine
            x={4}
            stroke="var(--mastered)"
            strokeDasharray="4 4"
            label={{ value: masteredLabel, position: "top", fill: "var(--muted)", fontSize: 11 }}
          />
          <Tooltip
            cursor={{ fill: "var(--surface-2)" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="chart-tooltip">
                  <strong>{payload[0].payload.name}</strong>
                  <div className="muted">
                    {Number(payload[0].payload.average).toFixed(2)} / 5 · n = {payload[0].payload.count}
                  </div>
                </div>
              ) : null
            }
          />
          {/* minPointSize: a 0/5 average still shows a stub next to its name */}
          <Bar
            dataKey="average"
            fill="var(--accent)"
            radius={[0, 4, 4, 0]}
            barSize={14}
            minPointSize={3}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
